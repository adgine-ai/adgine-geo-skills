#!/usr/bin/env python3
"""极简 Markdown → HTML 转换（零依赖，面向富文本平台：微信公众号/知乎等）。

只覆盖 GEO 文章常用语法：标题 / 加粗 / 斜体 / 行内代码 / 代码块 / 链接 /
图片 / 无序与有序列表 / 引用 / 段落 / 换行。微信只认内联样式外的纯标签结构，
这里输出干净的语义化标签即可；复杂排版（表格嵌套等）留待按需增强。

与扩展侧 core/html.ts 的 htmlToMarkdown 互为逆操作（轻量版），保持口径一致。
"""
import re


def _inline(text: str) -> str:
    """处理行内元素：代码 / 加粗 / 斜体 / 链接 / 图片。"""
    # 行内代码先占位，避免被加粗/斜体规则误伤
    codes: list[str] = []

    def _stash_code(m: re.Match) -> str:
        codes.append(m.group(1))
        return f"\x00CODE{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    # 图片 ![alt](src)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)",
        lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" />',
        text,
    )
    # 链接 [text](href)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    # 加粗 **x** / __x__
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    # 斜体 *x* / _x_
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", text)
    # 还原行内代码
    for i, c in enumerate(codes):
        text = text.replace(f"\x00CODE{i}\x00", f"<code>{c}</code>")
    return text


def markdown_to_html(md: str) -> str:
    if not md:
        return ""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    in_code = False
    code_lang = ""
    code_buf: list[str] = []
    list_type: str | None = None  # 'ul' | 'ol'
    para: list[str] = []

    def flush_para() -> None:
        if para:
            out.append(f"<p>{_inline(' '.join(para).strip())}</p>")
            para.clear()

    def flush_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while i < n:
        line = lines[i]
        # 代码块
        if line.strip().startswith("```"):
            if not in_code:
                flush_para(); flush_list()
                in_code = True
                code_lang = line.strip()[3:].strip()
                code_buf = []
            else:
                in_code = False
                cls = f' class="language-{code_lang}"' if code_lang else ""
                code = "\n".join(code_buf)
                code = (
                    code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                out.append(f"<pre><code{cls}>{code}</code></pre>")
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()
        # 空行
        if not stripped:
            flush_para(); flush_list()
            i += 1
            continue
        # 标题
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(); flush_list()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue
        # 引用
        if stripped.startswith(">"):
            flush_para(); flush_list()
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append(f"<blockquote><p>{_inline(' '.join(buf))}</p></blockquote>")
            continue
        # 无序列表
        if re.match(r"^[-*+]\s+", stripped):
            flush_para()
            if list_type != "ul":
                flush_list()
                out.append("<ul>")
                list_type = "ul"
            item = re.sub(r"^[-*+]\s+", "", stripped)
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue
        # 有序列表
        if re.match(r"^\d+\.\s+", stripped):
            flush_para()
            if list_type != "ol":
                flush_list()
                out.append("<ol>")
                list_type = "ol"
            item = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue
        # 普通段落行
        para.append(stripped)
        i += 1

    flush_para(); flush_list()
    return "\n".join(out)


if __name__ == "__main__":
    import sys

    src = sys.stdin.read()
    print(markdown_to_html(src))
