"""
审批与发布状态内存管理。

状态以 (project_key, biz_date) 为维度，按账号权限返回用户可见范围。
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, Optional, Set

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
    以字典实现的轻量状态存储，后续可替换为数据库或缓存。
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._storage: Dict[tuple[str, datetime], WorkflowSnapshot] = {}

    def get_snapshot(
        self,
        project_key: str,
        biz_date: datetime,
        visible_units: Iterable[str],
        seed_units: Iterable[str],
    ) -> WorkflowSnapshot:
        key = (project_key, biz_date)
        with self._lock:
            snapshot = self._storage.get(key)
            if snapshot is None:
                snapshot = WorkflowSnapshot()
                for unit in seed_units:
                    snapshot.units[unit] = UnitApprovalState(unit=unit)
                self._storage[key] = snapshot
            else:
                for unit in seed_units:
                    snapshot.units.setdefault(unit, UnitApprovalState(unit=unit))

        # 返回一个包含可视范围的浅拷贝，避免外部修改内部状态
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
            snapshot = self._storage.setdefault(key, WorkflowSnapshot())
            state = snapshot.units.setdefault(unit, UnitApprovalState(unit=unit))
            state.status = "approved"
            state.approved_by = actor.username
            state.approved_at = datetime.now(tz=EAST_8)
            return UnitApprovalState(**vars(state))

    def mark_published(
        self,
        project_key: str,
        biz_date: datetime,
        actor: AuthSession,
    ) -> PublishState:
        key = (project_key, biz_date)
        with self._lock:
            snapshot = self._storage.setdefault(key, WorkflowSnapshot())
            snapshot.publish.status = "published"
            snapshot.publish.published_by = actor.username
            snapshot.publish.published_at = datetime.now(tz=EAST_8)
            return PublishState(**vars(snapshot.publish))


workflow_status_manager = WorkflowStatusManager()
