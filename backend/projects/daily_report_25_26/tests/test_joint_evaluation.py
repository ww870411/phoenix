# -*- coding: utf-8 -*-
"""主城区供热联合评价模型单元测试。"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.projects.daily_report_25_26.api.joint_evaluation import router as joint_eval_router  # noqa: E402
from backend.projects.daily_report_25_26.services.joint_evaluation import (  # noqa: E402
    _normalize_area_to_10k_m2,
    aggregate_eval_rows,
    build_daily_eval_row,
    collect_rolling_periods,
    is_valid_eval_date,
    split_date_range,
)
from backend.services.auth_manager import get_current_session  # noqa: E402


def test_eval_date_window_filtering() -> None:
    """确认 11.1-11.4 与 4.1-4.5 被剔除，仅保留 11.5-3.31。"""
    for day in (date(2026, 11, 1), date(2026, 11, 4), date(2027, 4, 1), date(2027, 4, 5), date(2026, 10, 31)):
        assert not is_valid_eval_date(day)

    for day in (date(2026, 11, 5), date(2026, 12, 31), date(2027, 1, 15), date(2027, 2, 28), date(2027, 3, 31)):
        assert is_valid_eval_date(day)

    valid, excluded = split_date_range(date(2026, 11, 1), date(2026, 11, 7))
    assert valid == [date(2026, 11, 5), date(2026, 11, 6), date(2026, 11, 7)]
    assert excluded == [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4)]

    valid_end, excluded_end = split_date_range(date(2027, 3, 30), date(2027, 4, 5))
    assert valid_end == [date(2027, 3, 30), date(2027, 3, 31)]
    assert len(excluded_end) == 5


def test_rolling_periods_skips_excluded_dates() -> None:
    """确认滚动周期在跨过 4.1-4.5 时自动跳过测算外日期。"""
    chunks, skipped = collect_rolling_periods(date(2027, 4, 3), period_days=3, period_count=2)
    assert skipped == [date(2027, 4, 1), date(2027, 4, 2), date(2027, 4, 3)]
    assert chunks == [
        [date(2027, 3, 26), date(2027, 3, 27), date(2027, 3, 28)],
        [date(2027, 3, 29), date(2027, 3, 30), date(2027, 3, 31)],
    ]


def test_area_unit_normalization() -> None:
    """确认 constant_data 以万㎡录入时直接保留万㎡，若以㎡录入则自动换算为万㎡。"""
    assert abs(_normalize_area_to_10k_m2(2300.410422, "万㎡") - 2300.410422) < 1e-6
    assert abs(_normalize_area_to_10k_m2(2300.410422, None) - 2300.410422) < 1e-6
    assert abs(_normalize_area_to_10k_m2(23004104.22, "㎡") - 2300.410422) < 1e-6
    assert abs(_normalize_area_to_10k_m2(23004104.22, None) - 2300.410422) < 1e-6


def test_report_nov5_to_nov22_reconciliation() -> None:
    """用汇报附表（四）11月5日—22日样本数据校验参考单耗、偏差率、投诉指数与象限。"""
    area_10k = 2300.410422
    # 11月2日-4日前置气温及 11月5日-22日气温、实际单耗、实际投诉
    temps = {
        "2026-11-02": 10.52,
        "2026-11-03": 14.03,
        "2026-11-04": 16.05,
        "2026-11-05": 12.90,
        "2026-11-06": 6.09,
        "2026-11-07": 5.13,
        "2026-11-08": 1.58,
        "2026-11-09": 3.09,
        "2026-11-10": 9.90,
        "2026-11-11": 11.52,
        "2026-11-12": 12.21,
        "2026-11-13": 12.03,
        "2026-11-14": 10.83,
        "2026-11-15": 7.66,
        "2026-11-16": 5.85,
        "2026-11-17": 4.57,
        "2026-11-18": 4.42,
        "2026-11-19": 3.21,
        "2026-11-20": 2.56,
        "2026-11-21": -0.05,
        "2026-11-22": 4.34,
    }
    actual_unit_heats = [
        10.91, 12.79, 15.04, 18.68, 15.49, 13.20,
        12.54, 11.98, 10.75, 11.43, 13.73, 13.25,
        14.96, 18.94, 18.92, 18.91, 18.13, 16.05,
    ]
    complaints = [
        263, 268, 274, 242, 174, 149,
        89, 61, 50, 46, 51, 76,
        130, 87, 89, 60, 55, 101,
    ]

    heat_map = {}
    complaint_map = {}
    eval_rows = []
    start = date(2026, 11, 5)
    for idx in range(18):
        day = start + timedelta(days=idx)
        heat_map[day] = actual_unit_heats[idx] * area_10k
        complaint_map[day] = float(complaints[idx])
        eval_rows.append(build_daily_eval_row(day, area_10k, temps, heat_map, complaint_map))

    # 校验首日 11-05：参考单耗 9.29，偏差率 +17.37%左右，投诉指数 316.8，Ⅰ象限
    day1 = eval_rows[0]
    assert abs(day1["ref_unit_heat"] - 9.30) <= 0.02
    assert day1["quadrant"]["code"] == "I"
    assert abs(day1["complaint_index"] - 316.8) <= 0.2

    # 校验 18 天累计汇总：参考总耗热约 602,678 GJ，偏差率约 +1.41%，实际投诉 2265，投诉指数 151.6
    summary = aggregate_eval_rows(eval_rows)
    assert summary["valid_days"] == 18
    assert summary["actual_complaints"] == 2265
    assert abs(summary["ref_heat_gj"] - 602678) <= 300
    assert abs(summary["heat_deviation_pct"] - 1.41) <= 0.15
    assert abs(summary["complaint_index"] - 151.6) <= 0.2
    assert summary["quadrant"]["code"] == "I"


def test_joint_evaluation_api_requires_global_admin() -> None:
    """确认 /joint-evaluation 接口对非 Global_admin 返回 403，对 Global_admin 正常放行。"""
    app = FastAPI()
    app.include_router(joint_eval_router)
    client = TestClient(app)

    app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group="Group_admin")
    denied = client.get("/joint-evaluation")
    assert denied.status_code == 403

    app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group="Global_admin")
    with patch("backend.projects.daily_report_25_26.api.joint_evaluation.SessionLocal"), patch(
        "backend.projects.daily_report_25_26.api.joint_evaluation.build_joint_evaluation",
        return_value={"ok": True, "mode": "single"},
    ):
        allowed = client.get("/joint-evaluation")
    assert allowed.status_code == 200
    assert allowed.json()["ok"] is True

