"""
认证与权限管理。

- 账号来源：backend_data/账户信息.json
- 权限矩阵：backend_data/auth/permissions.json

提供：
1. 账号认证（明文密码，仅用于当前开发环境）
2. 会话令牌（内存缓存 + 30 分钟有效期）
3. 权限解析（页面访问、可见单位、操作权限、表单过滤规则）
4. FastAPI 依赖：获取当前登录会话
"""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from fastapi import Header, HTTPException, status

from backend.config import DATA_DIRECTORY


EAST_8 = timezone(timedelta(hours=8))
SESSION_TTL_SECONDS = 1440 * 60  # 24小时


@dataclass(frozen=True)
class ActionFlags:
    can_submit: bool = False
    can_approve: bool = False
    can_publish: bool = False


@dataclass(frozen=True)
class SheetRule:
    mode: str = "all"  # all / explicit / by_unit
    sheets: Set[str] = field(default_factory=set)

    def serialize(self) -> Dict[str, object]:
        payload: Dict[str, object] = {"mode": self.mode}
        if self.sheets:
            payload["sheets"] = sorted(self.sheets)
        return payload


@dataclass(frozen=True)
class GroupPermissions:
    name: str
    hierarchy: int
    page_access: Set[str]
    sheet_rules: Dict[str, SheetRule]
    units_access: List[str]
    actions: ActionFlags


@dataclass(frozen=True)
class UserRecord:
    username: str
    password: str
    group: str
    unit: Optional[str]


@dataclass
class AuthSession:
    username: str
    group: str
    unit: Optional[str]
    hierarchy: int
    permissions: GroupPermissions
    allowed_units: Set[str]
    token: str
    issued_at: datetime
    expires_at: datetime

    def to_user_payload(self) -> Dict[str, object]:
        return {
            "username": self.username,
            "group": self.group,
            "unit": self.unit,
            "hierarchy": self.hierarchy,
        }

    def to_permissions_payload(self) -> Dict[str, object]:
        sheet_rules = {
            page_key: rule.serialize() for page_key, rule in self.permissions.sheet_rules.items()
        }
        return {
            "page_access": sorted(self.permissions.page_access),
            "sheet_rules": sheet_rules,
            "units_access": sorted(self.allowed_units),
            "actions": {
                "can_submit": self.permissions.actions.can_submit,
                "can_approve": self.permissions.actions.can_approve,
                "can_publish": self.permissions.actions.can_publish,
            },
        }


class AuthManager:
    """集中式账号、权限、会话管理。"""

    def __init__(self) -> None:
        self._accounts_path = (DATA_DIRECTORY / "账户信息.json").resolve()
        self._permissions_path = (DATA_DIRECTORY / "auth" / "permissions.json").resolve()
        self._lock = threading.RLock()
        self._session_lock = threading.RLock()

        self._users_by_name: Dict[str, UserRecord] = {}
        self._groups: Dict[str, GroupPermissions] = {}
        self._known_units: Set[str] = set()
        self._biz_date_offset_days: int = -1

        self._accounts_mtime: Optional[float] = None
        self._permissions_mtime: Optional[float] = None

        self._date_config_path = (DATA_DIRECTORY / "date.json").resolve()
        self._date_config_mtime: Optional[float] = None
        self._display_date_cache: Optional[date] = None

        self._sessions: Dict[str, AuthSession] = {}
        self._user_tokens: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------ #
    # 配置加载
    # ------------------------------------------------------------------ #
    def _ensure_loaded(self) -> None:
        with self._lock:
            accounts_mtime = self._accounts_path.stat().st_mtime if self._accounts_path.exists() else None
            permissions_mtime = (
                self._permissions_path.stat().st_mtime if self._permissions_path.exists() else None
            )

            reload_needed = (
                accounts_mtime is None
                or permissions_mtime is None
                or accounts_mtime != self._accounts_mtime
                or permissions_mtime != self._permissions_mtime
            )
            if not reload_needed:
                return

            users = self._load_accounts()
            groups, biz_offset = self._load_permissions()

            self._users_by_name = users
            self._groups = groups
            self._biz_date_offset_days = biz_offset
            self._known_units = self._extract_known_units(users.values())

            self._accounts_mtime = accounts_mtime
            self._permissions_mtime = permissions_mtime

            # 配置变更时清理所有已登录会话，避免权限失效
            with self._session_lock:
                self._sessions.clear()
                self._user_tokens.clear()

    def _load_accounts(self) -> Dict[str, UserRecord]:
        if not self._accounts_path.exists():
            raise HTTPException(status_code=500, detail="账户信息文件缺失")
        try:
            raw = json.loads(self._accounts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"账户信息文件解析失败: {exc}") from exc

        users_raw = raw.get("users")
        if not isinstance(users_raw, dict):
            raise HTTPException(status_code=500, detail="账户信息需包含 users 字段")

        users: Dict[str, UserRecord] = {}
        for group_name, entries in users_raw.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                username = str(entry.get("username", "")).strip()
                password = str(entry.get("password", "")).strip()
                unit = entry.get("unit")
                if not username or not password:
                    continue
                record = UserRecord(username=username, password=password, group=group_name, unit=unit)
                users[username] = record
        if not users:
            raise HTTPException(status_code=500, detail="账户信息为空")
        return users

    def _load_permissions(self) -> tuple[Dict[str, GroupPermissions], int]:
        if not self._permissions_path.exists():
            raise HTTPException(status_code=500, detail="权限配置文件缺失")
        try:
            raw = json.loads(self._permissions_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail=f"权限配置文件解析失败: {exc}") from exc

        groups_raw = raw.get("groups")
        if not isinstance(groups_raw, dict):
            raise HTTPException(status_code=500, detail="权限配置需包含 groups 字段")

        biz_offset = -1
        metadata = raw.get("metadata")
        if isinstance(metadata, dict):
            offset = metadata.get("biz_date_offset_days")
            if isinstance(offset, int):
                biz_offset = offset

        groups: Dict[str, GroupPermissions] = {}
        for group_name, cfg in groups_raw.items():
            if not isinstance(cfg, dict):
                continue
            hierarchy = int(cfg.get("hierarchy", 0))
            page_access_raw = cfg.get("page_access") or []
            page_access = {str(page).strip() for page in page_access_raw if str(page).strip()}

            sheet_rules_raw = cfg.get("sheet_rules") or {}
            sheet_rules: Dict[str, SheetRule] = {}
            for page_key, rule_cfg in sheet_rules_raw.items():
                if not isinstance(rule_cfg, dict):
                    continue
                mode = str(rule_cfg.get("mode", "all")).strip().lower() or "all"
                sheets_list = rule_cfg.get("sheets") or []
                sheets = {str(s).strip() for s in sheets_list if str(s).strip()}
                sheet_rules[str(page_key).strip()] = SheetRule(mode=mode, sheets=sheets)

            # 未显式配置的 page 使用默认 rule
            for page_key in page_access:
                sheet_rules.setdefault(page_key, SheetRule(mode="all"))

            units_access_raw = cfg.get("units_access") or []
            units_access = [str(unit).strip() for unit in units_access_raw if str(unit).strip()]

            actions_cfg = cfg.get("actions") or {}
            actions = ActionFlags(
                can_submit=bool(actions_cfg.get("can_submit")),
                can_approve=bool(actions_cfg.get("can_approve")),
                can_publish=bool(actions_cfg.get("can_publish")),
            )

            groups[group_name] = GroupPermissions(
                name=group_name,
                hierarchy=hierarchy,
                page_access=page_access,
                sheet_rules=sheet_rules,
                units_access=units_access,
                actions=actions,
            )

        if not groups:
            raise HTTPException(status_code=500, detail="权限配置为空")
        return groups, biz_offset

    @staticmethod
    def _extract_known_units(users: Iterable[UserRecord]) -> Set[str]:
        units: Set[str] = set()
        for user in users:
            if user.unit:
                units.add(str(user.unit))
        return units

    # ------------------------------------------------------------------ #
    # 登录 / 会话
    # ------------------------------------------------------------------ #
    def login(self, username: str, password: str) -> AuthSession:
        self._ensure_loaded()

        normalized = username.strip()
        record = self._users_by_name.get(normalized)
        if not record or record.password != password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        group_permissions = self._groups.get(record.group)
        if not group_permissions:
            raise HTTPException(status_code=500, detail=f"用户组 {record.group} 未配置权限")

        issued_at = self._now()
        expires_at = issued_at + timedelta(seconds=SESSION_TTL_SECONDS)
        token = secrets.token_urlsafe(32)
        allowed_units = self._resolve_units(group_permissions.units_access, record.unit)

        session = AuthSession(
            username=record.username,
            group=record.group,
            unit=record.unit,
            hierarchy=group_permissions.hierarchy,
            permissions=group_permissions,
            allowed_units=allowed_units,
            token=token,
            issued_at=issued_at,
            expires_at=expires_at,
        )

        with self._session_lock:
            self._invalidate_user_sessions(record.username)
            self._sessions[token] = session
            bucket = self._user_tokens.setdefault(record.username, set())
            bucket.add(token)

        return session

    def logout(self, token: str) -> None:
        with self._session_lock:
            session = self._sessions.pop(token, None)
            if session:
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                if bucket and not bucket:
                    self._user_tokens.pop(session.username, None)

    def require_session_from_header(self, authorization: Optional[str]) -> AuthSession:
        if not authorization:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少认证信息")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证头格式错误")
        token = parts[1]
        return self.require_session(token)

    def require_session(self, token: str) -> AuthSession:
        self._ensure_loaded()

        with self._session_lock:
            self._cleanup_expired_locked()
            session = self._sessions.get(token)
            if not session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效")
            now = self._now()
            if session.expires_at <= now:
                self._sessions.pop(token, None)
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已过期")
            # 滚动延长有效期
            session.expires_at = now + timedelta(seconds=SESSION_TTL_SECONDS)
            return session

    def _invalidate_user_sessions(self, username: str) -> None:
        tokens = self._user_tokens.get(username)
        if not tokens:
            return
        for token in list(tokens):
            self._sessions.pop(token, None)
        self._user_tokens.pop(username, None)

    def _cleanup_expired_locked(self) -> None:
        now = self._now()
        expired_tokens = [token for token, sess in self._sessions.items() if sess.expires_at <= now]
        for token in expired_tokens:
            session = self._sessions.pop(token, None)
            if session:
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                if bucket and not bucket:
                    self._user_tokens.pop(session.username, None)

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #
    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=EAST_8)

    def _resolve_units(self, configured_units: List[str], user_unit: Optional[str]) -> Set[str]:
        resolved: Set[str] = set()
        for unit in configured_units:
            if unit == "*":
                return set(self._known_units) or set()
            if unit == "{user_unit}" and user_unit:
                resolved.add(user_unit)
            elif unit:
                resolved.add(unit)
        if not resolved and user_unit:
            resolved.add(user_unit)
        return resolved

    def list_known_units(self) -> List[str]:
        self._ensure_loaded()
        return sorted(self._known_units)

    def current_biz_date(self) -> date:
        base = self._now().date()
        offset = self._biz_date_offset_days
        return base + timedelta(days=offset)

    def _refresh_display_date_locked(self) -> None:
        if not self._date_config_path.exists():
            self._date_config_mtime = None
            self._display_date_cache = None
            return
        try:
            raw = json.loads(self._date_config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._display_date_cache = None
        else:
            display_value = raw.get("set_biz_date")
            parsed: Optional[date] = None
            if isinstance(display_value, str) and display_value:
                try:
                    parsed = date.fromisoformat(display_value)
                except ValueError:
                    parsed = None
            self._display_date_cache = parsed
        finally:
            try:
                self._date_config_mtime = self._date_config_path.stat().st_mtime
            except FileNotFoundError:
                self._date_config_mtime = None
                self._display_date_cache = None

    def current_display_date(self) -> date:
        biz_date = self.current_biz_date()
        with self._lock:
            try:
                current_mtime = self._date_config_path.stat().st_mtime
            except FileNotFoundError:
                current_mtime = None
            if current_mtime != self._date_config_mtime:
                self._refresh_display_date_locked()
            return self._display_date_cache or biz_date

    def set_display_date(self, target_date: date) -> None:
        try:
            raw_text = self._date_config_path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            if not isinstance(payload, dict):
                payload = {}
        except FileNotFoundError:
            payload = {}
        except json.JSONDecodeError:
            payload = {}
        payload["set_biz_date"] = target_date.isoformat()
        with self._lock:
            self._date_config_path.parent.mkdir(parents=True, exist_ok=True)
            self._date_config_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._date_config_mtime = self._date_config_path.stat().st_mtime
            self._display_date_cache = target_date


auth_manager = AuthManager()


def get_current_session(authorization: str = Header(None, alias="Authorization")) -> AuthSession:
    """
    FastAPI 依赖：解析 Authorization Bearer 头并返回会话。
    """

    return auth_manager.require_session_from_header(authorization)
