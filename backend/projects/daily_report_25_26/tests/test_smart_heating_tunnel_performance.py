# -*- coding: utf-8 -*-
"""中继调度、缓存隔离和真实 HTTP 连接复用回归；所有配置与缓存均使用测试目录。"""

import ast
import asyncio
import base64
import gzip
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib import request as urllib_request

import httpx
import pytest
from fastapi import FastAPI

from backend.projects.daily_report_25_26.api import smart_heating_tunnel as tunnel


PREFIX = "/api/v1/projects/daily_report_25_26/smart-heating-tunnel"


@pytest.fixture
def gateway(monkeypatch, tmp_path):
    """隔离业务配置、队列和文件，不向实际中继派发任务。"""
    config = dict(tunnel.DEFAULT_TUNNEL_CONFIG, auth_password="保留的测试密码")
    monkeypatch.setattr(tunnel, "TUNNEL", tunnel.TunnelManager())
    monkeypatch.setattr(tunnel, "STATIC_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(tunnel, "FALLBACK_STATIC_CACHE_DIR", tmp_path / "seed")
    monkeypatch.setattr(tunnel, "STATIC_MEMORY_CACHE", {})
    monkeypatch.setattr(tunnel, "STATIC_CACHE_TIMES", {})
    monkeypatch.setattr(tunnel, "load_tunnel_config", lambda: dict(config))
    monkeypatch.setattr(tunnel, "save_tunnel_config", config.update)
    monkeypatch.setattr(tunnel, "verify_global_admin_access", lambda req: SimpleNamespace(token=""))
    tunnel.TUNNEL.record_heartbeat("test")
    app = FastAPI()
    app.include_router(tunnel.public_router, prefix="/api/v1/projects/daily_report_25_26")
    app.include_router(tunnel.router, prefix="/api/v1/projects/daily_report_25_26")
    return app, config


async def exchange(ac, body=b"body", content_type="application/javascript"):
    """模拟办公电脑的一次真实 poll/respond 往返。"""
    secret = tunnel.load_tunnel_config()["tunnel_secret"]
    headers = {"X-Tunnel-Secret": secret}
    polled = await ac.post(PREFIX + "/poll", headers=headers, json={"timeout": 5})
    assert polled.status_code == 200
    task = polled.json()["task"]
    replied = await ac.post(PREFIX + "/respond", headers=headers, json={
        "request_id": task["request_id"], "status_code": 200,
        "headers": {"Content-Type": content_type},
        "body_b64": base64.b64encode(body).decode("ascii"), "duration_ms": 2,
    })
    assert replied.json()["ok"]
    return task


def test_twenty_concurrent_assets_only_dispatch_once(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            calls = [asyncio.create_task(ac.get(PREFIX + "/gateway/static/shared.js?v=2")) for _ in range(20)]
            task = await exchange(ac, b"window.shared=1;")
            results = await asyncio.gather(*calls)
            assert all(r.status_code == 200 and r.content == b"window.shared=1;" for r in results)
            assert tunnel.TUNNEL.request_queue.empty()
            assert not tunnel.TUNNEL.pending_futures
            assert not tunnel.TUNNEL.static_inflight
            assert task["path"] == "/static/shared.js"
            assert "intranet;dur=2" in results[0].headers["server-timing"]
            cached = await ac.get(PREFIX + "/gateway/static/shared.js?v=2")
            assert cached.headers["x-accel-cache"] == "HIT"
            assert tunnel.TUNNEL.request_queue.empty()
    asyncio.run(run())


def test_versions_and_targets_get_distinct_assets(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            for version, body in [("1", b"one"), ("2", b"two")]:
                call = asyncio.create_task(ac.get(PREFIX + "/gateway/static/app.js?v=" + version))
                await exchange(ac, body)
                assert (await call).content == body
            assert (await ac.get(PREFIX + "/gateway/static/app.js?v=1")).content == b"one"
            gateway[1]["target_base_url"] = "http://another-platform:6688"
            call = asyncio.create_task(ac.get(PREFIX + "/gateway/static/app.js?v=1"))
            await exchange(ac, b"another")
            assert (await call).content == b"another"
    asyncio.run(run())


def test_expired_cache_reloads_and_head_has_no_body(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            url = PREFIX + "/gateway/static/reload.js"
            call = asyncio.create_task(ac.get(url))
            await exchange(ac, b"old")
            old = await call
            assert old.headers["etag"] == (await ac.get(url)).headers["etag"]
            key = next(iter(tunnel.STATIC_CACHE_TIMES))
            tunnel.STATIC_CACHE_TIMES[key] -= tunnel.STATIC_CACHE_TTL + 1
            call = asyncio.create_task(ac.get(url, headers={"If-None-Match": old.headers["etag"]}))
            task = await exchange(ac, b"new-content")
            assert "if-none-match" not in task["headers"]
            assert (await call).content == b"new-content"
            head = await ac.head(url)
            assert head.content == b"" and head.headers["content-length"] == "11"
            cached = await ac.get(url)
            unchanged = await ac.get(url, headers={"If-None-Match": cached.headers["etag"]})
            assert unchanged.status_code == 304
    asyncio.run(run())


def test_known_seed_version_avoids_relay(gateway):
    seed = tunnel.FALLBACK_STATIC_CACHE_DIR / "static" / "seed.js"
    seed.parent.mkdir(parents=True)
    seed.write_bytes(b"known-v1")
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            seeded = await ac.get(PREFIX + "/gateway/static/seed.js?v=1")
            assert seeded.content == b"known-v1" and seeded.headers["x-accel-cache"] == "HIT"
            assert tunnel.TUNNEL.request_queue.empty()
            call = asyncio.create_task(ac.get(PREFIX + "/gateway/static/seed.js?v=2"))
            await exchange(ac, b"new-v2")
            assert (await call).content == b"new-v2"
    asyncio.run(run())


def test_gateway_timeout_cleans_pending_and_skips_expired_task(gateway, monkeypatch):
    monkeypatch.setattr(tunnel, "TUNNEL_REQUEST_TIMEOUT", 0.02)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            timed_out = await ac.get(PREFIX + "/gateway/slow-data")
            assert timed_out.status_code == 504
            assert not tunnel.TUNNEL.pending_futures
            assert (await ac.get(PREFIX + "/status")).json()["pending_requests"] == 0
            monkeypatch.setattr(tunnel, "TUNNEL_REQUEST_TIMEOUT", 60)
            active = asyncio.create_task(ac.get(PREFIX + "/gateway/current-data"))
            task = await exchange(ac, b'{}', "application/json")
            assert task["path"] == "/current-data"
            assert (await active).status_code == 200
            assert tunnel.TUNNEL.request_queue.empty()
    asyncio.run(run())


def test_poll_skips_cancelled_task(gateway):
    async def run():
        manager = tunnel.TUNNEL
        stale = asyncio.create_task(manager.dispatch({"request_id": "stale", "created_at": time.time()}))
        await asyncio.sleep(0)
        stale.cancel()
        with pytest.raises(asyncio.CancelledError):
            await stale
        active = asyncio.create_task(manager.dispatch({"request_id": "active", "created_at": time.time()}))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            task = await exchange(ac)
        assert task["request_id"] == "active"
        await active
        assert manager.request_queue.empty()
    asyncio.run(run())


def test_cancelled_static_caller_does_not_cancel_shared_work(gateway):
    async def run():
        manager = tunnel.TUNNEL
        first = asyncio.create_task(manager.dispatch({"request_id": "shared", "created_at": time.time()}, "asset"))
        second = asyncio.create_task(manager.dispatch({"request_id": "unused", "created_at": time.time()}, "asset"))
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            await exchange(ac)
        assert (await second).status_code == 200
        assert manager.request_queue.empty()
    asyncio.run(run())


def test_password_and_downloaded_server_address(gateway, monkeypatch):
    monkeypatch.delenv("PHOENIX_TUNNEL_PUBLIC_URL", raising=False)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://backend:8000") as ac:
            saved = await ac.post(PREFIX + "/config", json={"auth_password": "", "portal_path": "/changed/"})
            assert saved.status_code == 200
            assert gateway[1]["auth_password"] == "保留的测试密码"
            downloaded = await ac.get(PREFIX + "/client-script")
            assert '"phoenix_server_url": "https://platform.smartview.top"' in downloaded.text
            assert "def post_phoenix_json" in downloaded.text
            gateway[1]["auth_password"] = "路径\\test\\u1234"
            downloaded = await ac.get(PREFIX + "/client-script")
            ast.parse(downloaded.text, feature_version=(3, 8))
            monkeypatch.setenv("PHOENIX_TUNNEL_PUBLIC_URL", "https://configured.example/")
            downloaded = await ac.get(PREFIX + "/client-script")
            assert '"phoenix_server_url": "https://configured.example"' in downloaded.text
    asyncio.run(run())


def test_html_relative_base_and_jquery_deduplication(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            call = asyncio.create_task(ac.get(PREFIX + "/gateway/vindex/nested/index.html"))
            html = b'<html><head><base href="/wrong/"><script src="/static/js/libs/jquery-1.8.2.min.js"></script></head><body></body></html>'
            await exchange(ac, html, "text/html")
            rendered = (await call).text
            assert rendered.count("jquery-1.8.2.min.js") == 1
            assert rendered.count("<base ") == 1
            assert 'gateway/vindex/nested/">' in rendered
    asyncio.run(run())


def load_relay_without_local_config():
    """只替换模块初始化的配置读取，执行真实客户端函数，避免生成办公电脑配置文件。"""
    path = tunnel._get_client_script_template_path()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CONFIG" for t in node.targets):
            node.value = ast.Name(id="DEFAULT_CONFIG", ctx=ast.Load())
    namespace = {"__file__": str(path), "__name__": "relay_test"}
    exec(compile(ast.fix_missing_locations(tree), str(path), "exec"), namespace)
    return namespace


def test_real_http_connection_reuse():
    relay = load_relay_without_local_config()
    connections = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            connections.append(self.client_address)
            time.sleep(0.02)  # 固定模拟每次建连的开销，只比较相同环境中的连接数和耗时。

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = b'{"ok":true,"has_task":false}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    relay["CONFIG"]["phoenix_server_url"] = "http://127.0.0.1:" + str(server.server_port)
    try:
        started = time.perf_counter()
        for _ in range(10):
            with urllib_request.urlopen(urllib_request.Request(
                relay["CONFIG"]["phoenix_server_url"] + "/baseline", data=b"{}",
            )) as response:
                response.read()
        baseline_ms = (time.perf_counter() - started) * 1000
        assert len(connections) == 10
        connections.clear()
        started = time.perf_counter()
        for _ in range(5):
            relay["post_phoenix_json"]("poll", b"{}", timeout=2)
            relay["post_phoenix_json"]("respond", b"{}", timeout=2)
        reused_ms = (time.perf_counter() - started) * 1000
        assert len(connections) == 1
        print(f"\n真实 HTTP 回归：10 次请求，连接数 10 → 1；模拟建连开销 20 ms，耗时 {baseline_ms:.1f} → {reused_ms:.1f} ms")
    finally:
        connection = getattr(relay["PHOENIX_CONNECTION"], "connection", None)
        if connection is not None:
            connection.close()
        server.shutdown()
        server.server_close()
        worker.join()


def test_relay_file_logging_in_same_directory(tmp_path):
    relay = load_relay_without_local_config()
    expected_default = tunnel._get_client_script_template_path().parent / "smart_heating_tunnel.log"
    assert Path(relay["LOG_FILE"]) == expected_default

    log_path = tmp_path / "smart_heating_tunnel.log"
    relay["setup_logging"](str(log_path))
    try:
        relay["logger"].info("中继日志落盘测试 %s", "OK")
        for h in relay["logger"].handlers:
            h.flush()
        content = log_path.read_text(encoding="utf-8")
        assert "中继日志落盘测试 OK" in content
    finally:
        # 清理测试挂载的临时文件处理器，避免影响同进程其他测试
        for h in list(relay["logger"].handlers):
            if getattr(h, "baseFilename", None) == str(log_path):
                relay["logger"].removeHandler(h)
                h.close()
        relay["logger"]._file_logging_configured = False


def test_gzip_respond_and_client_compression(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            big_body = ("<div>工况数据</div>" * 300).encode("utf-8")
            call = asyncio.create_task(ac.get(PREFIX + "/gateway/fhrjl_ssxx/"))
            secret = tunnel.load_tunnel_config()["tunnel_secret"]
            headers = {"X-Tunnel-Secret": secret}
            polled = await ac.post(PREFIX + "/poll", headers=headers, json={"timeout": 5})
            task = polled.json()["task"]
            raw_json = json.dumps({
                "request_id": task["request_id"],
                "status_code": 200,
                "headers": {"Content-Type": "text/html; charset=utf-8"},
                "body_b64": base64.b64encode(big_body).decode("ascii"),
                "duration_ms": 12,
            }).encode("utf-8")
            gz_json = gzip.compress(raw_json)
            assert len(gz_json) < len(raw_json)
            replied = await ac.post(
                PREFIX + "/respond",
                headers={**headers, "Content-Encoding": "gzip", "Content-Type": "application/json"},
                content=gz_json,
            )
            assert replied.status_code == 200 and replied.json()["ok"] is True
            resp = await call
            assert resp.status_code == 200
            assert "工况数据" in resp.text

    asyncio.run(run())

    relay = load_relay_without_local_config()
    captured = {}

    def fake_post(endpoint, payload, timeout, content_encoding=None):
        captured["endpoint"] = endpoint
        captured["payload"] = payload
        captured["content_encoding"] = content_encoding
        return {"ok": True}

    relay["post_phoenix_json"] = fake_post
    relay["send_response_to_phoenix"]({
        "request_id": "req-gz-1",
        "status_code": 200,
        "headers": {},
        "cookies": [],
        "body_b64": base64.b64encode(b"A" * 5000).decode("ascii"),
        "duration_ms": 5,
    })
    assert captured["endpoint"] == "respond"
    assert captured["content_encoding"] == "gzip"
    decoded = json.loads(gzip.decompress(captured["payload"]).decode("utf-8"))
    assert decoded["request_id"] == "req-gz-1"


def test_history_links_options_and_js_navigation_rewritten(gateway):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway[0]), base_url="http://test") as ac:
            html = (
                '<html><head></head><body>'
                '<a href = "/bj_ls_xx/">报警历史</a>'
                '<a href="http://192.168.1.206:6688/fhrjl_lsxx/">历史记录</a>'
                '<select id="selectpath"><option value="/ry_ssxx/">热源</option></select>'
                '<button onclick="window.open(\'/ls_popup/\')">弹窗</button>'
                '<script>location.href = \'/ls_script/\';</script>'
                '</body></html>'
            ).encode("utf-8")
            call = asyncio.create_task(ac.get(PREFIX + "/gateway/gk_ssxx/"))
            await exchange(ac, html, "text/html; charset=utf-8")
            rendered = (await call).text
            assert f'href="{PREFIX}/gateway/bj_ls_xx/"' in rendered
            assert f'href="{PREFIX}/gateway/fhrjl_lsxx/"' in rendered
            assert f'<option value="{PREFIX}/gateway/ry_ssxx/">' in rendered
            assert f"window.open('{PREFIX}/gateway/ls_popup/')" in rendered
            assert f"location.href = '{PREFIX}/gateway/ls_script/'" in rendered
            assert "window.__phoenixGatewayUrl" in rendered
            assert "origWindowOpen" in rendered

            js_call = asyncio.create_task(ac.get(PREFIX + "/gateway/static/js/jc/custom.js"))
            await exchange(
                ac,
                b"function go(){ window.location.href = '/ls_js/'; window.open('http://192.168.1.206:6688/ls2/'); }",
                "application/javascript",
            )
            js_rendered = (await js_call).text
            assert f"window.location.href = '{PREFIX}/gateway/ls_js/'" in js_rendered
            assert f"window.open('{PREFIX}/gateway/ls2/')" in js_rendered

    asyncio.run(run())
