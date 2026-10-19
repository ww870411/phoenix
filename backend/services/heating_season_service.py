# -*- coding: utf-8 -*-
"""
供热采暖期中枢管理服务 (Heating Season Service)

统一纳管系统的采暖期运行状态、时间窗口基准及跨周期滚动规则。
支持手动修改或滚动供暖期后：
1. 自动推导历史同期编码（如 26-27 -> 24-25）；
2. 动态生成常量表与计算引擎使用的别名映射；
3. 同步联动业务基准日期（date.json），并无缝同步 auth_manager 内存缓存；
4. 保证底层数据库历史数据 100% 完整保留与增量入库。
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.services.auth_manager import auth_manager, EAST_8
from backend.services.project_data_paths import (
    get_project_runtime_dir as _resolve_runtime_dir,
    resolve_global_date_path,
)


DEFAULT_SEASON_CONFIG: Dict[str, Any] = {
    "active_period": "25-26",
    "peer_period": "24-25",
    "start_date": "2025-11-01",
    "end_date": "2026-04-05",
    "switch_date_rule": "10-01",
    "stat_days": 156,
    "description": "供热集团生产日报供暖期全局运行参数",
}

AVAILABLE_SEASONS: List[str] = [
    "23-24",
    "24-25",
    "25-26",
    "26-27",
    "27-28",
    "28-29",
]


def _get_project_runtime_dir(project_key: str = "daily_report_25_26") -> Path:
    """获取项目 runtime 存储目录（对齐 DATA_DIRECTORY 统一路径）。"""
    runtime_dir = _resolve_runtime_dir(project_key)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def _get_season_config_path(project_key: str = "daily_report_25_26") -> Path:
    """获取供暖期配置文件路径。"""
    return _get_project_runtime_dir(project_key) / "season_config.json"


def _get_date_config_path(project_key: str = "daily_report_25_26") -> Path:
    """获取基准业务日期配置文件路径（标准解析函数，兼容本地与容器环境）。"""
    return resolve_global_date_path()


def parse_period_years(period: str) -> Optional[Tuple[int, int]]:
    """解析形如 '25-26' 为具体年份数字 (25, 26)。"""
    m = re.match(r"^\s*(\d{2})-(\d{2})\s*$", str(period or ""))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def shift_season_period(period: str, delta: int = -1) -> str:
    """
    推导相对供暖期编码。
    例如：
    - shift_season_period('26-27', -1) -> '25-26'
    - shift_season_period('25-26', -1) -> '24-25'
    - shift_season_period('25-26', +1) -> '26-27'
    """
    parsed = parse_period_years(period)
    if not parsed:
        return period
    y1, y2 = parsed
    new_y1 = (y1 + delta) % 100
    new_y2 = (y2 + delta) % 100
    return f"{new_y1:02d}-{new_y2:02d}"


def get_default_season_dates(period: str) -> Tuple[str, str]:
    """根据供暖期编码推导标准开栓日与停热日（默认 11-01 至次年 04-05）。"""
    parsed = parse_period_years(period)
    if not parsed:
        return "2025-11-01", "2026-04-05"
    y1, y2 = parsed
    start_year = 2000 + y1
    end_year = 2000 + y2
    return f"{start_year}-11-01", f"{end_year}-04-05"


def read_current_biz_date(project_key: str = "daily_report_25_26") -> str:
    """从 date.json 读取当前的 set_biz_date。"""
    date_path = _get_date_config_path(project_key)
    if date_path.exists():
        try:
            with open(date_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                val = data.get("set_biz_date")
                if val and isinstance(val, str):
                    return val.strip()
        except Exception:
            pass
    return "2026-03-28"


def write_current_biz_date(project_key: str, new_biz_date: str) -> bool:
    """
    更新 date.json 中的 set_biz_date，并同步刷新 auth_manager 内存缓存。
    """
    clean_date_str = (new_biz_date or "").strip()
    try:
        parsed_d = date.fromisoformat(clean_date_str)
    except (ValueError, TypeError):
        return False

    date_path = _get_date_config_path(project_key)
    try:
        payload: Dict[str, Any] = {}
        if date_path.exists():
            try:
                with open(date_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        payload = loaded
            except Exception:
                pass
        payload["set_biz_date"] = clean_date_str
        date_path.parent.mkdir(parents=True, exist_ok=True)
        with open(date_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # 核心关键：同步刷新 auth_manager 内部缓存与时间戳！
        try:
            auth_manager.set_display_date(parsed_d)
        except Exception:
            pass

        return True
    except Exception:
        return False


def set_business_date(project_key: str, new_biz_date: str) -> Dict[str, Any]:
    """
    独立设置全局基准业务日期。
    """
    clean_date_str = (new_biz_date or "").strip()
    try:
        date.fromisoformat(clean_date_str)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"日期格式错误，必须为 YYYY-MM-DD 格式，收到: {new_biz_date}") from exc

    ok = write_current_biz_date(project_key, clean_date_str)
    if not ok:
        raise IOError(f"写入日期配置文件失败: {clean_date_str}")

    return {
        "ok": True,
        "set_biz_date": clean_date_str,
        "current_biz_date": clean_date_str,
        "message": f"基准业务日期已成功设置为 {clean_date_str}",
    }


def get_season_config(project_key: str = "daily_report_25_26") -> Dict[str, Any]:
    """
    读取并返回当前的供暖期全局配置。
    若文件不存在，则自动初始化并保存。
    """
    cfg_path = _get_season_config_path(project_key)
    config = dict(DEFAULT_SEASON_CONFIG)
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    config.update(loaded)
        except Exception:
            pass
    else:
        config["updated_at"] = datetime.now(tz=EAST_8).isoformat()
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    config["current_biz_date"] = read_current_biz_date(project_key)
    config["available_seasons"] = AVAILABLE_SEASONS
    return config


def update_season_config(
    project_key: str,
    active_period: str,
    biz_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    手动设置并滚动当前供暖期。
    1. 自动计算 peer_period；
    2. 校验或更新开栓/停热日；
    3. 若提供了 biz_date 或跨期，自动联动更新 date.json 并同步 auth_manager；
    4. 刷新持久化配置文件。
    """
    active_period = (active_period or "").strip()
    parsed = parse_period_years(active_period)
    if not parsed:
        raise ValueError(f"供暖期格式错误，必须为形如 '25-26'、'26-27' 的两位跨年标识，收到: {active_period}")

    peer_period = shift_season_period(active_period, -1)
    def_start, def_end = get_default_season_dates(active_period)

    current_cfg = get_season_config(project_key)
    current_cfg["active_period"] = active_period
    current_cfg["peer_period"] = peer_period
    current_cfg["start_date"] = (start_date or "").strip() or def_start
    current_cfg["end_date"] = (end_date or "").strip() or def_end
    if description:
        current_cfg["description"] = description
    current_cfg["updated_at"] = datetime.now(tz=EAST_8).isoformat()

    # 处理业务日期联动
    target_biz_date = (biz_date or "").strip()
    if not target_biz_date:
        existing_date = read_current_biz_date(project_key)
        y1, y2 = parsed
        year1_str = str(2000 + y1)
        year2_str = str(2000 + y2)
        if not (existing_date.startswith(year1_str) or existing_date.startswith(year2_str)):
            target_biz_date = current_cfg["start_date"]
        else:
            target_biz_date = existing_date

    write_current_biz_date(project_key, target_biz_date)
    current_cfg["current_biz_date"] = target_biz_date

    # 写入 season_config.json
    cfg_path = _get_season_config_path(project_key)
    save_data = {
        "active_period": current_cfg["active_period"],
        "peer_period": current_cfg["peer_period"],
        "start_date": current_cfg["start_date"],
        "end_date": current_cfg["end_date"],
        "switch_date_rule": current_cfg.get("switch_date_rule", "10-01"),
        "stat_days": current_cfg.get("stat_days", 156),
        "description": current_cfg.get("description", "供热集团生产日报供暖期全局运行参数"),
        "updated_at": current_cfg["updated_at"],
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return get_season_config(project_key)


def get_season_aliases(project_key: str = "daily_report_25_26") -> Dict[str, str]:
    """
    获取当前供暖期的完整动态别名字典。
    供常量表（legacy_full.py）和运行时表达式解析器动态匹配。
    """
    cfg = get_season_config(project_key)
    active = cfg.get("active_period", "25-26")
    peer = cfg.get("peer_period", "24-25")

    aliases: Dict[str, str] = {
        "本供暖期": active,
        "同供暖期": peer,
        "本期": active,
        "同期": peer,
        "当前期": active,
        "历史同期": peer,
        active: active,
        peer: peer,
    }

    aliases[f"({active})"] = active
    aliases[f"（{active}）"] = active
    aliases[f"({peer})"] = peer
    aliases[f"（{peer}）"] = peer
    aliases["(本供暖期)"] = active
    aliases["（本供暖期）"] = active
    aliases["(同供暖期)"] = peer
    aliases["（同供暖期）"] = peer

    for s in AVAILABLE_SEASONS:
        aliases.setdefault(s, s)
        aliases.setdefault(f"({s})", s)
        aliases.setdefault(f"（{s}）", s)

    return aliases


def get_frame_to_period(project_key: str = "daily_report_25_26") -> Dict[str, str]:
    """
    获取时间帧与供暖期编码的动态映射。
    替代 runtime_expression.py 中的硬编码 FRAME_TO_PERIOD。
    """
    cfg = get_season_config(project_key)
    active = cfg.get("active_period", "25-26")
    peer = cfg.get("peer_period", "24-25")
    return {
        "biz_date": active,
        "sum_month_biz": active,
        "sum_ytd_biz": active,
        "peer_date": peer,
        "sum_month_peer": peer,
        "sum_ytd_peer": peer,
    }


def format_project_display_name(project_key: str, default_name: str = "供暖期生产日报") -> str:
    """
    根据当前激活的供暖期动态格式化项目展示名称。
    如 active_period='25-26' -> '2025-2026供暖期生产日报'
    active_period='26-27' -> '2026-2027供暖期生产日报'
    """
    if project_key == "daily_report_25_26":
        try:
            cfg = get_season_config(project_key)
            active = cfg.get("active_period")
            if active and "-" in active:
                parts = active.split("-")
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    return f"20{parts[0]}-20{parts[1]}供暖期生产日报"
        except Exception:
            pass
    return default_name
