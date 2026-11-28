# -*- coding: utf-8 -*-
"""会议排座助手后端存储与权限单测。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.projects.meeting_seating.api.router import router as meeting_seating_router
from backend.projects.meeting_seating.services import profile_store
from backend.services.auth_manager import get_current_session


def _make_session(group: str, groups=None, username: str = "tester"):
    return SimpleNamespace(
        username=username,
        group=group,
        groups=groups if groups is not None else [group],
    )


def test_profile_store_crud_and_row_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg_path = tmp_path / "seating_profiles.json"
    monkeypatch.setattr(profile_store, "resolve_profiles_config_path", lambda: cfg_path)

    initial = profile_store.list_profiles()
    assert initial["profiles"]
    active = initial["active_profile"]
    layout = active["layout"]

    # 默认按边/排管理：共8排，屏幕席6席、主席席7席、其余6排各8席（共61席）
    assert len(layout["rows"]) == 8
    expected_counts = {"A": 6, "B": 7, "C": 8, "D": 8, "E": 8, "F": 8, "G": 8, "H": 8}
    for r in layout["rows"]:
        assert len(r["seats"]) == expected_counts[r["id"]]
        if r["zone"] == "rear":
            assert r["tableCount"] == 4
        else:
            assert r["tableCount"] == 3
    assert len(layout["plants"]) == 4
    assert layout["paper"] == "portrait"
    assert layout["room"]["door"]["enabled"] is True
    assert layout["room"]["equipmentRoom"]["enabled"] is True
    assert layout["room"]["leftWindows"] == 4
    assert layout["room"]["rightWindows"] == 4

    # 新建存档
    created = profile_store.create_profile("班子会方案", source_profile_id=active["id"])
    new_id = created["profile"]["id"]
    assert created["active_id"] == new_id
    assert len(created["profiles"]) == 2

    # 修改并保存姓名、单座隐藏、整排隐藏及花盆位置
    edited_layout = created["profile"]["layout"]
    edited_layout["rows"][0]["seats"][0]["name"] = "张主任"
    edited_layout["rows"][0]["seats"][1]["hidden"] = True
    edited_layout["rows"][-1]["hidden"] = True
    edited_layout["plants"][0]["x"] = 410
    edited_layout["plants"][0]["y"] = 360
    edited_layout["emptySeatDisplay"] = "dash"
    updated = profile_store.update_profile(new_id, layout=edited_layout)
    saved_layout = updated["profile"]["layout"]
    assert saved_layout["rows"][0]["seats"][0]["name"] == "张主任"
    assert saved_layout["rows"][0]["seats"][1]["hidden"] is True
    assert saved_layout["rows"][-1]["hidden"] is True
    assert saved_layout["plants"][0]["x"] == 410
    assert saved_layout["emptySeatDisplay"] == "dash"

    # 重命名存档
    renamed = profile_store.rename_profile(new_id, "年度扩大会议方案")
    assert renamed["profile"]["name"] == "年度扩大会议方案"

    # 删除存档（保留至少 1 个）
    deleted = profile_store.delete_profile(new_id)
    assert len(deleted["profiles"]) == 1
    with pytest.raises(ValueError, match="至少保留一个布局存档"):
        profile_store.delete_profile(deleted["active_id"])


def test_global_admin_only_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from backend.projects.meeting_seating.api.router import _require_global_admin

    _require_global_admin(_make_session("Global_admin"))
    _require_global_admin(_make_session("Group_admin", groups=["Group_admin", "Global_admin"]))

    for role in ("Group_admin", "ZhuChengQu_admin", "Unit_admin", "unit_filler", "Group_viewer"):
        with pytest.raises(HTTPException) as exc_info:
            _require_global_admin(_make_session(role))
        assert exc_info.value.status_code == 403

    cfg_path = tmp_path / "api_profiles.json"
    monkeypatch.setattr(profile_store, "resolve_profiles_config_path", lambda: cfg_path)

    app = FastAPI()
    app.include_router(meeting_seating_router, prefix="/api/v1/projects/meeting_seating")

    current_user = {"session": _make_session("Unit_admin")}
    app.dependency_overrides[get_current_session] = lambda: current_user["session"]
    client = TestClient(app)

    resp_forbidden = client.get("/api/v1/projects/meeting_seating/profiles")
    assert resp_forbidden.status_code == 403

    current_user["session"] = _make_session("Global_admin")
    resp_ok = client.get("/api/v1/projects/meeting_seating/profiles")
    assert resp_ok.status_code == 200
    assert resp_ok.json()["ok"] is True

    resp_create = client.post(
        "/api/v1/projects/meeting_seating/profiles",
        json={"name": "测试方案A"},
    )
    assert resp_create.status_code == 200
    pid = resp_create.json()["profile"]["id"]

    resp_rename = client.patch(
        f"/api/v1/projects/meeting_seating/profiles/{pid}/rename",
        json={"name": "测试方案B"},
    )
    assert resp_rename.status_code == 200
    assert resp_rename.json()["profile"]["name"] == "测试方案B"

    resp_del = client.delete(f"/api/v1/projects/meeting_seating/profiles/{pid}")
    assert resp_del.status_code == 200
