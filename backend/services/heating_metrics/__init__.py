# -*- coding: utf-8 -*-
"""
供热生产指标高性能计算套件 (Heating Metrics Engine Suite)

用于替代 PostgreSQL public schema 下嵌套复杂视图 (sum_basic_data, groups, analysis_*)，
提供毫秒级、采暖期自适应的纯 Python 内存计算服务。
"""

from .season_utils import (
    get_season_period,
    get_peer_date,
    get_season_windows,
)
from .daily_engine import DailyDashboardEngine

__all__ = [
    "get_season_period",
    "get_peer_date",
    "get_season_windows",
    "DailyDashboardEngine",
]
