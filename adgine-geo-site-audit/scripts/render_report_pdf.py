#!/usr/bin/env python3
"""Render a GEO audit Markdown report to PDF."""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional


CHROME_PATHS = [
    "headless_shell",
    "headless_shell.exe",
    "chromium",
    "chromium.exe",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "chrome.exe",
    "msedge",
    "msedge.exe",
    "/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

PDF_EXPORT_PROMPT_RE = re.compile(
    r"^\s*(?:[-*]\s*)?需要我将本报告导出为\s*PDF\s*吗？(?:回复[“\"]导出\s*PDF[”\"]即可。?)?\s*$",
    re.MULTILINE,
)
PDF_COLLECT_RESULT_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?采集结果(?:\*\*)?\s*[:：].*$",
    re.MULTILINE,
)
AUDIT_TIME_CST_RE = re.compile(
    r"^(\s*(?:\*\*)?审计时间(?:\*\*)?\s*[:：]\s*[^\n]*?)\s+CST(\s*)$",
    re.MULTILINE,
)
VISIBILITY_NOTE = (
    "> 本章节基于当前运行模型采样，仅用于粗略观察品牌在 AI 回答中的可见性；"
    "该采样不参与 GEO 总分。如需更精确、持续的 AI 可见性数据，"
    "可注册 [adgine.ai](https://adgine.ai/) 进行持续监测。"
)
LEGACY_VISIBILITY_NOTES = (
    "> 本章节基于当前运行模型的隔离采样，不代表 ChatGPT、Claude、Perplexity 等线上产品的真实可见性结果；该采样不参与 GEO 总分。",
    "> 基于当前运行模型隔离采样，不代表 ChatGPT、Claude、Perplexity 等线上产品真实可见性；该采样不参与 GEO 总分。",
)
VISIBILITY_SCORE_RE = re.compile(
    r"\*\*AI 可见性采样分\*\*\s*[:：]\s*([^\n<]+)",
    re.MULTILINE,
)

DIMENSION_DISPLAY_LABELS = {
    "D1": "维度一：技术可达性",
    "D2": "维度二：内容质量",
    "D3": "维度三：品牌实体",
    "D4": "维度四：AI 可引用性",
    "D5": "维度五：AI 可推荐",
}


def absolute_path(path: Path) -> Path:
    """Return an absolute path without resolving symlinks such as /tmp on macOS."""
    return path.expanduser().absolute()


def _elapsed_since(started: float) -> float:
    return round(time.perf_counter() - started, 3)


def write_timing_file(
    output_path: Optional[str],
    *,
    input_path: Path,
    pdf_path: Path,
    engine: str,
    timings: dict[str, float],
    engine_errors: Optional[list[str]] = None,
) -> None:
    if not output_path:
        return
    payload = {
        "input": str(input_path),
        "output": str(pdf_path),
        "engine": engine,
        "timings": timings,
        "engine_errors": engine_errors or [],
    }
    Path(output_path).expanduser().absolute().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def chrome_candidate_paths() -> list[str]:
    candidates: list[str] = []
    env_path = os.environ.get("GEO_AUDIT_CHROME_PATH")
    if env_path:
        candidates.append(env_path)

    home = Path.home()
    local_app_data = os.environ.get("LOCALAPPDATA")
    program_files = [os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)")]
    playwright_patterns = [
        str(home / "Library/Caches/ms-playwright/chromium-*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        str(home / "Library/Caches/ms-playwright/chromium-*/chrome-*/Chromium.app/Contents/MacOS/Chromium"),
        str(home / "Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell"),
        str(home / "Library/Caches/ms-playwright/chromium-*/chrome-*/headless_shell"),
        str(home / ".cache/ms-playwright/chromium-*/chrome-*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"),
        str(home / ".cache/ms-playwright/chromium-*/chrome-*/Chromium.app/Contents/MacOS/Chromium"),
        str(home / ".cache/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell"),
        str(home / ".cache/ms-playwright/chromium-*/chrome-*/headless_shell"),
    ]
    if local_app_data:
        local_ms_playwright = Path(local_app_data) / "ms-playwright"
        playwright_patterns.extend([
            str(local_ms_playwright / "chromium-*" / "chrome-win" / "chrome.exe"),
            str(local_ms_playwright / "chromium-*" / "chrome-win" / "Chromium.exe"),
            str(local_ms_playwright / "chromium_headless_shell-*" / "chrome-win" / "headless_shell.exe"),
            str(local_ms_playwright / "chromium-*" / "chrome-win" / "headless_shell.exe"),
        ])
    for base in program_files:
        if not base:
            continue
        root = Path(base)
        candidates.extend([
            str(root / "Google/Chrome for Testing/Application/chrome.exe"),
            str(root / "Google/Chrome/Application/chrome.exe"),
            str(root / "Microsoft/Edge/Application/msedge.exe"),
            str(root / "Chromium/Application/chrome.exe"),
        ])
    for pattern in playwright_patterns:
        candidates.extend(sorted(glob.glob(pattern), reverse=True))

    candidates.extend(CHROME_PATHS)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def find_chrome() -> Optional[str]:
    for path in chrome_candidate_paths():
        found = shutil.which(path)
        if found:
            return found
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _popen_browser(cmd: list[str]) -> subprocess.Popen:
    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    return subprocess.Popen(cmd, **kwargs)


def _terminate_browser(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.communicate(timeout=3)
        return
    except Exception:
        pass

    try:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    try:
        process.communicate(timeout=2)
    except Exception:
        # Some macOS Chrome/headless_shell crashes can leave the child process
        # temporarily uninterruptible. Do not let cleanup block the exporter.
        pass


def chrome_pdf_ready(chrome_path: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="geo-audit-pdf-check-") as tmpdir:
        html_path = Path(tmpdir) / "check.html"
        pdf_path = Path(tmpdir) / "check.pdf"
        html_path.write_text("<!doctype html><html><body>PDF check</body></html>", encoding="utf-8")
        code, message = print_to_pdf(chrome_path, html_path, pdf_path, timeout_seconds=5)
        if code == 0:
            return True, message
        return False, message


def resolve_output_path(input_path: Path, output_arg: Optional[str]) -> Path:
    if output_arg:
        return absolute_path(Path(output_arg))
    return absolute_path(input_path.with_suffix(".pdf"))


def _extract_title(markdown_text: str, fallback: str = "GEO Audit Report") -> str:
    match = re.search(r"^#\s+(.+?)\s*$", markdown_text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def strip_pdf_export_prompt(markdown_text: str) -> str:
    cleaned = PDF_EXPORT_PROMPT_RE.sub("", markdown_text)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def normalize_audit_timezone(markdown_text: str) -> str:
    return AUDIT_TIME_CST_RE.sub(r"\1 Asia/Shanghai (UTC+08:00)\2", markdown_text)


def strip_legacy_visibility_detail_columns(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    trimming_visibility_table = False
    for line in lines:
        stripped = line.strip()
        if stripped == "| ID | 类型 | Prompt | 是否可见 | 排名 | 官网/站内来源 | 实体正确 | 幻觉 |":
            output.append("| ID | 类型 | Prompt | 是否可见 | 排名 | 官网/站内来源 |")
            trimming_visibility_table = True
            continue
        if trimming_visibility_table:
            if stripped.startswith("|") and set(stripped) <= {"|", "-", ":", " "}:
                output.append("|----|------|--------|------|---:|------|")
                continue
            if stripped.startswith("|"):
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                output.append("| " + " | ".join(cells[:6]) + " |")
                continue
            trimming_visibility_table = False
        output.append(line)
    return "\n".join(output)


def extract_ai_visibility_score(markdown_text: str) -> str:
    match = VISIBILITY_SCORE_RE.search(markdown_text)
    if not match:
        return "未执行"
    return match.group(1).replace("<br>", "").strip().rstrip()


def remove_legacy_visibility_score_heading(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == "## 可见性得分":
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("## GEO 总分:"):
                i += 1
            if i < len(lines) and lines[i].strip().startswith("## GEO 总分:"):
                output.append(lines[i])
                i += 1
            continue
        output.append(lines[i])
        i += 1
    return "\n".join(output)


def remove_geo_score_detail_lines(markdown_text: str) -> str:
    detail_labels = (
        "公开数据 GEO 分",
        "AI 可见性采样分",
        "最终综合分",
        "公开数据 GEO 原始分",
        "上限调整",
        "综合分公式",
    )
    lines = markdown_text.splitlines()
    output: list[str] = []
    in_geo_score = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## GEO 总分"):
            in_geo_score = True
            output.append(line)
            continue
        if in_geo_score and stripped.startswith("## ") and not stripped.startswith("## GEO 总分"):
            in_geo_score = False
        if in_geo_score and any(stripped.startswith(f"**{label}**") for label in detail_labels):
            continue
        output.append(line)
    return "\n".join(output)


def inject_d5_score_row(markdown_text: str, d5_score: str) -> str:
    # New reports use the Excel-derived 5-dimension table. AI visibility is a
    # separate reference section and must not be injected into the score table.
    if "维度五：AI 可推荐" in markdown_text or "AI 可见性采样参考" in markdown_text:
        return markdown_text
    lines = markdown_text.splitlines()
    output: list[str] = []
    in_score_table = False
    has_d5 = False
    comprehensive_weights = {
        "D1": "14%",
        "D2": "17.5%",
        "D3": "17.5%",
        "D4": "21%",
    }
    for line in lines:
        stripped = line.strip()
        was_d4_row = stripped.startswith("| D4 ")
        if stripped in {"| 维度 | 得分 | 权重 |", "| 维度 | 得分 | 综合权重 |"}:
            in_score_table = True
            has_d5 = False
            output.append("| 评估维度 | 得分 | 综合权重 |")
            continue
        if in_score_table and stripped.startswith("| D5 "):
            has_d5 = True
            line = line.replace("D5 AI 可推荐", DIMENSION_DISPLAY_LABELS["D5"])
            stripped = line.strip()
        if in_score_table and stripped.startswith("| D") and not stripped.startswith("| D5 "):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) == 3:
                dimension_key = cells[0].split(maxsplit=1)[0]
                if dimension_key in comprehensive_weights:
                    line = f"| {DIMENSION_DISPLAY_LABELS[dimension_key]} | {cells[1]} | {comprehensive_weights[dimension_key]} |"
                    stripped = line.strip()
        output.append(line)
        if in_score_table and was_d4_row and not has_d5 and d5_score != "未执行":
            output.append(f"| AI 可见性采样参考 | {d5_score} | 不参与总分 |")
            has_d5 = True
            continue
        if in_score_table and stripped and not stripped.startswith("|"):
            in_score_table = False
    return "\n".join(output)


def normalize_dimension_display_labels(markdown_text: str) -> str:
    replacements = {
        r"^## D1:\s*技术可达性": "## 维度一：技术可达性",
        r"^## D2:\s*内容质量": "## 维度二：内容质量",
        r"^## D3:\s*品牌实体": "## 维度三：品牌实体",
        r"^## D4:\s*AI\s*可引用性": "## 维度四：AI 可引用性",
        r"^## D5:\s*AI\s*可推荐": "## 维度五：AI 可推荐",
    }
    normalized = markdown_text
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.MULTILINE)
    normalized = re.sub(r"(\|\s*)D([1-4])\.(\d+)(\s*\|)", r"\1\2.\3\4", normalized)
    return normalized


def remove_visibility_section_score_rows(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| 公开数据 GEO 分 |") or stripped.startswith("| 最终综合分 |"):
            continue
        output.append(line)
    return "\n".join(output)


def normalize_numbered_list_continuations(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(\d+)\.\s+(.+?)\s*$", line)
        if not match:
            output.append(line)
            i += 1
            continue

        continuation: list[str] = []
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        while j < len(lines):
            stripped = lines[j].strip()
            if not stripped:
                break
            if (
                re.match(r"^\d+\.\s+", stripped)
                or stripped.startswith("#")
                or stripped.startswith("|")
                or stripped.startswith("- ")
                or stripped.startswith("```")
            ):
                break
            continuation.append(stripped)
            j += 1
        if continuation:
            item_text = re.sub(r"\s{2,}$", "", match.group(2)).strip()
            output.append(f"{match.group(1)}. {item_text}: {' '.join(continuation)}")
            k = j
            while k < len(lines) and not lines[k].strip():
                k += 1
            i = k if k < len(lines) and re.match(r"^\d+\.\s+", lines[k].strip()) else j
            continue

        output.append(line)
        i += 1
    return "\n".join(output)


def prepare_markdown_for_pdf(markdown_text: str) -> str:
    d5_score = extract_ai_visibility_score(markdown_text)
    cleaned = strip_pdf_export_prompt(markdown_text)
    cleaned = normalize_audit_timezone(cleaned)
    cleaned = PDF_COLLECT_RESULT_RE.sub("", cleaned)
    cleaned = re.sub(r"^##\s*演示说明\s*$", "## 报告说明", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("Agent 模拟可见性测试", "AI 可见性采样参考")
    cleaned = cleaned.replace("## D6: AI 可见性采样测试", "## AI 可见性采样参考")
    cleaned = cleaned.replace("## D5: AI 可见性采样测试", "## AI 可见性采样参考")
    cleaned = cleaned.replace("## AI 可见性采样测试", "## AI 可见性采样参考")
    cleaned = cleaned.replace("Agent 模拟可见性分", "AI 可见性采样分")
    cleaned = cleaned.replace("Agent 可见性总分", "AI 可见性采样分")
    cleaned = cleaned.replace("Agent 可见性", "AI 可见性采样")
    cleaned = cleaned.replace("agent 模型", "运行模型")
    for legacy_note in LEGACY_VISIBILITY_NOTES:
        cleaned = cleaned.replace(legacy_note, VISIBILITY_NOTE)
    cleaned = cleaned.replace("| 幻觉率 |", "| 事实错误率 |")
    cleaned = cleaned.replace(
        "可在 https://adgine.ai/ 注册后使用",
        "可在 [adgine.ai](https://adgine.ai/) 注册后使用",
    )
    cleaned = strip_legacy_visibility_detail_columns(cleaned)
    cleaned = remove_legacy_visibility_score_heading(cleaned)
    cleaned = remove_geo_score_detail_lines(cleaned)
    cleaned = inject_d5_score_row(cleaned, d5_score)
    cleaned = normalize_dimension_display_labels(cleaned)
    cleaned = remove_visibility_section_score_rows(cleaned)
    cleaned = normalize_numbered_list_continuations(cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def _inline_markdown_to_html(text: str) -> str:
    code_tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{html.escape(match.group(1))}</code>")
        return f"@@GEO_CODE_{len(code_tokens) - 1}@@"

    text = re.sub(r"`([^`\n]+)`", stash_code, text)
    rendered = html.escape(text)

    def render_link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2)
        return f'<a href="{href}">{label}</a>'

    rendered = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", render_link, rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", rendered)

    for i, token in enumerate(code_tokens):
        rendered = rendered.replace(f"@@GEO_CODE_{i}@@", token)
    return rendered


def _fallback_markdown_to_html(markdown_text: str) -> str:
    """Small fallback renderer for tests and clear errors when markdown is absent."""
    lines = markdown_text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            text = stripped[level:].strip()
            out.append(f"<h{level}>{_inline_markdown_to_html(text)}</h{level}>")
            i += 1
            continue
        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            code_text = html.escape("\n".join(code_lines))
            out.append(f"<pre><code>{code_text}</code></pre>")
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= {"|", "-", ":", " "}:
            headers = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append("<table><thead><tr>")
            out.extend(f"<th>{_inline_markdown_to_html(cell)}</th>" for cell in headers)
            out.append("</tr></thead><tbody>")
            for row in rows:
                out.append("<tr>")
                out.extend(f"<td>{_inline_markdown_to_html(cell)}</td>" for cell in row)
                out.append("</tr>")
            out.append("</tbody></table>")
            continue
        if stripped.startswith("- "):
            out.append("<ul>")
            while i < len(lines) and lines[i].strip().startswith("- "):
                out.append(f"<li>{_inline_markdown_to_html(lines[i].strip()[2:].strip())}</li>")
                i += 1
            out.append("</ul>")
            continue
        if re.match(r"^\d+\.\s+", stripped):
            out.append("<ol>")
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip()).strip()
                out.append(f"<li>{_inline_markdown_to_html(item)}</li>")
                i += 1
            out.append("</ol>")
            continue
        out.append(f"<p>{_inline_markdown_to_html(stripped)}</p>")
        i += 1
    return "\n".join(out)


def markdown_body_to_html(markdown_text: str) -> str:
    try:
        import markdown as markdown_lib  # type: ignore
    except ImportError:
        return _fallback_markdown_to_html(markdown_text)

    return markdown_lib.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )


def render_markdown_to_html(markdown_text: str, title: Optional[str] = None) -> str:
    markdown_text = prepare_markdown_for_pdf(markdown_text)
    title = title or _extract_title(markdown_text)
    body = markdown_body_to_html(markdown_text)
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escaped_title}</title>
  <style>
    @page {{
      size: A4;
      margin: 16mm 14mm;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC",
        "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      font-size: 13px;
      line-height: 1.55;
      margin: 0;
    }}
    h1, h2, h3 {{
      color: #0f172a;
      line-height: 1.25;
      margin: 1.4em 0 0.55em;
      page-break-after: avoid;
    }}
    h1 {{
      font-size: 26px;
      margin-top: 0;
      padding-bottom: 8px;
      border-bottom: 2px solid #e5e7eb;
    }}
    h2 {{
      font-size: 18px;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 4px;
    }}
    h3 {{
      font-size: 15px;
    }}
    p, ul, ol {{
      margin: 0.4em 0 0.9em;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 18px;
      page-break-inside: auto;
      font-size: 11px;
    }}
    tr {{
      page-break-inside: avoid;
      page-break-after: auto;
    }}
    th, td {{
      border: 1px solid #d1d5db;
      padding: 6px 7px;
      vertical-align: top;
      word-break: break-word;
    }}
    th {{
      background: #f3f4f6;
      font-weight: 700;
    }}
    code {{
      background: #f3f4f6;
      border-radius: 4px;
      padding: 1px 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.92em;
    }}
    pre {{
      background: #0f172a;
      color: #f8fafc;
      padding: 12px;
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    blockquote {{
      margin: 12px 0;
      padding-left: 12px;
      border-left: 4px solid #cbd5e1;
      color: #475569;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
    }}
    .status-pass,
    .status-warn,
    .status-fail,
    .status-error {{
      display: inline-block;
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 10px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .status-pass {{
      background: #ecfdf5;
      color: #047857;
    }}
    .status-warn {{
      background: #fffbeb;
      color: #b45309;
    }}
    .status-fail {{
      background: #fef2f2;
      color: #b91c1c;
    }}
    .status-error {{
      background: #fef2f2;
      color: #7f1d1d;
    }}
    td.score-excellent {{ color: #047857; font-weight: 700; }}
    td.score-good {{ color: #0369a1; font-weight: 700; }}
    td.score-fair {{ color: #b45309; font-weight: 700; }}
    td.score-poor {{ color: #c2410c; font-weight: 700; }}
    td.score-critical {{ color: #b91c1c; font-weight: 700; }}
  </style>
</head>
<body>
{body}
<script>
(function() {{
  function scoreClass(n) {{
    if (n >= 80) return 'score-excellent';
    if (n >= 65) return 'score-good';
    if (n >= 50) return 'score-fair';
    if (n >= 35) return 'score-poor';
    return 'score-critical';
  }}

  document.querySelectorAll('td').forEach(function(td) {{
    var text = td.textContent.trim();
    function replaceWithBadge(className) {{
      td.textContent = '';
      var span = document.createElement('span');
      span.className = className;
      span.textContent = text;
      td.appendChild(span);
    }}
    if (/^✅\\s*PASS/.test(text)) replaceWithBadge('status-pass');
    else if (/^⚠️?\\s*WARN/.test(text)) replaceWithBadge('status-warn');
    else if (/^❌\\s*FAIL/.test(text)) replaceWithBadge('status-fail');
    else if (/^🔴\\s*ERROR/.test(text)) replaceWithBadge('status-error');

    var match = text.match(/^(\\d{{1,3}}(?:\\.\\d+)?)\\s*\\/\\s*100$/);
    if (match) td.classList.add(scoreClass(parseFloat(match[1])));
  }});
}})();
</script>
</body>
</html>
"""


def write_html(markdown_path: Path, html_text: str, keep_html: bool) -> Path:
    if keep_html:
        html_path = absolute_path(markdown_path.with_suffix(".html"))
        html_path.write_text(html_text, encoding="utf-8")
        return html_path
    fd, tmp_name = tempfile.mkstemp(prefix="geo-audit-report-", suffix=".html")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html_text)
    return Path(tmp_name).resolve()


def print_to_pdf(
    chrome_path: str,
    html_path: Path,
    output_path: Path,
    *,
    timeout_seconds: int = 60,
) -> tuple[int, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="geo-audit-crash-dumps-") as crash_dir, tempfile.TemporaryDirectory(prefix="geo-audit-chrome-profile-") as profile_dir:
        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--disable-background-networking",
            "--disable-breakpad",
            "--disable-crash-reporter",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-sync",
            "--no-first-run",
            "--noerrdialogs",
            "--no-sandbox",
            "--run-all-compositor-stages-before-draw",
            "--no-pdf-header-footer",
            "--print-to-pdf-no-header",
            "--virtual-time-budget=5000",
            f"--crash-dumps-dir={crash_dir}",
            f"--user-data-dir={profile_dir}",
            f"--print-to-pdf={str(output_path)}",
            html_path.as_uri(),
        ]
        try:
            process = _popen_browser(cmd)
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _terminate_browser(process)
            return 124, f"Chrome timed out after {exc.timeout} seconds while printing PDF."
        except OSError as exc:
            return 126, f"Chrome could not be started: {exc}"
    combined = "\n".join(part for part in [stdout, stderr] if part)
    if process.returncode != 0:
        message = combined.strip()
        if not message:
            message = (
                f"Chrome exited with code {process.returncode} without stderr/stdout. "
                "It may be unavailable, blocked by the OS, or blocked by the execution sandbox."
            )
        return process.returncode or 1, message
    if not output_path.exists() or output_path.stat().st_size == 0:
        return 1, "Chrome completed but did not create a non-empty PDF."
    return 0, combined.strip()


def install_playwright(timeout_seconds: int = 900) -> tuple[int, str]:
    commands = [
        [sys.executable, "-m", "pip", "install", "playwright"],
        [sys.executable, "-m", "playwright", "install", "chromium"],
    ]
    output_parts: list[str] = []
    for command in commands:
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return 124, f"{' '.join(command)} timed out after {exc.timeout} seconds."
        except OSError as exc:
            return 126, f"{' '.join(command)} could not be started: {exc}"
        output_parts.append("\n".join(part for part in [result.stdout, result.stderr] if part).strip())
        if result.returncode != 0:
            message = output_parts[-1] or f"{' '.join(command)} exited with {result.returncode}."
            return result.returncode or 1, message
    return 0, "\n".join(part for part in output_parts if part)


def print_to_pdf_with_playwright(
    html_path: Path,
    output_path: Path,
    *,
    executable_path: Optional[str] = None,
    timeout_seconds: int = 60,
) -> tuple[int, str]:
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        return 127, f"Playwright is not installed in this Python environment: {exc}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    browser = None
    try:
        with sync_playwright() as playwright:
            launch_kwargs: dict[str, Any] = {
                "headless": True,
                "args": [
                    "--disable-background-networking",
                    "--disable-breakpad",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-sync",
                    "--no-first-run",
                    "--no-sandbox",
                ],
                "timeout": timeout_seconds * 1000,
            }
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            browser = playwright.chromium.launch(
                **launch_kwargs,
            )
            page = browser.new_page()
            page.goto(html_path.as_uri(), wait_until="load", timeout=timeout_seconds * 1000)
            page.emulate_media(media="print")
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
            )
            browser.close()
            browser = None
    except PlaywrightError as exc:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        return 1, f"Playwright PDF export failed: {exc}"
    except Exception as exc:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        return 1, f"Playwright PDF export failed: {exc}"

    if not output_path.exists() or output_path.stat().st_size == 0:
        return 1, "Playwright completed but did not create a non-empty PDF."
    return 0, "PDF generated with Playwright Chromium."


def _is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s|:\-]+\|?\s*$", line)) and "-" in line


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _reportlab_inline(text: str) -> str:
    status_replacements = [
        ("✅ PASS", "PASS"),
        ("⚠️ WARN", "WARN"),
        ("⚠ WARN", "WARN"),
        ("❌ FAIL", "FAIL"),
        ("🔴 ERROR", "ERROR"),
        ("✅", "是"),
        ("❌", "否"),
        ("⚠️", "注意"),
        ("⚠", "注意"),
    ]
    for old, new in status_replacements:
        text = text.replace(old, new)
    code_tokens: list[str] = []
    link_tokens: list[str] = []

    def stash_link(match: re.Match[str]) -> str:
        label = html.escape(match.group(1))
        href = html.escape(match.group(2), quote=True)
        link_tokens.append(f'<a href="{href}" color="#2563eb"><u>{label}</u></a>')
        return f"@@GEO_RL_LINK_{len(link_tokens) - 1}@@"

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(html.escape(match.group(1)))
        return f"@@GEO_RL_CODE_{len(code_tokens) - 1}@@"

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", stash_link, text)
    text = re.sub(r"`([^`\n]+)`", stash_code, text)
    rendered = html.escape(text)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", rendered)
    for i, token in enumerate(code_tokens):
        rendered = rendered.replace(
            f"@@GEO_RL_CODE_{i}@@",
            f'<font name="Courier">{token}</font>',
        )
    for i, token in enumerate(link_tokens):
        rendered = rendered.replace(f"@@GEO_RL_LINK_{i}@@", token)
    return rendered


def _table_col_widths(headers: list[str], total_width: float) -> list[float]:
    weights: list[float] = []
    for header in headers:
        if "Prompt" in header or "说明" in header or "发现" in header or "建议" in header:
            weights.append(2.4)
        elif "URL" in header or "来源" in header:
            weights.append(1.7)
        elif header in {"#", "权重", "状态", "排名"}:
            weights.append(0.8)
        else:
            weights.append(1.15)
    total = sum(weights) or 1
    return [total_width * weight / total for weight in weights]


def _existing_font_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if path and Path(path).exists()]


def _register_reportlab_fonts(pdfmetrics: Any, TTFont: Any, UnicodeCIDFont: Any) -> tuple[str, str]:
    font_env = os.environ.get("GEO_AUDIT_PDF_FONT_PATH")
    windir = os.environ.get("WINDIR", r"C:\Windows")
    font_families = [
        {
            "normal": _existing_font_paths([
                str(Path("/System/Library/Fonts/STHeiti Light.ttc")),
                str(Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
            ]),
            "bold": _existing_font_paths([
                str(Path("/System/Library/Fonts/STHeiti Medium.ttc")),
                str(Path("/System/Library/Fonts/STHeiti Light.ttc")),
                str(Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
            ]),
        },
        {
            "normal": _existing_font_paths([
                str(Path(windir) / "Fonts" / "msyh.ttc"),
                str(Path(windir) / "Fonts" / "simhei.ttf"),
                str(Path(windir) / "Fonts" / "simsun.ttc"),
                str(Path(windir) / "Fonts" / "arialuni.ttf"),
            ]),
            "bold": _existing_font_paths([
                str(Path(windir) / "Fonts" / "msyhbd.ttc"),
                str(Path(windir) / "Fonts" / "msyh.ttc"),
                str(Path(windir) / "Fonts" / "simhei.ttf"),
                str(Path(windir) / "Fonts" / "simsun.ttc"),
            ]),
        },
        {
            "normal": _existing_font_paths([
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.otf",
                "/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Regular.otf",
            ]),
            "bold": _existing_font_paths([
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.otf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.otf",
                "/usr/share/fonts/opentype/source-han-sans/SourceHanSansCN-Bold.otf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]),
        },
    ]
    if font_env:
        font_families.insert(0, {"normal": _existing_font_paths([font_env]), "bold": _existing_font_paths([font_env])})

    for family in font_families:
        if not family["normal"]:
            continue
        normal_path = family["normal"][0]
        bold_path = (family["bold"] or family["normal"])[0]
        try:
            registered = set(pdfmetrics.getRegisteredFontNames())
            if "GeoAuditSans" not in registered:
                pdfmetrics.registerFont(TTFont("GeoAuditSans", normal_path, subfontIndex=0))
            if "GeoAuditSans-Bold" not in registered:
                pdfmetrics.registerFont(TTFont("GeoAuditSans-Bold", bold_path, subfontIndex=0))
            pdfmetrics.registerFontFamily(
                "GeoAuditSans",
                normal="GeoAuditSans",
                bold="GeoAuditSans-Bold",
                italic="GeoAuditSans",
                boldItalic="GeoAuditSans-Bold",
            )
            return "GeoAuditSans", "GeoAuditSans-Bold"
        except Exception:
            continue

    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        pdfmetrics.registerFontFamily(
            "STSong-Light",
            normal="STSong-Light",
            bold="STSong-Light",
            italic="STSong-Light",
            boldItalic="STSong-Light",
        )
    except Exception:
        pass
    return "STSong-Light", "STSong-Light"


def _render_markdown_to_pdf_reportlab(markdown_text: str, output_path: Path) -> tuple[int, str]:
    try:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import mm  # type: ignore
        from reportlab.pdfbase import pdfmetrics  # type: ignore
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont  # type: ignore
        from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
        from reportlab.platypus import (  # type: ignore
            ListFlowable,
            ListItem,
            PageBreak,
            Paragraph,
            Preformatted,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        return 6, f"ReportLab renderer is unavailable: {exc}. Install dependencies with `pip install -r requirements.txt`."

    markdown_text = prepare_markdown_for_pdf(markdown_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=_extract_title(markdown_text),
    )
    base = getSampleStyleSheet()
    normal_font, bold_font = _register_reportlab_fonts(pdfmetrics, TTFont, UnicodeCIDFont)
    normal = ParagraphStyle(
        "GeoNormal",
        parent=base["Normal"],
        fontName=normal_font,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#111827"),
        spaceAfter=6,
        wordWrap="CJK",
    )
    h1 = ParagraphStyle(
        "GeoH1",
        parent=normal,
        fontName=bold_font,
        fontSize=21,
        leading=27,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12,
    )
    h2 = ParagraphStyle(
        "GeoH2",
        parent=normal,
        fontName=bold_font,
        fontSize=14.5,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "GeoH3",
        parent=normal,
        fontName=bold_font,
        fontSize=11.5,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=4,
    )
    table_text = ParagraphStyle(
        "GeoTableText",
        parent=normal,
        fontSize=7.7,
        leading=10.2,
        spaceAfter=0,
    )
    code = ParagraphStyle(
        "GeoCode",
        parent=base["Code"],
        fontName="Courier",
        fontSize=7.2,
        leading=9,
        backColor=colors.HexColor("#f3f4f6"),
        borderPadding=5,
        wordWrap="CJK",
    )
    styles = {1: h1, 2: h2, 3: h3}

    def paragraph(text: str, style: ParagraphStyle = normal) -> Paragraph:
        return Paragraph(_reportlab_inline(text), style)

    def paragraph_block(block_lines: list[str], style: ParagraphStyle = normal) -> Paragraph:
        rendered_lines = [_reportlab_inline(line.rstrip()) for line in block_lines]
        return Paragraph("<br/>".join(rendered_lines), style)

    story: list[Any] = []
    lines = markdown_text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue
        if stripped == "---":
            story.append(Spacer(1, 6))
            i += 1
            continue
        if stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 3)
            text = stripped[level:].strip()
            story.append(paragraph(text, styles[level]))
            story.append(Spacer(1, 2))
            i += 1
            continue
        if stripped.startswith("```"):
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            story.append(Preformatted("\n".join(code_lines), code))
            story.append(Spacer(1, 6))
            continue
        if (
            stripped.startswith("|")
            and i + 1 < len(lines)
            and _is_table_separator(lines[i + 1])
        ):
            headers = _split_table_row(stripped)
            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_table_row(lines[i]))
                i += 1
            column_count = max([len(headers), *(len(row) for row in rows)] or [1])
            headers = headers + [""] * (column_count - len(headers))
            data: list[list[Any]] = [[paragraph(cell, table_text) for cell in headers]]
            for row in rows:
                row = row + [""] * (column_count - len(row))
                data.append([paragraph(cell, table_text) for cell in row[:column_count]])
            table = Table(
                data,
                colWidths=_table_col_widths(headers, doc.width),
                repeatRows=1,
                splitByRow=1,
            )
            table_commands: list[tuple[Any, ...]] = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
            if "状态" in headers:
                status_col = headers.index("状态")
                for row_number, row in enumerate(rows, start=1):
                    status_text = (row + [""] * column_count)[status_col]
                    if "PASS" in status_text:
                        bg, fg = "#ecfdf5", "#047857"
                    elif "WARN" in status_text:
                        bg, fg = "#fffbeb", "#b45309"
                    elif "FAIL" in status_text:
                        bg, fg = "#fef2f2", "#b91c1c"
                    elif "ERROR" in status_text:
                        bg, fg = "#fef2f2", "#7f1d1d"
                    else:
                        continue
                    table_commands.extend([
                        ("BACKGROUND", (status_col, row_number), (status_col, row_number), colors.HexColor(bg)),
                        ("TEXTCOLOR", (status_col, row_number), (status_col, row_number), colors.HexColor(fg)),
                    ])
            table.setStyle(
                TableStyle(table_commands)
            )
            story.append(table)
            story.append(Spacer(1, 8))
            continue
        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(ListItem(paragraph(lines[i].strip()[2:].strip(), normal)))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=12))
            story.append(Spacer(1, 4))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines):
                current = lines[i].strip()
                if not re.match(r"^\d+\.\s+", current):
                    break
                item_lines = [re.sub(r"^\d+\.\s+", "", current).strip()]
                i += 1
                while i < len(lines):
                    continuation = lines[i].strip()
                    if not continuation:
                        break
                    if (
                        re.match(r"^\d+\.\s+", continuation)
                        or continuation.startswith("#")
                        or continuation.startswith("|")
                        or continuation.startswith("- ")
                        or continuation.startswith("```")
                    ):
                        break
                    item_lines.append(continuation)
                    i += 1
                items.append(ListItem(paragraph_block(item_lines, normal)))
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i >= len(lines) or not re.match(r"^\d+\.\s+", lines[i].strip()):
                    break
            story.append(ListFlowable(items, bulletType="1", bulletFormat="%s.", leftIndent=14))
            story.append(Spacer(1, 4))
            continue

        paragraph_lines = [raw.rstrip()]
        i += 1
        while i < len(lines):
            candidate_raw = lines[i]
            candidate = candidate_raw.strip()
            if (
                not candidate
                or candidate.startswith("#")
                or candidate.startswith("|")
                or candidate.startswith("- ")
                or candidate.startswith("```")
                or candidate == "---"
                or re.match(r"^\d+\.\s+", candidate)
            ):
                break
            paragraph_lines.append(candidate_raw.rstrip())
            i += 1
        should_keep_breaks = any(line.endswith("  ") or line.strip().startswith("**") for line in paragraph_lines)
        if should_keep_breaks:
            story.append(paragraph_block(paragraph_lines, normal))
        else:
            story.append(paragraph(" ".join(line.strip() for line in paragraph_lines), normal))

    try:
        doc.build(story or [paragraph("GEO Audit Report", normal)])
    except Exception as exc:
        return 6, f"ReportLab renderer failed: {exc}"
    if not output_path.exists() or output_path.stat().st_size == 0:
        return 6, "ReportLab renderer completed but did not create a non-empty PDF."
    return 0, "PDF generated with ReportLab."


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render a GEO audit Markdown report to PDF.")
    parser.add_argument("report_md", help="Path to the UTF-8 Markdown report")
    parser.add_argument("--output", "-o", help="Output PDF path. Defaults to report_md with .pdf suffix")
    parser.add_argument("--keep-html", action="store_true", help="Keep the intermediate HTML next to the Markdown file")
    default_engine = os.environ.get("GEO_AUDIT_PDF_ENGINE", "reportlab").lower()
    if default_engine not in {"auto", "playwright", "chrome", "reportlab"}:
        default_engine = "reportlab"
    parser.add_argument(
        "--engine",
        choices=["auto", "playwright", "chrome", "reportlab"],
        default=default_engine,
        help="PDF engine to use. Default reportlab avoids launching Chrome; auto tries ReportLab, Playwright, then Chrome.",
    )
    parser.add_argument(
        "--install-playwright",
        action="store_true",
        help="Install Playwright and Chromium into the current Python environment before rendering.",
    )
    parser.add_argument(
        "--timings-output",
        help="Optional JSON path for PDF rendering timings, for debugging slow exports.",
    )
    args = parser.parse_args(argv)
    module_started = time.perf_counter()
    timings: dict[str, float] = {}

    input_path = absolute_path(Path(args.report_md))
    if not input_path.exists():
        print(f"ERROR: Markdown report not found: {input_path}", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"ERROR: Markdown report is not a file: {input_path}", file=sys.stderr)
        return 2

    output_path = resolve_output_path(input_path, args.output)
    stage_started = time.perf_counter()
    markdown_text = input_path.read_text(encoding="utf-8")
    timings["markdown_read_seconds"] = _elapsed_since(stage_started)
    stage_started = time.perf_counter()
    html_text = render_markdown_to_html(markdown_text)
    timings["markdown_to_html_seconds"] = _elapsed_since(stage_started)
    stage_started = time.perf_counter()
    html_path = write_html(input_path, html_text, args.keep_html)
    timings["html_write_seconds"] = _elapsed_since(stage_started)

    if args.install_playwright and args.engine in {"auto", "playwright"}:
        stage_started = time.perf_counter()
        install_code, install_message = install_playwright()
        timings["playwright_install_seconds"] = _elapsed_since(stage_started)
        if install_code != 0:
            print(f"ERROR: Playwright installation failed: {install_message}", file=sys.stderr)
            if not args.keep_html:
                try:
                    html_path.unlink(missing_ok=True)
                except OSError:
                    pass
            return 4

    def cleanup_html() -> None:
        if not args.keep_html:
            try:
                html_path.unlink(missing_ok=True)
            except OSError:
                pass

    engine_errors: list[str] = []
    reportlab_attempted = False

    if args.engine in {"auto", "reportlab"}:
        reportlab_attempted = True
        stage_started = time.perf_counter()
        fallback_code, fallback_message = _render_markdown_to_pdf_reportlab(markdown_text, output_path)
        timings["reportlab_pdf_seconds"] = _elapsed_since(stage_started)
        if fallback_code == 0:
            timings["total_pdf_module_seconds"] = _elapsed_since(module_started)
            write_timing_file(
                args.timings_output,
                input_path=input_path,
                pdf_path=output_path,
                engine="reportlab",
                timings=timings,
                engine_errors=engine_errors,
            )
            print(f"PDF written to {output_path}")
            if args.keep_html:
                print(f"HTML written to {html_path}")
            else:
                cleanup_html()
            return 0
        engine_errors.append(fallback_message)
        if args.engine == "reportlab":
            cleanup_html()
            print(f"ERROR: PDF generation failed: {fallback_message}", file=sys.stderr)
            return 5

    try:
        if args.engine in {"auto", "playwright"}:
            stage_started = time.perf_counter()
            code, message = print_to_pdf_with_playwright(
                html_path,
                output_path,
                executable_path=os.environ.get("GEO_AUDIT_PLAYWRIGHT_EXECUTABLE_PATH"),
            )
            timings["playwright_pdf_seconds"] = _elapsed_since(stage_started)
            if code == 0:
                timings["total_pdf_module_seconds"] = _elapsed_since(module_started)
                write_timing_file(
                    args.timings_output,
                    input_path=input_path,
                    pdf_path=output_path,
                    engine="playwright",
                    timings=timings,
                    engine_errors=engine_errors,
                )
                print(f"PDF written to {output_path}")
                if args.keep_html:
                    print(f"HTML written to {html_path}")
                else:
                    cleanup_html()
                return 0
            engine_errors.append(message)

        if args.engine == "playwright":
            cleanup_html()
            print(f"ERROR: PDF generation failed: {engine_errors[-1]}", file=sys.stderr)
            return 5

        if args.engine in {"auto", "chrome"}:
            stage_started = time.perf_counter()
            chrome_path = find_chrome()
            timings["chrome_lookup_seconds"] = _elapsed_since(stage_started)
            if chrome_path:
                stage_started = time.perf_counter()
                code, message = print_to_pdf(chrome_path, html_path, output_path)
                timings["chrome_pdf_seconds"] = _elapsed_since(stage_started)
                if code == 0:
                    timings["total_pdf_module_seconds"] = _elapsed_since(module_started)
                    write_timing_file(
                        args.timings_output,
                        input_path=input_path,
                        pdf_path=output_path,
                        engine="chrome",
                        timings=timings,
                        engine_errors=engine_errors,
                    )
                    print(f"PDF written to {output_path}")
                    if args.keep_html:
                        print(f"HTML written to {html_path}")
                    else:
                        cleanup_html()
                    return 0
                engine_errors.append(f"Chrome PDF export failed: {message}")
            else:
                engine_errors.append("Chrome/Chromium executable not found.")
    finally:
        cleanup_html()

    if args.engine == "chrome":
        print(f"ERROR: PDF generation failed: {engine_errors[-1] if engine_errors else 'Chrome export unavailable.'}", file=sys.stderr)
        return 5

    fallback_message = engine_errors[0] if reportlab_attempted and engine_errors else ""
    if not reportlab_attempted:
        stage_started = time.perf_counter()
        fallback_code, fallback_message = _render_markdown_to_pdf_reportlab(markdown_text, output_path)
        timings["reportlab_pdf_seconds"] = _elapsed_since(stage_started)
        if fallback_code == 0:
            timings["total_pdf_module_seconds"] = _elapsed_since(module_started)
            write_timing_file(
                args.timings_output,
                input_path=input_path,
                pdf_path=output_path,
                engine="reportlab",
                timings=timings,
                engine_errors=engine_errors,
            )
            if engine_errors:
                print(f"WARNING: {'; '.join(engine_errors)} Used ReportLab renderer.", file=sys.stderr)
            print(f"PDF written to {output_path}")
            if args.keep_html:
                print(f"HTML written to {html_path}")
            return 0

    if engine_errors:
        print(f"ERROR: PDF generation failed: {'; '.join(engine_errors)}", file=sys.stderr)
        print(f"ERROR: {fallback_message}", file=sys.stderr)
        return 5

    print(f"ERROR: PDF generation failed: {fallback_message}", file=sys.stderr)
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
