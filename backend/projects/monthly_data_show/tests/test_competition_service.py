# -*- coding: utf-8 -*-
"""供暖期指标竞赛取数与持久化服务回归测试。"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from backend.projects.monthly_data_show.services import competition_service


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeSession:
    """只读模拟数据库会话，验证取数口径而不改动生产库。"""

    def __init__(self, responses):
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        sql_text = str(sql)
        if "FROM monthly_data_show" in sql_text:
            return _FakeResult(self._responses.get("monthly", []))
        if "sum_month_total_net_complaints" in sql_text:
            return _FakeResult(self._responses.get("complaints", []))
        if "FROM constant_data" in sql_text:
            return _FakeResult(self._responses.get("area", []))
        if "AVG(real_time_price)" in sql_text:
            return _FakeResult(self._responses.get("spot_rt", []))
        if "beihai_unit1_sales" in sql_text:
            return _FakeResult(self._responses.get("spot_beihai", []))
        if "xianghai_unit1_sales" in sql_text:
            return _FakeResult(self._responses.get("spot_xianghai", []))
        raise AssertionError(f"未预期的 SQL 查询: {sql_text}")


def test_in_progress_month_keeps_monthly_actual_empty_and_fetches_spot_price():
    """进行中月份月报实际值留空（不回退日报），现货电价按实时均价×1.05与加权电价取值。"""
    fake_responses = {
        "monthly": [
            ("北海", "耗标煤总量", "吨", "plan", 25130.24),
            ("北海", "电厂耗水量", "吨", "plan", 101743.2),
            ("香海", "耗标煤总量", "吨", "plan", 23173.0),
            ("供热公司", "耗标煤总量", "吨", "plan", 53207.79),
            ("庄河", "外购热量", "吉焦", "plan", 117734.73),
        ],
        "complaints": [
            ("GongRe", "供热公司", 120.0, date(2026, 11, 12)),
        ],
        "area": [
            ("GongRe", 5000.0, "2026-2027", None),
        ],
        "spot_rt": [
            (200.0, date(2026, 11, 12)),
        ],
        "spot_beihai": [
            (26063.0, 100.0, date(2026, 11, 7)),
        ],
        "spot_xianghai": [
            (24522.0, 100.0, date(2026, 11, 7)),
        ],
    }

    fake_engine_res = SimpleNamespace(
        rows=[
            {"company": "北海", "item": "全厂热效率", "type": "plan", "value": 0.8205},
            {"company": "香海", "item": "全厂热效率", "type": "plan", "value": 0.8079},
            {"company": "供热公司", "item": "供暖热耗率", "type": "plan", "value": 0.02572},
        ]
    )

    with (
        patch.object(competition_service, "SessionLocal", return_value=_FakeSession(fake_responses)),
        patch("backend.projects.monthly_data_show.api.workspace.query_month_data_show", return_value=fake_engine_res),
    ):
        res = competition_service.get_auto_fetch_competition_data("2026-11")

    assert res["ok"] is True
    assert res["is_historical"] is False
    assert res["spot_latest_date"] == "2026-11-12"
    assert res["spot_bill_latest_date"] == "2026-11-07"

    beihai = res["units"]["BeiHai"]
    assert beihai["coal_consumption"]["targetValue"] == 25130.24
    assert beihai["coal_consumption"]["actualValue"] is None
    assert beihai["heat_efficiency"]["targetValue"] == 82.05
    assert beihai["heat_efficiency"]["actualValue"] is None
    assert beihai["spot_price"]["targetValue"] == 210.0  # 200 * 1.05
    assert beihai["spot_price"]["actualValue"] == 260.63

    xianghai = res["units"]["XiangHai"]
    assert xianghai["spot_price"]["targetValue"] == 210.0
    assert xianghai["spot_price"]["actualValue"] == 245.22

    gongre = res["units"]["GongRe"]
    assert gongre["coal_consumption"]["targetValue"] == 53207.79
    assert gongre["coal_consumption"]["actualValue"] is None
    assert gongre["heat_unit_consumption"]["targetValue"] == 257.2
    assert gongre["heat_unit_consumption"]["actualValue"] is None
    assert gongre["service_complaint_rate"]["actualValue"] == 0.024

    zhuanghe = res["units"]["ZhuangHe"]
    assert zhuanghe["purchased_heat"]["targetValue"] == 117734.73
    assert zhuanghe["purchased_heat"]["actualValue"] is None


def test_historical_month_returns_monthly_real_values():
    """已出月报月份严格返回 monthly_data_show 计划值与实际值。"""
    fake_responses = {
        "monthly": [
            ("北海", "耗标煤总量", "吨", "plan", 57789.0),
            ("北海", "耗标煤总量", "吨", "real", 46848.88),
            ("庄河", "外购热量", "吉焦", "plan", 181300.0),
            ("庄河", "外购热量", "吉焦", "real", 249708.0),
        ],
        "complaints": [],
        "area": [],
        "spot_rt": [(125.42, date(2026, 1, 31))],
        "spot_beihai": [(13050.0, 100.0, date(2026, 1, 31))],
        "spot_xianghai": [(12316.0, 100.0, date(2026, 1, 31))],
    }
    fake_engine_res = SimpleNamespace(rows=[])

    with (
        patch.object(competition_service, "SessionLocal", return_value=_FakeSession(fake_responses)),
        patch("backend.projects.monthly_data_show.api.workspace.query_month_data_show", return_value=fake_engine_res),
    ):
        res = competition_service.get_auto_fetch_competition_data("2026-01")

    assert res["is_historical"] is True
    assert res["units"]["BeiHai"]["coal_consumption"]["targetValue"] == 57789.0
    assert res["units"]["BeiHai"]["coal_consumption"]["actualValue"] == 46848.88
    assert res["units"]["ZhuangHe"]["purchased_heat"]["actualValue"] == 249708.0
    assert res["units"]["BeiHai"]["spot_price"]["targetValue"] == 131.69
    assert res["units"]["BeiHai"]["spot_price"]["actualValue"] == 130.5


def test_save_and_get_competition_record_contract():
    """验证保存与读取接口序列化结构与入参解析。"""
    captured = {}

    class _WriteReadSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            sql_text = str(sql)
            if "INSERT INTO competition_monthly_records" in sql_text:
                captured["params"] = params
                status_val = params["status"]
                pub_val = "2026-11-13T15:30:00+08:00" if status_val == "final" else None
                return _FakeResult([(99, status_val, pub_val, "2026-11-13T15:30:00+08:00")])
            if "SELECT id, report_month" in sql_text:
                return _FakeResult([
                    (
                        99,
                        date(2026, 11, 1),
                        "final",
                        115000.0,
                        8456.0,
                        123456.0,
                        0,
                        [{"code": "BeiHai", "baseReward": 60000, "extraRewards": [{"title": "稳供", "amount": 8456}], "calculatedReward": 68456}],
                        {"month": "2026-11"},
                        "2026-11-13T15:30:00+08:00",
                        "2026-11-13T14:30:00",
                        "2026-11-13T15:30:00+08:00",
                    )
                ])
            return _FakeResult([])

        def commit(self):
            captured["committed"] = True

    with (
        patch.object(competition_service, "ensure_competition_table"),
        patch.object(competition_service, "SessionLocal", return_value=_WriteReadSession()),
    ):
        save_res = competition_service.save_competition_record(
            "2026-11",
            {
                "status": "final",
                "base_reward": 115000.0,
                "extra_reward": 8456.0,
                "total_reward": 123456.0,
                "disqualified_count": 0,
                "data_payload": [{"code": "BeiHai"}],
                "summary_payload": {"month": "2026-11"},
            },
        )
        get_res = competition_service.get_competition_record("2026-11")

    assert save_res["ok"] is True
    assert save_res["status"] == "final"
    assert save_res["published_at"] is not None
    assert captured["committed"] is True
    assert captured["params"]["report_month"] == date(2026, 11, 1)
    assert captured["params"]["status"] == "final"
    assert captured["params"]["base_reward"] == 115000.0
    assert captured["params"]["extra_reward"] == 8456.0
    assert get_res["ok"] is True
    assert get_res["found"] is True
    assert get_res["status"] == "final"
    assert get_res["base_reward"] == 115000.0
    assert get_res["extra_reward"] == 8456.0
    assert get_res["total_reward"] == 123456.0
    assert get_res["published_at"] == "2026-11-13T15:30:00+08:00"
    assert get_res["summary_payload"] == {"month": "2026-11"}


def test_save_invalid_status_rejected_and_season_summary_distinguishes_final():
    """校验非法状态拒绝，并验证供暖期兑现台账仅将 final 计入已定稿统计。"""
    import pytest

    with patch.object(competition_service, "ensure_competition_table"):
        with pytest.raises(ValueError):
            competition_service.save_competition_record("2026-11", {"status": "unknown"})

    class _SeasonSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            return _FakeResult([
                (
                    date(2026, 11, 1),
                    "final",
                    260000.0,
                    5000.0,
                    265000.0,
                    0,
                    [{"code": "BeiHai", "name": "北海热电厂", "score": 100.0, "baseReward": 70000.0, "extraRewards": [{"title": "专项", "amount": 5000}], "calculatedReward": 75000.0, "eligible": True}],
                    {},
                    "2026-12-01T10:00:00",
                    "2026-12-01T10:00:00",
                ),
                (
                    date(2026, 12, 1),
                    "saved",
                    250000.0,
                    2000.0,
                    252000.0,
                    1,
                    [{"code": "BeiHai", "name": "北海热电厂", "score": 95.0, "baseReward": 66500.0, "extraRewards": [{"title": "加分", "amount": 2000}], "calculatedReward": 68500.0, "eligible": True}],
                    {},
                    None,
                    "2027-01-02T09:00:00",
                ),
            ])

    with (
        patch.object(competition_service, "ensure_competition_table"),
        patch.object(competition_service, "SessionLocal", return_value=_SeasonSession()),
    ):
        res = competition_service.get_competition_records_summary(["2026-11", "2026-12", "2027-01", "2027-02", "2027-03"])

    assert res["ok"] is True
    assert len(res["records"]) == 5
    assert res["records"][0]["status"] == "final"
    assert res["records"][1]["status"] == "saved"
    assert res["records"][2]["status"] == "unrecorded"
    assert res["final_summary"] == {
        "count": 1,
        "base_reward": 260000.0,
        "extra_reward": 5000.0,
        "total_reward": 265000.0,
    }
    assert res["all_saved_summary"] == {
        "count": 2,
        "base_reward": 510000.0,
        "extra_reward": 7000.0,
        "total_reward": 517000.0,
    }
    beihai_nov = next(u for u in res["records"][0]["units"] if u["code"] == "BeiHai")
    assert beihai_nov["extraReward"] == 5000.0
    assert beihai_nov["reward"] == 75000.0

