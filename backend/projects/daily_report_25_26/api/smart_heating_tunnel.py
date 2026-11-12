# -*- coding: utf-8 -*-
"""
智慧供热平台内网反向代理隧道 (Tunnel & Gateway) API
提供：
1. /poll: 供办公电脑中继客户端并发拉取待转发请求
2. /respond: 供办公电脑中继客户端回传内网响应
3. /gateway/{subpath:path}: 面向前端 iframe 的反向代理网关 (注入 Base 路径与绝对路径重写)
4. /config: 查询与保存内网平台账号密码、中继通讯密钥及自动登录配置
5. /status: 查询中继客户端实时连接状态、IP 及心跳
6. /client-script: 动态生成并下载已预填配置的 Win7 Python 3.8 中继客户端脚本
"""

import asyncio
import base64
import json
import logging
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.config import DATA_DIRECTORY
from backend.services.auth_manager import AuthSession, auth_manager, get_current_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smart-heating-tunnel", tags=["smart_heating_tunnel"])
public_router = APIRouter(prefix="/smart-heating-tunnel", tags=["smart_heating_tunnel"])


def is_global_admin_user_session(session: AuthSession) -> bool:
    """
    【安全红线】：严格仅限 Global_admin / 超级管理员本人 (ww870411) 访问。
    坚决排除 Group_admin、Unit_admin 以及其他任何角色。
    """
    if getattr(session, "username", "") == "ww870411":
        return True
    if getattr(session, "group", None) == "Global_admin":
        return True
    # 检查兼职组中是否包含 Global_admin
    user_record = auth_manager._users_by_name.get(getattr(session, "username", ""))
    if user_record and "Global_admin" in getattr(user_record, "groups", []):
        return True
    return False


def verify_global_admin_access(request: Request) -> AuthSession:
    """
    全链路强制严格仅限 Global_admin (超级管理员本人) 访问：
    支持从 Header (Authorization: Bearer)、Query (?phoenix_token= 或 ?token=)、
    以及 Cookie (phoenix_tunnel_admin_token / token) 中提取身份凭据。
    非 Global_admin 或无凭据时直接抛出 HTTPException 403 阻断访问。
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()

    if not token:
        token = request.query_params.get("phoenix_token") or request.query_params.get("token")

    if not token:
        token = (
            request.cookies.get("phoenix_tunnel_admin_token")
            or request.cookies.get("phoenix_token")
            or request.cookies.get("token")
        )

    if not token:
        raise HTTPException(status_code=403, detail="智慧供热内网直通严格仅限 Global_admin 访问 (未提供身份凭证)")

    try:
        session = auth_manager.require_session(token)
    except Exception:
        raise HTTPException(status_code=403, detail="身份认证已过期，请重新登录 Phoenix 后访问")

    if not is_global_admin_user_session(session):
        raise HTTPException(status_code=403, detail="权限不足：智慧供热内网直通功能严格仅限 Global_admin 本人访问")

    # 存入 request.state 便于后续流程（如写回 Cookie 和 Location 保持）使用
    request.state.admin_token = token
    return session

# 数据持久化目录与配置文件
DATA_DIR = (Path(DATA_DIRECTORY) / "projects" / "daily_report_25_26" / "smart_heating").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
TUNNEL_CONFIG_FILE = DATA_DIR / "tunnel_config.json"

DEFAULT_TUNNEL_CONFIG = {
    "target_base_url": "http://192.168.1.206:6688",
    "portal_path": "/vindex/",
    "login_path": "/vindex/login",
    "auth_username": "",
    "auth_password": "",
    "tunnel_secret": "phoenix_tunnel_secret_2026",
    "auto_login_enabled": True,
    "persisted_cookies": {},
}


def load_tunnel_config() -> Dict[str, Any]:
    """读取反向中继与账号持久化配置"""
    if not TUNNEL_CONFIG_FILE.exists():
        try:
            with open(TUNNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_TUNNEL_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("创建默认隧道配置失败: %s", e)
        return dict(DEFAULT_TUNNEL_CONFIG)
    try:
        with open(TUNNEL_CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            cfg = dict(DEFAULT_TUNNEL_CONFIG)
            cfg.update(saved)
            return cfg
    except Exception as e:
        logger.warning("读取隧道配置失败，使用默认值: %s", e)
        return dict(DEFAULT_TUNNEL_CONFIG)


def save_tunnel_config(cfg: Dict[str, Any]) -> None:
    """持久化保存反向中继与账号配置"""
    try:
        with open(TUNNEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("保存隧道配置失败: %s", e)


class TunnelManager:
    """反向代理隧道核心调度器"""

    def __init__(self):
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.pending_futures: Dict[str, asyncio.Future] = {}
        self.last_heartbeat: Optional[float] = None
        self.client_ip: Optional[str] = None
        self.active_workers: Dict[int, float] = {}

    def record_heartbeat(self, client_ip: str, worker_id: int = 1):
        self.last_heartbeat = time.time()
        self.client_ip = client_ip
        self.active_workers[worker_id] = time.time()

    def is_online(self, timeout_sec: float = 35.0) -> bool:
        if not self.last_heartbeat:
            return False
        return (time.time() - self.last_heartbeat) < timeout_sec

    def clean_stale_workers(self, timeout_sec: float = 35.0):
        now = time.time()
        self.active_workers = {w_id: t for w_id, t in self.active_workers.items() if now - t < timeout_sec}


TUNNEL = TunnelManager()


class TunnelPollRequest(BaseModel):
    worker_id: Optional[int] = Field(1, description="工作线程 ID")
    timeout: Optional[int] = Field(25, description="长轮询挂起超时秒数")
    target_base_url: Optional[str] = Field(None, description="内网平台地址")


class TunnelResponsePayload(BaseModel):
    request_id: str = Field(..., description="请求 ID")
    status_code: int = Field(200, description="HTTP 状态码")
    headers: Dict[str, str] = Field(default_factory=dict, description="响应头字典")
    cookies: Optional[List[str]] = Field(default_factory=list, description="内网返回的所有 Set-Cookie 列表")
    body_b64: Optional[str] = Field("", description="Base64 编码的响应体")
    duration_ms: Optional[int] = Field(0, description="内网执行耗时")


class TunnelConfigUpdateRequest(BaseModel):
    target_base_url: Optional[str] = Field(None, description="内网平台基础地址")
    portal_path: Optional[str] = Field(None, description="入口路径，如 /vindex/")
    login_path: Optional[str] = Field(None, description="登录表单路径")
    auth_username: Optional[str] = Field(None, description="内网平台用户名")
    auth_password: Optional[str] = Field(None, description="内网平台密码")
    tunnel_secret: Optional[str] = Field(None, description="中继通讯密钥")
    auto_login_enabled: Optional[bool] = Field(None, description="是否启用自动登录")


# ==============================================================================
# 1. 办公机中继端点：Poll 与 Respond
# ==============================================================================


@public_router.post("/poll", summary="办公机拉取待转发的请求任务")
async def poll_tunnel_task(
    req: Request,
    payload: TunnelPollRequest = Body(...),
    x_tunnel_secret: Optional[str] = Header(None, alias="X-Tunnel-Secret"),
):
    """
    办公电脑中继客户端调用此端点进行长轮询。
    若队列中有外部发起的 HTTP 请求，立即出队返回给客户端；
    若当前无请求，则挂起等待直到有新请求或达到超时时间。
    """
    config = load_tunnel_config()
    expected_secret = config.get("tunnel_secret") or DEFAULT_TUNNEL_CONFIG["tunnel_secret"]

    if x_tunnel_secret != expected_secret:
        raise HTTPException(status_code=403, detail="中继通信密钥无效")

    client_ip = req.client.host if req.client else "unknown"
    TUNNEL.record_heartbeat(client_ip=client_ip, worker_id=payload.worker_id or 1)
    TUNNEL.clean_stale_workers()

    timeout = min(max(payload.timeout or 25, 5), 30)

    try:
        task = await asyncio.wait_for(TUNNEL.request_queue.get(), timeout=float(timeout))
        return {"has_task": True, "task": task}
    except asyncio.TimeoutError:
        return {"has_task": False, "task": None}


@public_router.post("/respond", summary="办公机回传内网请求响应")
async def respond_tunnel_task(
    payload: TunnelResponsePayload = Body(...),
    x_tunnel_secret: Optional[str] = Header(None, alias="X-Tunnel-Secret"),
):
    """办公电脑客户端在内网执行请求完毕后，将响应内容回传至此端点"""
    config = load_tunnel_config()
    expected_secret = config.get("tunnel_secret") or DEFAULT_TUNNEL_CONFIG["tunnel_secret"]

    if x_tunnel_secret != expected_secret:
        raise HTTPException(status_code=403, detail="中继通信密钥无效")

    req_id = payload.request_id
    future = TUNNEL.pending_futures.get(req_id)
    if future and not future.done():
        future.set_result(payload)
        return {"ok": True, "message": "响应已分发"}

    return {"ok": False, "message": "请求已超时或不存在"}


# ==============================================================================
# 2. 网关入口：全量反向代理 (支持 Base 路径注入与 HTML 重写)
# ==============================================================================


@public_router.api_route(
    "/gateway/{subpath:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    summary="内网平台全量反向代理网关",
)
async def gateway_reverse_proxy(
    subpath: str,
    request: Request,
):
    """
    接收来自前端 iframe 或外网浏览器的请求，通过长轮询隧道转发给办公电脑，
    并在办公电脑请求内网后回传响应给外网。
    对于 HTML 内容，自动注入 <base> 标签和 URL 代理劫持脚本，防止相对路径与根路径资源 404。
    【安全红线】：严格仅限 Global_admin 用户访问。
    """
    # 严格校验 Global_admin 权限
    try:
        session = verify_global_admin_access(request)
    except HTTPException as e:
        accept = request.headers.get("accept", "").lower()
        if "text/html" in accept or subpath.endswith(".html") or subpath.endswith("/") or not subpath:
            forbidden_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>403 权限拒绝 - 仅限 Global_admin</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; border: 1px solid #ef4444; }}
        .icon {{ font-size: 3.5rem; margin-bottom: 1rem; }}
        h2 {{ margin: 0 0 1rem; color: #f87171; font-size: 1.5rem; }}
        p {{ color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem; }}
        .badge {{ display: inline-block; background: #b91c1c; color: #fff; padding: 4px 12px; border-radius: 999px; font-size: 0.85rem; font-weight: bold; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🚫</div>
        <div class="badge">访问权限拒绝 (403)</div>
        <h2>仅限 Global_admin 访问该页面</h2>
        <p>{e.detail}<br>智慧供热直通通道直连核心生产内网调度平台，严格仅限全局管理员 (Global_admin) 访问。</p>
    </div>
</body>
</html>"""
            return Response(content=forbidden_html, status_code=403, media_type="text/html")
        raise e

    # 检查中继是否在线
    if not TUNNEL.is_online():
        offline_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>中继未连接 - Phoenix 智慧供热平台直通</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; border: 1px solid #334155; }
        .icon { font-size: 3.5rem; margin-bottom: 1rem; }
        h2 { margin: 0 0 1rem; color: #38bdf8; font-size: 1.5rem; }
        p { color: #94a3b8; line-height: 1.6; margin-bottom: 1.5rem; }
        .badge { display: inline-block; background: #dc2626; color: #fff; padding: 4px 12px; border-radius: 999px; font-size: 0.85rem; font-weight: bold; margin-bottom: 1rem; }
        .btn { display: inline-block; background: #0284c7; color: white; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; transition: background 0.2s; }
        .btn:hover { background: #0369a1; }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🔌</div>
        <div class="badge">中继链路未连接</div>
        <h2>智慧供热内网直通暂不可用</h2>
        <p>目前尚未检测到办公电脑中继程序的有效心跳。<br>请确认已在 Win7 办公电脑上启动 <code>smart_heating_tunnel_win7.py</code> 脚本。</p>
        <button class="btn" onclick="window.location.reload()">重新连接 ⟳</button>
    </div>
</body>
</html>"""
        return Response(content=offline_html, status_code=503, media_type="text/html")

    req_id = str(uuid.uuid4())
    raw_body = await request.body()
    body_b64 = base64.b64encode(raw_body).decode("ascii") if raw_body else ""

    # 请求头清洗与透传
    headers_dict = {}
    for k, v in request.headers.items():
        if k.lower() not in {"host", "content-length", "connection"}:
            headers_dict[k] = v

    # 清洗请求 Cookie：过滤掉仅供 Phoenix 网关使用的内部 token，仅透传属于内网平台的会话 cookie (如 session=...)
    raw_cookie_header = headers_dict.get("cookie") or headers_dict.get("Cookie")
    if raw_cookie_header:
        parts = [c.strip() for c in raw_cookie_header.split(";") if c.strip()]
        forward_cookies = [
            c for c in parts
            if not c.startswith("phoenix_tunnel_admin_token=")
            and not c.startswith("phoenix_token=")
            and not c.startswith("token=")
        ]
        if forward_cookies:
            headers_dict["cookie"] = "; ".join(forward_cookies)
        else:
            headers_dict.pop("cookie", None)
            headers_dict.pop("Cookie", None)

    full_path = f"/{subpath}" if not subpath.startswith("/") else subpath
    # 提取 query string 并清理内部鉴权参数，避免内网平台收到无关参数
    token = getattr(request.state, "admin_token", None) or getattr(session, "token", "")
    raw_query = str(request.url.query)
    clean_pairs = []
    if raw_query:
        for p in raw_query.split("&"):
            if not p:
                continue
            k = p.split("=")[0].strip()
            if k not in ("phoenix_token", "token", "_t"):
                clean_pairs.append(p)
    query_str = "&".join(clean_pairs)

    task_payload = {
        "request_id": req_id,
        "method": request.method,
        "path": full_path,
        "query_string": query_str,
        "headers": headers_dict,
        "body_b64": body_b64,
        "created_at": time.time(),
    }

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    TUNNEL.pending_futures[req_id] = future

    # 推入排队队列
    await TUNNEL.request_queue.put(task_payload)

    # 等待中继响应（最长等待 35 秒）
    try:
        result_payload: TunnelResponsePayload = await asyncio.wait_for(future, timeout=35.0)
    except asyncio.TimeoutError:
        TUNNEL.pending_futures.pop(req_id, None)
        return Response(
            content="Tunnel Relay Gateway Timeout (办公电脑请求内网响应超时)".encode("utf-8"),
            status_code=504,
            media_type="text/plain; charset=utf-8",
        )
    finally:
        TUNNEL.pending_futures.pop(req_id, None)

    # 处理二进制响应
    body_bytes = base64.b64decode(result_payload.body_b64) if result_payload.body_b64 else b""

    # 处理响应头
    config = load_tunnel_config()
    resp_headers = {}
    content_type = ""
    gateway_prefix = "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/"
    gateway_base_clean = gateway_prefix.rstrip("/")

    skip_resp_headers = {
        "content-length",
        "transfer-encoding",
        "content-encoding",
        "connection",
        "x-frame-options",  # 剥离 X-Frame-Options 确保 Phoenix 前端 iframe 可正常嵌入
        "set-cookie",       # Set-Cookie 统一在下方通过 response.raw_headers / set_cookie 注入，避免覆盖
    }

    for k, v in result_payload.headers.items():
        lk = k.lower()
        if lk == "content-type":
            content_type = v
            resp_headers[k] = v
        elif lk == "location":
            # 重写 301/302 重定向 Location 头，防止浏览器跳转至无法访问的内网 IP
            target_base = config.get("target_base_url") or "http://192.168.1.206:6688"
            loc = v
            if loc.startswith(target_base):
                loc = loc[len(target_base):]
            if loc.startswith("/"):
                loc = f"{gateway_base_clean}/{loc.lstrip('/')}"
            # 关键修复：重定向时附带 phoenix_token，防止后续跳转请求丢失凭证导致 403 / 空白
            if token and "phoenix_token=" not in loc:
                delim = "&" if "?" in loc else "?"
                loc = f"{loc}{delim}phoenix_token={token}"
            resp_headers[k] = loc
        elif lk == "content-security-policy":
            # 清理 CSP 中的 frame-ancestors 避免阻断 iframe 呈现
            clean_csp = re.sub(r"frame-ancestors\s+[^;]+;?", "", v, flags=re.IGNORECASE)
            resp_headers[k] = clean_csp
        elif lk not in skip_resp_headers:
            resp_headers[k] = v

    # 允许被同源或外网父页面嵌入
    resp_headers["X-Frame-Options"] = "ALLOWALL"

    # 关键路径重写：HTML 内容正则重写 + Base 标签注入 + Ajax 全局拦截脚本
    if "text/html" in content_type.lower():
        try:
            html_text = body_bytes.decode("utf-8", errors="replace")

            # 1. 深度正则重写绝对路径：将 href="/static/...", src="/...", action="/..." 统一映射至网关
            # 匹配形如 href="/xxx" 或 src='/xxx'，排除已有前缀、协议或锚点
            def rewrite_abs_urls(match):
                attr = match.group(1)
                quote = match.group(2)
                path_part = match.group(3)
                extra_token = ""
                # 如果是表单提交 action，自动附加 phoenix_token 避免跨域 iframe 提交时丢失凭证直接 403
                if attr.lower() == "action" and token and "phoenix_token=" not in path_part:
                    delim = "&" if "?" in path_part else "?"
                    extra_token = f"{delim}phoenix_token={token}"
                return f"{attr}={quote}{gateway_base_clean}/{path_part}{extra_token}{quote}"

            html_text = re.sub(
                r'\b(href|src|action)=([\'"])/(?!(?:api/|projects/|#|data:|javascript:))([^\'"]*)[\'"]',
                rewrite_abs_urls,
                html_text,
            )

            # 2. 注入 base 标签与绝对路径全局 Ajax 拦截脚本（自动补全凭证）
            injection = f"""<base href="{gateway_prefix}">
<script>
(function() {{
    var gBase = '{gateway_base_clean}';
    var gToken = '{token or ""}';
    var origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {{
        if (typeof url === 'string') {{
            if (url.indexOf('192.168.1.206:6688') !== -1) {{
                url = url.replace(/https?:\\/\\/192\\.168\\.1\\.206:6688/, gBase);
            }} else if (url.startsWith('/') && !url.startsWith(gBase)) {{
                url = gBase + url;
            }}
            if (gToken && url.indexOf('phoenix_token=') === -1) {{
                var d = url.indexOf('?') === -1 ? '?' : '&';
                url = url + d + 'phoenix_token=' + encodeURIComponent(gToken);
            }}
        }}
        return origOpen.apply(this, arguments);
    }};
    if (window.fetch) {{
        var origFetch = window.fetch;
        window.fetch = function(input, init) {{
            if (typeof input === 'string') {{
                if (input.indexOf('192.168.1.206:6688') !== -1) {{
                    input = input.replace(/https?:\\/\\/192\\.168\\.1\\.206:6688/, gBase);
                }} else if (input.startsWith('/') && !input.startsWith(gBase)) {{
                    input = gBase + input;
                }}
                if (gToken && input.indexOf('phoenix_token=') === -1) {{
                    var d = input.indexOf('?') === -1 ? '?' : '&';
                    input = input + d + 'phoenix_token=' + encodeURIComponent(gToken);
                }}
            }}
            return origFetch(input, init);
        }};
    }}
    // 全局表单提交拦截：为所有动态表单补齐 phoenix_token 凭证
    document.addEventListener('submit', function(e) {{
        var form = e.target;
        if (form && gToken) {{
            var action = form.getAttribute('action') || window.location.href;
            if (action.indexOf('phoenix_token=') === -1) {{
                var d = action.indexOf('?') === -1 ? '?' : '&';
                form.setAttribute('action', action + d + 'phoenix_token=' + encodeURIComponent(gToken));
            }}
        }}
    }}, true);
}})();
</script>"""

            if "<head>" in html_text:
                html_text = html_text.replace("<head>", f"<head>\n{injection}\n", 1)
            elif "<HEAD>" in html_text:
                html_text = html_text.replace("<HEAD>", f"<HEAD>\n{injection}\n", 1)
            else:
                html_text = f"{injection}\n{html_text}"

            body_bytes = html_text.encode("utf-8")
            resp_headers["Content-Type"] = "text/html; charset=utf-8"
        except Exception as e:
            logger.warning("HTML 路径重写与 base 标签注入失败: %s", e)

    # 对 CSS 文件内部的 url(/static/...) 也进行安全重写
    elif "text/css" in content_type.lower():
        try:
            css_text = body_bytes.decode("utf-8", errors="replace")
            css_text = re.sub(
                r'url\([\'"]?/(?!(?:api/|projects/|data:))([^\'")]+)[\'"]?\)',
                rf'url("{gateway_base_clean}/\1")',
                css_text,
            )
            body_bytes = css_text.encode("utf-8")
        except Exception as e:
            logger.warning("CSS 内部 url 路径重写失败: %s", e)

    # 构造响应对象
    response = Response(
        content=body_bytes,
        status_code=result_payload.status_code,
        headers=resp_headers,
    )

    # 1. 忠实透传内网平台返回的所有 Set-Cookie 会话 Cookie（如 session=...，支持多条），彻底解决无法登录问题
    raw_cookie_sources = list(result_payload.cookies or [])
    for hk, hv in result_payload.headers.items():
        if hk.lower() == "set-cookie" and hv not in raw_cookie_sources:
            raw_cookie_sources.append(hv)

    for c_raw in raw_cookie_sources:
        if not c_raw or not isinstance(c_raw, str):
            continue
        # 清洗 Cookie 属性：移除 Domain 限制，重写 Path 为 / 确保全直通子路由皆可正常携带
        cleaned = re.sub(r'Domain=[^;]+;?\s*', '', c_raw, flags=re.IGNORECASE)
        cleaned = re.sub(r'Path=[^;]+;?\s*', 'Path=/; ', cleaned, flags=re.IGNORECASE)
        if 'Path=/' not in cleaned:
            cleaned = cleaned.rstrip('; ') + '; Path=/'
        # 去除 Secure 标记以兼容外网非 HTTPS / 中继局域网环境
        cleaned = re.sub(r'Secure;?\s*', '', cleaned, flags=re.IGNORECASE)
        response.raw_headers.append((b"set-cookie", cleaned.encode("latin-1")))

    # 2. 携带管理员凭据 Cookie，使 iframe 子资源、新标签页与异步请求全域无感鉴权
    if token:
        response.set_cookie(
            key="phoenix_tunnel_admin_token",
            value=token,
            path="/",
            samesite="lax",
            max_age=2592000,
        )

    return response


# ==============================================================================
# 3. 配置、状态与动态客户端下载
# ==============================================================================


@router.get("/config", summary="查询中继与内网平台账号配置")
async def get_tunnel_configuration(
    request: Request,
):
    """查询当前反向中继与账号配置（密码已脱敏，仅限 Global_admin）"""
    verify_global_admin_access(request)
    config = load_tunnel_config()
    safe_config = dict(config)
    # 对密码进行掩码保护
    pwd = safe_config.get("auth_password") or ""
    safe_config["has_password"] = bool(pwd)
    safe_config["auth_password"] = "******" if pwd else ""
    return safe_config


@router.post("/config", summary="更新内网平台账号与中继配置")
async def update_tunnel_configuration(
    request: Request,
    payload: TunnelConfigUpdateRequest = Body(...),
):
    """保存内网平台账号、密码以及中继参数（仅限 Global_admin）"""
    verify_global_admin_access(request)
    config = load_tunnel_config()
    if payload.target_base_url is not None:
        config["target_base_url"] = payload.target_base_url.rstrip("/")
    if payload.portal_path is not None:
        config["portal_path"] = payload.portal_path
    if payload.login_path is not None:
        config["login_path"] = payload.login_path
    if payload.auth_username is not None:
        config["auth_username"] = payload.auth_username
    if payload.auth_password is not None and payload.auth_password != "******":
        config["auth_password"] = payload.auth_password
    if payload.tunnel_secret is not None:
        config["tunnel_secret"] = payload.tunnel_secret
    if payload.auto_login_enabled is not None:
        config["auto_login_enabled"] = payload.auto_login_enabled

    save_tunnel_config(config)
    return {"ok": True, "message": "配置更新成功"}


@public_router.get("/status", summary="查询中继实时在线状态")
async def get_tunnel_status(
    request: Request,
):
    """获取办公电脑中继连接状态、心跳、IP 及活跃连接数（仅限 Global_admin）"""
    verify_global_admin_access(request)
    is_online = TUNNEL.is_online()
    last_hb_str = ""
    if TUNNEL.last_heartbeat:
        last_hb_str = datetime.fromtimestamp(TUNNEL.last_heartbeat).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "online": is_online,
        "last_heartbeat": last_hb_str,
        "client_ip": TUNNEL.client_ip or "未连接",
        "active_workers": len(TUNNEL.active_workers),
        "pending_requests": TUNNEL.request_queue.qsize(),
    }


def _get_client_script_template_path() -> Optional[Path]:
    """
    多路径探测中继客户端脚本模板位置：
    1. 优先读取挂载数据卷目录中的客户端脚本：
       phoenix/backend_data/projects/daily_report_25_26/smart_heating_tunnel_win7.py (容器内为 /app/data/...)
       确保宿主机挂载目录下修改后直接生效，无需重建 Docker 镜像。
    2. 若挂载文件不存在，自动尝试从源码目录同步初始化一份至挂载数据卷并返回。
    """
    mounted_dir = (Path(DATA_DIRECTORY) / "projects" / "daily_report_25_26").resolve()
    mounted_file = mounted_dir / "smart_heating_tunnel_win7.py"

    source_candidates = [
        Path(__file__).resolve().parent.parent / "smart_heating_tunnel_win7.py",
        Path(__file__).resolve().parent / "smart_heating_tunnel_win7.py",
        Path("/app/backend/projects/daily_report_25_26/smart_heating_tunnel_win7.py"),
    ]

    # 1. 优先使用挂载文件夹下的脚本
    if mounted_file.exists() and mounted_file.is_file():
        return mounted_file

    # 2. 若挂载文件不存在，尝试从源码中提取并自动写入挂载目录
    for src in source_candidates:
        if src.exists() and src.is_file():
            try:
                mounted_dir.mkdir(parents=True, exist_ok=True)
                with open(src, "r", encoding="utf-8") as f_in, open(mounted_file, "w", encoding="utf-8") as f_out:
                    f_out.write(f_in.read())
                logger.info("已自动将中继客户端脚本初始化至挂载目录: %s", mounted_file)
                return mounted_file
            except Exception as e:
                logger.warning("复制脚本至挂载目录失败: %s，直接使用源码模板", e)
            return src

    return None


@public_router.get("/client-script", summary="动态生成并下载中继客户端脚本")
async def download_client_script(
    request: Request,
):
    """
    根据当前系统的配置与请求域名，动态生成预填好配置的 smart_heating_tunnel_win7.py 客户端，
    优先读取挂载目录 (backend_data/projects/daily_report_25_26/) 下的文件，严格仅限 Global_admin 下载。
    """
    verify_global_admin_access(request)
    template_path = _get_client_script_template_path()
    if not template_path or not template_path.exists():
        raise HTTPException(status_code=404, detail="客户端脚本文件在挂载目录与源码中均不存在")

    with open(template_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    # 动态推断服务器根地址
    cfg = load_tunnel_config()
    base_url = str(request.base_url).rstrip("/")
    if "127.0.0.1" in base_url or "localhost" in base_url:
        server_url = "https://platform.smartview.top"
    else:
        server_url = base_url

    # 预注入配置字典
    injected_config = {
        "phoenix_server_url": server_url,
        "tunnel_secret": cfg.get("tunnel_secret") or DEFAULT_TUNNEL_CONFIG["tunnel_secret"],
        "intranet_base_url": cfg.get("target_base_url") or DEFAULT_TUNNEL_CONFIG["target_base_url"],
        "auth_username": cfg.get("auth_username") or "",
        "auth_password": cfg.get("auth_password") or "",
        "concurrency": 6,
        "poll_timeout": 25,
    }

    # 替换脚本中的 DEFAULT_CONFIG 定义
    config_repr = json.dumps(injected_config, ensure_ascii=False, indent=4)
    replacement = f"DEFAULT_CONFIG = {config_repr}"
    script_content = re.sub(
        r"DEFAULT_CONFIG\s*=\s*\{[\s\S]*?\}",
        replacement,
        script_content,
        count=1,
    )

    return Response(
        content=script_content.encode("utf-8"),
        media_type="text/x-python",
        headers={
            "Content-Disposition": 'attachment; filename="smart_heating_tunnel_win7.py"',
            "Content-Type": "text/x-python; charset=utf-8",
        },
    )
