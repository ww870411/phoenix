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
import gzip
import http.client
import json
import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from logging.handlers import RotatingFileHandler

# 脚本所在目录、配置文件及默认日志路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "smart_heating_tunnel_config.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "smart_heating_tunnel.log")
LOG_MAX_BYTES = 5 * 1024 * 1024  # 单文件最大 5MB
LOG_BACKUP_COUNT = 3

# 设置日志对象（文件处理器在 main() 启动时按需挂载，避免测试导入时产生文件）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PhoenixTunnel")
logger.setLevel(logging.INFO)


def setup_logging(log_file: str = LOG_FILE):
    """在脚本同目录下配置默认滚动日志文件，同时保留控制台输出。"""
    logger.setLevel(logging.INFO)
    if getattr(logger, "_file_logging_configured", False):
        return
    try:
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
        logger._file_logging_configured = True
    except Exception as e:
        logger.warning("初始化日志文件失败 (%s)，仅保留控制台日志: %s", log_file, e)

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
PHOENIX_CONNECTION = threading.local()


def post_phoenix_json(endpoint, payload, timeout, content_encoding=None):
    """每个工作线程复用一条公网连接，poll/respond 不再重复建立 TCP/TLS。"""
    parsed = urllib.parse.urlsplit(CONFIG["phoenix_server_url"])
    connection = getattr(PHOENIX_CONNECTION, "connection", None)
    if connection is None:
        connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(parsed.hostname, parsed.port, timeout=timeout)
        PHOENIX_CONNECTION.connection = connection
    connection.timeout = timeout
    if connection.sock is not None:
        connection.sock.settimeout(timeout)
    path = parsed.path.rstrip("/") + "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/" + endpoint
    req_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Tunnel-Secret": CONFIG["tunnel_secret"],
    }
    if content_encoding:
        req_headers["Content-Encoding"] = content_encoding
    try:
        connection.request("POST", path, body=payload, headers=req_headers)
        if connection.sock is not None:
            try:
                connection.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise urllib.error.HTTPError(path, response.status, response.reason, response.headers, None)
        return json.loads(body.decode("utf-8"))
    except Exception:
        # 失败连接释放后交由现有工作循环处理，不自动重发业务请求。
        connection.close()
        PHOENIX_CONNECTION.connection = None
        raise


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
    raw_len = 0

    try:
        with INTRANET_OPENER.open(req, timeout=30) as resp:
            status_code = resp.getcode()
            for header_key, header_val in resp.headers.items():
                resp_headers[header_key] = header_val
            if hasattr(resp, "headers"):
                set_cookies = resp.headers.get_all("Set-Cookie") or []
            raw_body = resp.read()
            raw_len = len(raw_body)
            body_out_b64 = base64.b64encode(raw_body).decode("ascii")

    except urllib.error.HTTPError as e:
        status_code = e.code
        for header_key, header_val in e.headers.items():
            resp_headers[header_key] = header_val
        if hasattr(e, "headers"):
            set_cookies = e.headers.get_all("Set-Cookie") or []
        raw_body = e.read()
        raw_len = len(raw_body)
        body_out_b64 = base64.b64encode(raw_body).decode("ascii")

    except Exception as e:
        logger.error("转发内网请求失败 [%s] %s %s (%s): %s", request_id, method, target_url, type(e).__name__, e)
        status_code = 504
        error_msg = f"中继办公电脑无法连接内网目标平台: {e}".encode("utf-8")
        raw_len = len(error_msg)
        resp_headers["Content-Type"] = "text/plain; charset=utf-8"
        body_out_b64 = base64.b64encode(error_msg).decode("ascii")

    duration_ms = int((time.time() - start_time) * 1000)
    queue_ms = float(task.get("queue_ms") or 0)
    logger.info(
        "内网响应 [%s] %s %s -> %s (队列=%.0fms, 内网=%dms, 大小=%dB)",
        request_id, method, req_path, status_code, queue_ms, duration_ms, raw_len,
    )

    return {
        "request_id": request_id,
        "status_code": status_code,
        "headers": resp_headers,
        "cookies": set_cookies,
        "body_b64": body_out_b64,
        "duration_ms": duration_ms,
    }


def send_response_to_phoenix(result: dict):
    """将内网响应结果回传给 Phoenix 云端隧道（大响应自动启用 gzip 压缩）"""
    raw_bytes = json.dumps(result, ensure_ascii=False).encode("utf-8")
    raw_len = len(raw_bytes)
    payload_bytes = raw_bytes
    content_encoding = None
    if raw_len > 1024:
        compressed_bytes = gzip.compress(raw_bytes, compresslevel=6)
        if len(compressed_bytes) < raw_len:
            payload_bytes = compressed_bytes
            content_encoding = "gzip"
    wire_len = len(payload_bytes)
    respond_start = time.time()
    try:
        reply = post_phoenix_json("respond", payload_bytes, timeout=35, content_encoding=content_encoding)
        respond_ms = int((time.time() - respond_start) * 1000)
        size_info = f"{wire_len}B(原始={raw_len}B)" if content_encoding else f"{wire_len}B"
        if not reply.get("ok"):
            logger.warning(
                "响应未被服务端采纳 [%s] (回传=%dms, 负载=%s): %s",
                result.get("request_id"), respond_ms, size_info, reply.get("message", ""),
            )
        else:
            logger.info(
                "回传完成 [%s] 状态=%s 回传=%dms 负载=%s",
                result.get("request_id"), result.get("status_code"), respond_ms, size_info,
            )
    except Exception as e:
        respond_ms = int((time.time() - respond_start) * 1000)
        logger.error(
            "回传响应到 Phoenix 失败 [%s] (耗时=%dms, 负载=%dB, %s): %s",
            result.get("request_id"), respond_ms, wire_len, type(e).__name__, e,
        )


def poll_worker_loop(worker_id: int):
    """单个并发轮询工作线程"""
    logger.info("中继工作线程 #%d 已启动", worker_id)
    server_base = CONFIG["phoenix_server_url"].rstrip("/")

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
            data = post_phoenix_json("poll", poll_payload, timeout=CONFIG["poll_timeout"] + 5)
            if fail_count > 0:
                logger.info("中继工作线程 #%d 已恢复连接 (此前连续异常 %d 次)", worker_id, fail_count)
                fail_count = 0
            if not data["has_task"]:
                continue
            result = execute_intranet_request(data["task"])
            send_response_to_phoenix(result)

        except urllib.error.HTTPError as e:
            fail_count += 1
            if e.code == 403:
                logger.critical("中继密钥 (tunnel_secret) 错误，请检查配置！HTTP 403")
                time.sleep(10)
            else:
                logger.warning("轮询服务异常 (线程 #%d, HTTP %s): %s", worker_id, e.code, e.reason)
                time.sleep(20 if e.code == 429 else 2)
        except urllib.error.URLError as e:
            fail_count += 1
            if fail_count <= 3 or fail_count % 10 == 0:
                logger.warning("无法连接 Phoenix 服务器 (%s): %s (将自动重试)", server_base, e.reason)
            time.sleep(2)
        except Exception as e:
            fail_count += 1
            logger.error("轮询异常 (线程 #%d, %s): %s", worker_id, type(e).__name__, e)
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
    setup_logging()
    print("=" * 70)
    print(" 🦅 Phoenix 智慧供热平台内网反向中继客户端 (Win7 + Python 3.8)")
    print("=" * 70)
    print(f" 目标内网系统: {CONFIG['intranet_base_url']}")
    print(f" 云端中继地址: {CONFIG['phoenix_server_url']}")
    print(f" 并发轮询通道: {CONFIG['concurrency']} 个线程")
    print(f" 配置来源: {CONFIG_FILE}（存在时覆盖脚本内置配置）")
    print(f" 日志文件: {LOG_FILE}（单文件上限 5MB，最多保留 {LOG_BACKUP_COUNT} 份）")
    print("=" * 70)

    logger.info(
        "启动中继客户端 | 目标内网=%s | 云端地址=%s | 并发=%s | poll_timeout=%s | 日志=%s",
        CONFIG["intranet_base_url"],
        CONFIG["phoenix_server_url"],
        CONFIG["concurrency"],
        CONFIG["poll_timeout"],
        LOG_FILE,
    )

    # 1. 测试内网平台连通
    test_intranet_connectivity()

    # 2. 启动并发工作线程池
    threads = []
    concurrency = int(CONFIG.get("concurrency") or 6)
    for i in range(1, concurrency + 1):
        t = threading.Thread(target=poll_worker_loop, args=(i,), name=f"Worker-{i}", daemon=True)
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
