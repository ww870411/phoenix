# -*- coding: utf-8 -*-
"""
在线用户心跳与 Presence 状态服务
用于记录全系统在线人员数量、所在单位、当前所在页面及更新时间
"""
import time
import threading
from typing import Dict, Any, List

# 内存线程安全在线用户哈希表 (超时阈值 80 秒)
_ONLINE_USERS_LOCK = threading.Lock()
_ONLINE_USERS: Dict[str, Dict[str, Any]] = {}
TIMEOUT_SECONDS = 80.0


def record_user_heartbeat(
    username: str,
    display_name: str = "",
    unit: str = "",
    group: str = "",
    current_page: str = "",
) -> Dict[str, Any]:
    """
    记录或更新用户的最新心跳与活动状态
    """
    now = time.time()
    clean_username = str(username or "").strip()
    if not clean_username:
        return {"ok": False, "message": "用户名为空"}

    clean_display = str(display_name or "").strip() or clean_username
    clean_unit = str(unit or "").strip() or "普通用户"
    clean_group = str(group or "").strip()
    clean_page = str(current_page or "").strip() or "在线"

    with _ONLINE_USERS_LOCK:
        _ONLINE_USERS[clean_username] = {
            "username": clean_username,
            "display_name": clean_display,
            "unit": clean_unit,
            "group": clean_group,
            "current_page": clean_page,
            "last_seen": now,
        }

    return {"ok": True, "online_count": get_online_users_count()}


def record_user_logout(username: str) -> None:
    """
    显式标记用户下线/退出登录
    """
    clean_username = str(username or "").strip()
    if not clean_username:
        return
    with _ONLINE_USERS_LOCK:
        _ONLINE_USERS.pop(clean_username, None)


def get_online_users_count() -> int:
    """
    获取当前活跃在线人数
    """
    return len(get_online_users_list())


def get_online_users_list() -> List[Dict[str, Any]]:
    """
    获取当前未超时（80秒内有心跳）的活跃在线人员列表
    """
    now = time.time()
    active_users: List[Dict[str, Any]] = []

    with _ONLINE_USERS_LOCK:
        expired_keys = []
        for uname, info in _ONLINE_USERS.items():
            elapsed = now - info["last_seen"]
            if elapsed <= TIMEOUT_SECONDS:
                active_users.append({
                    "username": info["username"],
                    "display_name": info["display_name"],
                    "unit": info["unit"],
                    "group": info["group"],
                    "current_page": info["current_page"],
                    "last_seen_seconds_ago": int(elapsed),
                })
            else:
                expired_keys.append(uname)
        
        # 顺便自动清理过期超时的离线用户记录
        for k in expired_keys:
            _ONLINE_USERS.pop(k, None)

    # 按照最新活跃时间降序排序
    active_users.sort(key=lambda x: x["last_seen_seconds_ago"])
    return active_users
