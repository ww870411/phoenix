"""
认证与权限管理。

- 账号来源：backend_data/账户信息.json
- 权限矩阵：backend_data/auth/permissions.json

提供：
1. 账号认证（明文密码，仅用于当前开发环境）
2. 会话令牌（内存缓存，可选“记住登录”写入数据库持久化）
3. 权限解析（页面访问、可见单位、操作权限、表单过滤规则）
4. FastAPI 依赖：获取当前登录会话
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from fastapi import Header, HTTPException, status

from sqlalchemy import text

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import SessionLocal


EAST_8 = timezone(timedelta(hours=8))
# 会话策略：默认不限制有效期，并允许并发登录，避免频繁掉线
SESSION_TTL_SECONDS: Optional[int] = None  # None 表示后台不再主动过期
ALLOW_CONCURRENT_SESSIONS = True
PERSISTENT_SESSION_TTL_SECONDS = 90 * 24 * 60 * 60  # 记住登录默认 90 天


@dataclass(frozen=True)
class ActionFlags:
    can_submit: bool = False
    can_approve: bool = False
    can_revoke: bool = False
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
    expires_at: Optional[datetime] = None
    persistent: bool = False

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
                "can_revoke": self.permissions.actions.can_revoke,
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
        self._persistent_ready = False

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
                can_revoke=bool(actions_cfg.get("can_revoke")),
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
    def login(self, username: str, password: str, remember: bool = False) -> AuthSession:
        self._ensure_loaded()

        normalized = username.strip()
        record = self._users_by_name.get(normalized)
        if not record or record.password != password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

        group_permissions = self._groups.get(record.group)
        if not group_permissions:
            raise HTTPException(status_code=500, detail=f"用户组 {record.group} 未配置权限")

        issued_at = self._now()
        persistent = bool(remember)
        expires_at = self._compute_expiry(issued_at, persistent)
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
            persistent=persistent,
        )

        with self._session_lock:
            if not ALLOW_CONCURRENT_SESSIONS:
                self._invalidate_user_sessions(record.username)
            self._sessions[token] = session
            bucket = self._user_tokens.setdefault(record.username, set())
            bucket.add(token)

        if persistent:
            self._persist_session(session)

        return session

    @staticmethod
    def _compute_expiry(issued_at: datetime, persistent: bool) -> Optional[datetime]:
        if persistent:
            return issued_at + timedelta(seconds=PERSISTENT_SESSION_TTL_SECONDS)
        if SESSION_TTL_SECONDS is not None:
            return issued_at + timedelta(seconds=SESSION_TTL_SECONDS)
        return None

    def logout(self, token: str) -> None:
        with self._session_lock:
            session = self._sessions.pop(token, None)
            if session:
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                if bucket and not bucket:
                    self._user_tokens.pop(session.username, None)
        self._delete_persistent_session(token)

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
                session = self._load_persistent_session(token)
                if session:
                    self._sessions[token] = session
                    bucket = self._user_tokens.setdefault(session.username, set())
                    bucket.add(token)
            if not session:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效")
            now = self._now()
            if session.expires_at and session.expires_at <= now:
                self._sessions.pop(token, None)
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                if session.persistent:
                    self._delete_persistent_session(token)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已过期")
            # 滚动延长有效期（仅当开启过期控制时）
            if session.persistent:
                session.expires_at = self._touch_persistent_session(token)
            elif SESSION_TTL_SECONDS is not None:
                session.expires_at = now + timedelta(seconds=SESSION_TTL_SECONDS)
            return session

    def _invalidate_user_sessions(self, username: str) -> None:
        tokens = self._user_tokens.get(username)
        if not tokens:
            return
        for token in list(tokens):
            self._sessions.pop(token, None)
            self._delete_persistent_session(token)
        self._user_tokens.pop(username, None)

    def _cleanup_expired_locked(self) -> None:
        now = self._now()
        expired_tokens = [
            token
            for token, sess in self._sessions.items()
            if sess.expires_at and sess.expires_at <= now
        ]
        for token in expired_tokens:
            session = self._sessions.pop(token, None)
            if session:
                bucket = self._user_tokens.get(session.username)
                if bucket and token in bucket:
                    bucket.remove(token)
                if bucket and not bucket:
                    self._user_tokens.pop(session.username, None)
                if session.persistent:
                    self._delete_persistent_session(token)

    def _persist_session(self, session: AuthSession) -> None:
        if not session.expires_at:
            raise HTTPException(status_code=500, detail="记住登录缺少过期时间")
        self._ensure_persistent_store()
        permissions_payload = session.to_permissions_payload()
        allowed_units_payload = sorted(session.allowed_units)
        params = {
            "token": session.token,
            "username": session.username,
            "user_group": session.group,
            "unit": session.unit,
            "hierarchy": session.hierarchy,
            "permissions": json.dumps(permissions_payload, ensure_ascii=False),
            "allowed_units": json.dumps(allowed_units_payload, ensure_ascii=False),
            "issued_at": session.issued_at,
            "expires_at": session.expires_at,
        }
        try:
            with SessionLocal() as db:
                db.execute(
                    text(
                        """
                        INSERT INTO auth_sessions (
                            token, username, user_group, unit, hierarchy,
                            permissions, allowed_units, issued_at, expires_at, last_accessed
                        ) VALUES (
                            :token, :username, :user_group, :unit, :hierarchy,
                            CAST(:permissions AS JSONB), CAST(:allowed_units AS JSONB), :issued_at, :expires_at, :issued_at
                        )
                        ON CONFLICT (token) DO UPDATE
                        SET
                            username = EXCLUDED.username,
                            user_group = EXCLUDED.user_group,
                            unit = EXCLUDED.unit,
                            hierarchy = EXCLUDED.hierarchy,
                            permissions = EXCLUDED.permissions,
                            allowed_units = EXCLUDED.allowed_units,
                            expires_at = EXCLUDED.expires_at,
                            last_accessed = EXCLUDED.last_accessed
                        """
                    ),
                    params,
                )
                db.commit()
        except Exception as exc:  # pragma: no cover - 仅记录
            logging.exception("保存登录状态失败")
            raise HTTPException(status_code=500, detail="保存登录状态失败") from exc

    def _load_persistent_session(self, token: str) -> Optional[AuthSession]:
        if not token:
            return None
        try:
            self._ensure_persistent_store()
            with SessionLocal() as db:
                row = (
                    db.execute(
                        text(
                            """
                            SELECT token, username, user_group, unit, hierarchy,
                                   permissions, allowed_units, issued_at, expires_at
                            FROM auth_sessions
                            WHERE token = :token
                            """
                        ),
                        {"token": token},
                    )
                    .mappings()
                    .first()
                )
        except Exception:
            return None
        if not row:
            return None
        expires_at = row["expires_at"]
        now = self._now()
        if expires_at and expires_at <= now:
            self._delete_persistent_session(token)
            return None
        record = self._users_by_name.get(row["username"])
        group_permissions = self._groups.get(row["user_group"])
        if not record or not group_permissions:
            self._delete_persistent_session(token)
            return None
        allowed_units_raw = row["allowed_units"]
        try:
            allowed_units_list = json.loads(allowed_units_raw) if isinstance(allowed_units_raw, str) else allowed_units_raw
        except json.JSONDecodeError:
            allowed_units_list = []
        allowed_units = {str(unit) for unit in (allowed_units_list or [])}
        session = AuthSession(
            username=row["username"],
            group=row["user_group"],
            unit=row["unit"],
            hierarchy=row["hierarchy"],
            permissions=group_permissions,
            allowed_units=allowed_units or self._resolve_units(group_permissions.units_access, record.unit),
            token=row["token"],
            issued_at=row["issued_at"],
            expires_at=expires_at,
            persistent=True,
        )
        return session

    def _delete_persistent_session(self, token: str) -> None:
        if not token:
            return
        try:
            self._ensure_persistent_store()
            with SessionLocal() as db:
                db.execute(text("DELETE FROM auth_sessions WHERE token = :token"), {"token": token})
                db.commit()
        except Exception:
            return

    def _touch_persistent_session(self, token: str) -> datetime:
        self._ensure_persistent_store()
        new_expiry = self._now() + timedelta(seconds=PERSISTENT_SESSION_TTL_SECONDS)
        try:
            with SessionLocal() as db:
                db.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET last_accessed = NOW(), expires_at = :expires_at
                        WHERE token = :token
                        """
                    ),
                    {"token": token, "expires_at": new_expiry},
                )
                db.commit()
        except Exception:
            pass
        return new_expiry

    def _ensure_persistent_store(self) -> None:
        if self._persistent_ready:
            return
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token         TEXT PRIMARY KEY,
                username      TEXT        NOT NULL,
                user_group    TEXT        NOT NULL,
                unit          TEXT,
                hierarchy     INTEGER     NOT NULL,
                permissions   JSONB       NOT NULL,
                allowed_units JSONB       NOT NULL,
                issued_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at    TIMESTAMPTZ NOT NULL,
                last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_username ON auth_sessions (username)",
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions (expires_at)",
        ]
        try:
            with SessionLocal() as db:
                for statement in ddl_statements:
                    db.execute(text(statement))
                db.commit()
            self._persistent_ready = True
        except Exception as exc:
            logging.exception("初始化 auth_sessions 表失败")
            raise HTTPException(status_code=500, detail="会话持久化表初始化失败") from exc

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
