# -*- coding: utf-8 -*-
"""
算法在线验算沙盒服务 (Live Metric Sandbox Service)

用于管理页面实时拆解并验算某个指标的输入、中间过程与输出数值：
- 输入：biz_date (日期), company (公司代码), item (指标代码)
- 输出：
  - 核心元数据（中文名、单位、公式）
  - 原始输入数据拆解（分子、分母、常量单价）
  - 演算推导步骤（详细计算过程）
  - 8 窗口计算结果矩阵
  - 同比增长分析
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.services.heating_metrics.season_utils import get_season_windows
from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
from backend.services.heating_metrics.catalog_data import METRICS_CATALOG


def _format_num(val: Any, decimals: int = 4) -> str:
    if val is None:
        return "—"
    try:
        f = float(val)
        return f"{f:,.{decimals}f}".rstrip("0").rstrip(".") if "." in f"{f:.{decimals}f}" else f"{f:,.0f}"
    except (TypeError, ValueError):
        return str(val)


def _calc_growth_rate(biz: Optional[float], peer: Optional[float]) -> str:
    if biz is None or peer is None or peer == 0:
        return "—"
    try:
        rate = ((biz - peer) / abs(peer)) * 100.0
        sign = "+" if rate > 0 else ""
        return f"{sign}{rate:.2f}%"
    except Exception:
        return "—"


def explain_metric_calculation(
    session: Session,
    biz_date_str: str,
    company: str,
    item: str,
) -> Dict[str, Any]:
    """
    在线拆解验算指定公司在指定日期的指标计算逻辑与数值。
    """
    engine = DailyDashboardEngine(session)
    windows = get_season_windows(biz_date_str)
    biz_date = windows["biz_date"]
    peer_date = windows["peer_date"]

    # 查元数据字典
    meta = next((m for m in METRICS_CATALOG if m["item"] == item), None)
    if not meta:
        meta = {
            "item": item,
            "item_cn": item,
            "unit": "",
            "formula_display": "动态指标",
            "formula_description": "该指标计算逻辑由计算引擎自动生成",
            "category_cn": "通用指标",
        }

    # 统一拉取全量计算结果
    if company in ("Group", "ZhuChengQu"):
        all_rows = engine.compute_groups(biz_date_str)
    else:
        all_rows = engine.compute_sum_basic_data(biz_date_str)

    target_row = next((r for r in all_rows if r.get("company") == company and r.get("item") == item), None)

    # 提取常数底表
    const_biz, const_peer = engine.fetch_constants(windows["biz_period"], windows["peer_period"])
    area_biz = const_biz.get((company, "amount_heating_fee_area"), 0.0)
    area_peer = const_peer.get((company, "amount_heating_fee_area"), 0.0)

    # 8 窗口结果
    results_8_windows = {}
    if target_row:
        results_8_windows = {
            "value_biz_date": target_row.get("value_biz_date"),
            "value_peer_date": target_row.get("value_peer_date"),
            "growth_daily": _calc_growth_rate(target_row.get("value_biz_date"), target_row.get("value_peer_date")),
            "sum_7d_biz": target_row.get("sum_7d_biz"),
            "sum_7d_peer": target_row.get("sum_7d_peer"),
            "growth_7d": _calc_growth_rate(target_row.get("sum_7d_biz"), target_row.get("sum_7d_peer")),
            "sum_month_biz": target_row.get("sum_month_biz"),
            "sum_month_peer": target_row.get("sum_month_peer"),
            "growth_month": _calc_growth_rate(target_row.get("sum_month_biz"), target_row.get("sum_month_peer")),
            "sum_ytd_biz": target_row.get("sum_ytd_biz"),
            "sum_ytd_peer": target_row.get("sum_ytd_peer"),
            "growth_ytd": _calc_growth_rate(target_row.get("sum_ytd_biz"), target_row.get("sum_ytd_peer")),
        }

    # 构造具体演算步骤
    steps: List[Dict[str, Any]] = []

    # 步骤 1：时间周期与供暖季判定
    steps.append({
        "step_no": 1,
        "title": "采暖期与时间窗口推导",
        "description": f"输入日期 {biz_date} 经系统智能判定属于 【{windows['biz_period']}】 供暖季，对应历史同期日为 【{peer_date}】（属于 【{windows['peer_period']}】 供暖季）。本期累计天数 {windows['days_ytd_biz']} 天，同期累计 {windows['days_ytd_peer']} 天。",
    })

    # 步骤 2：数据源与基准参数提取
    inputs_breakdown: List[Dict[str, Any]] = []
    if area_biz or area_peer:
        inputs_breakdown.append({
            "param_name": "供暖收费面积 (amount_heating_fee_area)",
            "biz_value": f"{area_biz:,.2f} 万㎡",
            "peer_value": f"{area_peer:,.2f} 万㎡",
            "source": "constant_data 常量表",
        })

    # 针对各具体指标详细拆解
    if item == "rate_std_coal_per_heat":
        coal_row = next((r for r in all_rows if r.get("company") == company and r.get("item") == "consumption_std_coal"), None)
        c_biz = coal_row.get("value_biz_date", 0.0) if coal_row else 0.0
        c_peer = coal_row.get("value_peer_date", 0.0) if coal_row else 0.0
        inputs_breakdown.append({
            "param_name": "分子：标煤耗量 (consumption_std_coal)",
            "biz_value": f"{_format_num(c_biz, 2)} 吨",
            "peer_value": f"{_format_num(c_peer, 2)} 吨",
            "source": "daily_basic_data 日报底表",
        })
        steps.append({
            "step_no": 2,
            "title": "输入参数采集",
            "description": "从生产底表提取标煤耗量，从常量表提取供暖面积。",
            "breakdown": inputs_breakdown,
        })
        calc_formula = f"当日标煤单耗 = {c_biz} ÷ {area_biz} = {_format_num(target_row.get('value_biz_date') if target_row else None, 4)} 吨/万㎡"
        steps.append({
            "step_no": 3,
            "title": "算式代入与向量计算",
            "description": calc_formula,
        })

    elif item == "rate_heat_per_10k_m2":
        sh_row = next((r for r in all_rows if r.get("company") == company and r.get("item") == "consumption_station_heat"), None)
        sh_biz = sh_row.get("value_biz_date", 0.0) if sh_row else 0.0
        sh_peer = sh_row.get("value_peer_date", 0.0) if sh_row else 0.0
        inputs_breakdown.append({
            "param_name": "分子：站内耗热量 (consumption_station_heat)",
            "biz_value": f"{_format_num(sh_biz, 2)} GJ",
            "peer_value": f"{_format_num(sh_peer, 2)} GJ",
            "source": "计算引擎派生或底表申报",
        })
        steps.append({
            "step_no": 2,
            "title": "输入参数采集",
            "description": "提取换热站净耗热量与建筑供暖面积。",
            "breakdown": inputs_breakdown,
        })
        calc_formula = f"当日供暖热单耗 = {sh_biz} ÷ {area_biz} = {_format_num(target_row.get('value_biz_date') if target_row else None, 4)} GJ/万㎡"
        steps.append({
            "step_no": 3,
            "title": "算式代入与向量计算",
            "description": calc_formula,
        })

    elif item == "eco_marginal_profit":
        dir_inc = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_direct_income"), None)
        coal_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_coal_cost"), None)
        gas_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_natural_gas_cost"), None)
        pwr_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_purchased_power_cost"), None)
        water_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_purchased_water_cost"), None)
        aux_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_measurable_auxiliary_materials"), None)
        out_heat_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_outer_heat_cost"), None)
        in_heat_cost = next((r for r in all_rows if r.get("company") == company and r.get("item") == "eco_inner_purchased_heat_cost"), None)

        inc_val = dir_inc.get("value_biz_date", 0.0) if dir_inc else 0.0
        inputs_breakdown.append({
            "param_name": "直接收入合计 (eco_direct_income)",
            "biz_value": f"{_format_num(inc_val, 2)} 万元",
            "source": "直接收入聚合",
        })
        inputs_breakdown.append({
            "param_name": "变动成本 (煤+气+电+水+辅材+外购热+内购热)",
            "biz_value": "各项变动成本逐项相加",
            "source": "7大变动成本算子",
        })
        steps.append({
            "step_no": 2,
            "title": "收支项全面归集",
            "description": "归集售电、采暖费、高温水、蒸汽等直接营业收入，以及燃料、外购水电等全部变动成本。",
            "breakdown": inputs_breakdown,
        })
        steps.append({
            "step_no": 3,
            "title": "边际收益扣减计算",
            "description": f"当日边际利润 = 直接收入 ({inc_val}) - 各项变动成本之和 = {_format_num(target_row.get('value_biz_date') if target_row else None, 2)} 万元",
        })

    else:
        # 通用指标说明
        steps.append({
            "step_no": 2,
            "title": "底表数据提取与向量化聚合",
            "description": f"提取指标 {meta.get('item_cn', item)}（{item}）在 4 个时间窗口的累计申报量，并由向量算子一次性推导 8 窗口值。",
        })
        steps.append({
            "step_no": 3,
            "title": "公式运算结果",
            "description": f"计算结果：当日 {_format_num(target_row.get('value_biz_date') if target_row else None, 2)} {meta.get('unit')}，供暖期累计 {_format_num(target_row.get('sum_ytd_biz') if target_row else None, 2)} {meta.get('unit')}。",
        })

    # 步骤 4：同期同比对比
    growth_day = results_8_windows.get("growth_daily", "—")
    growth_ytd = results_8_windows.get("growth_ytd", "—")
    steps.append({
        "step_no": len(steps) + 1,
        "title": "同期同比对账分析",
        "description": f"相比去年同期日，当日增长率为 【{growth_day}】；相比去年全采暖期同期，累计增长率为 【{growth_ytd}】。",
    })

    return {
        "ok": True,
        "query": {
            "biz_date": biz_date,
            "peer_date": peer_date,
            "company": company,
            "item": item,
            "biz_period": windows["biz_period"],
            "peer_period": windows["peer_period"],
        },
        "meta": meta,
        "results_8_windows": results_8_windows,
        "inputs_breakdown": inputs_breakdown,
        "steps": steps,
    }
