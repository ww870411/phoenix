"""静态全月计划完成比例：不依赖动态分解或业务数据库写入。"""
from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch
from backend.projects.daily_report_25_26.services.monthly_coal_progress import build_monthly_coal_progress, get_monthly_coal_progress, get_season_coal_progress

UNITS = [{'company': c, 'company_cn': n} for c, n in [('Group', '集团全口径'), ('ZhuChengQu', '主城区'), ('BeiHai', '北海热电厂'), ('XiangHai', '香海热电厂'), ('YanJiuYuan', '研究院')]]
HIERARCHY = {'Group': ['BeiHai', 'XiangHai', 'YanJiuYuan'], 'ZhuChengQu': ['BeiHai', 'XiangHai']}
def plan(code, value, unit='吨'):
    return {'company': code, 'value': value, 'unit': unit}
def actual(code, value, days=('2026-11-01',), unit='吨'):
    return {'company': code, 'value': value, 'unit': unit, 'dates': list(days)}
def result(plans, actuals, biz='2026-11-01'):
    return {r['company']: r for r in build_monthly_coal_progress(biz, plans, actuals, UNITS, HIERARCHY)['items']}

class MonthlyCoalProgressTests(TestCase):
    def test_static_month_denominator_and_over_plan_are_not_capped(self):
        r = result([plan('BeiHai', 100)], [actual('BeiHai', 125)])['BeiHai']
        self.assertEqual(r['completion_percent'], 125)
        self.assertEqual(r['remaining_value'], -25)
        self.assertEqual(r['status'], 'over_plan')

    def test_explicit_zero_actual_is_ready_but_missing_actual_is_not_zero(self):
        r = result([plan('BeiHai', 100)], [actual('BeiHai', 0)])['BeiHai']
        self.assertEqual(r['completion_percent'], 0)
        missing = result([plan('BeiHai', 100)], [])['BeiHai']
        self.assertIsNone(missing['actual_value'])
        self.assertIsNone(missing['completion_percent'])
        self.assertEqual(missing['status'], 'missing_actual')

    def test_missing_or_zero_plan_never_divides_by_zero(self):
        for plans, expected in [([], 'missing_plan'), ([plan('BeiHai', 0)], 'zero_plan')]:
            r = result(plans, [actual('BeiHai', 20)])['BeiHai']
            self.assertIsNone(r['completion_percent'])
            self.assertEqual(r['status'], expected)

    def test_partial_actual_is_visible_but_not_presented_as_complete_ratio(self):
        r = result([plan('BeiHai', 100)], [actual('BeiHai', 10)], '2026-11-02')['BeiHai']
        self.assertEqual(r['actual_value'], 10)
        self.assertEqual(r['reported_days'], 1)
        self.assertEqual(r['expected_days'], 2)
        self.assertIsNone(r['completion_percent'])
        self.assertIsNone(r['remaining_value'])

    def test_rollup_actual_and_authoritative_direct_plan_do_not_double_count(self):
        r = result([plan('Group', 1000), plan('ZhuChengQu', 700), plan('BeiHai', 400), plan('XiangHai', 400)], [actual('BeiHai', 100), actual('XiangHai', 200)])
        self.assertEqual(r['Group']['plan_value'], 1000)
        self.assertEqual(r['Group']['actual_value'], 300)
        self.assertEqual(r['Group']['completion_percent'], 30)
        self.assertEqual(r['ZhuChengQu']['completion_percent'], 300 / 700 * 100)

    def test_rollup_falls_back_to_children_and_missing_child_is_not_complete(self):
        r = result([plan('BeiHai', 100), plan('XiangHai', 200)], [actual('BeiHai', 50)])
        self.assertEqual(r['Group']['plan_value'], 300)
        self.assertEqual(r['Group']['plan_source'], 'rollup')
        self.assertEqual(r['Group']['status'], 'incomplete_actual')

    def test_ton_unit_conversion_preserves_precision(self):
        r = result([plan('BeiHai', '1.123456', '万吨')], [actual('BeiHai', '112.3456')])['BeiHai']
        self.assertEqual(r['plan_value'], 11234.56)
        self.assertEqual(r['completion_percent'], 1)
        invalid = result([plan('BeiHai', 100, '未知单位')], [actual('BeiHai', 1)])['BeiHai']
        self.assertIsNone(invalid['completion_percent'])

    def test_research_institute_not_displayed_but_existing_group_scope_retained(self):
        r = result([plan('Group', 100), plan('BeiHai', 90), plan('YanJiuYuan', 10)], [actual('BeiHai', 9), actual('YanJiuYuan', 1)])
        self.assertNotIn('YanJiuYuan', r)
        self.assertEqual(r['Group']['actual_value'], 10)

    def test_query_uses_exact_month_string_and_actual_date_cutoff_no_write(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.side_effect = [[plan('BeiHai', 100)], [actual('BeiHai', 1)]]
        r = get_monthly_coal_progress(session, '2026-11-01', UNITS, HIERARCHY)
        self.assertTrue(r['ok'])
        calls = session.execute.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[1]['month_start'], '2026-11-01')
        self.assertEqual(calls[1].args[1]['biz_date'], date(2026, 11, 1))
        self.assertTrue(all(str(c.args[0]).lstrip().startswith('SELECT') for c in calls))
        session.commit.assert_not_called()

    def season(self, plans, actuals, biz='2026-12-01'):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.side_effect = [plans, actuals]
        windows = {'biz_season_start': date(2026, 11, 30), 'biz_season_end': date(2026, 12, 31), 'biz_period': '26-27'}
        with patch('backend.services.heating_metrics.season_utils.get_season_windows', return_value=windows):
            data = get_season_coal_progress(session, biz, UNITS, HIERARCHY)
        self.assertEqual(session.execute.call_args_list[1].args[1]['season_start'], date(2026, 11, 30))
        self.assertEqual(session.execute.call_args_list[1].args[1]['biz_date'], min(date.fromisoformat(biz), date(2026, 12, 31)))
        session.commit.assert_not_called()
        return {row['company']: row for row in data['items']}

    def test_full_season_plan_includes_future_month_and_actual_uses_configured_start(self):
        plans = [{**plan('BeiHai', value), 'period': month} for value, month in [(100, '2026-11-01'), (200, '2026-12-01')]]
        rows = self.season(plans, [actual('BeiHai', 60, ['2026-11-30', '2026-12-01'])])
        self.assertEqual(rows['BeiHai']['plan_value'], 300)
        self.assertEqual(rows['BeiHai']['completion_percent'], 20)
        self.assertEqual(rows['BeiHai']['expected_days'], 2)
        self.assertEqual(rows['Group']['completion_percent'], 20)

    def test_missing_plan_month_and_actual_day_do_not_produce_false_season_percentage(self):
        plans = [{**plan('BeiHai', 100), 'period': '2026-11-01'}]
        row = self.season(plans, [actual('BeiHai', 60, ['2026-11-30', '2026-12-01'])])['BeiHai']
        self.assertIsNone(row['plan_value'])
        self.assertIsNone(row['completion_percent'])
        plans.append({**plan('BeiHai', 200), 'period': '2026-12-01'})
        row = self.season(plans, [actual('BeiHai', 60, ['2026-12-01'])])['BeiHai']
        self.assertEqual(row['status'], 'incomplete_actual')
        self.assertIsNone(row['completion_percent'])

    def test_before_season_does_not_invent_actual_or_percentage(self):
        row = self.season([{**plan('BeiHai', 100), 'period': m} for m in ['2026-11-01', '2026-12-01']], [], '2026-11-01')['BeiHai']
        self.assertEqual(row['expected_days'], 0)
        self.assertIsNone(row['actual_value'])
        self.assertIsNone(row['completion_percent'])

    def test_confirmed_25_26_plan_ends_march_but_actual_statistics_keep_season_boundaries(self):
        session = MagicMock()
        months = ['2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01', '2026-03-01']
        plans = [{**plan('BeiHai', 100), 'period': month} for month in months]
        days = [date(2025, 11, 1) + timedelta(days=i) for i in range(151)]
        session.execute.return_value.mappings.return_value.all.side_effect = [plans, [actual('BeiHai', 60, days)]]
        windows = {'biz_season_start': date(2025, 11, 1), 'biz_season_end': date(2026, 4, 5), 'biz_period': '25-26'}
        with patch('backend.services.heating_metrics.season_utils.get_season_windows', return_value=windows):
            data = get_season_coal_progress(session, '2026-03-31', UNITS, HIERARCHY)
        row = next(r for r in data['items'] if r['company'] == 'Group')
        self.assertEqual(data['plan_months'], months)
        self.assertEqual(row['actual_value'], 60)
        self.assertEqual(row['plan_value'], 500)
        self.assertEqual(row['completion_percent'], 12)
        self.assertEqual(row['expected_days'], 151)
        self.assertEqual(data['end_date'], '2026-04-05')
        self.assertEqual(session.execute.call_args_list[0].args[1]['last_month'], '2026-03-01')
        session.commit.assert_not_called()
