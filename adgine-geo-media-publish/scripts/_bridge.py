#!/usr/bin/env python3
"""Adgine 媒体发布桥接管理（Python 侧）。

职责：确保本地 bridge-server.js 在跑（没在跑则按需拉起），
并向它的 HTTP API（9378）发指令。对齐 wechatsync 的"按需拉起 + 主备接管"模式，
桥不常驻，用完由调用方决定是否保留。

零依赖：仅用 Python 标准库；bridge 进程本身用 Node（与 Chrome 扩展 WS 协议）。
"""
import os
import sys
import json
import time
import subprocess
import urllib.request as _req
import urllib.error as _uerr

_HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE_SERVER = os.path.join(_HERE, "bridge-server.js")
DEFAULT_PORT = int(os.environ.get("ADGINE_PUBLISH_PORT", "9377"))


def _http_port(port: int) -> int:
    return port + 1


def _post(path: str, payload: dict, port: int, timeout: float = 370.0) -> dict:
    url = f"http://localhost:{_http_port(port)}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = _req.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with _req.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path: str, port: int, timeout: float = 2.0) -> dict:
    url = f"http://localhost:{_http_port(port)}{path}"
    with _req.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _bridge_running(port: int) -> bool:
    try:
        _get("/status", port, timeout=1.5)
        return True
    except Exception:
        return False


def ensure_bridge(port: int = DEFAULT_PORT, wait_s: float = 5.0) -> None:
    """确保 bridge 在跑；没在跑则用 node 拉起 bridge-server.js。

    bridge-server 自带主备协商：9377 被占会降级为 SECONDARY 并转发给已存在的
    PRIMARY，因此重复拉起是安全的。等 HTTP API 起来即返回（扩展是否已连由
    后续 request 时的错误信息给出引导）。
    """
    if _bridge_running(port):
        return
    node = _find_node()
    if not node:
        raise RuntimeError(
            "未找到 node 可执行文件。媒体发布桥需要 Node.js（>=18）。请先安装 Node。"
        )
    env = dict(os.environ)
    # 子进程脱离当前会话常驻（macOS/Linux），日志丢弃避免阻塞
    subprocess.Popen(
        [node, BRIDGE_SERVER],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if _bridge_running(port):
            return
        time.sleep(0.3)
    raise RuntimeError(
        f"媒体发布桥启动超时（端口 {_http_port(port)} 未响应）。"
        f"若端口被占用，可设环境变量 ADGINE_PUBLISH_PORT 换端口，"
        f"或 kill $(lsof -i :{port} -t) 后重试。"
    )


def _find_node() -> str:
    for name in ("node",):
        path = _which(name)
        if path:
            return path
    return ""


def _which(name: str) -> str:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return ""


def _extension_connected(port: int) -> bool:
    """桥 /status 的 connected 字段即扩展 WS 是否已连上。"""
    try:
        return bool(_get("/status", port, timeout=2.0).get("connected"))
    except Exception:
        return False


def _wait_extension(port: int, timeout_s: float = 30.0) -> None:
    """等待扩展 WS 重连。扩展侧有 0.5–5s 的重连退避，瞬时断连会自动恢复；
    这里轮询等待，避免把瞬时断连直接抛成「请刷新插件」。超时仍未连上才报错。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _extension_connected(port):
            return
        time.sleep(0.5)
    raise RuntimeError(
        "Chrome 扩展未连接：请确认已安装 Adgine 同步助手扩展并开启「媒体发布桥接」"
    )


def request(method: str, params: dict, port: int = DEFAULT_PORT) -> dict:
    """向扩展发指令并返回结果。自动先 ensure_bridge。

    无需带 Token：桥与扩展之间在 WS 握手时已自动协商 Token，桥转发时自动带上。
    安全边界 = 桥只绑 127.0.0.1 + 扩展侧校验 Token，用户/skill 全程无感。
    """
    ensure_bridge(port)
    # 桥已起但扩展 WS 可能正在重连：先等它就绪，再发指令
    if not _extension_connected(port):
        _wait_extension(port)
    payload = {"method": method, "params": params}
    out = _post("/request", payload, port)
    if out.get("error"):
        err = str(out["error"])
        # 指令在飞行途中遇上 WS 断开：等重连后原样重试一次
        if "未连接" in err or "扩展未连接" in err:
            _wait_extension(port)
            out = _post("/request", payload, port)
            if out.get("error"):
                raise RuntimeError(out["error"])
            return out.get("result") or {}
        raise RuntimeError(err)
    return out.get("result") or {}
