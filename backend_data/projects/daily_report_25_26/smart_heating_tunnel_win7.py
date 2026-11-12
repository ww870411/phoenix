# -*- coding: utf-8 -*-
"""
================================================================================
🦅 Phoenix 智慧供热平台内网反向中继客户端 (Windows 7 + Python 3.8 全网直通版)
================================================================================
适用环境：
- 运行于可访问供热内网 (http://192.168.1.206:6688) 与 Phoenix 系统的 Win7 办公电脑。
- 100% 纯 Python 3.8 标准库编写，零 pip 外部依赖，开箱即用。
- 采用多线程并发反向长轮询隧道技术，自动维持连接与心跳。
- 内置平台账号登录持久化与自动代登引擎，外网访问免密直通。

使用方法：
1. 确认已在 Phoenix 控制台配置好内网平台账号与密码。
2. 双击本脚本或在命令行中运行：python smart_heating_tunnel_win7.py
3. 控制台显示“中继已成功连接”后，即可在外网 Phoenix 页面直接操作内网系统。
================================================================================
"""

import base64
import http.client
import json
import logging
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PhoenixTunnel")

# 脚本所在目录及本地持久化配置路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "smart_heating_tunnel_config.json")

# 默认出厂内置配置（可由 Phoenix 网页动态生成替换）
DEFAULT_CONFIG = {
    # Phoenix 云端服务器地址
    "phoenix_server_url": "https://platform.smartview.top",
    # 中继通讯密钥
    "tunnel_secret": "phoenix_tunnel_secret_2026",
    # 供热内网平台基础地址
    "intranet_base_url": "http://192.168.1.206:6688",
    # 内网登录账号与密码（为空时使用网页端持久化配置）
    "auth_username": "",
    "auth_password": "",
    # 并发轮询工作线程数 (推荐 12~16 高速并发)
    "concurrency": 16,
    # 轮询挂起超时秒数
    "poll_timeout": 25,
}


def load_config():
    """加载本地配置文件，不存在则创建默认配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                cfg = dict(DEFAULT_CONFIG)
                cfg.update(saved)
                # 性能优化：自动将旧版本配置的并发数平滑升级至 16
                if int(cfg.get("concurrency") or 0) < 16:
                    cfg["concurrency"] = 16
                return cfg
        except Exception as e:
            logger.warning("读取配置文件失败，使用内置配置: %s", e)
    else:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("创建配置文件失败: %s", e)
    return dict(DEFAULT_CONFIG)


CONFIG = load_config()

# 全局 Cookie 容器与持久化会话
class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    禁止 urllib 自动跟随 301/302 重定向。
    作为反向代理网关，必须将 302 重定向和 Location 头及 Set-Cookie 完整保留并传回给外网浏览器，
    由浏览器保存 Cookie 并执行跳转，确保 Session Cookie 不丢失。
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

COOKIE_JAR = CookieJar()
COOKIE_HANDLER = urllib.request.HTTPCookieProcessor(COOKIE_JAR)
INTRANET_OPENER = urllib.request.build_opener(NoRedirectHandler(), COOKIE_HANDLER)

# 停止事件
STOP_EVENT = threading.Event()


def make_full_intranet_url(path_or_url: str) -> str:
    """拼装内网目标地址"""
    base = CONFIG["intranet_base_url"].rstrip("/")
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    if not path_or_url.startswith("/"):
        path_or_url = "/" + path_or_url
    return base + path_or_url


def execute_intranet_request(task: dict) -> dict:
    """
    在办公电脑局域网内执行针对 192.168.1.206 的真实 HTTP 请求
    """
    request_id = task.get("request_id")
    method = (task.get("method") or "GET").upper()
    req_path = task.get("path") or "/"
    query_string = task.get("query_string") or ""
    headers = task.get("headers") or {}
    body_b64 = task.get("body_b64")

    # 拼装完整内网 URL
    target_url = make_full_intranet_url(req_path)
    if query_string:
        delimiter = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{delimiter}{query_string}"

    # 处理请求体
    req_data = None
    if body_b64:
        try:
            req_data = base64.b64decode(body_b64)
        except Exception as e:
            logger.error("解码请求体失败 [%s]: %s", request_id, e)
    elif method in ("POST", "PUT", "PATCH"):
        req_data = b""

    # 过滤与重构请求头
    filtered_headers = {}
    skip_headers = {
        "host",
        "content-length",
        "connection",
        "accept-encoding",  # 让内网返回明文以便代理处理
        "x-tunnel-secret",
    }
    for k, v in headers.items():
        if k.lower() not in skip_headers:
            filtered_headers[k] = v

    # 强制设置 Host 为内网目标 Host
    parsed_base = urllib.parse.urlparse(CONFIG["intranet_base_url"])
    filtered_headers["Host"] = parsed_base.netloc
    filtered_headers["User-Agent"] = headers.get("user-agent") or "Phoenix-Tunnel-Relay/1.0"

    req = urllib.request.Request(
        url=target_url,
        data=req_data,
        headers=filtered_headers,
        method=method,
    )

    start_time = time.time()
    status_code = 502
    resp_headers = {}
    set_cookies = []
    body_out_b64 = ""

    try:
        with INTRANET_OPENER.open(req, timeout=30) as resp:
            status_code = resp.getcode()
            for header_key, header_val in resp.headers.items():
                resp_headers[header_key] = header_val
            if hasattr(resp, "headers"):
                set_cookies = resp.headers.get_all("Set-Cookie") or []
            raw_body = resp.read()
            body_out_b64 = base64.b64encode(raw_body).decode("ascii")

    except urllib.error.HTTPError as e:
        status_code = e.code
        for header_key, header_val in e.headers.items():
            resp_headers[header_key] = header_val
        if hasattr(e, "headers"):
            set_cookies = e.headers.get_all("Set-Cookie") or []
        raw_body = e.read()
        body_out_b64 = base64.b64encode(raw_body).decode("ascii")

    except Exception as e:
        logger.error("转发内网请求失败 [%s] %s %s: %s", request_id, method, target_url, e)
        status_code = 504
        error_msg = f"中继办公电脑无法连接内网目标平台: {e}".encode("utf-8")
        resp_headers["Content-Type"] = "text/plain; charset=utf-8"
        body_out_b64 = base64.b64encode(error_msg).decode("ascii")

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info("内网响应 [%s] %s %s -> %s (%dms)", request_id, method, req_path, status_code, duration_ms)

    return {
        "request_id": request_id,
        "status_code": status_code,
        "headers": resp_headers,
        "cookies": set_cookies,
        "body_b64": body_out_b64,
        "duration_ms": duration_ms,
    }


def send_response_to_phoenix(result: dict):
    """将内网响应结果回传给 Phoenix 云端隧道"""
    server_base = CONFIG["phoenix_server_url"].rstrip("/")
    respond_url = f"{server_base}/api/v1/projects/daily_report_25_26/smart-heating-tunnel/respond"

    payload_bytes = json.dumps(result, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url=respond_url,
        data=payload_bytes,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Tunnel-Secret": CONFIG["tunnel_secret"],
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            pass
    except Exception as e:
        logger.error("回传响应到 Phoenix 失败 [%s]: %s", result.get("request_id"), e)


def poll_worker_loop(worker_id: int):
    """单个并发轮询工作线程"""
    logger.info("中继工作线程 #%d 已启动", worker_id)
    server_base = CONFIG["phoenix_server_url"].rstrip("/")
    poll_url = f"{server_base}/api/v1/projects/daily_report_25_26/smart-heating-tunnel/poll"

    poll_payload = json.dumps(
        {
            "worker_id": worker_id,
            "timeout": CONFIG["poll_timeout"],
            "target_base_url": CONFIG["intranet_base_url"],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    fail_count = 0

    while not STOP_EVENT.is_set():
        try:
            req = urllib.request.Request(
                url=poll_url,
                data=poll_payload,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Tunnel-Secret": CONFIG["tunnel_secret"],
                },
                method="POST",
            )

            # 超时时间比服务端的挂起时间长 5 秒
            with urllib.request.urlopen(req, timeout=CONFIG["poll_timeout"] + 5) as resp:
                resp_bytes = resp.read()
                fail_count = 0  # 成功连通重置失败计数

                if not resp_bytes:
                    continue

                data = json.loads(resp_bytes.decode("utf-8"))
                if not data.get("has_task"):
                    # 正常无任务长轮询返回，继续下一轮
                    continue

                task = data.get("task")
                if task and task.get("request_id"):
                    # 收到外网转发任务，立即在局域网内请求并回传
                    result = execute_intranet_request(task)
                    send_response_to_phoenix(result)

        except urllib.error.HTTPError as e:
            fail_count += 1
            if e.code == 403:
                logger.critical("中继密钥 (tunnel_secret) 错误，请检查配置！HTTP 403")
                time.sleep(10)
            else:
                logger.warning("轮询服务异常 (HTTP %s): %s", e.code, e.reason)
                time.sleep(3)
        except urllib.error.URLError as e:
            fail_count += 1
            if fail_count <= 3 or fail_count % 10 == 0:
                logger.warning("无法连接 Phoenix 服务器 (%s): %s (将自动重试)", server_base, e.reason)
            time.sleep(3)
        except Exception as e:
            fail_count += 1
            logger.error("轮询异常 (线程 #%d): %s", worker_id, e)
            time.sleep(2)


def test_intranet_connectivity():
    """启动前检测内网平台连通性"""
    url = make_full_intranet_url("/vindex/")
    logger.info("正在检测内网平台连通性: %s", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Phoenix-Tunnel-Tester"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info("✅ 内网平台可正常访问！响应状态码: %s", resp.getcode())
            return True
    except urllib.error.HTTPError as e:
        logger.info("✅ 内网平台网络已连通！响应状态码: %s (%s)", e.code, e.reason)
        return True
    except Exception as e:
        logger.warning("⚠️ 内网平台测试访问未直接成功 (请确认办公机是否能打开该网址): %s", e)
        return False


def main():
    print("=" * 70)
    print(" 🦅 Phoenix 智慧供热平台内网反向中继客户端 (Win7 + Python 3.8)")
    print("=" * 70)
    print(f" 目标内网系统: {CONFIG['intranet_base_url']}")
    print(f" 云端中继地址: {CONFIG['phoenix_server_url']}")
    print(f" 并发轮询通道: {CONFIG['concurrency']} 个线程")
    print("=" * 70)

    # 1. 测试内网平台连通
    test_intranet_connectivity()

    # 2. 启动并发工作线程池
    threads = []
    concurrency = int(CONFIG.get("concurrency") or 6)
    for i in range(1, concurrency + 1):
        t = threading.Thread(target=poll_worker_loop, args=(i,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1)  # 稍微错开启动时间

    logger.info("中继客户端运行中... 按 Ctrl+C 可停止程序。")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到退出信号，正在安全关闭...")
        STOP_EVENT.set()
        for t in threads:
            t.join(timeout=1.0)
        logger.info("中继客户端已安全退出。")


if __name__ == "__main__":
    main()
