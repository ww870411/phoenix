# -*- coding: utf-8 -*-
"""智慧供热旁路精算与质检平台 —— 采集配置与 Cookie 设置单元测试。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.projects.smart_heating_platform.services import collector_config_service as svc
from backend.services.auth_manager import ActionFlags, AuthSession, GroupPermissions, get_current_session


def _build_session(group: str, username: str = "tester") -> AuthSession:
    return AuthSession(
        username=username,
        group=group,
        unit="主城区",
        hierarchy=1 if group == "Global_admin" else 2,
        permissions=GroupPermissions(
            name=group,
            hierarchy=1 if group == "Global_admin" else 2,
            page_access={"*"},
            sheet_rules={},
            units_access=["主城区"],
            actions=ActionFlags(),
            projects={},
        ),
        allowed_units={"主城区"},
        token="test-token",
        issued_at=datetime.now(timezone.utc),
    )


def test_cookie_normalization_and_masking():
    assert svc.normalize_cookie_input("Cookie: session=.eJx1234567890abcdef") == "session=.eJx1234567890abcdef"
    assert svc.normalize_cookie_input(".eJx1234567890abcdef") == "session=.eJx1234567890abcdef"
    masked = svc.mask_cookie("session=.eJx9lF2PojAUhv8L114giF93Agvd4pqVkvARk4bVj")
    assert "***" in masked
    assert "lF2PojAUhv8L114giF93Agvd4pqVkvAR" not in masked


def test_collector_settings_crud_and_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr(svc, "DATA_DIRECTORY", tmp_path)

    app = create_app()
    client = TestClient(app)

    # 1. 非 Global_admin 被 403 拦截
    app.dependency_overrides[get_current_session] = lambda: _build_session("Group_admin", "group_user")
    res_forbidden = client.get("/api/v1/projects/smart_heating_platform/settings/collector")
    assert res_forbidden.status_code == 403

    # 2. Global_admin 正常读取默认值
    app.dependency_overrides[get_current_session] = lambda: _build_session("Global_admin", "ww870411")
    res_get = client.get("/api/v1/projects/smart_heating_platform/settings/collector")
    assert res_get.status_code == 200
    body = res_get.json()
    assert body["ok"] is True
    assert body["data"]["has_cookie"] is False
    assert body["data"]["effective_base_url"] == svc.PUBLIC_SOURCE_URL
    assert body["data"]["snapshot_interval_minutes"] == 5
    assert body["data"]["max_workers"] == 4
    assert body["data"]["table_bottom_sync_hours"] == 1

    # 3. 保存新 Cookie、间隔与并发线程数
    res_put = client.put(
        "/api/v1/projects/smart_heating_platform/settings/collector",
        json={
            "source_mode": "public",
            "cookie": ".eJx9SecretTestSessionCookieValue123456789",
            "snapshot_interval_minutes": 5,
            "max_workers": 6,
            "request_interval_seconds": 0.9,
            "hourly_offset_minutes": 8,
        },
    )
    assert res_put.status_code == 200
    saved = res_put.json()["data"]
    assert saved["has_cookie"] is True
    assert "SecretTestSessionCookieValue" not in saved["cookie_masked"]
    assert saved["snapshot_interval_minutes"] == 5
    assert saved["max_workers"] == 6
    assert saved["request_interval_seconds"] == 0.9
    assert saved["hourly_offset_minutes"] == 8
    assert saved["updated_by"] == "ww870411"

    # 3b. 并发线程数越界拦截
    res_bad_workers = client.put(
        "/api/v1/projects/smart_heating_platform/settings/collector",
        json={"max_workers": 32},
    )
    assert res_bad_workers.status_code == 400

    # 4. 仅修改其他参数时不传 cookie，应保留既有 Cookie
    res_put_partial = client.put(
        "/api/v1/projects/smart_heating_platform/settings/collector",
        json={"source_mode": "intranet"},
    )
    assert res_put_partial.status_code == 200
    partial_data = res_put_partial.json()["data"]
    assert partial_data["has_cookie"] is True
    assert partial_data["effective_base_url"] == svc.INTRANET_SOURCE_URL

    # 5. 请求间隔低于 0.5 秒被拒绝（保护源站 Werkzeug）
    res_bad = client.put(
        "/api/v1/projects/smart_heating_platform/settings/collector",
        json={"request_interval_seconds": 0.1},
    )
    assert res_bad.status_code == 400

    # 6. 清空 Cookie
    res_clear = client.put(
        "/api/v1/projects/smart_heating_platform/settings/collector",
        json={"clear_cookie": True},
    )
    assert res_clear.status_code == 200
    assert res_clear.json()["data"]["has_cookie"] is False
