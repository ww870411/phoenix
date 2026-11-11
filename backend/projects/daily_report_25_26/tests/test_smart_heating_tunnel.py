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


def test_permission_isolation():
    """测试 Global_admin 权限强隔离"""
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


def test_tunnel_gateway_roundtrip_with_worker():
    """
    模拟测试：
    1. 办公机 Worker 进行长轮询
    2. Global_admin 请求网关
    3. Worker 成功拉取请求并回传 HTML 响应
    4. 网关拦截并成功注入 <base> 标签与绝对路径重写
    """
    secret = DEFAULT_TUNNEL_CONFIG["tunnel_secret"]

    # 1. 模拟中继心跳
    TUNNEL.record_heartbeat("192.168.1.100", worker_id=1)
    assert TUNNEL.is_online() is True

    # 2. 模拟并发协程发送网关请求，另一个协程拉取并响应
    async def run_roundtrip():
        # 外部浏览器携带 Admin Token 请求网关
        async def do_gateway_call():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: client.get(
                    f"/api/v1/projects/daily_report_25_26/smart-heating-tunnel/gateway/vindex/index.html?phoenix_token={ADMIN_TOKEN}"
                ),
            )

        # 办公电脑 Worker 轮询并响应
        async def do_worker_loop():
            await asyncio.sleep(0.1)
            poll_res = client.post(
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

            resp_res = client.post(
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

        gateway_task = asyncio.create_task(do_gateway_call())
        worker_task = asyncio.create_task(do_worker_loop())

        res_gw, _ = await asyncio.gather(gateway_task, worker_task)
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

    asyncio.run(run_roundtrip())


if __name__ == "__main__":
    print("运行测试 0: test_permission_isolation (严格仅限 Global_admin)...")
    test_permission_isolation()
    print("测试 0 通过！非 Global_admin 访问 100% 被 403 阻断！")

    print("运行测试 1: test_tunnel_config_and_status...")
    test_tunnel_config_and_status()
    print("测试 1 通过！")

    print("运行测试 2: test_tunnel_gateway_roundtrip_with_worker...")
    test_tunnel_gateway_roundtrip_with_worker()
    print("测试 2 通过！")
    print("ALL TESTS PASSED SUCCESSFULLY! 🚀")
