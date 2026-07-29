#!/usr/bin/env python3
"""检测各平台在用户本地浏览器（Chrome 扩展）里的登录态。

示例：
  python3 scripts/check_login.py                  # 全部平台
  python3 scripts/check_login.py --platform zhihu # 单个平台
  python3 scripts/check_login.py --json
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _bridge  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="检测媒体平台登录态")
    p.add_argument("--platform", help="单个平台 id（缺省=全部）")
    p.add_argument("--port", type=int, default=_bridge.DEFAULT_PORT)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    try:
        if args.platform:
            result = _bridge.request("checkAuth", {"platform": args.platform}, port=args.port)
            rows = [result]
        else:
            result = _bridge.request("listPlatforms", {}, port=args.port)
            rows = result if isinstance(result, list) else []
    except RuntimeError as e:
        msg = str(e)
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(f"✗ 检测失败：{msg}", file=sys.stderr)
            if "未连接" in msg:
                print(
                    "\n请确认：本机 Chrome 已装 Adgine 同步助手扩展，"
                    "且「媒体发布桥接」为开（Token 自动协商，无需配置）。",
                    file=sys.stderr,
                )
        sys.exit(1)

    if args.json:
        print(json.dumps({"ok": True, "platforms": rows}, ensure_ascii=False))
        return

    if not rows:
        print("未获取到平台信息")
        return
    for r in rows:
        name = r.get("name") or r.get("platform") or r.get("id") or "?"
        pid = r.get("id") or r.get("platform") or ""
        authed = r.get("isAuthenticated")
        mark = "✓ 已登录" if authed else "✗ 未登录"
        hint = f"（{r['authHint']}）" if not authed and r.get("authHint") else ""
        print(f"  {mark}  {name} [{pid}]{hint}")


if __name__ == "__main__":
    main()
