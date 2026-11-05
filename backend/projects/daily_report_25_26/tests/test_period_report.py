"""周期边界、分析分支与接口权限回归；不写业务数据库。"""
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.services.auth_manager import get_current_session
from backend.projects.daily_report_25_26.api.period_report import router
from backend.projects.daily_report_25_26.services.period_report import validate_period, metric_story, report_value, build_period_report


class PeriodReportTests(TestCase):
    def test_missing_metrics_follow_user_zero_convention(self):
        for value in (None, '', float('nan'), float('inf')):
            self.assertEqual(report_value(value), 0)
        self.assertEqual(report_value(-12.5), -12.5)
        self.assertEqual(report_value(0), 0)

    def test_november_period_keeps_engine_peer_and_zero_fills_unknown(self):
        module = 'backend.projects.daily_report_25_26.services.period_report'
        def calculate(company, keys, start, end, **kwargs):
            self.assertEqual((start.month, start.day, end.month, end.day), (11, 1, 11, 4))
            return {'consumption_std_coal': {'value_biz_date': 400 if start.year == 2026 else 300}}
        with patch(module + '.HeatingAnalysisEngine') as engine, patch(module + '.get_monthly_coal_progress', return_value={'items': []}):
            engine.return_value.compute_analysis_rows.side_effect = calculate
            report = build_period_report(None, date(2026, 11, 1), date(2026, 11, 4), False)
        coal = next(p for p in report['pages'] if p['key'] == 'consumption_std_coal')
        self.assertEqual((coal['rows'][0]['curr'], coal['rows'][0]['sync'], coal['rows'][0]['delta']), (400, 300, 100))
        gas = next(p for p in report['pages'] if p['key'] == 'consumption_natural_gas')
        self.assertEqual((gas['rows'][0]['curr'], gas['rows'][0]['sync']), (0, 0))

    def test_period_bounds(self):
        validate_period(date(2026, 1, 16), date(2026, 1, 24))
        validate_period(date(2026, 1, 31), date(2026, 2, 2))
        for start, end in [(date(2026, 2, 1), date(2026, 1, 1)),
                           (date(2026, 9, 30), date(2026, 10, 1))]:
            with self.assertRaises(ValueError):
                validate_period(start, end)

    def test_negative_profit_and_missing(self):
        rows = [{'name': '集团', 'curr': 10, 'sync': -2, 'prev': None},
                {'name': '甲', 'curr': None, 'sync': 0, 'prev': None}]
        story = ' '.join(metric_story('边际利润', rows, '万元', False))
        self.assertIn('由亏转盈', story)
        self.assertNotIn('%', story)
        self.assertNotIn('较上期', story)
        self.assertNotIn('部分单位本期缺少完整依据', story)

    def test_offsetting_changes_do_not_create_contribution_percentage(self):
        rows = [{'name': '集团', 'curr': 100, 'sync': 99, 'prev': 100},
                {'name': '甲', 'curr': 200, 'sync': 100, 'prev': 200},
                {'name': '乙', 'curr': 0, 'sync': 99, 'prev': 0}]
        story = ' '.join(metric_story('标煤耗量', rows, '吨', True))
        self.assertIn('甲', story)
        self.assertNotIn('占集团增量', story)

    def test_permission_and_bad_dates_before_database(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_viewer')
        client = TestClient(app)
        self.assertEqual(client.get('/period-report').status_code, 403)
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        with patch('backend.projects.daily_report_25_26.api.period_report.SessionLocal') as session:
            self.assertEqual(client.get('/period-report?start=2026-01-01').status_code, 422)
            self.assertEqual(client.get('/period-report?start=2026-02-01&end=2026-01-01').status_code, 422)
            session.assert_not_called()
