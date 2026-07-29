#!/usr/bin/env python3
"""把文章发布到用户本地浏览器已登录的社交媒体平台草稿箱。

通过 Adgine 同步助手 Chrome 扩展完成（扩展复用用户本地登录态调各平台后台）。

两种内容来源：
  --content-id <uuid>            — 从 GEO 云端内容库拉取（需 GEO_API_KEY）
  --title <t> --content-file <f> — 直接用本地 markdown/html 文件

平台：
  --platform zhihu|weixin|baijiahao|toutiao|csdn|xiaohongshu|...

示例：
  python3 scripts/save_draft.py --platform zhihu --title "我的文章" --content-file ./a.md
  python3 scripts/save_draft.py --platform weixin --content-id <uuid>

运行前提（手机端/纯云端不可用）：
  - 本机 Chrome 已安装 Adgine 同步助手扩展并登录目标平台
  - 「媒体发布桥接」默认开启；Token 自动协商，无需手动配置
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge  # noqa: E402
import _md2html  # noqa: E402


def _load_geo_content(content_id: str) -> dict:
    """从 GEO 云端拉文章内容（复用 adgine-geo-content 的 _client.py 机制）。

    内容库实际字段（与 manage_content.py / generate_article.py 一致）：
      标题  article_title
      正文  article_body（Markdown；部分任务输出里也见 full_content）
    扩展侧契约（extension/src/types.ts）：
      富文本平台（微信公众号/知乎…）读 article.content（HTML）
      Markdown 平台（CSDN/掘金…）优先读 article.markdown，缺省再由 content 兜底转换
    因此这里两个字段都要给：markdown 原文 + 由 markdown 转出的 html。
    """
    try:
        from _client import get_api_config, api_get, extract_data  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "使用 --content-id 需要 GEO_API_KEY 与云端内容库；"
            "若直接用本地文件，请改用 --title + --content-file。"
        ) from e
    key, base = get_api_config()
    pid = os.environ.get("GEO_PROJECT_ID", "")
    if not pid:
        # 未显式指定项目时，自动取第一个项目兜底（媒体发布通常跨项目取稿）
        projs = extract_data(api_get("/api/projects", key, base, params={"limit": 1}))
        items = projs.get("items", []) if isinstance(projs, dict) else projs
        if items:
            pid = items[0].get("id", "")
    if not pid:
        raise RuntimeError("未能确定 GEO 项目（GEO_PROJECT_ID 未设置，且云端无项目）")
    resp = api_get(f"/api/projects/{pid}/content/{content_id}", key, base)
    data = extract_data(resp) or {}
    markdown = (
        data.get("article_body")
        or data.get("full_content")
        or data.get("body_markdown")
        or data.get("markdown")
        or ""
    )
    html = (
        data.get("body_html")
        or data.get("content_html")
        or _md2html.markdown_to_html(markdown)
    )
    return {
        "title": data.get("article_title") or data.get("title") or "",
        "content": html,
        "markdown": markdown,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="发布到社交媒体草稿箱")
    p.add_argument("--platform", required=True, help="目标平台 id（zhihu/weixin/...）")
    p.add_argument("--title", help="文章标题（直接模式）")
    p.add_argument("--content-file", help="本地正文文件路径（md/html，直接模式）")
    p.add_argument("--content-id", help="GEO 云端内容库 content_id（云端模式）")
    p.add_argument("--summary", default="", help="摘要（可选）")
    p.add_argument("--cover", default="", help="封面图 URL（可选）")
    p.add_argument("--tags", default="", help="逗号分隔标签（可选）")
    p.add_argument("--port", type=int, default=_bridge.DEFAULT_PORT, help="桥 WS 端口（默认 9377）")
    p.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = p.parse_args()

    if not args.content_id and not (args.title and args.content_file):
        print("ERROR: 需 --content-id，或 --title + --content-file", file=sys.stderr)
        sys.exit(1)

    if args.content_id:
        article = _load_geo_content(args.content_id)
    else:
        if not os.path.isfile(args.content_file):
            print(f"ERROR: 正文文件不存在: {args.content_file}", file=sys.stderr)
            sys.exit(1)
        with open(args.content_file, encoding="utf-8") as f:
            body = f.read()
        # 简单判断：含 < 标签当 html，否则当 markdown
        is_html = "<" in body and ">" in body
        if is_html:
            article = {"title": args.title, "content": body, "markdown": ""}
        else:
            # markdown 文件：原文给 markdown 平台，转换后的 html 给富文本平台，
            # 与云端模式保持一致，避免微信公众号等拿到空 content。
            article = {
                "title": args.title,
                "content": _md2html.markdown_to_html(body),
                "markdown": body,
            }

    article.setdefault("summary", args.summary)
    article.setdefault("cover", args.cover)
    if args.tags:
        article["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    try:
        result = _bridge.request(
            "saveDraft",
            {"platform": args.platform, "article": article},
            port=args.port,
        )
    except RuntimeError as e:
        msg = str(e)
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(f"✗ 发布失败：{msg}", file=sys.stderr)
            if "扩展未连接" in msg or "开启「媒体发布桥接」" in msg or "未连接" in msg:
                print(
                    "\n请先完成一次性准备：\n"
                    "  1. 在本机 Chrome 安装 Adgine 同步助手扩展\n"
                    "  2. 确认扩展设置里「媒体发布桥接」为开（Token 自动协商，无需复制）\n"
                    "  3. 确认目标平台已在本机 Chrome 登录",
                    file=sys.stderr,
                )
        sys.exit(1)

    if args.json:
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
        return

    if result.get("success"):
        print(f"✓ 已存到 {args.platform} 草稿箱")
        if result.get("draftUrl"):
            print(f"  编辑链接：{result['draftUrl']}")
        if result.get("note"):
            print(f"  {result['note']}")
    else:
        print(f"✗ {args.platform} 存草稿失败：{result.get('error', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
