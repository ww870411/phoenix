# -*- coding: utf-8 -*-
"""
供热生产指标统一算法内核 (Metric Formulas Kernel)

收口原 PostgreSQL public schema 中 sum_basic_data 与 groups 视图内定义的全部 69 项指标计算公式。
提供向量化 8 窗口计算助手、单耗/成本/收入算子，以及针对特殊企业（如 GongRe、热电厂）的定制口径。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union


# 8 窗口向量索引约定：
# 0: value_biz_date
# 1: value_peer_date
# 2: sum_7d_biz
# 3: sum_7d_peer
# 4: sum_month_biz
# 5: sum_month_peer
# 6: sum_ytd_biz
# 7: sum_ytd_peer

def zeros_vec() -> List[float]:
    """返回初始全 0 的 8 窗口向量。"""
    return [0.0] * 8


def add_vec(a: List[float], b: List[float]) -> List[float]:
    """两个 8 窗口向量对应元素相加。"""
    return [round(a[i] + b[i], 8) for i in range(8)]


def sub_vec(a: List[float], b: List[float]) -> List[float]:
    """两个 8 窗口向量对应元素相减。"""
    return [round(a[i] - b[i], 8) for i in range(8)]


def mul_scalar(a: List[float], factor: float) -> List[float]:
    """8 窗口向量乘以标量。"""
    return [round(a[i] * factor, 8) for i in range(8)]


def mul_biz_peer(a: List[float], c_biz: float, c_peer: float) -> List[float]:
    """本期项（偶数位）乘 c_biz，同期项（奇数位）乘 c_peer。"""
    c_biz = float(c_biz or 0.0)
    c_peer = float(c_peer or 0.0)
    return [
        round(a[0] * c_biz, 8), round(a[1] * c_peer, 8),
        round(a[2] * c_biz, 8), round(a[3] * c_peer, 8),
        round(a[4] * c_biz, 8), round(a[5] * c_peer, 8),
        round(a[6] * c_biz, 8), round(a[7] * c_peer, 8),
    ]


def div_biz_peer(a: List[float], d_biz: float, d_peer: float, round_digits: Optional[int] = None) -> List[Optional[float]]:
    """
    本期项除以 d_biz，同期项除以 d_peer（除数为 0 或 None 时安全返回 None，模拟 SQL NULLIF）。
    """
    d_biz = float(d_biz or 0.0)
    d_peer = float(d_peer or 0.0)

    res: List[Optional[float]] = []
    for i in range(8):
        denom = d_biz if (i % 2 == 0) else d_peer
        if denom == 0.0 or denom is None:
            res.append(None)
        else:
            val = a[i] / denom
            if round_digits is not None:
                val = round(val, round_digits)
            res.append(val)
    return res


def compute_station_heat(
    company: str,
    raw_metrics: Dict[str, List[float]],
) -> List[float]:
    """
    站内耗热量（GJ）：
    特殊公司（JinZhou, BeiFang, JinPu, ZhuangHe, YanJiuYuan）按 供热量 - 高温水销售量 计算；
    其余公司按底表申报的 consumption_station_heat 计算。
    """
    special_plants = {"JinZhou", "BeiFang", "JinPu", "ZhuangHe", "YanJiuYuan"}
    if company in special_plants:
        heat = raw_metrics.get("amount_heat_supply", zeros_vec())
        hot_water = raw_metrics.get("amount_hot_water_sales", zeros_vec())
        return sub_vec(heat, hot_water)
    return raw_metrics.get("consumption_station_heat", zeros_vec())


def compute_auxiliary_cost(
    raw_metrics: Dict[str, List[float]],
    constants_biz: Dict[str, float],
    constants_peer: Dict[str, float],
) -> List[float]:
    """
    可计量辅材成本（万元）：
    各项辅材耗量 × 对应单价 / 10000 并累加。
    辅材涵盖：酸、碱、油、氨水、石灰石、石灰石粉、氧化镁、脱硝剂。
    """
    aux_items = [
        ("consumption_acid", "price_acid"),
        ("consumption_alkali", "price_alkali"),
        ("consumption_oil", "price_oil"),
        ("consumption_ammonia_water", "price_n_ammonia_water"),
        ("consumption_limestone", "price_limestone"),
        ("consumption_limestone_powder", "price_limestone_powder"),
        ("consumption_magnesium_oxide", "price_magnesium_oxide"),
        ("consumption_denitration_agent", "price_denitration_agent"),
    ]
    total_cost = zeros_vec()
    for item_key, price_key in aux_items:
        qty = raw_metrics.get(item_key, zeros_vec())
        p_biz = constants_biz.get(price_key, 0.0)
        p_peer = constants_peer.get(price_key, 0.0)
        cost_i = mul_biz_peer(qty, p_biz, p_peer)
        total_cost = add_vec(total_cost, cost_i)
    return mul_scalar(total_cost, 1.0 / 10000.0)


def compute_overall_efficiency(
    raw_metrics: Dict[str, List[float]],
) -> List[Optional[float]]:
    """
    全厂热效率（%）：
    分子：供热量 + 36.0 × 售电量 - 外购热量
    分母：29.308 × 标煤耗量
    保留 4 位小数。
    """
    heat = raw_metrics.get("amount_heat_supply", zeros_vec())
    power_sales = raw_metrics.get("amount_power_sales", zeros_vec())
    outer_heat = raw_metrics.get("consumption_outer_purchased_heat", zeros_vec())
    std_coal = raw_metrics.get("consumption_std_coal", zeros_vec())

    res: List[Optional[float]] = []
    for i in range(8):
        denom = 29.308 * std_coal[i]
        if denom == 0.0:
            res.append(None)
        else:
            num = heat[i] + (36.0 * power_sales[i]) - outer_heat[i]
            val = round(num / denom, 4)
            res.append(val)
    return res
