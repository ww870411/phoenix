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
    """
    根据给定的业务日 biz_date 计算完整的 4 窗口及同期定义。
    
    窗口包括：
    - 当日：biz_date vs peer_date
    - 7日滚动：biz_7d_start ~ biz_date vs peer_7d_start ~ peer_date
    - 当月累计：biz_month_start ~ biz_date vs peer_month_start ~ peer_date
    - 采暖期至今(YTD)：biz_ytd_start ~ biz_date vs peer_ytd_start ~ peer_date
    """
    biz_date = parse_date(biz_date_in)
    peer_date = get_peer_date(biz_date)

    biz_7d_start = biz_date - timedelta(days=6)
    peer_7d_start = peer_date - timedelta(days=6)

    biz_month_start = biz_date.replace(day=1)
    peer_month_start = peer_date.replace(day=1)

    # 采暖期初起始日：10月1日之后属于当年11月1日开栓；10月1日之前属于前一年11月1日
    if biz_date.month >= 10:
        biz_ytd_start = date(biz_date.year, 11, 1)
    else:
        biz_ytd_start = date(biz_date.year - 1, 11, 1)

    peer_ytd_start = get_peer_date(biz_ytd_start)

    biz_period = get_season_period(biz_date)
    peer_period = get_season_period(peer_date)

    days_day_biz = 1
    days_day_peer = 1
    days_7_biz = 7
    days_7_peer = 7
    days_month_biz = (biz_date - biz_month_start).days + 1
    days_month_peer = (peer_date - peer_month_start).days + 1
    days_ytd_biz = (biz_date - biz_ytd_start).days + 1
    days_ytd_peer = (peer_date - peer_ytd_start).days + 1

    return {
        "biz_date": biz_date,
        "peer_date": peer_date,
        "biz_7d_start": biz_7d_start,
        "peer_7d_start": peer_7d_start,
        "biz_month_start": biz_month_start,
        "peer_month_start": peer_month_start,
        "biz_ytd_start": biz_ytd_start,
        "peer_ytd_start": peer_ytd_start,
        "biz_period": biz_period,
        "peer_period": peer_period,
        "days_day_biz": days_day_biz,
        "days_day_peer": days_day_peer,
        "days_7_biz": days_7_biz,
        "days_7_peer": days_7_peer,
        "days_month_biz": days_month_biz,
        "days_month_peer": days_month_peer,
        "days_ytd_biz": days_ytd_biz,
        "days_ytd_peer": days_ytd_peer,
    }
