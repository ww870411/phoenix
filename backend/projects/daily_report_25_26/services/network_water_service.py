# -*- coding: utf-8 -*-
"""各单位热网耗水量（水力哑铃图）统计服务

业务口径规范：
1. 仅统计“热网耗水量/补水量”，不包含电厂自用耗水。
2. 六大统计主体：
   - 主城区：供热公司总口径（“其中：电厂一次网补水量” + “其中：换热站补水量”）
   - 金州热电：“其中：热网补水量”
   - 北方热电：“其中：热网补水量”
   - 金普公司：“其中：热网补水量”
   - 庄河环海：“其中：热网补水量”
   - 研究院：“其中：热网补水量”
3. 三大时间维度：
   - 当日（业务日）：biz_date vs peer_date
   - 本月累计：biz_month_start ~ biz_month_end vs peer_month_start ~ peer_month_end
   - 供暖期累计：biz_ytd_start ~ biz_ytd_end vs peer_ytd_start ~ peer_ytd_end
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from backend.db.database_daily_report_25_26 import DailyBasicData, SessionLocal
from backend.services.dashboard_expression import load_default_push_date
from backend.services.heating_metrics.season_utils import get_season_windows, parse_date

# 六大业务主体配置
WATER_ENTITIES = [
    {
        "key": "ZhuChengQu",
        "name": "主城区",
        "company": "GongRe",
        "sheet": "GongRe_Sheet",
        "items": ["consumption_network_fill_water", "consumption_station_fill_water"],
        "desc": "一次网补水+换热站补水",
    },
    {
        "key": "JinZhou",
        "name": "金州热电",
        "company": "JinZhou",
        "sheet": "JinZhou_Sheet",
        "items": ["consumption_network_water"],
        "desc": "热网补水量",
    },
    {
        "key": "BeiFang",
        "name": "北方热电",
        "company": "BeiFang",
        "sheet": "BeiFang_Sheet",
        "items": ["consumption_network_water"],
        "desc": "热网补水量",
    },
    {
        "key": "JinPu",
        "name": "金普公司",
        "company": "JinPu",
        "sheet": "JinPu_Sheet",
        "items": ["consumption_network_water"],
        "desc": "热网补水量",
    },
    {
        "key": "ZhuangHe",
        "name": "庄河环海",
        "company": "ZhuangHe",
        "sheet": "ZhuangHe_Sheet",
        "items": ["consumption_network_water"],
        "desc": "热网补水量",
    },
    {
        "key": "YanJiuYuan",
        "name": "研究院",
        "company": "YanJiuYuan",
        "sheet": "YanJiuYuan_Sheet",
        "items": ["consumption_network_water"],
        "desc": "热网补水量",
    },
]


def get_network_water_dumbbell(
    project_key: str = "daily_report_25_26",
    show_date: Optional[str] = None,
) -> Dict[str, Any]:
    """计算各单位热网耗水量哑铃图数据集（包含当日、本月累计、供暖期累计三大维度及全网汇总）。"""
    target_date_str = (show_date or "").strip()
    if not target_date_str:
        target_date_str = load_default_push_date(project_key) or datetime.date.today().isoformat()

    biz_date = parse_date(target_date_str)
    windows = get_season_windows(biz_date)

    session = SessionLocal()
    try:
        all_sheets = [e["sheet"] for e in WATER_ENTITIES]
        all_items = list({itm for e in WATER_ENTITIES for itm in e["items"]})

        def _query_period_sum(start_d: datetime.date, end_d: datetime.date) -> Dict[str, float]:
            rows = (
                session.query(
                    DailyBasicData.company,
                    DailyBasicData.sheet_name,
                    DailyBasicData.item,
                    func.sum(DailyBasicData.value),
                )
                .filter(
                    DailyBasicData.date >= start_d,
                    DailyBasicData.date <= end_d,
                    DailyBasicData.sheet_name.in_(all_sheets),
                    DailyBasicData.item.in_(all_items),
                )
                .group_by(
                    DailyBasicData.company,
                    DailyBasicData.sheet_name,
                    DailyBasicData.item,
                )
                .all()
            )

            mapping: Dict[tuple, float] = {}
            for comp, sheet, itm, val in rows:
                if val is not None:
                    mapping[(comp, sheet, itm)] = float(val) if isinstance(val, (int, float, Decimal)) else 0.0
                else:
                    mapping[(comp, sheet, itm)] = 0.0

            result: Dict[str, float] = {}
            for ent in WATER_ENTITIES:
                total = sum(mapping.get((ent["company"], ent["sheet"], itm), 0.0) for itm in ent["items"])
                result[ent["key"]] = round(total, 1)
            return result

        # 1. 当日（业务日）
        curr_day = _query_period_sum(windows["biz_date"], windows["biz_date"])
        peer_day = _query_period_sum(windows["peer_date"], windows["peer_date"])

        # 2. 本月累计
        curr_month = _query_period_sum(windows["biz_month_start"], windows["biz_month_end"])
        peer_month = _query_period_sum(windows["peer_month_start"], windows["peer_month_end"])

        # 3. 供暖期累计
        curr_season = _query_period_sum(windows["biz_ytd_start"], windows["biz_ytd_end"])
        peer_season = _query_period_sum(windows["peer_ytd_start"], windows["peer_ytd_end"])

        def _format_dimension(
            curr_map: Dict[str, float],
            peer_map: Dict[str, float],
            biz_range_str: str,
            peer_range_str: str,
            label: str,
        ) -> Dict[str, Any]:
            items: List[Dict[str, Any]] = []
            for ent in WATER_ENTITIES:
                c = curr_map.get(ent["key"], 0.0)
                p = peer_map.get(ent["key"], 0.0)
                diff = round(c - p, 1)
                diff_rate = round((diff / p * 100), 1) if p > 0 else (0.0 if diff == 0 else None)
                items.append({
                    "key": ent["key"],
                    "name": ent["name"],
                    "desc": ent["desc"],
                    "current": c,
                    "peer": p,
                    "diff": diff,
                    "diff_rate": diff_rate,
                })

            tot_c = round(sum(i["current"] for i in items), 1)
            tot_p = round(sum(i["peer"] for i in items), 1)
            tot_diff = round(tot_c - tot_p, 1)
            tot_rate = round((tot_diff / tot_p * 100), 1) if tot_p > 0 else 0.0

            return {
                "label": label,
                "biz_range": biz_range_str,
                "peer_range": peer_range_str,
                "total": {
                    "current": tot_c,
                    "peer": tot_p,
                    "diff": tot_diff,
                    "diff_rate": tot_rate,
                },
                "items": items,
            }

        return {
            "ok": True,
            "project_key": project_key,
            "biz_date": str(windows["biz_date"]),
            "peer_date": str(windows["peer_date"]),
            "biz_period": windows.get("biz_period", ""),
            "peer_period": windows.get("peer_period", ""),
            "dimensions": {
                "day": _format_dimension(
                    curr_day,
                    peer_day,
                    str(windows["biz_date"]),
                    str(windows["peer_date"]),
                    "当日（业务日）",
                ),
                "month": _format_dimension(
                    curr_month,
                    peer_month,
                    f"{windows['biz_month_start']} 至 {windows['biz_month_end']}",
                    f"{windows['peer_month_start']} 至 {windows['peer_month_end']}",
                    "本月累计",
                ),
                "season": _format_dimension(
                    curr_season,
                    peer_season,
                    f"{windows['biz_ytd_start']} 至 {windows['biz_ytd_end']}",
                    f"{windows['peer_ytd_start']} 至 {windows['peer_ytd_end']}",
                    "供暖期累计",
                ),
            },
        }
    finally:
        session.close()
