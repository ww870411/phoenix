"""
AI 报告使用量统计与限制服务。

功能：
- 记录每位用户每日生成的 AI 报告次数。
- 限制普通用户每日最大生成次数（默认 5 次）。
- 是否不限次数由 permissions.json 的动作位 `can_unlimited_ai_usage` 决定。
- 数据存储于 shared/ai_usage_stats.json（兼容旧路径），每日自动重置计数。
"""

import json
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from backend.services.project_data_paths import resolve_ai_usage_stats_path, resolve_permissions_path

# 数据文件路径
USAGE_STATS_FILE = resolve_ai_usage_stats_path()

# 限制配置
DAILY_LIMIT_DEFAULT = 5
DEFAULT_PROJECT_KEY = "daily_report_25_26"

# 东八区时区
EAST_8 = timezone(timedelta(hours=8))

# 线程锁，防止并发写入冲突（多进程环境下需注意文件锁，但此处简单起见使用线程锁+原子写入）
_lock = threading.Lock()


def _get_today_str() -> str:
    """获取当前东八区日期字符串 (YYYY-MM-DD)。"""
    return datetime.now(EAST_8).strftime("%Y-%m-%d")


def _load_stats() -> Dict[str, Any]:
    """读取统计文件，若不存在或解析失败则返回默认结构。"""
    if not USAGE_STATS_FILE.exists():
        return {"date": _get_today_str(), "usage": {}}
    
    try:
        content = USAGE_STATS_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, dict):
            return {"date": _get_today_str(), "usage": {}}
        return data
    except Exception:
        return {"date": _get_today_str(), "usage": {}}


def _load_permissions() -> Dict[str, Any]:
    path = resolve_permissions_path()
    if not path.exists():
        return {}
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _is_unlimited_group(user_group: str, project_key: str) -> bool:
    permissions = _load_permissions()
    groups = permissions.get("groups")
    if not isinstance(groups, dict):
        return False
    group_cfg = groups.get(user_group)
    if not isinstance(group_cfg, dict):
        return False

    projects = group_cfg.get("projects")
    if isinstance(projects, dict):
        project_cfg = projects.get(project_key)
        if isinstance(project_cfg, dict):
            project_actions = project_cfg.get("actions")
            if isinstance(project_actions, dict):
                return bool(project_actions.get("can_unlimited_ai_usage", False))

    # 兼容旧结构（若仍存在）
    legacy_actions = group_cfg.get("actions")
    if isinstance(legacy_actions, dict):
        return bool(legacy_actions.get("can_unlimited_ai_usage", False))
    return False


def _save_stats(data: Dict[str, Any]) -> None:
    """原子性写入统计文件。"""
    temp_file = USAGE_STATS_FILE.with_suffix(".tmp")
    try:
        with temp_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(USAGE_STATS_FILE)
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        raise e


def check_and_increment_usage(
    username: str,
    user_group: str,
    project_key: str = DEFAULT_PROJECT_KEY,
) -> Tuple[bool, str]:
    """
    检查用户今日是否还可以生成报告，并增加计数。
    
    Returns:
        (allowed, message): allowed 为 True 表示允许，False 表示拒绝。message 为拒绝原因或当前状态。
    """
    if not username:
        return False, "无效的用户信息"

    today = _get_today_str()
    group = (user_group or "").strip()
    normalized_project_key = (project_key or DEFAULT_PROJECT_KEY).strip() or DEFAULT_PROJECT_KEY
    is_unlimited = _is_unlimited_group(group, normalized_project_key)

    with _lock:
        stats = _load_stats()
        
        # 检查日期，如果是新的一天，重置数据
        if stats.get("date") != today:
            stats = {
                "date": today,
                "usage": {}
            }
        
        usage_map = stats.get("usage", {})
        current_count = usage_map.get(username, 0)
        
        # 检查限制
        if not is_unlimited and current_count >= DAILY_LIMIT_DEFAULT:
            return False, f"今日 AI 报告生成次数已达上限（{current_count}/{DAILY_LIMIT_DEFAULT}）。"
        
        # 增加计数并保存
        new_count = current_count + 1
        usage_map[username] = new_count
        stats["usage"] = usage_map
        
        try:
            _save_stats(stats)
        except Exception as e:
            # 只有保存成功才算成功，避免计数丢失
            return False, f"保存统计数据失败: {str(e)}"
            
        limit_info = "不限" if is_unlimited else f"{DAILY_LIMIT_DEFAULT}"
        return True, f"今日已用 {new_count}/{limit_info}"

def get_usage_stats() -> Dict[str, Any]:
    """获取当前统计信息（只读）。"""
    with _lock:
        return _load_stats()
