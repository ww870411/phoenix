"""日期边界、历史常量、失败路径、缓存、审批主体的供暖期回归。"""
import os
import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from backend.services.heating_metrics.season_utils import get_season_windows

SETTINGS = {
    "26-27": {"start_date": "2026-11-05", "end_date": "2027-04-05", "temperature_start_date": "2026-11-01"},
    "25-26": {"start_date": "2025-11-03", "end_date": "2026-04-05", "temperature_start_date": "2025-11-02"},
}


class WindowTests(unittest.TestCase):
    def setUp(self):
        mocked = patch("backend.services.heating_season_service.get_period_settings", side_effect=lambda period: SETTINGS[period])
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_before_start(self):
        windows = get_season_windows("2026-11-01")
        self.assertEqual(windows["days_day_biz"], 1)
        for key in ("days_7_biz", "days_month_biz", "days_ytd_biz"):
            self.assertEqual(windows[key], 0)

    def test_independent_period_settings(self):
        windows = get_season_windows("2026-11-06")
        self.assertEqual((windows["days_ytd_biz"], windows["days_ytd_peer"]), (2, 4))
        self.assertEqual(windows["biz_temperature_start"], date(2026, 11, 1))
        self.assertEqual(windows["peer_temperature_start"], date(2025, 11, 2))

    def test_year_boundary_and_after_end(self):
        windows = get_season_windows("2027-01-01")
        self.assertEqual((windows["biz_period"], windows["days_month_biz"], windows["days_ytd_biz"]), ("26-27", 1, 58))
        windows = get_season_windows("2027-04-10")
        self.assertEqual((windows["biz_ytd_end"], windows["days_ytd_biz"]), (date(2027, 4, 5), 152))

    def test_temperature_card_ranges(self):
        from backend.services.dashboard_expression import _fill_cumulative_cards
        with patch("backend.services.dashboard_expression._fetch_daily_average_temperature_map", return_value={}) as fetch:
            _fill_cumulative_cards(None, {"供暖期平均气温": {}}, "2026-11-06", fetcher=lambda *args: {})
        self.assertEqual(fetch.call_args_list[0].args[1:], (date(2026, 11, 1), date(2026, 11, 6)))
        self.assertEqual(fetch.call_args_list[1].args[1:], (date(2025, 11, 2), date(2025, 11, 6)))


class DashboardReadTests(unittest.TestCase):
    def test_cache_miss_preserves_history_and_outside_interval_queries(self):
        from backend.projects.daily_report_25_26.api.dashboard import get_dashboard_data
        prefix = "backend.projects.daily_report_25_26.api.dashboard"
        for target in ("2025-11-01", "2026-11-01", "2027-04-06"):
            with self.subTest(target=target):
                result = MagicMock()
                result.to_dict.return_value = {"push_date": target, "data": {"历史指标": 123}}
                with patch(f"{prefix}.dashboard_cache.get_cached_payload", return_value=(None, {"disabled": False})), patch(f"{prefix}.evaluate_dashboard", return_value=result), patch(f"{prefix}.dashboard_cache.update_cache_entry") as write, patch("backend.services.heating_season_service.get_season_config", return_value={"start_date": "2026-11-05", "end_date": "2027-04-05"}):
                    response = get_dashboard_data(target)
                self.assertTrue(response["ok"])
                self.assertEqual(response["push_date"], target)
                self.assertFalse(response["cache_hit"])
                self.assertEqual(response["data"], {"历史指标": 123})
                write.assert_not_called()

    def test_current_interval_query_does_not_recreate_deleted_cache(self):
        from backend.projects.daily_report_25_26.api.dashboard import get_dashboard_data
        prefix = "backend.projects.daily_report_25_26.api.dashboard"
        result = MagicMock()
        result.to_dict.return_value = {"push_date": "2026-11-06", "data": {}}
        with patch(f"{prefix}.dashboard_cache.get_cached_payload", return_value=(None, {"disabled": False})), patch(f"{prefix}.evaluate_dashboard", return_value=result), patch(f"{prefix}.dashboard_cache.update_cache_entry", return_value={"disabled": False}) as write, patch("backend.services.heating_season_service.get_season_config", return_value={"start_date": "2026-11-05", "end_date": "2027-04-05"}):
            self.assertTrue(get_dashboard_data("2026-11-06")["ok"])
        write.assert_not_called()

    def test_existing_history_cache_remains_readable(self):
        from backend.projects.daily_report_25_26.api.dashboard import get_dashboard_data
        prefix = "backend.projects.daily_report_25_26.api.dashboard"
        with patch(f"{prefix}.dashboard_cache.get_cached_payload", return_value=({"ok": True, "push_date": "2025-11-01", "data": {"历史缓存": 123}}, {"disabled": False})), patch(f"{prefix}.evaluate_dashboard") as evaluate, patch(f"{prefix}.dashboard_cache.update_cache_entry") as write:
            response = get_dashboard_data("2025-11-01")
        self.assertTrue(response["cache_hit"])
        self.assertEqual(response["data"], {"历史缓存": 123})
        evaluate.assert_not_called()
        write.assert_not_called()


class ContractTests(unittest.TestCase):
    def test_history_constant(self):
        from backend.services.runtime_expression import EvalContext, Evaluator
        context = EvalContext("daily_report_25_26", {"company": "BeiHai"}, "sum_basic_data", {"c": "constant_data"}, {"售电单价": "price_power_sales"}, context={"biz_date": "2025-11-01"})
        evaluator = Evaluator(context, {}, {"c": {"price_power_sales": {"24-25": Decimal("0.4"), "25-26": Decimal("0.395")}}}, {})
        self.assertEqual(evaluator._value_of_const("售电单价", "biz_date"), Decimal("0.395"))
        self.assertEqual(evaluator._value_of_const("售电单价", "peer_date"), Decimal("0.4"))

    def test_failure_does_not_query_old_view(self):
        from backend.services.runtime_expression import _fetch_metrics_from_view_batch
        session = MagicMock()
        with patch("backend.services.heating_metrics.daily_engine.DailyDashboardEngine.compute_groups", side_effect=RuntimeError("模拟失败")):
            with self.assertRaises(RuntimeError):
                _fetch_metrics_from_view_batch(session, "groups", ["Group"], "2026-11-01")
        session.execute.assert_not_called()

    def test_analysis_failure_propagates(self):
        from backend.services.data_analysis import _query_analysis_rows, _query_analysis_timeline
        with patch("backend.services.data_analysis.SessionLocal"), patch("backend.services.heating_metrics.analysis_engine.HeatingAnalysisEngine.compute_analysis_rows", side_effect=RuntimeError("模拟失败")), patch("backend.services.heating_metrics.analysis_engine.HeatingAnalysisEngine.compute_analysis_timeline", side_effect=RuntimeError("模拟失败")):
            for query in (_query_analysis_rows, _query_analysis_timeline):
                with self.assertRaises(RuntimeError):
                    query("groups", "Group", ["consumption_std_coal"], date(2026, 11, 1), date(2026, 11, 6))

    def test_cache_schedule_accepts_explicit_history_range(self):
        from backend.services.dashboard_cache import resolve_publish_schedule
        with patch("backend.services.heating_season_service.get_season_config", return_value={"active_period": "26-27", **SETTINGS["26-27"]}), patch("backend.services.dashboard_cache._write_json_dict") as write:
            days, label = resolve_publish_schedule(preset="season")
            self.assertEqual((days[0], days[-1], len(days), label), ("2026-11-05", "2027-04-05", 152, "26-27"))
            with self.assertRaises(ValueError):
                resolve_publish_schedule(preset="25-26")
            history, label = resolve_publish_schedule(start_date="2025-11-01", end_date="2026-04-05")
            self.assertEqual((history[0], history[-1], len(history)), ("2025-11-01", "2026-04-05", 156))
            self.assertIn("2025-11-01", label)
            write.assert_not_called()

    def test_workflow_isolation_keeps_history(self):
        from backend.services.workflow_status import WorkflowStatusManager, WorkflowSnapshot, UnitApprovalState
        manager = WorkflowStatusManager()
        anchor = datetime(2026, 11, 1)
        manager._storage[("daily_report_25_26", anchor)] = WorkflowSnapshot(units={"BeiHai": UnitApprovalState("BeiHai", "approved"), "high_lot_1": UnitApprovalState("high_lot_1")})
        with patch.object(manager, "_ensure_loaded_locked"), patch.object(manager, "_persist_locked"):
            result = manager.get_snapshot("daily_report_25_26", anchor, ["BeiHai", "high_lot_1"], ["BeiHai"])
            empty = manager.get_snapshot("daily_report_25_26", anchor, ["high_lot_1"], ["BeiHai"])
        self.assertEqual(set(result.units), {"BeiHai"})
        self.assertEqual(result.units["BeiHai"].status, "approved")
        self.assertEqual(empty.units, {})
        self.assertIn("high_lot_1", manager._storage[("daily_report_25_26", anchor)].units)

    def test_disable_cache_keeps_old_entries(self):
        from backend.services.dashboard_cache import disable_cache
        index = {"entries": {"2025-11-01": {"dir_name": "2025-11-01"}}, "disabled": False}
        with patch("backend.services.dashboard_cache._ensure_split_cache_ready"), patch("backend.services.dashboard_cache._load_index", return_value=index), patch("backend.services.dashboard_cache._write_index") as write, patch("backend.services.dashboard_cache.get_cache_status", return_value={}):
            disable_cache("daily_report_25_26")
        written = write.call_args.args[1]
        self.assertTrue(written["disabled"])
        self.assertEqual(written["entries"], {"2025-11-01": {"dir_name": "2025-11-01"}})

    def test_no_duplicate_top_level_definitions(self):
        import ast
        import inspect
        import importlib
        from collections import Counter
        for name in ("heating_season_service", "dashboard_cache", "dashboard_expression", "runtime_expression", "data_analysis", "heating_metrics.analysis_engine", "heating_metrics.daily_engine", "heating_metrics.season_utils"):
            module = importlib.import_module(f"backend.services.{name}")
            counts = Counter(node.name for node in ast.parse(inspect.getsource(module)).body if isinstance(node, (ast.FunctionDef, ast.ClassDef)))
            self.assertEqual([key for key, count in counts.items() if count > 1], [], name)


@unittest.skipUnless(os.environ.get("PHOENIX_TEST_POSTGRES") == "1", "显式开启数据库临时表回归")
class PostgresTests(unittest.TestCase):
    def test_actual_aggregation_with_configured_boundaries(self):
        from sqlalchemy import text
        from backend.db.database_daily_report_25_26 import SessionLocal
        from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
        from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine
        with SessionLocal() as session:
            try:
                # 临时同名表仅在本会话可见，结束 rollback，正式数据不变。
                session.execute(text("CREATE TEMP TABLE daily_basic_data (company text, company_cn text, item text, item_cn text, unit text, value numeric, date date, sheet_name text) ON COMMIT DROP"))
                session.execute(text("INSERT INTO daily_basic_data VALUES ('BeiHai','北海','consumption_std_coal','标煤耗量','吨',:value,:date,'BeiHai_co_generation_Sheet')"), [
                    {"date": "2026-11-01", "value": 1000}, {"date": "2026-11-05", "value": 2}, {"date": "2026-11-06", "value": 3},
                    {"date": "2027-04-05", "value": 5}, {"date": "2027-04-06", "value": 2000},
                    {"date": "2025-11-01", "value": 3000}, {"date": "2025-11-03", "value": 7}, {"date": "2025-11-06", "value": 11},
                ])
                with patch("backend.services.heating_season_service.get_period_settings", side_effect=lambda period: SETTINGS[period]):
                    engine = DailyDashboardEngine(session)
                    key = ("BeiHai", "consumption_std_coal")
                    row = engine.fetch_base_aggregated_data(get_season_windows("2026-11-06"))[key]
                    self.assertEqual(row["vec"], [3, 11, 5, 18, 5, 18, 5, 18])
                    row = engine.fetch_base_aggregated_data(get_season_windows("2026-11-01"))[key]
                    self.assertEqual((row["vec"][0], row["vec"][6]), (1000, 0))
                    row = engine.fetch_base_aggregated_data(get_season_windows("2027-04-06"))[key]
                    self.assertEqual((row["vec"][0], row["vec"][6]), (2000, 10))
                    rows = HeatingAnalysisEngine(session).compute_company_analysis("2026-11-01", "2026-11-06", "BeiHai")
                    metric = next(row for row in rows if row["item"] == "consumption_std_coal")
                    self.assertEqual((metric["value_biz_date"], metric["value_peer_date"]), (5, 18))
                    rows = HeatingAnalysisEngine(session).compute_analysis_rows("BeiHai", ["consumption_std_coal"], date(2026, 11, 1), date(2026, 11, 1), aggregate=True)
                    self.assertEqual(rows["consumption_std_coal"]["value_biz_date"], 0)
                    session.execute(text("INSERT INTO daily_basic_data VALUES ('BeiHai','北海','sum_season_total_net_complaints','累计净投诉量','件',:value,:date,'test_counter')"), [
                        {"date": "2026-11-01", "value": 100}, {"date": "2026-11-04", "value": 120}, {"date": "2026-11-06", "value": 125},
                        {"date": "2025-11-01", "value": 1000}, {"date": "2025-11-02", "value": 1007}, {"date": "2025-11-06", "value": 1025},
                    ])
                    row = engine.fetch_base_aggregated_data(get_season_windows("2026-11-06"))[("BeiHai", "sum_season_total_net_complaints")]
                    self.assertEqual(row["vec"], [5, 18] * 4)
                    session.execute(text("INSERT INTO daily_basic_data VALUES ('BeiHai','北海','sum_season_total_net_complaints','累计净投诉量','件',99999,'2025-10-31','test_counter')"))
                    with patch("backend.services.heating_season_service.get_period_settings", side_effect=lambda period: {**SETTINGS[period], "start_date": f"20{period[:2]}-11-01"}):
                        row = engine.fetch_base_aggregated_data(get_season_windows("2026-11-01"))[("BeiHai", "sum_season_total_net_complaints")]
                        self.assertEqual(row["vec"][1], 1000)
            finally:
                session.rollback()


if __name__ == "__main__":
    unittest.main()
