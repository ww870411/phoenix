# -*- coding: utf-8 -*-
"""
供热采暖期与时间窗口动态工具集 (Season Utils)

根据业务日期自动推导所属采暖期编码（如 '25-26', '26-27'）、基准期初日、同期映射日及窗口天数，
彻底解除 SQL 视图中固化 '2025-11-01' 等日期的硬编码束缚。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Union


def parse_date(val: Optional[Union[str, date, datetime]]) -> date:
    """将字符串或日期时间对象统一转换为 date 对象。未传入或为常规标识时默认昨日。"""
    if val is None:
        return date.today() - timedelta(days=1)
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val_clean = val.strip().split("T")[0].split(" ")[0].lower()
        if not val_clean or val_clean in {"regular", "default", "none"}:
            return date.today() - timedelta(days=1)
        return datetime.strptime(val_clean, "%Y-%m-%d").date()
    raise TypeError(f"无法将类型 {type(val)} 转换为 datetime.date: {val}")


def get_season_period(d: Union[str, date, datetime]) -> str:
    """
    计算给定日期所归属的供暖期编码（如 2025-11-15 -> '25-26'，2026-03-10 -> '25-26'）。
    规则：10月1日及以后为当年度采暖季（当年后两位-次年后两位）；10月1日之前属于上年度采暖季。
    """
    dt = parse_date(d)
    if dt.month >= 10:
        y1 = dt.year % 100
        y2 = (dt.year + 1) % 100
    else:
        y1 = (dt.year - 1) % 100
        y2 = dt.year % 100
    return f"{y1:02d}-{y2:02d}"


def get_peer_date(d: Union[str, date, datetime]) -> date:
    """计算同期日期（去年的同一日）。针对闰年2月29日自动回退为2月28日。"""
    dt = parse_date(d)
    try:
        return dt.replace(year=dt.year - 1)
    except ValueError:
        # 处理闰年 2月29日 -> 平年 2月28日
        if dt.month == 2 and dt.day == 29:
            return dt.replace(year=dt.year - 1, day=28)
        raise


def get_season_windows(biz_date_in: Union[str, date, datetime]) -> Dict[str, Any]:
    """当日保持原日期；7日、月、供暖期累计分别与各自期别统计区间求交集。"""
    from backend.services.heating_season_service import get_period_settings

    biz_date = parse_date(biz_date_in)
    peer_date = get_peer_date(biz_date)
    result = {"biz_date": biz_date, "peer_date": peer_date,
              "biz_period": get_season_period(biz_date), "peer_period": get_season_period(peer_date),
              "days_day_biz": 1, "days_day_peer": 1}
    for side, anchor in (("biz", biz_date), ("peer", peer_date)):
        settings = get_period_settings(result[f"{side}_period"])
        start, end = parse_date(settings["start_date"]), parse_date(settings["end_date"])
        result[f"{side}_season_start"] = start
        result[f"{side}_season_end"] = end
        result[f"{side}_temperature_start"] = parse_date(settings["temperature_start_date"])
        for window, raw_start, count_key in (
            ("7d", anchor - timedelta(days=6), "7"),
            ("month", anchor.replace(day=1), "month"),
            ("ytd", start, "ytd"),
        ):
            first, last = max(raw_start, start), min(anchor, end)
            result[f"{side}_{window}_start"] = first
            result[f"{side}_{window}_end"] = last
            result[f"days_{count_key}_{side}"] = max(0, (last - first).days + 1)
    return result


def clip_statistical_range(start: date, end: date, period: str) -> tuple[date, date]:
    """累计区间与所属期统计边界求交集，空交集用 start > end 表示。"""
    from backend.services.heating_season_service import get_period_settings
    settings = get_period_settings(period)
    return max(start, parse_date(settings["start_date"])), min(end, parse_date(settings["end_date"]))


def get_heating_income_fraction(start: date, end: date, period: str) -> float:
    """暖收入按该期完整统计区间等额分摊；首尾均计入，区间外不分摊。"""
    from backend.services.heating_season_service import get_period_settings
    settings = get_period_settings(period)
    season_start, season_end = parse_date(settings["start_date"]), parse_date(settings["end_date"])
    total_days = (season_end - season_start).days + 1
    if total_days <= 0:
        raise ValueError("暖收入分摊的供暖期开始日不能晚于结束日")
    valid_days = max(0, (min(end, season_end) - max(start, season_start)).days + 1)
    return valid_days / total_days
