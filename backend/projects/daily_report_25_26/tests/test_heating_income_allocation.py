"""验证暖收入在独立供暖期区间内守恒分摊，区间外不产生收入。"""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from backend.services.heating_metrics.season_utils import get_heating_income_fraction
from backend.projects.daily_report_25_26.tests.test_season_rollover import SETTINGS


class HeatingIncomeAllocationTests(unittest.TestCase):
    def setUp(self):
        settings = patch("backend.services.heating_season_service.get_period_settings", side_effect=lambda period: SETTINGS[period])
        settings.start()
        self.addCleanup(settings.stop)
        self.constants = ({("BeiHai", "eco_season_heating_income"): 15200.0}, {("BeiHai", "eco_season_heating_income"): 30800.0})

    def test_daily_amounts_sum_to_full_income_and_include_both_endpoints(self):
        start, end = date(2026, 11, 5), date(2027, 4, 5)
        fractions = [get_heating_income_fraction(start + timedelta(days=i), start + timedelta(days=i), "26-27") for i in range(152)]
        self.assertAlmostEqual(sum(fractions), 1)
        self.assertAlmostEqual(fractions[0], 1 / 152)
        self.assertAlmostEqual(fractions[-1], 1 / 152)
        self.assertEqual(get_heating_income_fraction(start - timedelta(days=1), end + timedelta(days=1), "26-27"), 1)

    def test_leap_year_single_day_and_invalid_config(self):
        with patch("backend.services.heating_season_service.get_period_settings", return_value={"start_date": "2023-11-01", "end_date": "2024-04-05"}):
            self.assertAlmostEqual(get_heating_income_fraction(date(2024, 2, 29), date(2024, 2, 29), "23-24"), 1 / 157)
        with patch("backend.services.heating_season_service.get_period_settings", return_value={"start_date": "2026-11-05", "end_date": "2026-11-05"}):
            self.assertEqual(get_heating_income_fraction(date(2026, 11, 5), date(2026, 11, 5), "26-27"), 1)
        with patch("backend.services.heating_season_service.get_period_settings", return_value={"start_date": "2026-11-06", "end_date": "2026-11-05"}):
            with self.assertRaises(ValueError):
                get_heating_income_fraction(date(2026, 11, 5), date(2026, 11, 5), "26-27")

    def daily_row(self, day):
        from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
        engine = DailyDashboardEngine(MagicMock())
        with patch.object(engine, "fetch_constants", return_value=self.constants), patch.object(engine, "fetch_base_aggregated_data", return_value={
            ("BeiHai", "consumption_std_coal"): {"company_cn": "北海", "item_cn": "标煤耗量", "unit": "吨", "vec": [7] * 8}
        }):
            rows = engine.compute_sum_basic_data(day)
        return next(row for row in rows if row["item"] == "eco_heating_supply_income"), rows

    def test_daily_month_week_and_season_use_independent_denominators(self):
        row, _ = self.daily_row("2026-11-06")
        for field, expected in {"value_biz_date": 100, "value_peer_date": 200, "sum_7d_biz": 200, "sum_7d_peer": 800, "sum_month_biz": 200, "sum_month_peer": 800, "sum_ytd_biz": 200, "sum_ytd_peer": 800}.items():
            self.assertAlmostEqual(row[field], expected)

    def test_daily_before_and_after_interval_zero_but_raw_daily_unchanged(self):
        for day in ("2026-11-04", "2027-04-06"):
            row, rows = self.daily_row(day)
            self.assertEqual(row["value_biz_date"], 0)
            self.assertEqual(next(r for r in rows if r["item"] == "consumption_std_coal")["value_biz_date"], 7)

    def test_company_analysis_and_subsheet_match_daily_and_full_season(self):
        from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine
        engine = HeatingAnalysisEngine(MagicMock())
        base = {("BeiHai", "consumption_std_coal"): {"company_cn": "北海", "item_cn": "标煤耗量", "unit": "吨", "biz": 0, "peer": 0}}
        sub = {("test_sheet", "consumption_std_coal"): {"company_cn": "北海", "item_cn": "标煤耗量", "unit": "吨", "biz": 0, "peer": 0}}
        with patch.object(engine, "fetch_constants", return_value=self.constants), patch.object(engine, "fetch_base_aggregated_range", return_value=base), patch.object(engine, "fetch_base_beihai_sub", return_value=sub):
            for method in (engine.compute_company_analysis, engine.compute_beihai_sub_analysis):
                for start, end, expected in (("2026-11-04", "2026-11-04", 0), ("2026-11-05", "2026-11-05", 100), ("2027-04-06", "2027-04-06", 0), ("2026-11-01", "2027-04-10", 15200)):
                    with self.subTest(method=method.__name__, start=start):
                        item = "eco_heating_supply_income" if method == engine.compute_company_analysis else "eco_direct_income"
                        row = next(r for r in method(start, end) if r["item"] == item)
                        self.assertAlmostEqual(row["value_biz_date"], expected)


if __name__ == "__main__":
    unittest.main()
