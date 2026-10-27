# -*- coding: utf-8 -*-
"""
动态计划月度日分解核心计算服务 (Dynamic Decomposition Service)。

基于 HDD20 供热度日与优化后建议 k 模型，将月度计划指标科学、动态地分解到每日。
算法规则严格对齐：
1. HDD20 = max(20 - 日平均气温, 0)
2. 全月平均 HDD20 = 1/N * sum(HDD20_d)
3. 具备 k 值的指标：日权重 W_d = max(0, 1 + k * (当日HDD20 - 当月平均HDD20))
4. 没有纳入 k 值范畴的指标：k 视为 0，日权重均为 1.0，各日均摊呈现水平直线 (每天无差别)
5. 初始日计划 P_daily(d) = 月计划 * W_d / sum(W)，尾差按分厘调整保持全月分毫不差
6. 聚合口径（集团全口径、主城区）在各子口径分解后按既定算法进行聚合显示：
   - 总量指标（供热量、发电量、耗煤等）：逐日相加聚合 (sum of sub_companies)
   - 单耗指标（热单耗、电单耗）：按聚合口径专属建议 k 与月计划分解
7. 全月气温门禁校验：需数据库（calc_temperature_data）全月每日气温齐全方可分解。
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text

# 汇总口径下属实体映射
ROLLUP_HIERARCHY: Dict[str, List[str]] = {
    "Group": ["BeiHai", "XiangHai", "GongRe", "JinZhou", "BeiFang", "JinPu", "ZhuangHe", "YanJiuYuan"],
    "ZhuChengQu": ["BeiHai", "XiangHai", "GongRe"],
}

# 单位中文名映射
COMPANY_CN_MAP = {
    "Group": "集团全口径",
    "ZhuChengQu": "主城区",
    "BeiHai": "北海热电厂",
    "XiangHai": "香海热电厂",
    "GongRe": "供热公司",
    "JinZhou": "金州热电",
    "BeiFang": "北方热电",
    "JinPu": "金普热电",
    "ZhuangHe": "庄河环海",
    "YanJiuYuan": "研究院",
}


def check_temperature_completeness(
    year_month: str,
    session,
) -> Tuple[bool, List[Dict[str, Any]], List[str], int]:
    """
    核对指定月份（形如 '2026-11'）在 calc_temperature_data 中是否存在全月每日气温。
    
    返回:
      (has_full_month, temp_rows, missing_dates, total_days_in_month)
    """
    parts = year_month.strip().split("-")
    if len(parts) != 2:
        return False, [], [], 0

    year, month = int(parts[0]), int(parts[1])
    total_days = calendar.monthrange(year, month)[1]

    # 查询 calc_temperature_data 该月所有日期记录
    stmt = text("""
        SELECT date, aver_temp, max_temp, min_temp
        FROM calc_temperature_data
        WHERE to_char(date, 'YYYY-MM') = :ym
        ORDER BY date ASC
    """)
    rows = session.execute(stmt, {"ym": year_month}).fetchall()

    row_map: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        d_str = r[0].strftime("%Y-%m-%d") if hasattr(r[0], "strftime") else str(r[0])
        avg_t = float(r[1]) if r[1] is not None else None
        max_t = float(r[2]) if r[2] is not None else None
        min_t = float(r[3]) if r[3] is not None else None
        row_map[d_str] = {
            "date": d_str,
            "aver_temp": avg_t,
            "max_temp": max_t,
            "min_temp": min_t,
        }

    # 检查从 1 到 total_days 是否每日都存在有效日均温
    missing_dates = []
    temp_rows = []
    for day_num in range(1, total_days + 1):
        d_str = f"{year:04d}-{month:02d}-{day_num:02d}"
        if d_str in row_map and row_map[d_str]["aver_temp"] is not None:
            temp_rows.append(row_map[d_str])
        else:
            missing_dates.append(d_str)

    has_full_month = (len(missing_dates) == 0 and len(temp_rows) == total_days)
    return has_full_month, temp_rows, missing_dates, total_days


def decompose_single_series(
    month_plan: float,
    k_value: float,
    hdd20_series: List[float],
    avg_hdd20: float,
    precision: int = 2,
) -> Tuple[List[float], List[float]]:
    """
    对单个指标进行日分解，并进行尾差平差保证日计划合计严格等于月计划。
    
    返回: (daily_plans, daily_weights)
    """
    n_days = len(hdd20_series)
    if n_days == 0:
        return [], []

    if month_plan <= 0:
        return [0.0] * n_days, [1.0] * n_days

    # 若 k 值为 0 或没有 k 模型，按天数严格均摊，形成水平直线
    if abs(k_value) < 1e-9:
        weights = [1.0] * n_days
        raw_val = month_plan / n_days
        rounded = [round(raw_val, precision) for _ in range(n_days)]
        diff = round(month_plan - sum(rounded), precision)
        rounded[-1] = round(rounded[-1] + diff, precision)
        return rounded, weights

    # 根据日 HDD20 计算日权重：W_d = max(0, 1 + k * (HDD20_d - avg_HDD20))
    weights = [max(0.0, 1.0 + k_value * (hdd - avg_hdd20)) for hdd in hdd20_series]
    sum_w = sum(weights)

    # 异常保护：若权重全为 0，退化为均摊
    if sum_w <= 1e-9:
        raw_val = month_plan / n_days
        rounded = [round(raw_val, precision) for _ in range(n_days)]
        diff = round(month_plan - sum(rounded), precision)
        rounded[-1] = round(rounded[-1] + diff, precision)
        return rounded, [1.0] * n_days

    # 按权重初始分解
    raw_plans = [month_plan * (w / sum_w) for w in weights]
    rounded = [round(v, precision) for v in raw_plans]

    # 尾差平差：调整到最后一日，保证 sum(rounded) == month_plan
    diff = round(month_plan - sum(rounded), precision)
    rounded[-1] = round(rounded[-1] + diff, precision)

    # 格式化权重保留 4 位小数
    formatted_weights = [round(w, 4) for w in weights]
    return rounded, formatted_weights


def get_dynamic_daily_decomposition(
    company: str,
    year_month: str,
    session,
) -> Dict[str, Any]:
    """
    获取指定单位在指定计划月份的动态日分解计划与气温分布。
    
    支持实体子口径直接分解与聚合口径（Group、ZhuChengQu）多级向上聚合。
    未纳入 k 值的指标按均摊计算（水平直线）。
    """
    # 1. 气温门禁校验
    has_full_month, temp_rows, missing_dates, total_days = check_temperature_completeness(year_month, session)
    if not has_full_month:
        return {
            "ok": True,
            "has_full_month": False,
            "company": company,
            "company_cn": COMPANY_CN_MAP.get(company, company),
            "year_month": year_month,
            "total_days": total_days,
            "available_days": len(temp_rows),
            "missing_dates": missing_dates,
            "message": f"{year_month} 气温数据不完整（已录入 {len(temp_rows)}/{total_days} 天），缺少全月气温，无法进行动态分解。请先点击【导入35天预报】补全气温。",
        }

    # 2. 计算日均温序列与 HDD20 序列
    dates = [r["date"] for r in temp_rows]
    day_labels = [d.split("-", 1)[1] for d in dates]  # MM-DD
    temps = [r["aver_temp"] for r in temp_rows]
    hdd20_series = [max(20.0 - t, 0.0) for t in temps]
    avg_temp = round(sum(temps) / len(temps), 2)
    avg_hdd20 = round(sum(hdd20_series) / len(hdd20_series), 4)

    # 解析月份整数，如 '2026-11' -> 11
    month_int = int(year_month.split("-")[1])
    is_rollup = company in ROLLUP_HIERARCHY
    sub_companies = ROLLUP_HIERARCHY.get(company, [])

    # 3. 如果是聚合口径：分别对各子口径全量指标分解，再向上汇总结算
    if is_rollup:
        sub_decompositions: Dict[str, Dict[str, Any]] = {}
        for sub_c in sub_companies:
            sub_res = _decompose_entity_company(sub_c, month_int, year_month, hdd20_series, avg_hdd20, session)
            sub_decompositions[sub_c] = sub_res

        # 查询该聚合口径自身的建议 k 值表
        k_rows = session.execute(
            text("""
                SELECT item, item_cn, unit, k_value
                FROM dynamic_month_plan_k
                WHERE company = :comp AND month = :m
                ORDER BY id
            """),
            {"comp": company, "m": month_int},
        ).fetchall()
        k_map = {kr[0]: (float(kr[3]) if kr[3] is not None else 0.0, kr[1], kr[2]) for kr in k_rows}

        # 查询聚合口径直报的所有指标
        direct_rows = session.execute(
            text("""
                SELECT item, item_cn, unit, value
                FROM paln_and_real_month_data
                WHERE company = :comp AND period LIKE :ym_like AND type = 'plan'
                ORDER BY id
            """),
            {"comp": company, "ym_like": f"{year_month}%"},
        ).fetchall()
        direct_map = {dr[0]: (float(dr[3]) if dr[3] is not None else 0.0, dr[1], dr[2]) for dr in direct_rows}

        # 收集所有出现过的指标键
        all_item_keys = []
        for dr in direct_rows:
            if dr[0] not in all_item_keys:
                all_item_keys.append(dr[0])
        for kr in k_rows:
            if kr[0] not in all_item_keys:
                all_item_keys.append(kr[0])
        for sub_c in sub_companies:
            for it in sub_decompositions[sub_c]["metrics_map"].keys():
                if it not in all_item_keys:
                    all_item_keys.append(it)

        rollup_metrics: List[Dict[str, Any]] = []

        for item_key in all_item_keys:
            # 获取中文名和单位
            it_cn = ""
            unit = ""
            if item_key in direct_map:
                it_cn = direct_map[item_key][1]
                unit = direct_map[item_key][2] or ""
            elif item_key in k_map:
                it_cn = k_map[item_key][1]
                unit = k_map[item_key][2] or ""
            else:
                for sub_c in sub_companies:
                    sub_m = sub_decompositions[sub_c]["metrics_map"].get(item_key)
                    if sub_m:
                        it_cn = sub_m["item_cn"]
                        unit = sub_m["unit"]
                        break

            k_info = k_map.get(item_key)
            k_val = k_info[0] if k_info else 0.0
            has_k = (k_info is not None and abs(k_val) > 1e-9)

            is_rate_metric = "单耗" in it_cn
            precision = 4 if is_rate_metric else 2

            if not is_rate_metric:
                # 总量指标：聚合口径当日计划 = 各子口径当日分解计划之和
                daily_sum = [0.0] * len(dates)
                total_month_plan = 0.0
                for sub_c in sub_companies:
                    sub_m = sub_decompositions[sub_c].get("metrics_map", {}).get(item_key)
                    if sub_m:
                        total_month_plan += sub_m["month_plan"]
                        for i, v in enumerate(sub_m["daily_plans"]):
                            daily_sum[i] += v

                # 若子口径无此指标但直报有值
                if total_month_plan <= 0 and item_key in direct_map:
                    total_month_plan = direct_map[item_key][0]
                    daily_sum, _ = decompose_single_series(
                        total_month_plan, k_val, hdd20_series, avg_hdd20, precision
                    )

                daily_plans = [round(v, precision) for v in daily_sum]
                total_month_plan = round(total_month_plan, precision)
                diff = round(total_month_plan - sum(daily_plans), precision)
                if abs(diff) > 0 and len(daily_plans) > 0:
                    daily_plans[-1] = round(daily_plans[-1] + diff, precision)

                daily_weights = []
                for v in daily_plans:
                    w = round((v / total_month_plan * len(dates)), 4) if total_month_plan > 0 else 1.0
                    daily_weights.append(w)

                rollup_metrics.append({
                    "item": item_key,
                    "item_cn": it_cn,
                    "unit": unit,
                    "k_value": k_val,
                    "has_k": has_k,
                    "month_plan": total_month_plan,
                    "daily_plans": daily_plans,
                    "daily_weights": daily_weights,
                    "is_ratio": False,
                    "is_rate": False,
                    "is_rollup": True,
                })
            else:
                # 单耗指标：使用聚合口径专属月计划与建议 k 分解（无 k 则水平直线）
                month_plan = direct_map.get(item_key, (0.0,))[0]
                daily_plans, daily_weights = decompose_single_series(
                    month_plan=month_plan,
                    k_value=k_val,
                    hdd20_series=hdd20_series,
                    avg_hdd20=avg_hdd20,
                    precision=precision,
                )

                rollup_metrics.append({
                    "item": item_key,
                    "item_cn": it_cn,
                    "unit": unit,
                    "k_value": k_val,
                    "has_k": has_k,
                    "month_plan": month_plan,
                    "daily_plans": daily_plans,
                    "daily_weights": daily_weights,
                    "is_ratio": True,
                    "is_rate": True,
                    "is_rollup": True,
                })

        return {
            "ok": True,
            "has_full_month": True,
            "company": company,
            "company_cn": COMPANY_CN_MAP.get(company, company),
            "year_month": year_month,
            "is_rollup": True,
            "dates": dates,
            "day_labels": day_labels,
            "temperatures": [round(t, 2) for t in temps],
            "hdd20_series": [round(h, 2) for h in hdd20_series],
            "avg_temperature": avg_temp,
            "avg_hdd20": avg_hdd20,
            "metrics": rollup_metrics,
            "sub_companies": sub_companies,
        }

    else:
        # 4. 普通实体子口径直接分解
        entity_res = _decompose_entity_company(company, month_int, year_month, hdd20_series, avg_hdd20, session)
        return {
            "ok": True,
            "has_full_month": True,
            "company": company,
            "company_cn": COMPANY_CN_MAP.get(company, company),
            "year_month": year_month,
            "is_rollup": False,
            "dates": dates,
            "day_labels": day_labels,
            "temperatures": [round(t, 2) for t in temps],
            "hdd20_series": [round(h, 2) for h in hdd20_series],
            "avg_temperature": avg_temp,
            "avg_hdd20": avg_hdd20,
            "metrics": entity_res["metrics_list"],
        }


def _decompose_entity_company(
    company: str,
    month_int: int,
    year_month: str,
    hdd20_series: List[float],
    avg_hdd20: float,
    session,
) -> Dict[str, Any]:
    """计算单个实体单位全量指标的日分解明细（有k值动态波动，无k值水平均摊）。"""
    # 1. 查询该单位配置的 k 值字典
    k_rows = session.execute(
        text("""
            SELECT item, item_cn, unit, k_value
            FROM dynamic_month_plan_k
            WHERE company = :comp AND month = :m
            ORDER BY id
        """),
        {"comp": company, "m": month_int},
    ).fetchall()
    k_map = {kr[0]: (float(kr[3]) if kr[3] is not None else 0.0, kr[1], kr[2]) for kr in k_rows}

    # 2. 查询该单位在当月的所有月计划指标
    p_rows = session.execute(
        text("""
            SELECT item, item_cn, unit, value
            FROM paln_and_real_month_data
            WHERE company = :comp AND period LIKE :ym_like AND type = 'plan'
            ORDER BY id
        """),
        {"comp": company, "ym_like": f"{year_month}%"},
    ).fetchall()

    metrics_list = []
    metrics_map = {}
    seen_items = set()

    # 先处理在 paln_and_real_month_data 出现的指标
    for pr in p_rows:
        item_key = pr[0]
        item_cn = pr[1]
        unit = pr[2] or ""
        month_plan = float(pr[3]) if pr[3] is not None else 0.0
        seen_items.add(item_key)

        k_info = k_map.get(item_key)
        k_val = k_info[0] if k_info else 0.0
        has_k = (k_info is not None and abs(k_val) > 1e-9)

        is_rate_metric = "单耗" in item_cn
        precision = 4 if is_rate_metric else 2

        daily_plans, daily_weights = decompose_single_series(
            month_plan=month_plan,
            k_value=k_val,
            hdd20_series=hdd20_series,
            avg_hdd20=avg_hdd20,
            precision=precision,
        )

        m_data = {
            "item": item_key,
            "item_cn": item_cn,
            "unit": unit,
            "k_value": k_val,
            "has_k": has_k,
            "month_plan": month_plan,
            "daily_plans": daily_plans,
            "daily_weights": daily_weights,
            "is_ratio": is_rate_metric,
            "is_rate": is_rate_metric,
            "is_rollup": False,
        }
        metrics_list.append(m_data)
        metrics_map[item_key] = m_data

    # 若 k_rows 还有尚未包含的项，也补全
    for kr in k_rows:
        item_key = kr[0]
        if item_key not in seen_items:
            k_val = float(kr[3]) if kr[3] is not None else 0.0
            has_k = abs(k_val) > 1e-9
            is_rate_metric = "单耗" in kr[1]
            precision = 4 if is_rate_metric else 2
            daily_plans, daily_weights = decompose_single_series(
                month_plan=0.0,
                k_value=k_val,
                hdd20_series=hdd20_series,
                avg_hdd20=avg_hdd20,
                precision=precision,
            )
            m_data = {
                "item": item_key,
                "item_cn": kr[1],
                "unit": kr[2] or "",
                "k_value": k_val,
                "has_k": has_k,
                "month_plan": 0.0,
                "daily_plans": daily_plans,
                "daily_weights": daily_weights,
                "is_ratio": is_rate_metric,
                "is_rate": is_rate_metric,
                "is_rollup": False,
            }
            metrics_list.append(m_data)
            metrics_map[item_key] = m_data

    return {"metrics_list": metrics_list, "metrics_map": metrics_map}
