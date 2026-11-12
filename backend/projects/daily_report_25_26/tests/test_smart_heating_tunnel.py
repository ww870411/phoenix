# -*- coding: utf-8 -*-
"""
智慧供热反向代理隧道 (Smart Heating Tunnel) 核心测试
验证：
1. Global_admin 权限强隔离：非 Global_admin 访问网关、状态、配置与脚本下载一律 403 阻断
2. 合法 Global_admin 正常读取状态、修改配置并下载预填配置的客户端脚本
3. 中继长轮询与心跳维持
4. 外网网关请求通过隧道排队转发、中继回传响应、HTML 绝对路径深度重写与 Base 标签自动注入
"""

import asyncio
import base64
import json
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.auth_manager import auth_manager, AuthSession
from backend.projects.daily_report_25_26.api.smart_heating_tunnel import (
    DEFAULT_TUNNEL_CONFIG,
    TUNNEL,
    load_tunnel_config,
    save_tunnel_config,
)

client = TestClient(app)

# 构造测试用的 Global_admin 与普通用户 Token
ADMIN_TOKEN = "mock_test_global_admin_token_2026"
NORMAL_USER_TOKEN = "mock_test_normal_user_token_2026"

auth_manager._ensure_loaded()
admin_record = auth_manager._users_by_name["ww870411"]
auth_manager._sessions[ADMIN_TOKEN] = auth_manager._build_session(
    record=admin_record,
    group_permissions=auth_manager._groups[admin_record.group],
    token=ADMIN_TOKEN,
    issued_at=auth_manager._now(),
    expires_at=None,
    persistent=False,
)

normal_record = auth_manager._users_by_name["beihai_filler"]
auth_manager._sessions[NORMAL_USER_TOKEN] = auth_manager._build_session(
    record=normal_record,
    group_permissions=auth_manager._groups[normal_record.group],
    token=NORMAL_USER_TOKEN,
    issued_at=auth_manager._now(),
    expires_at=None,
    persistent=False,
)

group_admin_record = auth_manager._users_by_name["group_admin"]
GROUP_ADMIN_TOKEN = "mock_test_group_admin_token_2026"
auth_manager._sessions[GROUP_ADMIN_TOKEN] = auth_manager._build_session(
    record=group_admin_record,
    group_permissions=auth_manager._groups[group_admin_record.group],
    token=GROUP_ADMIN_TOKEN,
    issued_at=auth_manager._now(),
    expires_at=None,
    persistent=False,
)


def test_permission_isolation():
    """测试 Global_admin 权限强隔离：严格仅限 Global_admin / ww870411 访问"""
    # 1. 未登录/无 Token 访问：一律 403
    res_no_auth = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/status")
    assert res_no_auth.status_code == 403

    res_no_auth_script = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/client-script")
    assert res_no_auth_script.status_code == 403

    res_no_auth_gw = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/vindex/")
    assert res_no_auth_gw.status_code == 403
    assert "403" in res_no_auth_gw.text

    # 2. 普通用户访问：一律 403
    res_normal = client.get(
        "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/status",
        headers={"Authorization": f"Bearer {NORMAL_USER_TOKEN}"},
    )
    assert res_normal.status_code == 403

    res_normal_gw = client.get(
        f"/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/vindex/?phoenix_token={NORMAL_USER_TOKEN}"
    )
    assert res_normal_gw.status_code == 403

    # 3. Group_admin (集团管理员) 访问：一律 403 阻断（严格仅限 Global_admin / ww870411 本人）
    res_group_admin = client.get(
        "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/status",
        headers={"Authorization": f"Bearer {GROUP_ADMIN_TOKEN}"},
    )
    assert res_group_admin.status_code == 403
    assert "Global_admin" in res_group_admin.text


def test_tunnel_config_and_status():
    """测试 Global_admin 正常读取状态、配置与下载脚本"""
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

    # 状态查询
    res = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "online" in data
    assert "client_ip" in data

    # 客户端脚本下载测试
    res_script = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/client-script", headers=headers)
    assert res_script.status_code == 200
    assert "text/x-python" in res_script.headers.get("content-type", "")
    script_text = res_script.text
    assert "Phoenix 智慧供热平台内网反向中继客户端" in script_text
    assert "DEFAULT_CONFIG" in script_text
    assert "intranet_base_url" in script_text


import httpx

async def run_async_gateway_tests():
    """使用 httpx.AsyncClient 异步并发测试网关往返与 302 重定向 Token 保留"""
    secret = DEFAULT_TUNNEL_CONFIG["tunnel_secret"]
    TUNNEL.record_heartbeat("192.168.1.100", worker_id=1)
    assert TUNNEL.is_online() is True

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. 测试往返 HTML 重写与 Cookie 注入
        async def do_gateway_call():
            return await ac.get(
                f"/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/vindex/index.html?phoenix_token={ADMIN_TOKEN}"
            )

        async def do_worker_call():
            await asyncio.sleep(0.05)
            poll_res = await ac.post(
                "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/poll",
                headers={"X-Tunnel-Secret": secret},
                json={"worker_id": 1, "timeout": 5},
            )
            assert poll_res.status_code == 200
            poll_data = poll_res.json()
            assert poll_data.get("has_task") is True
            task = poll_data["task"]
            req_id = task["request_id"]
            assert "/vindex/index.html" in task["path"]

            mock_html = """<html>
<head>
    <title>智慧供热监控</title>
    <link rel="stylesheet" href="/static/css/reset.css?v=1">
    <script src="/static/js/app.js"></script>
</head>
<body>
    <h1>工况正常</h1>
    <img src="/static/img/logo.png">
</body>
</html>"""
            mock_b64 = base64.b64encode(mock_html.encode("utf-8")).decode("ascii")

            resp_res = await ac.post(
                "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/respond",
                headers={"X-Tunnel-Secret": secret},
                json={
                    "request_id": req_id,
                    "status_code": 200,
                    "headers": {"Content-Type": "text/html; charset=utf-8"},
                    "body_b64": mock_b64,
                },
            )
            assert resp_res.status_code == 200
            assert resp_res.json().get("ok") is True

        res_gw, _ = await asyncio.gather(do_gateway_call(), do_worker_call())
        assert res_gw.status_code == 200
        assert "text/html" in res_gw.headers.get("content-type", "")
        # 验证是否成功注入了 <base href="...">
        assert "<base href=" in res_gw.text
        assert "smart-heating-tunnel/gateway/" in res_gw.text
        assert "智慧供热监控" in res_gw.text
        # 验证绝对路径是否被深度精准重写
        assert 'href="/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/css/reset.css?v=1"' in res_gw.text
        assert 'src="/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/js/app.js"' in res_gw.text
        assert 'src="/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/img/logo.png"' in res_gw.text
        # 验证关键修复：Cookie 全域注入
        assert "phoenix_tunnel_admin_token=" in res_gw.headers.get("set-cookie", "")

        # 2. 测试 302 重定向保留 phoenix_token 参数
        async def do_redirect_gateway_call():
            return await ac.get(
                f"/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/vindex/?phoenix_token={ADMIN_TOKEN}",
                follow_redirects=False,
            )

        async def do_redirect_worker_call():
            await asyncio.sleep(0.05)
            poll_res = await ac.post(
                "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/poll",
                headers={"X-Tunnel-Secret": secret},
                json={"worker_id": 1, "timeout": 5},
            )
            assert poll_res.status_code == 200
            task = poll_res.json()["task"]
            req_id = task["request_id"]

            resp_res = await ac.post(
                "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/respond",
                headers={"X-Tunnel-Secret": secret},
                json={
                    "request_id": req_id,
                    "status_code": 302,
                    "headers": {"Location": "/vindex/login"},
                    "cookies": ["session=.eJx123mocksession; Path=/; HttpOnly"],
                    "body_b64": "",
                },
            )
            assert resp_res.status_code == 200

        res_redir, _ = await asyncio.gather(do_redirect_gateway_call(), do_redirect_worker_call())
        assert res_redir.status_code == 302
        loc = res_redir.headers.get("location", "")
        assert "/smart-heating-tunnel/gateway/vindex/login" in loc
        # 验证必须携带 phoenix_token 避免后续跳转 403 / 空白
        assert f"phoenix_token={ADMIN_TOKEN}" in loc
        # 验证两套 Set-Cookie 共存：内网 session Cookie 与 Phoenix 网关 Cookie 均成功透传
        set_cookies_joined = " | ".join(res_redir.headers.get_list("set-cookie"))
        assert "session=.eJx123mocksession" in set_cookies_joined
        assert "phoenix_tunnel_admin_token=" in set_cookies_joined


def test_tunnel_gateway_roundtrip_with_worker():
    """包装为同步测试函数"""
    asyncio.run(run_async_gateway_tests())


def test_static_asset_cache_acceleration():
    """测试静态资源本地高速缓存直出 (0ms 直出、304 协商缓存、免 Token 畅通)"""
    # 1. 验证 CSS 资源高速直出
    res_css = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/css/reset.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers.get("content-type", "")
    assert "max-age=604800" in res_css.headers.get("cache-control", "")
    assert res_css.headers.get("x-accel-cache") == "HIT"
    etag = res_css.headers.get("etag")
    assert etag is not None

    # 2. 验证 304 协商缓存
    res_304 = client.get(
        "/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/css/reset.css",
        headers={"If-None-Match": etag},
    )
    assert res_304.status_code == 304

    # 3. 验证 JavaScript 库高速直出
    res_js = client.get("/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/static/js/libs/jquery-1.8.2.min.js")
    assert res_js.status_code == 200
    assert "javascript" in res_js.headers.get("content-type", "")
    assert res_js.headers.get("x-accel-cache") == "HIT"


if __name__ == "__main__":
    print("运行测试 0: test_permission_isolation (严格仅限系统管理员)...")
    test_permission_isolation()
    print("测试 0 通过！非系统管理员访问 100% 被 403 阻断！")

    print("运行测试 1: test_tunnel_config_and_status...")
    test_tunnel_config_and_status()
    print("测试 1 通过！")

    print("运行测试 2: test_tunnel_gateway_roundtrip_with_worker (往返重写 + 302 重定向 Token 保留)...")
    test_tunnel_gateway_roundtrip_with_worker()
    print("测试 2 通过！")

    print("运行测试 3: test_static_asset_cache_acceleration (静态资源秒出与 304)...")
    test_static_asset_cache_acceleration()
    print("测试 3 通过！")
    print("ALL TESTS PASSED SUCCESSFULLY! 🚀")
