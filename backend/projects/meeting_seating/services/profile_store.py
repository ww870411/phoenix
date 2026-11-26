# -*- coding: utf-8 -*-
"""会议排座助手配置文件存储服务（按边/排管理座位数量，支持多存档、隐藏桌椅与花盆位置调整）。"""

from __future__ import annotations

import copy
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.project_data_paths import get_project_config_dir

PROJECT_KEY = "meeting_seating"
CONFIG_FILENAME = "seating_profiles.json"
_STORE_LOCK = threading.RLock()

VALID_ZONES = ("front", "innerLeft", "innerRight", "innerRear", "left", "right", "rear")
FIXED_ZONES = ("front", "innerLeft", "innerRight", "innerRear")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def resolve_profiles_config_path() -> Path:
    """返回会议排座配置文件绝对路径。"""
    config_dir = get_project_config_dir(PROJECT_KEY)
    config_dir.mkdir(parents=True, exist_ok=True)
    return (config_dir / CONFIG_FILENAME).resolve()


def _make_row(row_id: str, label: str, zone: str, seat_count: int = 6, hidden: bool = False) -> Dict[str, Any]:
    seats = [
        {"id": f"{row_id}-{i + 1}", "name": "", "hidden": False}
        for i in range(max(0, min(24, seat_count)))
    ]
    return {
        "id": row_id,
        "label": label,
        "zone": zone,
        "tableCount": 3,
        "hidden": hidden,
        "seats": seats,
    }


def build_default_layout() -> Dict[str, Any]:
    """构建贴合实景会议室的初始平面布局（按边/排控制座位数，每边默认 3 桌拼接共 6 席）。"""
    rows = [
        _make_row("A", "主席席", "front", 6),
        _make_row("B", "窗侧内排", "innerLeft", 6),
        _make_row("C", "右侧内排", "innerRight", 6),
        _make_row("D", "回字桌后排", "innerRear", 6),
        _make_row("E", "右侧外围排", "right", 6),
        _make_row("F", "后方第1排", "rear", 6),
        _make_row("G", "后方第2排", "rear", 6),
        _make_row("H", "后方第3排", "rear", 6),
    ]
    plants = [
        {"id": "P-1", "x": 294, "y": 392, "label": "花盆 1", "hidden": False},
        {"id": "P-2", "x": 474, "y": 392, "label": "花盆 2", "hidden": False},
        {"id": "P-3", "x": 294, "y": 584, "label": "花盆 3", "hidden": False},
        {"id": "P-4", "x": 474, "y": 584, "label": "花盆 4", "hidden": False},
    ]
    return {
        "version": 3,
        "meeting": "会议座位安排图",
        "subtitle": "",
        "paper": "portrait",
        "mono": False,
        "numbers": True,
        "flip": False,
        "showHiddenPreview": False,
        "room": {
            "door": {"enabled": True, "label": "出入口（外开）"},
            "equipmentRoom": {"enabled": True, "label": "设备室"},
            "leftWindows": 4,
            "rightWindows": 4,
            "screenLabel": "显示屏 / 会场正前方",
        },
        "rows": rows,
        "plants": plants,
        "seq": 10,
    }


def _migrate_v2_tables_to_rows(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """兼容迁移旧版 v2 tables 数据至按边/排管理的 rows 结构。"""
    default_rows = build_default_layout()["rows"]
    zone_by_gid = {r["id"]: r["zone"] for r in default_rows}
    grouped: Dict[str, Dict[str, Any]] = {}
    for tbl in tables:
        if not isinstance(tbl, dict):
            continue
        gid = str(tbl.get("groupId") or "G")[:16]
        if gid not in grouped:
            grouped[gid] = {
                "id": gid,
                "label": str(tbl.get("groupLabel") or gid)[:32],
                "zone": zone_by_gid.get(gid, "rear"),
                "tableCount": 3,
                "hidden": bool(tbl.get("hidden", False)),
                "seats": [],
            }
        else:
            if not tbl.get("hidden", False):
                grouped[gid]["hidden"] = False
        for s in tbl.get("seats") or []:
            if isinstance(s, dict):
                grouped[gid]["seats"].append(
                    {
                        "id": str(s.get("id") or f"{gid}-{len(grouped[gid]['seats']) + 1}")[:40],
                        "name": str(s.get("name") or "")[:40],
                        "hidden": bool(s.get("hidden", False)),
                    }
                )
    rows = list(grouped.values())
    existing_zones = {r["zone"] for r in rows}
    for dr in default_rows:
        if dr["zone"] in FIXED_ZONES and dr["zone"] not in existing_zones:
            rows.append(copy.deepcopy(dr))
    return rows


def _sanitize_layout(raw: Any) -> Dict[str, Any]:
    """规范化按边/排管理的布局结构，兼容旧版数据迁移。"""
    default = build_default_layout()
    if not isinstance(raw, dict):
        return default

    layout = copy.deepcopy(default)
    layout["version"] = 3
    layout["meeting"] = str(raw.get("meeting") or "会议座位安排图")[:100]
    layout["subtitle"] = str(raw.get("subtitle") or "")[:120]
    layout["paper"] = "portrait" if raw.get("paper") == "portrait" else "landscape"
    layout["mono"] = bool(raw.get("mono", False))
    layout["numbers"] = bool(raw.get("numbers", True))
    layout["flip"] = bool(raw.get("flip", False))
    layout["showHiddenPreview"] = bool(raw.get("showHiddenPreview", False))
    seq = raw.get("seq", 10)
    layout["seq"] = seq if isinstance(seq, int) and 10 <= seq < 1_000_000 else 10

    room_raw = raw.get("room")
    if isinstance(room_raw, dict):
        room = layout["room"]
        if isinstance(room_raw.get("leftWindows"), int):
            room["leftWindows"] = max(0, min(8, room_raw["leftWindows"]))
        if isinstance(room_raw.get("rightWindows"), int):
            room["rightWindows"] = max(0, min(8, room_raw["rightWindows"]))
        if isinstance(room_raw.get("screenLabel"), str):
            room["screenLabel"] = room_raw["screenLabel"][:60]
        door_raw = room_raw.get("door")
        if isinstance(door_raw, dict):
            room["door"]["enabled"] = bool(door_raw.get("enabled", True))
            if isinstance(door_raw.get("label"), str):
                room["door"]["label"] = door_raw["label"][:32]
        eq_raw = room_raw.get("equipmentRoom")
        if isinstance(eq_raw, dict):
            room["equipmentRoom"]["enabled"] = bool(eq_raw.get("enabled", True))
            if isinstance(eq_raw.get("label"), str):
                room["equipmentRoom"]["label"] = eq_raw["label"][:24]

    rows_raw = raw.get("rows")
    if not isinstance(rows_raw, list) and isinstance(raw.get("tables"), list):
        rows_raw = _migrate_v2_tables_to_rows(raw["tables"])

    if isinstance(rows_raw, list):
        cleaned_rows: List[Dict[str, Any]] = []
        seen_ids = set()
        for idx, item in enumerate(rows_raw[:30]):
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id") or f"R{idx + 1}")[:16]
            if rid in seen_ids:
                rid = f"R{idx + 10}"
            seen_ids.add(rid)
            zone = str(item.get("zone") or "rear")
            if zone not in VALID_ZONES:
                zone = "rear"
            label = str(item.get("label") or rid)[:32]
            hidden = bool(item.get("hidden", False))
            seats_in = item.get("seats") if isinstance(item.get("seats"), list) else item.get("names")
            cleaned_seats: List[Dict[str, Any]] = []
            if isinstance(seats_in, list):
                for s_idx, s in enumerate(seats_in[:24]):
                    if isinstance(s, dict):
                        cleaned_seats.append(
                            {
                                "id": str(s.get("id") or f"{rid}-{s_idx + 1}")[:40],
                                "name": str(s.get("name") or "")[:40],
                                "hidden": bool(s.get("hidden", False)),
                            }
                        )
                    elif isinstance(s, str):
                        cleaned_seats.append(
                            {
                                "id": f"{rid}-{s_idx + 1}",
                                "name": s[:40],
                                "hidden": False,
                            }
                        )
            cleaned_rows.append(
                {
                    "id": rid,
                    "label": label,
                    "zone": zone,
                    "tableCount": 3,
                    "hidden": hidden,
                    "seats": cleaned_seats,
                }
            )
        # 确保中央回字四边至少各有一条记录
        for fz in FIXED_ZONES:
            if not any(r["zone"] == fz for r in cleaned_rows):
                fallback = next(r for r in default["rows"] if r["zone"] == fz)
                cleaned_rows.append(copy.deepcopy(fallback))
        layout["rows"] = cleaned_rows

    plants_raw = raw.get("plants")
    if isinstance(plants_raw, list):
        cleaned_plants: List[Dict[str, Any]] = []
        for idx, p in enumerate(plants_raw[:20]):
            if not isinstance(p, dict):
                continue
            cleaned_plants.append(
                {
                    "id": str(p.get("id") or f"P-{idx + 1}")[:32],
                    "x": int(p.get("x") or 0),
                    "y": int(p.get("y") or 0),
                    "label": str(p.get("label") or f"花盆 {idx + 1}")[:24],
                    "hidden": bool(p.get("hidden", False)),
                }
            )
        layout["plants"] = cleaned_plants

    return layout


def _summarize_layout(layout: Dict[str, Any]) -> Dict[str, int]:
    rows = layout.get("rows") or []
    visible_rows = 0
    total_seats = 0
    assigned_seats = 0
    for row in rows:
        if row.get("hidden"):
            continue
        visible_rows += 1
        for seat in row.get("seats") or []:
            if seat.get("hidden"):
                continue
            total_seats += 1
            if str(seat.get("name") or "").strip():
                assigned_seats += 1
    return {
        "row_count": visible_rows,
        "total_seats": total_seats,
        "assigned_seats": assigned_seats,
    }


def _profile_meta(profile: Dict[str, Any]) -> Dict[str, Any]:
    layout = profile.get("layout") or {}
    return {
        "id": profile["id"],
        "name": profile["name"],
        "created_at": profile.get("created_at") or "",
        "updated_at": profile.get("updated_at") or "",
        "summary": _summarize_layout(layout),
    }


def _default_store() -> Dict[str, Any]:
    now = _now_iso()
    default_id = "default_square_3x4"
    return {
        "version": 1,
        "active_id": default_id,
        "profiles": [
            {
                "id": default_id,
                "name": "默认实景回字布局",
                "created_at": now,
                "updated_at": now,
                "layout": build_default_layout(),
            }
        ],
    }


def _write_store(path: Path, store: Dict[str, Any]) -> None:
    serialized = json.dumps(store, ensure_ascii=False, indent=2) + "\n"
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(serialized, encoding="utf-8")
    temp_path.replace(path)


def _read_or_init_store() -> Dict[str, Any]:
    path = resolve_profiles_config_path()
    if not path.exists():
        store = _default_store()
        _write_store(path, store)
        return store

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        store = _default_store()
        _write_store(path, store)
        return store

    profiles = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles, list) or not profiles:
        store = _default_store()
        _write_store(path, store)
        return store

    normalized_profiles: List[Dict[str, Any]] = []
    seen_ids = set()
    for item in profiles:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or uuid.uuid4().hex[:10]).strip()
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)
        normalized_profiles.append(
            {
                "id": pid,
                "name": str(item.get("name") or "未命名方案").strip()[:60] or "未命名方案",
                "created_at": str(item.get("created_at") or _now_iso()),
                "updated_at": str(item.get("updated_at") or _now_iso()),
                "layout": _sanitize_layout(item.get("layout")),
            }
        )

    if not normalized_profiles:
        store = _default_store()
        _write_store(path, store)
        return store

    active_id = str(raw.get("active_id") or "")
    if active_id not in {p["id"] for p in normalized_profiles}:
        active_id = normalized_profiles[0]["id"]

    return {
        "version": 1,
        "active_id": active_id,
        "profiles": normalized_profiles,
    }


def list_profiles() -> Dict[str, Any]:
    with _STORE_LOCK:
        store = _read_or_init_store()
        active_id = store["active_id"]
        active_profile = next((p for p in store["profiles"] if p["id"] == active_id), store["profiles"][0])
        return {
            "config_path": str(resolve_profiles_config_path()),
            "active_id": active_profile["id"],
            "profiles": [_profile_meta(p) for p in store["profiles"]],
            "active_profile": active_profile,
        }


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    with _STORE_LOCK:
        store = _read_or_init_store()
        for profile in store["profiles"]:
            if profile["id"] == profile_id:
                return copy.deepcopy(profile)
        return None


def create_profile(
    name: str,
    layout: Optional[Dict[str, Any]] = None,
    source_profile_id: Optional[str] = None,
    activate: bool = True,
) -> Dict[str, Any]:
    clean_name = str(name or "").strip()[:60]
    if not clean_name:
        raise ValueError("存档名称不能为空")

    with _STORE_LOCK:
        store = _read_or_init_store()
        base_layout: Optional[Dict[str, Any]] = None
        if layout is not None:
            base_layout = _sanitize_layout(layout)
        elif source_profile_id:
            source = next((p for p in store["profiles"] if p["id"] == source_profile_id), None)
            if source is None:
                raise KeyError("源存档不存在")
            base_layout = copy.deepcopy(source["layout"])
        else:
            base_layout = build_default_layout()

        now = _now_iso()
        new_id = f"p_{uuid.uuid4().hex[:10]}"
        profile = {
            "id": new_id,
            "name": clean_name,
            "created_at": now,
            "updated_at": now,
            "layout": base_layout,
        }
        store["profiles"].append(profile)
        if activate:
            store["active_id"] = new_id
        _write_store(resolve_profiles_config_path(), store)
        return {
            "active_id": store["active_id"],
            "profile": profile,
            "profiles": [_profile_meta(p) for p in store["profiles"]],
        }


def update_profile(
    profile_id: str,
    layout: Optional[Dict[str, Any]] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    with _STORE_LOCK:
        store = _read_or_init_store()
        target = next((p for p in store["profiles"] if p["id"] == profile_id), None)
        if target is None:
            raise KeyError("目标存档不存在")

        if name is not None:
            clean_name = str(name).strip()[:60]
            if not clean_name:
                raise ValueError("存档名称不能为空")
            target["name"] = clean_name

        if layout is not None:
            target["layout"] = _sanitize_layout(layout)

        target["updated_at"] = _now_iso()
        _write_store(resolve_profiles_config_path(), store)
        return {
            "active_id": store["active_id"],
            "profile": target,
            "profiles": [_profile_meta(p) for p in store["profiles"]],
        }


def rename_profile(profile_id: str, name: str) -> Dict[str, Any]:
    return update_profile(profile_id=profile_id, name=name)


def activate_profile(profile_id: str) -> Dict[str, Any]:
    with _STORE_LOCK:
        store = _read_or_init_store()
        target = next((p for p in store["profiles"] if p["id"] == profile_id), None)
        if target is None:
            raise KeyError("目标存档不存在")
        store["active_id"] = profile_id
        _write_store(resolve_profiles_config_path(), store)
        return {
            "active_id": store["active_id"],
            "profile": target,
            "profiles": [_profile_meta(p) for p in store["profiles"]],
        }


def delete_profile(profile_id: str) -> Dict[str, Any]:
    with _STORE_LOCK:
        store = _read_or_init_store()
        if len(store["profiles"]) <= 1:
            raise ValueError("至少保留一个布局存档")
        next_profiles = [p for p in store["profiles"] if p["id"] != profile_id]
        if len(next_profiles) == len(store["profiles"]):
            raise KeyError("目标存档不存在")
        store["profiles"] = next_profiles
        if store["active_id"] == profile_id:
            store["active_id"] = next_profiles[0]["id"]
        _write_store(resolve_profiles_config_path(), store)
        active_profile = next(
            (p for p in store["profiles"] if p["id"] == store["active_id"]),
            store["profiles"][0],
        )
        return {
            "active_id": store["active_id"],
            "active_profile": active_profile,
            "profiles": [_profile_meta(p) for p in store["profiles"]],
        }
