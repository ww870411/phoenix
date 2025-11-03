"""
审批与发布状态管理（持久化版）。

状态以 (project_key, biz_date) 为维度，存储在 DATA_DIRECTORY/status.json。
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

from backend.config import DATA_DIRECTORY
from backend.services.auth_manager import EAST_8, AuthSession


@dataclass
class UnitApprovalState:
    unit: str
    status: str = "pending"  # pending | approved
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class PublishState:
    status: str = "pending"  # pending | published
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None


@dataclass
class WorkflowSnapshot:
    units: Dict[str, UnitApprovalState] = field(default_factory=dict)
    publish: PublishState = field(default_factory=PublishState)


class WorkflowStatusManager:
    """
    以 JSON 文件实现的审批/发布状态存储。

    文件结构示例：
    {
      "daily_report_25_26": {
        "2025-11-02T00:00:00+08:00": {
          "units": {
            "BeiHai": {"status": "approved", "approved_by": "...", "approved_at": "..."}
          },
          "publish": {"status": "pending", "published_by": null, "published_at": null}
        }
      }
    }
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._storage: Dict[Tuple[str, datetime], WorkflowSnapshot] = {}
        self._data_path: Path = (DATA_DIRECTORY / "status.json").resolve()
        self._loaded = False
        self._data_mtime: Optional[float] = None

    def get_snapshot(
        self,
        project_key: str,
        biz_date: datetime,
        visible_units: Iterable[str],
        seed_units: Iterable[str],
    ) -> WorkflowSnapshot:
        key = (project_key, biz_date)
        with self._lock:
            self._ensure_loaded_locked()
            snapshot = self._storage.get(key)
            changed = False
            if snapshot is None:
                snapshot = WorkflowSnapshot()
                for unit in seed_units:
                    snapshot.units[unit] = UnitApprovalState(unit=unit)
                self._storage[key] = snapshot
                changed = True
            else:
                for unit in seed_units:
                    if unit not in snapshot.units:
                        snapshot.units[unit] = UnitApprovalState(unit=unit)
                        changed = True

            if changed:
                self._persist_locked()

        visible_set = {unit for unit in visible_units}
        filtered_units = {
            unit: state for unit, state in snapshot.units.items() if not visible_set or unit in visible_set
        }
        clone = WorkflowSnapshot(
            units={unit: UnitApprovalState(**vars(state)) for unit, state in filtered_units.items()},
            publish=PublishState(**vars(snapshot.publish)),
        )
        return clone

    def mark_approved(
        self,
        project_key: str,
        biz_date: datetime,
        unit: str,
        actor: AuthSession,
    ) -> UnitApprovalState:
        key = (project_key, biz_date)
        with self._lock:
            self._ensure_loaded_locked()
            snapshot = self._storage.setdefault(key, WorkflowSnapshot())
            state = snapshot.units.setdefault(unit, UnitApprovalState(unit=unit))
            state.status = "approved"
            state.approved_by = actor.username
            state.approved_at = datetime.now(tz=EAST_8)
            self._persist_locked()
            return UnitApprovalState(**vars(state))

    def mark_pending(
        self,
        project_key: str,
        biz_date: datetime,
        unit: str,
        _actor: AuthSession,
    ) -> UnitApprovalState:
        key = (project_key, biz_date)
        with self._lock:
            self._ensure_loaded_locked()
            snapshot = self._storage.setdefault(key, WorkflowSnapshot())
            state = snapshot.units.setdefault(unit, UnitApprovalState(unit=unit))
            state.status = "pending"
            state.approved_by = None
            state.approved_at = None
            self._persist_locked()
            return UnitApprovalState(**vars(state))

    def mark_published(
        self,
        project_key: str,
        biz_date: datetime,
        actor: AuthSession,
    ) -> PublishState:
        key = (project_key, biz_date)
        with self._lock:
            self._ensure_loaded_locked()
            snapshot = self._storage.setdefault(key, WorkflowSnapshot())
            snapshot.publish.status = "published"
            snapshot.publish.published_by = actor.username
            snapshot.publish.published_at = datetime.now(tz=EAST_8)
            self._persist_locked()
            return PublishState(**vars(snapshot.publish))

    # ------------------------------------------------------------------ #
    # 内部工具
    # ------------------------------------------------------------------ #
    def _ensure_loaded_locked(self) -> None:
        try:
            current_mtime = self._data_path.stat().st_mtime
        except FileNotFoundError:
            current_mtime = None

        if self._loaded and current_mtime == self._data_mtime:
            return

        self._storage.clear()
        raw: Dict[str, object]
        if self._data_path.exists():
            try:
                raw = json.loads(self._data_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                raw = {}
        else:
            raw = {}

        if isinstance(raw, dict):
            for project_key, per_project in raw.items():
                if not isinstance(per_project, dict):
                    continue
                for biz_key, payload in per_project.items():
                    if not isinstance(payload, dict):
                        continue
                    try:
                        biz_datetime = datetime.fromisoformat(biz_key)
                    except ValueError:
                        continue
                    snapshot = WorkflowSnapshot()
                    units_raw = payload.get("units") or {}
                    if isinstance(units_raw, dict):
                        for unit_name, state_raw in units_raw.items():
                            if not isinstance(unit_name, str):
                                continue
                            if not isinstance(state_raw, dict):
                                state_raw = {}
                            approved_at_raw = state_raw.get("approved_at")
                            approved_at = None
                            if isinstance(approved_at_raw, str):
                                try:
                                    approved_at = datetime.fromisoformat(approved_at_raw)
                                except ValueError:
                                    approved_at = None
                            snapshot.units[unit_name] = UnitApprovalState(
                                unit=unit_name,
                                status=state_raw.get("status", "pending"),
                                approved_by=state_raw.get("approved_by"),
                                approved_at=approved_at,
                            )
                    publish_raw = payload.get("publish") or {}
                    published_at = None
                    if isinstance(publish_raw, dict):
                        published_at_raw = publish_raw.get("published_at")
                        if isinstance(published_at_raw, str):
                            try:
                                published_at = datetime.fromisoformat(published_at_raw)
                            except ValueError:
                                published_at = None
                        snapshot.publish = PublishState(
                            status=publish_raw.get("status", "pending"),
                            published_by=publish_raw.get("published_by"),
                            published_at=published_at,
                        )
                    self._storage[(project_key, biz_datetime)] = snapshot

        self._loaded = True
        self._data_mtime = current_mtime

    def _persist_locked(self) -> None:
        payload: Dict[str, Dict[str, Dict[str, object]]] = {}
        for (project_key, biz_datetime), snapshot in self._storage.items():
            project_bucket = payload.setdefault(project_key, {})
            biz_key = biz_datetime.isoformat()

            units_payload: Dict[str, Dict[str, Optional[str]]] = {}
            for unit_name, state in snapshot.units.items():
                units_payload[unit_name] = {
                    "status": state.status,
                    "approved_by": state.approved_by,
                    "approved_at": state.approved_at.isoformat() if state.approved_at else None,
                }

            project_bucket[biz_key] = {
                "units": units_payload,
                "publish": {
                    "status": snapshot.publish.status,
                    "published_by": snapshot.publish.published_by,
                    "published_at": snapshot.publish.published_at.isoformat()
                    if snapshot.publish.published_at
                    else None,
                },
            }

        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._data_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            self._data_mtime = self._data_path.stat().st_mtime
        except FileNotFoundError:
            self._data_mtime = None


workflow_status_manager = WorkflowStatusManager()
