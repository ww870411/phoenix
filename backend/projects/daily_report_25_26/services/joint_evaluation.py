# -*- coding: utf-8 -*-
"""
主城区供热运行联合评价模型服务 (Joint Evaluation Service)

基于采暖度日数 HDD20（含前 3 日热惯性滞后与月份阶段修正）构建参考耗热基准，
结合同月单位面积参考投诉率构建独立服务评价维度，输出供热偏差率、投诉强度指数、
四象限运行诊断与历史经验波动参考带对比。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.services.dashboard_expression import load_default_push_date
from backend.services.heating_metrics.daily_engine import DailyDashboardEngine, ZHUCHENGQU_COMPANIES
from backend.services.heating_metrics.season_utils import get_season_period, parse_date

PROJECT_KEY = "daily_report_25_26"
AREA_COMPANY = "GongRe"
AREA_ITEM = "amount_heating_fee_area"
HEAT_ITEM = "consumption_station_heat"
COMPLAINT_ITEM = "amount_daily_service_complaints"
FORECAST_HORIZON_DAYS = 5
FORECAST_TEMP_TYPE = "near"

# 冻结后的 HDD20 三日滞后参考单耗模型参数（单位：GJ/万㎡·日）
MODEL_INTERCEPT = 3.3730
MODEL_COEF_HDD20_TODAY = 0.5137
MODEL_COEF_HDD20_PREV3 = 0.3521
BASE_TEMP_C = 20.0

MONTH_HEAT_ADJUSTMENTS: Dict[int, float] = {
    11: 0.0,
    12: 0.2672,
    1: -0.1808,
    2: -1.2883,
    3: -3.7264,
}

# 同口径近两季（2024-2025、2025-2026）分月单位面积日均参考投诉率（件/万㎡·日）
MONTH_COMPLAINT_RATES: Dict[int, float] = {
    11: 0.036085,
    12: 0.023953,
    1: 0.019384,
    2: 0.012987,
    3: 0.006254,
}

# 样本外留一供暖期交叉验证历史经验波动带（5%—95%分位，单位：%）
EMPIRICAL_BANDS: List[Dict[str, Any]] = [
    {"period_days": 1, "label": "1日", "window_count": 442, "p5": -20.80, "median": -0.61, "p95": 21.89, "rmse": 14.21},
    {"period_days": 7, "label": "7日", "window_count": 424, "p5": -16.77, "median": -0.22, "p95": 13.56, "rmse": 9.30},
    {"period_days": 14, "label": "14日", "window_count": 403, "p5": -13.83, "median": 0.69, "p95": 9.78, "rmse": 7.74},
    {"period_days": 18, "label": "18日", "window_count": 391, "p5": -12.11, "median": 1.33, "p95": 8.05, "rmse": 6.95},
    {"period_days": 30, "label": "30日", "window_count": 355, "p5": -8.89, "median": 0.39, "p95": 6.43, "rmse": 5.06},
]

QUADRANT_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "I": {
        "code": "I",
        "name": "Ⅰ 高耗热·高投诉",
        "short_name": "Ⅰ 高耗高诉",
        "feature": "偏差率 > 0%，投诉指数 > 100",
        "diagnosis": "投入与效果背离",
        "action": "优先排查管网水力失衡、局部故障及换热站响应滞后，严防盲目加量。",
        "color": "#ef4444",
    },
    "II": {
        "code": "II",
        "name": "Ⅱ 低耗热·高投诉",
        "short_name": "Ⅱ 低耗高诉",
        "feature": "偏差率 ≤ 0%，投诉指数 > 100",
        "diagnosis": "供热不足或滞后",
        "action": "核查降温前预热是否及时，重点补强低温时段与末端欠热区域。",
        "color": "#f59e0b",
    },
    "III": {
        "code": "III",
        "name": "Ⅲ 低耗热·低投诉",
        "short_name": "Ⅲ 低耗低诉",
        "feature": "偏差率 ≤ 0%，投诉指数 ≤ 100",
        "diagnosis": "潜在能效改善区",
        "action": "结合室温抽测确认达标情况，总结提炼精益调度与节能经验。",
        "color": "#10b981",
    },
    "IV": {
        "code": "IV",
        "name": "Ⅳ 高耗热·低投诉",
        "short_name": "Ⅳ 高耗低诉",
        "feature": "偏差率 > 0%，投诉指数 ≤ 100",
        "diagnosis": "服务良好但偏粗放",
        "action": "在稳住室温达标前提下，审视回温时段降负荷节奏与节能余量空间。",
        "color": "#3b82f6",
    },
}


def is_valid_eval_date(target_date: date) -> bool:
    """
    判定日期是否处于联合评价模型有效测算区间内（11月5日—次年3月31日）。
    11月1日—11月4日、4月1日—4月5日及非供暖月份均视为测算外日期。
    """
    if target_date.month == 11:
        return target_date.day >= 5
    if target_date.month in (12, 1, 2, 3):
        return True
    return False


def calc_hdd20(avg_temp_c: Optional[float]) -> Optional[float]:
    """根据日均室外气温计算采暖度日数 HDD20 = max(0, 20 - T)。"""
    if avg_temp_c is None:
        return None
    return max(0.0, BASE_TEMP_C - float(avg_temp_c))


def calc_reference_unit_heat(month: int, hdd20_today: float, hdd20_prev3: float) -> float:
    """计算单日模型参考热单耗（GJ/万㎡·日）。"""
    if month not in MONTH_HEAT_ADJUSTMENTS:
        raise ValueError(f"月份 {month} 不在联合评价模型适用范围（11月—次年3月）内")
    return (
        MODEL_INTERCEPT
        + MODEL_COEF_HDD20_TODAY * float(hdd20_today)
        + MODEL_COEF_HDD20_PREV3 * float(hdd20_prev3)
        + MONTH_HEAT_ADJUSTMENTS[month]
    )


def calc_reference_complaints(month: int, area_10k_m2: float) -> float:
    """计算单日同月同面积参考投诉量（件）。"""
    if month not in MONTH_COMPLAINT_RATES:
        raise ValueError(f"月份 {month} 不在联合评价模型适用范围（11月—次年3月）内")
    return MONTH_COMPLAINT_RATES[month] * float(area_10k_m2)


def classify_quadrant(heat_deviation_pct: Optional[float], complaint_index: Optional[float]) -> Optional[Dict[str, str]]:
    """根据供热偏差率（0%分界）与投诉强度指数（100分界）归属四象限。"""
    if heat_deviation_pct is None or complaint_index is None:
        return None
    high_heat = heat_deviation_pct > 0.0
    high_complaint = complaint_index > 100.0
    if high_heat and high_complaint:
        return QUADRANT_DEFINITIONS["I"]
    if (not high_heat) and high_complaint:
        return QUADRANT_DEFINITIONS["II"]
    if (not high_heat) and (not high_complaint):
        return QUADRANT_DEFINITIONS["III"]
    return QUADRANT_DEFINITIONS["IV"]


def match_empirical_band(valid_day_count: int) -> Dict[str, Any]:
    """匹配与评价有效天数最接近的历史经验波动参考带。"""
    if valid_day_count <= 0:
        return {**EMPIRICAL_BANDS[0], "exact": False}
    for band in EMPIRICAL_BANDS:
        if band["period_days"] == valid_day_count:
            return {**band, "exact": True}
    nearest = min(EMPIRICAL_BANDS, key=lambda item: (abs(item["period_days"] - valid_day_count), item["period_days"]))
    return {**nearest, "exact": False}


def evaluate_band_status(heat_deviation_pct: Optional[float], band: Dict[str, Any]) -> Dict[str, Any]:
    """判定偏差率是否落在对应周期历史 5%~95% 经验波动带内。"""
    if heat_deviation_pct is None:
        return {"status": "unknown", "label": "数据不足，无法比对经验波动带"}
    p5 = float(band["p5"])
    p95 = float(band["p95"])
    if heat_deviation_pct < p5:
        return {"status": "below_p5", "label": f"低于历史5%下界（{p5:+.2f}%），存在明显偏低风险"}
    if heat_deviation_pct > p95:
        return {"status": "above_p95", "label": f"超出历史95%上界（{p95:+.2f}%），能耗明显偏高"}
    return {"status": "within_band", "label": f"处于{band['label']}历史5%–95%正常经验带（{p5:+.2f}% ~ {p95:+.2f}%）内"}


def split_date_range(start_date: date, end_date: date) -> Tuple[List[date], List[date]]:
    """切分日期闭区间为（有效评价日列表，被剔除的测算外日期列表）。"""
    valid_dates: List[date] = []
    excluded_dates: List[date] = []
    cursor = start_date
    while cursor <= end_date:
        if is_valid_eval_date(cursor):
            valid_dates.append(cursor)
        else:
            excluded_dates.append(cursor)
        cursor += timedelta(days=1)
    return valid_dates, excluded_dates


def collect_rolling_periods(
    anchor_date: date,
    period_days: int,
    period_count: int,
) -> Tuple[List[List[date]], List[date]]:
    """
    从距离 anchor_date 最近的期间或单日算起，向前收集连续有效评价日并切分为最多 period_count 个周期。
    凡遇到 11.1-11.4、4.1-4.5 等测算外日期自动剔除并记录，不占用有效周期天数；
    如遇供暖季边界（11月5日之前再无本季有效日），停止跨夏季向更早年份无限回溯。
    返回：(按时间正序排列的周期列表, 被跳过的测算外日期列表)
    """
    period_days = max(1, min(int(period_days), 60))
    period_count = max(1, min(int(period_count), 60))
    season_period = get_season_period(anchor_date)
    season_start_year = 2000 + int(season_period.split("-")[0])
    season_eval_start = date(season_start_year, 11, 5)

    valid_desc: List[date] = []
    excluded_desc: List[date] = []
    target_valid_total = period_days * period_count

    cursor = anchor_date
    while cursor >= season_eval_start and len(valid_desc) < target_valid_total:
        if is_valid_eval_date(cursor):
            valid_desc.append(cursor)
        else:
            excluded_desc.append(cursor)
        cursor -= timedelta(days=1)

    if not valid_desc:
        return [], sorted(excluded_desc)

    # 先按从近到远切分，每组 period_days 天；再翻转为时间正序（第1期 -> 最近一期）
    chunks_desc: List[List[date]] = []
    for idx in range(0, len(valid_desc), period_days):
        chunk = list(reversed(valid_desc[idx : idx + period_days]))
        chunks_desc.append(chunk)
    chunks_asc = list(reversed(chunks_desc))
    return chunks_asc, sorted(excluded_desc)


def _round_opt(val: Optional[float], digits: int) -> Optional[float]:
    if val is None:
        return None
    return round(float(val), digits)


def _normalize_area_to_10k_m2(value: Optional[float], unit: Optional[str]) -> Optional[float]:
    """
    将 constant_data 中的供暖收费面积统一换算为“万㎡”。
    系统常量表（GongRe_constant_Sheet）默认以“万㎡”录入；仅当单位明确为“㎡”（不含“万”）
    或未标注单位且数值大于 100,000（明显为平方米级）时执行 ÷ 10000 换算。
    """
    if value is None or float(value) <= 0:
        return None
    val = float(value)
    unit_text = str(unit or "").strip()
    if unit_text == "㎡" or (not unit_text and val > 100000.0):
        return val / 10000.0
    return val


def build_daily_eval_row(
    target_date: date,
    area_10k_m2: Optional[float],
    avg_temp_map: Dict[str, Optional[float]],
    heat_map: Dict[date, float],
    complaint_map: Dict[date, float],
) -> Dict[str, Any]:
    """基于单日基础数据与前 3 日气温，计算单日联合评价结果（area_10k_m2 单位为万㎡）。"""
    iso = target_date.isoformat()
    valid_area_10k = float(area_10k_m2) if (area_10k_m2 is not None and float(area_10k_m2) > 0) else None
    area_m2 = (valid_area_10k * 10000.0) if valid_area_10k is not None else None
    avg_temp = avg_temp_map.get(iso)
    hdd20_today = calc_hdd20(avg_temp)

    prev_hdd_vals: List[float] = []
    for offset in (1, 2, 3):
        prev_iso = (target_date - timedelta(days=offset)).isoformat()
        prev_hdd = calc_hdd20(avg_temp_map.get(prev_iso))
        if prev_hdd is not None:
            prev_hdd_vals.append(prev_hdd)
    has_prev3_temp = len(prev_hdd_vals) == 3
    hdd20_prev3 = (sum(prev_hdd_vals) / 3.0) if has_prev3_temp else None

    has_heat = target_date in heat_map
    has_complaint = target_date in complaint_map
    actual_heat_gj = float(heat_map[target_date]) if has_heat else None
    actual_complaints = float(complaint_map[target_date]) if has_complaint else None

    ref_unit_heat: Optional[float] = None
    ref_heat_gj: Optional[float] = None
    actual_unit_heat: Optional[float] = None
    heat_deviation_pct: Optional[float] = None
    heat_delta_gj: Optional[float] = None

    if hdd20_today is not None and hdd20_prev3 is not None and target_date.month in MONTH_HEAT_ADJUSTMENTS:
        ref_unit_heat = calc_reference_unit_heat(target_date.month, hdd20_today, hdd20_prev3)
        if valid_area_10k is not None:
            ref_heat_gj = ref_unit_heat * valid_area_10k
            if actual_heat_gj is not None and ref_heat_gj > 0:
                actual_unit_heat = actual_heat_gj / valid_area_10k
                heat_delta_gj = actual_heat_gj - ref_heat_gj
                heat_deviation_pct = heat_delta_gj / ref_heat_gj * 100.0

    ref_complaints: Optional[float] = None
    complaint_delta: Optional[float] = None
    complaint_index: Optional[float] = None
    if valid_area_10k is not None and target_date.month in MONTH_COMPLAINT_RATES:
        ref_complaints = calc_reference_complaints(target_date.month, valid_area_10k)
        if actual_complaints is not None and ref_complaints > 0:
            complaint_delta = actual_complaints - ref_complaints
            complaint_index = actual_complaints / ref_complaints * 100.0

    quadrant = classify_quadrant(heat_deviation_pct, complaint_index)
    missing_reasons: List[str] = []
    if valid_area_10k is None:
        missing_reasons.append("缺少GongRe供暖收费面积")
    if avg_temp is None:
        missing_reasons.append("缺少当日日均气温")
    if not has_prev3_temp:
        missing_reasons.append("缺少前3日完整气温")
    if not has_heat:
        missing_reasons.append("缺少站内耗热量")
    if not has_complaint:
        missing_reasons.append("缺少省市平台投诉量")

    return {
        "date": iso,
        "month": target_date.month,
        "area_m2": _round_opt(area_m2, 2),
        "area_10k_m2": _round_opt(valid_area_10k, 4),
        "avg_temp": _round_opt(avg_temp, 2),
        "hdd20_today": _round_opt(hdd20_today, 2),
        "hdd20_prev3": _round_opt(hdd20_prev3, 2),
        "actual_unit_heat": _round_opt(actual_unit_heat, 2),
        "ref_unit_heat": _round_opt(ref_unit_heat, 2),
        "actual_heat_gj": _round_opt(actual_heat_gj, 2),
        "ref_heat_gj": _round_opt(ref_heat_gj, 2),
        "heat_delta_gj": _round_opt(heat_delta_gj, 2),
        "heat_deviation_pct": _round_opt(heat_deviation_pct, 2),
        "actual_complaints": _round_opt(actual_complaints, 0),
        "ref_complaints": _round_opt(ref_complaints, 2),
        "complaint_delta": _round_opt(complaint_delta, 2),
        "complaint_index": _round_opt(complaint_index, 1),
        "quadrant": quadrant,
        "is_complete": len(missing_reasons) == 0,
        "missing_reasons": missing_reasons,
        "_raw": {
            "area_10k_m2": valid_area_10k,
            "avg_temp": avg_temp,
            "hdd20_today": hdd20_today,
            "hdd20_prev3": hdd20_prev3,
            "actual_heat_gj": actual_heat_gj,
            "ref_heat_gj": ref_heat_gj,
            "actual_complaints": actual_complaints,
            "ref_complaints": ref_complaints,
        },
    }


def aggregate_eval_rows(rows: Sequence[Dict[str, Any]], label: str = "") -> Dict[str, Any]:
    """
    严格按“先累计区间总量、再求比值”汇总一组有效日记录。
    对于单个维度仅统计同时具备实际值与参考值的日期，防止未填报日被误作 0 拉低偏差率。
    """
    total_valid_days = len(rows)
    if total_valid_days == 0:
        band = match_empirical_band(0)
        return {
            "label": label or "无有效评价区间",
            "start_date": None,
            "end_date": None,
            "valid_days": 0,
            "complete_days": 0,
            "heat_valid_days": 0,
            "complaint_valid_days": 0,
            "avg_temp": None,
            "avg_hdd20_today": None,
            "avg_hdd20_prev3": None,
            "actual_unit_heat_avg": None,
            "ref_unit_heat_avg": None,
            "actual_heat_gj": None,
            "ref_heat_gj": None,
            "heat_delta_gj": None,
            "heat_deviation_pct": None,
            "actual_complaints": None,
            "ref_complaints": None,
            "complaint_delta": None,
            "complaint_index": None,
            "quadrant": None,
            "empirical_band": band,
            "band_status": evaluate_band_status(None, band),
            "incomplete_dates": [],
        }

    heat_pairs = [
        (r["_raw"]["actual_heat_gj"], r["_raw"]["ref_heat_gj"], r["_raw"]["area_10k_m2"])
        for r in rows
        if r["_raw"]["actual_heat_gj"] is not None
        and r["_raw"]["ref_heat_gj"] is not None
        and r["_raw"]["area_10k_m2"] is not None
    ]
    complaint_pairs = [
        (r["_raw"]["actual_complaints"], r["_raw"]["ref_complaints"])
        for r in rows
        if r["_raw"]["actual_complaints"] is not None and r["_raw"]["ref_complaints"] is not None
    ]

    temp_vals = [r["_raw"]["avg_temp"] for r in rows if r["_raw"]["avg_temp"] is not None]
    hdd_vals = [r["_raw"]["hdd20_today"] for r in rows if r["_raw"]["hdd20_today"] is not None]
    prev3_vals = [r["_raw"]["hdd20_prev3"] for r in rows if r["_raw"]["hdd20_prev3"] is not None]

    actual_heat_sum = sum(p[0] for p in heat_pairs) if heat_pairs else None
    ref_heat_sum = sum(p[1] for p in heat_pairs) if heat_pairs else None
    heat_delta_sum = (actual_heat_sum - ref_heat_sum) if (actual_heat_sum is not None and ref_heat_sum is not None) else None
    heat_deviation_pct = (
        (heat_delta_sum / ref_heat_sum * 100.0)
        if (heat_delta_sum is not None and ref_heat_sum is not None and ref_heat_sum > 0)
        else None
    )

    area_days_sum = sum(p[2] for p in heat_pairs) if heat_pairs else None
    actual_unit_heat_avg = (actual_heat_sum / area_days_sum) if (actual_heat_sum is not None and area_days_sum and area_days_sum > 0) else None
    ref_unit_heat_avg = (ref_heat_sum / area_days_sum) if (ref_heat_sum is not None and area_days_sum and area_days_sum > 0) else None

    actual_comp_sum = sum(p[0] for p in complaint_pairs) if complaint_pairs else None
    ref_comp_sum = sum(p[1] for p in complaint_pairs) if complaint_pairs else None
    comp_delta_sum = (actual_comp_sum - ref_comp_sum) if (actual_comp_sum is not None and ref_comp_sum is not None) else None
    complaint_index = (
        (actual_comp_sum / ref_comp_sum * 100.0)
        if (actual_comp_sum is not None and ref_comp_sum is not None and ref_comp_sum > 0)
        else None
    )

    quadrant = classify_quadrant(heat_deviation_pct, complaint_index)
    complete_days = sum(1 for r in rows if r["is_complete"])
    band = match_empirical_band(len(heat_pairs) if heat_pairs else total_valid_days)
    band_status = evaluate_band_status(heat_deviation_pct, band)

    start_iso = rows[0]["date"]
    end_iso = rows[-1]["date"]
    auto_label = start_iso if start_iso == end_iso else f"{start_iso} ~ {end_iso}"

    return {
        "label": label or auto_label,
        "start_date": start_iso,
        "end_date": end_iso,
        "valid_days": total_valid_days,
        "complete_days": complete_days,
        "heat_valid_days": len(heat_pairs),
        "complaint_valid_days": len(complaint_pairs),
        "avg_temp": _round_opt(sum(temp_vals) / len(temp_vals), 2) if temp_vals else None,
        "avg_hdd20_today": _round_opt(sum(hdd_vals) / len(hdd_vals), 2) if hdd_vals else None,
        "avg_hdd20_prev3": _round_opt(sum(prev3_vals) / len(prev3_vals), 2) if prev3_vals else None,
        "actual_unit_heat_avg": _round_opt(actual_unit_heat_avg, 2),
        "ref_unit_heat_avg": _round_opt(ref_unit_heat_avg, 2),
        "actual_heat_gj": _round_opt(actual_heat_sum, 2),
        "ref_heat_gj": _round_opt(ref_heat_sum, 2),
        "heat_delta_gj": _round_opt(heat_delta_sum, 2),
        "heat_deviation_pct": _round_opt(heat_deviation_pct, 2),
        "actual_complaints": _round_opt(actual_comp_sum, 0),
        "ref_complaints": _round_opt(ref_comp_sum, 2),
        "complaint_delta": _round_opt(comp_delta_sum, 2),
        "complaint_index": _round_opt(complaint_index, 1),
        "quadrant": quadrant,
        "empirical_band": band,
        "band_status": band_status,
        "incomplete_dates": [r["date"] for r in rows if not r["is_complete"]],
    }


def _fetch_gongre_fee_area_map(db: Session, periods: Iterable[str]) -> Dict[str, Optional[float]]:
    """
    直接读取 constant_data 中 GongRe 的 amount_heating_fee_area 并规范化为“万㎡”。
    优先选用总表 GongRe_constant_Sheet、最近操作时间记录。
    """
    period_list = sorted({str(p) for p in periods if p})
    if not period_list:
        return {}
    rows = db.execute(
        text(
            """
            SELECT period, value, unit, sheet_name
            FROM constant_data
            WHERE company = :company
              AND item = :item
              AND period = ANY(:periods)
            ORDER BY
              CASE WHEN sheet_name = 'GongRe_constant_Sheet' THEN 0 ELSE 1 END,
              operation_time DESC NULLS LAST,
              id DESC
            """
        ),
        {"company": AREA_COMPANY, "item": AREA_ITEM, "periods": period_list},
    ).mappings().all()
    area_map: Dict[str, Optional[float]] = {}
    for row in rows:
        period_key = str(row["period"])
        if period_key in area_map:
            continue
        val = row.get("value")
        normalized = _normalize_area_to_10k_m2(float(val) if val is not None else None, row.get("unit"))
        area_map[period_key] = normalized
    return area_map


def _fetch_daily_metric_series(
    db: Session,
    start_date: date,
    end_date: date,
) -> Tuple[Dict[date, float], Dict[date, float]]:
    """拉取指定闭区间内主城区 ZhuChengQu 逐日站内耗热量与省市平台投诉量。"""
    if start_date > end_date:
        return {}, {}
    rows = db.execute(
        text(
            """
            SELECT date, item, SUM(value) AS total_value
            FROM daily_basic_data
            WHERE date BETWEEN :start_date AND :end_date
              AND company = ANY(:companies)
              AND item = ANY(:items)
            GROUP BY date, item
            ORDER BY date
            """
        ),
        {
            "start_date": start_date,
            "end_date": end_date,
            "companies": ZHUCHENGQU_COMPANIES,
            "items": [HEAT_ITEM, COMPLAINT_ITEM],
        },
    ).mappings().all()
    heat_map: Dict[date, float] = {}
    complaint_map: Dict[date, float] = {}
    for row in rows:
        day = row["date"]
        if day is None or row["total_value"] is None:
            continue
        item = str(row["item"])
        val = float(row["total_value"])
        if item == HEAT_ITEM:
            heat_map[day] = val
        elif item == COMPLAINT_ITEM:
            complaint_map[day] = val
    return heat_map, complaint_map


def _strip_raw(row: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(row)
    cleaned.pop("_raw", None)
    return cleaned


def _fetch_near_temperature_daily_map(
    db: Session,
    start_date: date,
    end_date: date,
) -> Dict[str, Dict[str, Any]]:
    """按北京时间读取 temperature_data 中指定类型的逐日均温、极值与小时数。"""
    if start_date > end_date:
        return {}
    rows = db.execute(
        text(
            """
            SELECT
                DATE_TRUNC('day', (date_time AT TIME ZONE 'Asia/Shanghai'))::date AS day,
                AVG(value) AS avg_temp,
                MIN(value) AS min_temp,
                MAX(value) AS max_temp,
                COUNT(*) AS hours_count
            FROM temperature_data
            WHERE type = :temp_type
              AND (date_time AT TIME ZONE 'Asia/Shanghai')::date BETWEEN :start_date AND :end_date
            GROUP BY day
            ORDER BY day
            """
        ),
        {
            "temp_type": FORECAST_TEMP_TYPE,
            "start_date": start_date,
            "end_date": end_date,
        },
    ).mappings().all()
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        day_val = row.get("day")
        if day_val is None or row.get("avg_temp") is None:
            continue
        iso = day_val.isoformat() if hasattr(day_val, "isoformat") else str(day_val)
        result[iso] = {
            "avg_temp": float(row["avg_temp"]),
            "min_temp": float(row["min_temp"]) if row.get("min_temp") is not None else None,
            "max_temp": float(row["max_temp"]) if row.get("max_temp") is not None else None,
            "hours_count": int(row["hours_count"] or 0),
        }
    return result


def _build_daily_forecast_advice(
    *,
    in_valid_window: bool,
    ref_heat_gj: Optional[float],
    delta_vs_prev_ref_gj: Optional[float],
    pct_vs_prev_ref: Optional[float],
    temp_delta_vs_prev: Optional[float],
    pct_vs_base_actual: Optional[float],
) -> Dict[str, str]:
    """依据日间参考需热增减与热惯性缓冲，生成单日生产调度辅助建议。"""
    if not in_valid_window:
        return {
            "level": "muted",
            "tag": "测算窗口外",
            "reason": "该日期不在 11月5日—次年3月31日模型有效测算期内。",
        }
    if ref_heat_gj is None or pct_vs_prev_ref is None or delta_vs_prev_ref_gj is None:
        return {
            "level": "muted",
            "tag": "待补齐基准",
            "reason": "缺少完整前 3 日气温或收费面积，暂无法给出调度建议。",
        }

    if pct_vs_prev_ref >= 5.0 or delta_vs_prev_ref_gj >= 1500.0:
        reason = f"较前日参考需热量增加 {delta_vs_prev_ref_gj:+,.0f} GJ（{pct_vs_prev_ref:+.1f}%），建议提前升负荷并做好蓄热。"
        return {"level": "warm", "tag": "建议提前升负荷", "reason": reason}

    if pct_vs_prev_ref <= -5.0 or delta_vs_prev_ref_gj <= -1500.0:
        reason = f"较前日参考需热量回落 {delta_vs_prev_ref_gj:+,.0f} GJ（{pct_vs_prev_ref:+.1f}%），建议顺势分步压减负荷避免超供。"
        if pct_vs_base_actual is not None and pct_vs_base_actual > 3.0:
            reason += f" 注意当前基日实耗偏低，仍高于基日实耗 {pct_vs_base_actual:+.1f}%。"
        return {"level": "cool", "tag": "建议顺势减负荷", "reason": reason}

    if temp_delta_vs_prev is not None and abs(temp_delta_vs_prev) >= 2.0:
        reason = (
            f"气温较前日波动 {temp_delta_vs_prev:+.1f}℃，受前 3 日热惯性缓冲，"
            f"参考需热仅变动 {pct_vs_prev_ref:+.1f}%，建议微调避免过调。"
        )
        return {"level": "amber", "tag": "惯性过渡·微调", "reason": reason}

    reason = f"参考需热较前日变化平稳（{delta_vs_prev_ref_gj:+,.0f} GJ，{pct_vs_prev_ref:+.1f}%），建议维持稳态均衡供热。"
    return {"level": "steady", "tag": "平稳运行保稳", "reason": reason}


def build_forecast_payload(
    *,
    base_date: date,
    near_temp_map: Dict[str, Dict[str, Any]],
    fallback_avg_temp_map: Dict[str, Optional[float]],
    area_map: Dict[str, Optional[float]],
    base_actual_heat_gj: Optional[float] = None,
    base_actual_complaints: Optional[float] = None,
    horizon_days: int = FORECAST_HORIZON_DAYS,
) -> Dict[str, Any]:
    """
    基于系统最新业务日之后 N 日（不含业务日本身）的 type='near' 逐小时气温预报，
    滚动计算未来每日参考单耗、参考耗热量基准与生产调度建议，并附带业务日自身作对照。
    """
    merged_avg_temp_map: Dict[str, Optional[float]] = dict(fallback_avg_temp_map)
    for iso_key, info in near_temp_map.items():
        if info.get("avg_temp") is not None:
            merged_avg_temp_map[iso_key] = float(info["avg_temp"])

    base_iso = base_date.isoformat()
    base_area_10k = area_map.get(get_season_period(base_date))
    base_heat_map = {base_date: float(base_actual_heat_gj)} if base_actual_heat_gj is not None else {}
    base_complaint_map = {base_date: float(base_actual_complaints)} if base_actual_complaints is not None else {}
    base_eval_raw = build_daily_eval_row(
        base_date,
        base_area_10k,
        merged_avg_temp_map,
        base_heat_map,
        base_complaint_map,
    )
    base_eval = _strip_raw(base_eval_raw)
    base_temp_info = near_temp_map.get(base_iso) or {}
    base_avg_temp = base_eval_raw["_raw"]["avg_temp"]
    base_ref_heat_gj = base_eval_raw["_raw"]["ref_heat_gj"]
    base_actual_raw = base_eval_raw["_raw"]["actual_heat_gj"]

    baseline_row = {
        **base_eval,
        "row_type": "baseline",
        "offset_days": 0,
        "offset_label": "业务日对照",
        "min_temp": _round_opt(base_temp_info.get("min_temp"), 1),
        "max_temp": _round_opt(base_temp_info.get("max_temp"), 1),
        "hours_count": base_temp_info.get("hours_count"),
        "in_valid_window": is_valid_eval_date(base_date),
    }

    forecast_days: List[Dict[str, Any]] = []
    prev_avg_temp = base_avg_temp
    prev_ref_heat_gj = base_ref_heat_gj

    for offset in range(1, max(1, horizon_days) + 1):
        target_day = base_date + timedelta(days=offset)
        target_iso = target_day.isoformat()
        temp_info = near_temp_map.get(target_iso) or {}
        raw_avg_temp = float(temp_info["avg_temp"]) if temp_info.get("avg_temp") is not None else None
        hdd20_today = calc_hdd20(raw_avg_temp)

        prev_hdd_vals: List[float] = []
        for lag in (1, 2, 3):
            lag_iso = (target_day - timedelta(days=lag)).isoformat()
            lag_hdd = calc_hdd20(merged_avg_temp_map.get(lag_iso))
            if lag_hdd is not None:
                prev_hdd_vals.append(lag_hdd)
        hdd20_prev3 = (sum(prev_hdd_vals) / 3.0) if len(prev_hdd_vals) == 3 else None

        in_window = is_valid_eval_date(target_day)
        day_area_10k = area_map.get(get_season_period(target_day))

        ref_unit_heat: Optional[float] = None
        ref_heat_gj: Optional[float] = None
        if in_window and hdd20_today is not None and hdd20_prev3 is not None and target_day.month in MONTH_HEAT_ADJUSTMENTS:
            ref_unit_heat = calc_reference_unit_heat(target_day.month, hdd20_today, hdd20_prev3)
            if day_area_10k is not None:
                ref_heat_gj = ref_unit_heat * day_area_10k

        ref_complaints: Optional[float] = None
        if in_window and day_area_10k is not None and target_day.month in MONTH_COMPLAINT_RATES:
            ref_complaints = calc_reference_complaints(target_day.month, day_area_10k)

        temp_delta_vs_prev = (
            (raw_avg_temp - prev_avg_temp) if (raw_avg_temp is not None and prev_avg_temp is not None) else None
        )
        temp_delta_vs_base = (
            (raw_avg_temp - base_avg_temp) if (raw_avg_temp is not None and base_avg_temp is not None) else None
        )
        delta_vs_base_ref_gj = (
            (ref_heat_gj - base_ref_heat_gj) if (ref_heat_gj is not None and base_ref_heat_gj is not None) else None
        )
        pct_vs_base_ref = (
            (delta_vs_base_ref_gj / base_ref_heat_gj * 100.0)
            if (delta_vs_base_ref_gj is not None and base_ref_heat_gj and base_ref_heat_gj > 0)
            else None
        )
        delta_vs_base_actual_gj = (
            (ref_heat_gj - base_actual_raw) if (ref_heat_gj is not None and base_actual_raw is not None) else None
        )
        pct_vs_base_actual = (
            (delta_vs_base_actual_gj / base_actual_raw * 100.0)
            if (delta_vs_base_actual_gj is not None and base_actual_raw and base_actual_raw > 0)
            else None
        )
        delta_vs_prev_ref_gj = (
            (ref_heat_gj - prev_ref_heat_gj) if (ref_heat_gj is not None and prev_ref_heat_gj is not None) else None
        )
        pct_vs_prev_ref = (
            (delta_vs_prev_ref_gj / prev_ref_heat_gj * 100.0)
            if (delta_vs_prev_ref_gj is not None and prev_ref_heat_gj and prev_ref_heat_gj > 0)
            else None
        )

        advice = _build_daily_forecast_advice(
            in_valid_window=in_window,
            ref_heat_gj=ref_heat_gj,
            delta_vs_prev_ref_gj=delta_vs_prev_ref_gj,
            pct_vs_prev_ref=pct_vs_prev_ref,
            temp_delta_vs_prev=temp_delta_vs_prev,
            pct_vs_base_actual=pct_vs_base_actual,
        )

        forecast_days.append(
            {
                "row_type": "forecast",
                "date": target_iso,
                "month": target_day.month,
                "offset_days": offset,
                "offset_label": f"后第{offset}日 (+{offset}d)",
                "in_valid_window": in_window,
                "area_10k_m2": _round_opt(day_area_10k, 4),
                "avg_temp": _round_opt(raw_avg_temp, 2),
                "min_temp": _round_opt(temp_info.get("min_temp"), 1),
                "max_temp": _round_opt(temp_info.get("max_temp"), 1),
                "hours_count": temp_info.get("hours_count"),
                "hdd20_today": _round_opt(hdd20_today, 2),
                "hdd20_prev3": _round_opt(hdd20_prev3, 2),
                "ref_unit_heat": _round_opt(ref_unit_heat, 2),
                "ref_heat_gj": _round_opt(ref_heat_gj, 2),
                "ref_complaints": _round_opt(ref_complaints, 2),
                "temp_delta_vs_prev": _round_opt(temp_delta_vs_prev, 2),
                "temp_delta_vs_base": _round_opt(temp_delta_vs_base, 2),
                "delta_vs_base_ref_gj": _round_opt(delta_vs_base_ref_gj, 2),
                "pct_vs_base_ref": _round_opt(pct_vs_base_ref, 2),
                "delta_vs_base_actual_gj": _round_opt(delta_vs_base_actual_gj, 2),
                "pct_vs_base_actual": _round_opt(pct_vs_base_actual, 2),
                "delta_vs_prev_ref_gj": _round_opt(delta_vs_prev_ref_gj, 2),
                "pct_vs_prev_ref": _round_opt(pct_vs_prev_ref, 2),
                "advice": advice,
            }
        )
        prev_avg_temp = raw_avg_temp
        prev_ref_heat_gj = ref_heat_gj

    # 汇总未来 3 日趋势提示
    valid_ref_days = [d for d in forecast_days if d["ref_heat_gj"] is not None]
    valid_temp_days = [d for d in forecast_days if d["avg_temp"] is not None]
    total_ref_heat_gj = sum(d["ref_heat_gj"] for d in valid_ref_days) if valid_ref_days else None
    avg_ref_heat_gj = (total_ref_heat_gj / len(valid_ref_days)) if valid_ref_days else None
    avg_forecast_temp = (
        sum(d["avg_temp"] for d in valid_temp_days) / len(valid_temp_days)
        if valid_temp_days
        else None
    )

    trend_type = "steady"
    if len(valid_temp_days) >= 1 and base_avg_temp is not None:
        end_temp = valid_temp_days[-1]["avg_temp"]
        span_temp_delta = end_temp - base_avg_temp
        if span_temp_delta >= 2.0:
            trend_type = "warming"
        elif span_temp_delta <= -2.0:
            trend_type = "cooling"
        elif max(d["avg_temp"] for d in valid_temp_days) - min(d["avg_temp"] for d in valid_temp_days) >= 3.0:
            trend_type = "fluctuating"

    if valid_ref_days:
        min_ref = min(valid_ref_days, key=lambda d: d["ref_heat_gj"])
        max_ref = max(valid_ref_days, key=lambda d: d["ref_heat_gj"])
        avg_pct_vs_base_ref = (
            ((avg_ref_heat_gj - base_ref_heat_gj) / base_ref_heat_gj * 100.0)
            if (avg_ref_heat_gj is not None and base_ref_heat_gj and base_ref_heat_gj > 0)
            else None
        )
        avg_pct_vs_base_actual = (
            ((avg_ref_heat_gj - base_actual_raw) / base_actual_raw * 100.0)
            if (avg_ref_heat_gj is not None and base_actual_raw and base_actual_raw > 0)
            else None
        )
        trend_label = {
            "warming": f"未来 {horizon_days} 日整体回暖",
            "cooling": f"未来 {horizon_days} 日明显降温",
            "fluctuating": f"未来 {horizon_days} 日气温波动明显",
            "steady": f"未来 {horizon_days} 日气温整体平稳",
        }[trend_type]
        headline = f"{trend_label}（均温 {avg_forecast_temp:.2f}℃，参考日均耗热 {avg_ref_heat_gj:,.0f} GJ"
        if avg_pct_vs_base_ref is not None:
            headline += f"，较基准日参考 {avg_pct_vs_base_ref:+.1f}%"
        headline += "）"

        parts = [
            f"后 {horizon_days} 日累计参考需热量约 {total_ref_heat_gj:,.0f} GJ（单日区间 {min_ref['date'][5:]} {min_ref['ref_heat_gj']:,.0f} GJ ~ {max_ref['date'][5:]} {max_ref['ref_heat_gj']:,.0f} GJ）。"
        ]
        if avg_pct_vs_base_actual is not None:
            parts.append(
                f"对比业务日 {base_iso} 实耗（{base_actual_raw:,.0f} GJ），后 {horizon_days} 日参考均值变化 {avg_pct_vs_base_actual:+.1f}%。"
            )
        base_q = base_eval_raw.get("quadrant")
        if base_q and base_q.get("code") == "II" and trend_type == "warming":
            parts.append("基准日处于「Ⅱ 低耗高诉」，次日虽升温但仍受前 3 日低温惯性影响，建议先稳住末端达标后再随气温回升阶梯压减。")
        elif base_q and base_q.get("code") == "II" and trend_type == "cooling":
            parts.append("基准日处于「Ⅱ 低耗高诉」且后续降温，务必提前 1 日蓄热加量防欠热扩诉。")
        elif base_q and base_q.get("code") in {"I", "IV"} and trend_type == "warming":
            parts.append("基准日负荷偏高且即将回暖，建议抓住回暖窗口有序下调供水温度/流量以压降能耗。")
        elif trend_type == "cooling":
            parts.append("建议关注降温前 1 日热惯性滞后效应，提前平滑抬升热负荷。")
        else:
            parts.append("建议结合逐日参考基准节奏平稳微调一网流量与供温。")
        suggestion = " ".join(parts)
    else:
        headline = f"暂无完整未来 {horizon_days} 日有效参考耗热基准"
        suggestion = f"请检查未来 {horizon_days} 日是否处于模型有效期（11月5日—次年3月31日）及 near 气温数据是否已入库。"

    return {
        "base_date": base_iso,
        "horizon_days": horizon_days,
        "temperature_type": FORECAST_TEMP_TYPE,
        "baseline": baseline_row,
        "days": forecast_days,
        "advisory": {
            "trend_type": trend_type,
            "headline": headline,
            "suggestion": suggestion,
            "total_ref_heat_gj": _round_opt(total_ref_heat_gj, 2),
            "avg_ref_heat_gj": _round_opt(avg_ref_heat_gj, 2),
            "avg_temp": _round_opt(avg_forecast_temp, 2),
        },
    }


def build_joint_evaluation(
    db: Session,
    *,
    mode: str = "single",
    biz_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_days: int = 1,
    period_count: int = 7,
) -> Dict[str, Any]:
    """
    执行主城区供热运行联合评价：
    - mode='single': 以 biz_date 为准输出该单日评价，并附带截至该日最近 period_count 个有效日演进轨迹；
    - mode='rolling': 以 end_date（默认 biz_date）为锚点，按 period_days × period_count 切分连续有效周期；
    - mode='range': 针对 start_date ~ end_date 区间自动剔除测算外日期后输出区间累计评价与逐日明细。
    """
    default_biz_iso = load_default_push_date(PROJECT_KEY)
    default_biz_date = parse_date(default_biz_iso)
    normalized_mode = (mode or "single").strip().lower()
    if normalized_mode not in {"single", "rolling", "range"}:
        raise ValueError(f"不支持的评价模式: {mode}")

    anchor_date = end_date or biz_date or default_biz_date
    period_chunks: List[List[date]] = []
    excluded_dates: List[date] = []

    if normalized_mode == "single":
        target_day = biz_date or anchor_date
        anchor_date = target_day
        trace_days = max(1, min(int(period_count), 60))
        chunks, excluded_dates = collect_rolling_periods(target_day, 1, trace_days)
        valid_dates = [chunk[0] for chunk in chunks]
        if not is_valid_eval_date(target_day) and target_day not in excluded_dates:
            excluded_dates.append(target_day)
        excluded_dates = sorted(set(excluded_dates))
        period_chunks = chunks
    elif normalized_mode == "rolling":
        period_chunks, excluded_dates = collect_rolling_periods(anchor_date, period_days, period_count)
        valid_dates = [d for chunk in period_chunks for d in chunk]
    else:
        range_start = start_date or anchor_date
        range_end = end_date or anchor_date
        if range_start > range_end:
            range_start, range_end = range_end, range_start
        anchor_date = range_end
        valid_dates, excluded_dates = split_date_range(range_start, range_end)
        if valid_dates:
            period_chunks = [valid_dates]

    forecast_dates = [default_biz_date + timedelta(days=k) for k in range(0, FORECAST_HORIZON_DAYS + 1)]
    target_period = get_season_period(anchor_date)
    periods_needed = (
        {target_period}
        | {get_season_period(d) for d in valid_dates}
        | {get_season_period(d) for d in forecast_dates}
    )
    area_map = _fetch_gongre_fee_area_map(db, periods_needed)
    current_area_10k_m2 = area_map.get(target_period)
    current_area_m2 = (current_area_10k_m2 * 10000.0) if current_area_10k_m2 else None

    if valid_dates:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
        temp_start = min_date - timedelta(days=3)
        avg_temp_map = DailyDashboardEngine(db).get_temperature_daily_avg_map(temp_start, max_date)
        heat_map, complaint_map = _fetch_daily_metric_series(db, min_date, max_date)
    else:
        avg_temp_map = {}
        heat_map, complaint_map = {}, {}

    # 固定抓取系统最新业务日之后 N 日（含前 3 日热惯性窗口）的 type='near' 逐小时气温
    forecast_temp_start = default_biz_date - timedelta(days=3)
    forecast_temp_end = default_biz_date + timedelta(days=FORECAST_HORIZON_DAYS)
    near_temp_map = _fetch_near_temperature_daily_map(db, forecast_temp_start, forecast_temp_end)
    forecast_fallback_temps = dict(avg_temp_map)
    missing_base_window = any(
        (default_biz_date - timedelta(days=k)).isoformat() not in forecast_fallback_temps
        and (default_biz_date - timedelta(days=k)).isoformat() not in near_temp_map
        for k in range(0, 4)
    )
    if missing_base_window:
        extra_temps = DailyDashboardEngine(db).get_temperature_daily_avg_map(forecast_temp_start, default_biz_date)
        forecast_fallback_temps.update(extra_temps)

    if default_biz_date in heat_map or default_biz_date in complaint_map:
        base_actual_heat = heat_map.get(default_biz_date)
        base_actual_complaints = complaint_map.get(default_biz_date)
    else:
        base_heat_map, base_complaint_map = _fetch_daily_metric_series(db, default_biz_date, default_biz_date)
        base_actual_heat = base_heat_map.get(default_biz_date)
        base_actual_complaints = base_complaint_map.get(default_biz_date)

    forecast_payload = build_forecast_payload(
        base_date=default_biz_date,
        near_temp_map=near_temp_map,
        fallback_avg_temp_map=forecast_fallback_temps,
        area_map=area_map,
        base_actual_heat_gj=base_actual_heat,
        base_actual_complaints=base_actual_complaints,
        horizon_days=FORECAST_HORIZON_DAYS,
    )

    rows_by_date: Dict[date, Dict[str, Any]] = {}
    for d in valid_dates:
        day_area = area_map.get(get_season_period(d))
        rows_by_date[d] = build_daily_eval_row(d, day_area, avg_temp_map, heat_map, complaint_map)

    all_eval_rows = [rows_by_date[d] for d in valid_dates]

    # 生成周期摘要列表（单日模式附带近期轨迹、滚动模式每周期一段、区间模式整段）
    period_summaries: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(period_chunks, start=1):
        chunk_rows = [rows_by_date[d] for d in chunk]
        if normalized_mode == "rolling" and len(chunk) > 1:
            lbl = f"第{idx}期（{chunk[0].strftime('%m/%d')}—{chunk[-1].strftime('%m/%d')}）"
        elif len(chunk) == 1:
            lbl = chunk[0].isoformat()
        else:
            lbl = f"{chunk[0].isoformat()} ~ {chunk[-1].isoformat()}"
        item = aggregate_eval_rows(chunk_rows, label=lbl)
        item["index"] = idx
        period_summaries.append(item)

    if normalized_mode == "single":
        if is_valid_eval_date(anchor_date) and anchor_date in rows_by_date:
            primary_summary = aggregate_eval_rows([rows_by_date[anchor_date]], label=anchor_date.isoformat())
        else:
            primary_summary = aggregate_eval_rows([], label=anchor_date.isoformat())
        trajectory_summary = aggregate_eval_rows(all_eval_rows, label="轨迹区间合计") if all_eval_rows else None
    else:
        primary_summary = aggregate_eval_rows(all_eval_rows)
        trajectory_summary = None

    return {
        "ok": True,
        "mode": normalized_mode,
        "default_biz_date": default_biz_date.isoformat(),
        "anchor_date": anchor_date.isoformat(),
        "anchor_in_valid_window": is_valid_eval_date(anchor_date),
        "season_period": target_period,
        "area_source": {
            "company": AREA_COMPANY,
            "item": AREA_ITEM,
            "period": target_period,
            "area_m2": _round_opt(current_area_m2, 2),
            "area_10k_m2": _round_opt(current_area_10k_m2, 4),
            "area_missing": current_area_10k_m2 is None or current_area_10k_m2 <= 0,
        },
        "excluded_dates": [d.isoformat() for d in excluded_dates],
        "excluded_count": len(excluded_dates),
        "valid_day_count": len(valid_dates),
        "summary": primary_summary,
        "trajectory_summary": trajectory_summary,
        "periods": period_summaries,
        "daily_rows": [_strip_raw(r) for r in all_eval_rows],
        "forecast": forecast_payload,
        "model_spec": {
            "valid_window_rule": "每年 11月5日 — 次年3月31日（自动剔除 11.1–11.4 与 4.1–4.5）",
            "equation": "参考日单耗 = 3.3730 + 0.5137 × 当日HDD20 + 0.3521 × 前3日平均HDD20 + 月份修正量",
            "intercept": MODEL_INTERCEPT,
            "coef_hdd20_today": MODEL_COEF_HDD20_TODAY,
            "coef_hdd20_prev3": MODEL_COEF_HDD20_PREV3,
            "month_heat_adjustments": [
                {"month": m, "label": f"{m}月", "adjustment": adj}
                for m, adj in MONTH_HEAT_ADJUSTMENTS.items()
            ],
            "month_complaint_rates": [
                {"month": m, "label": f"{m}月", "rate_per_10k_m2_day": rate}
                for m, rate in MONTH_COMPLAINT_RATES.items()
            ],
            "empirical_bands": EMPIRICAL_BANDS,
            "quadrants": list(QUADRANT_DEFINITIONS.values()),
            "data_scope": {
                "company_scope": "ZhuChengQu（实际耗热与省市平台投诉均由 GongRe 统一归口）",
                "heat_item": HEAT_ITEM,
                "complaint_item": COMPLAINT_ITEM,
                "area_source": f"constant_data.{AREA_COMPANY}.{AREA_ITEM}",
            },
        },
    }
