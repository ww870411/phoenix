# -*- coding: utf-8 -*-
"""审计日志服务：事件写入、查询与分类统计。"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.config import DATA_DIRECTORY

EAST_8 = timezone(timedelta(hours=8))
LOG_DIR = Path(DATA_DIRECTORY).resolve() / "shared" / "log"
MAX_SCAN_FILES = 30


def _normalize_text(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _parse_time(value: object) -> Optional[datetime]:
    raw = _normalize_text(value)
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _day_file_path(day: datetime) -> Path:
    return LOG_DIR / f"audit-{day.astimezone(EAST_8).strftime('%Y-%m-%d')}.ndjson"


def append_events(events: Iterable[Dict[str, Any]]) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    grouped: Dict[Path, List[str]] = {}
    for item in events:
        server_time = _parse_time(item.get("ts")) or datetime.now(timezone.utc)
        payload = dict(item)
        payload["ts"] = server_time.astimezone(timezone.utc).isoformat()
        payload["ts_east8"] = server_time.astimezone(EAST_8).isoformat()
        path = _day_file_path(server_time)
        grouped.setdefault(path, []).append(json.dumps(payload, ensure_ascii=False))
    written = 0
    for path, lines in grouped.items():
        with path.open("a", encoding="utf-8") as fp:
            for line in lines:
                fp.write(line)
                fp.write("\n")
                written += 1
    return written


def _iter_recent_files(days: int = 7) -> List[Path]:
    if not LOG_DIR.exists():
        return []
    all_files = sorted(
        [path for path in LOG_DIR.glob("audit-*.ndjson") if path.is_file()],
        key=lambda p: p.name,
        reverse=True,
    )
    # 双保险：按天数和扫描上限裁剪
    keep_days = max(1, int(days))
    return all_files[: min(MAX_SCAN_FILES, keep_days + 2)]


def _read_events_from_files(files: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in lines:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    rows.sort(key=lambda item: _parse_time(item.get("ts")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return rows


def query_events(
    *,
    days: int = 7,
    username: str = "",
    category: str = "",
    action: str = "",
    keyword: str = "",
    limit: int = 200,
) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 1000))
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=max(1, int(days)))
    files = _iter_recent_files(days=days)
    events = _read_events_from_files(files)

    wanted_user = _normalize_text(username).lower()
    wanted_category = _normalize_text(category).lower()
    wanted_action = _normalize_text(action).lower()
    wanted_keyword = _normalize_text(keyword).lower()

    filtered: List[Dict[str, Any]] = []
    for item in events:
        ts = _parse_time(item.get("ts"))
        if not ts or ts < start:
            continue
        if wanted_user and _normalize_text(item.get("username")).lower() != wanted_user:
            continue
        if wanted_category and _normalize_text(item.get("category")).lower() != wanted_category:
            continue
        if wanted_action and _normalize_text(item.get("action")).lower() != wanted_action:
            continue
        if wanted_keyword:
            blob = json.dumps(item, ensure_ascii=False).lower()
            if wanted_keyword not in blob:
                continue
        filtered.append(item)
        if len(filtered) >= safe_limit:
            break
    return filtered


def build_stats(*, days: int = 7) -> Dict[str, Any]:
    events = query_events(days=days, limit=5000)
    by_category = Counter()
    by_action = Counter()
    by_user = Counter()
    by_page = Counter()
    for item in events:
        by_category[_normalize_text(item.get("category"), "unknown")] += 1
        by_action[_normalize_text(item.get("action"), "unknown")] += 1
        by_user[_normalize_text(item.get("username"), "unknown")] += 1
        by_page[_normalize_text(item.get("page"), "unknown")] += 1
    return {
        "total": len(events),
        "by_category": dict(by_category.most_common()),
        "by_action": dict(by_action.most_common(30)),
        "by_user": dict(by_user.most_common(30)),
        "by_page": dict(by_page.most_common(30)),
    }
