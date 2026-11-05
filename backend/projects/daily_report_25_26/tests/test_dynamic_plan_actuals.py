"""实际值的发布日边界、单指标计算及日/月切换回归。"""
from datetime import date
from unittest import TestCase
from unittest.mock import patch

from backend.projects.daily_report_25_26.services.dynamic_plan_actuals import get_dynamic_plan_actuals, get_dynamic_plan_actuals_batch, _convert


def raw(day, value, company='BeiHai', item='consumption_std_coal', unit='吨'):
    return {'date': date.fromisoformat(day), 'value': value, 'company': company,
            'company_cn': company, 'item': item, 'item_cn': item, 'unit': unit}


class Session:
    """只模拟底表读取，计算与集团汇总使用真实业务引擎。"""
    def __init__(self, rows, constants=()):
        self.rows, self.constants, self.calls = rows, constants, []

    def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, params))
        if 'constant_data' in sql:
            result = self.constants
        elif 'SELECT DISTINCT' in sql:
            result = [{'company': r['company'], 'item': r['item'], 'period': params['period']}
                      for r in self.rows if params['first'] <= r['date'] <= params['last'] and r['value'] is not None]
        else:
            result = [r for r in self.rows if params['start'] <= r['date'] <= params['end']]
        class Result:
            def mappings(self): return self
            def all(self): return result
        return Result()


def query(session, mode='day', start='2026-11', end='2026-11', published=('2026-11-02',),
          company='BeiHai', item='consumption_std_coal', unit='吨'):
    return get_dynamic_plan_actuals(session, company, item, unit, start, end, mode, published)


class ActualsTests(TestCase):
    def test_historical_daily_actuals_use_full_month_before_publication(self):
        session = Session([raw(f'2026-11-{day:02}', day) for day in range(1, 31)])
        result = query(session, published=('2026-12-01',))
        self.assertEqual(result['values']['2026-11-01'], 1)
        self.assertEqual(result['values']['2026-11-30'], 30)
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(session.calls[0][1]['end'], date(2026, 11, 30))

    def test_batch_uses_one_snapshot_and_one_read_for_multiple_metrics(self):
        session = Session([raw('2026-11-01', 2), raw('2026-11-02', 3),
                           raw('2026-11-03', 999), raw('2026-11-01', 8, item='amount_heat_supply', unit='GJ')])
        metrics = [{'item': 'consumption_std_coal', 'unit': '吨'}, {'item': 'amount_heat_supply', 'unit': 'GJ'}]
        result = get_dynamic_plan_actuals_batch(session, 'BeiHai', metrics, '2026-11', '2026-11', 'month', ['2026-11-02'])
        self.assertEqual(result['metrics']['consumption_std_coal']['values']['2026-11'], 5)
        self.assertIsNone(result['metrics']['amount_heat_supply']['values']['2026-11'])
        self.assertEqual(len(session.calls), 3)
        self.assertEqual(result['latest_published_date'], '2026-11-02')

    def test_cumulative_endpoint_rejects_wrong_month_without_querying_database(self):
        from backend.projects.daily_report_25_26.api.dynamic_plan import CumulativeActualRequest, get_cumulative_actuals_endpoint
        with patch('backend.services.workflow_status.workflow_status_manager.list_published_dates', return_value=['2026-12-01']), \
             patch('backend.projects.daily_report_25_26.api.dynamic_plan.SessionLocal') as session:
            result = get_cumulative_actuals_endpoint(CumulativeActualRequest(company='Group', year_month='2026-11', metrics=[]))
        self.assertFalse(result['available'])
        session.assert_not_called()

    def test_daily_preserves_zero_and_excludes_unpublished_scattered_rows(self):
        session = Session([raw('2026-11-01', 0), raw('2026-11-02', 12), raw('2026-11-03', 999)])
        result = query(session, published=('2026-11-01', '2026-11-02'))
        self.assertEqual(result['values']['2026-11-01'], 0)
        self.assertEqual(result['values']['2026-11-02'], 12)
        self.assertIsNone(result['values']['2026-11-03'])
        self.assertEqual(len(result['values']), 30)
        for sql, params in session.calls:
            if 'daily_basic_data' in sql:
                self.assertLessEqual(params.get('end', params.get('last')), date(2026, 11, 2))

    def test_months_accumulate_independently_and_keep_future_empty(self):
        rows = [raw(f'2026-11-{day:02}', 1) for day in range(1, 31)]
        rows += [raw('2026-12-01', 3), raw('2026-12-02', 4), raw('2026-12-03', 999)]
        result = query(Session(rows), 'month', '2026-11', '2027-01', ('2026-12-02',))
        self.assertEqual(result['values'], {'2026-11': 30, '2026-12': 7, '2027-01': None})

    def test_missing_or_null_is_not_zero_and_month_does_not_hide_missing_day(self):
        session = Session([raw('2026-11-01', 0), raw('2026-11-02', None)])
        self.assertIsNone(query(session)['values']['2026-11-02'])
        self.assertIsNone(query(session, 'month')['values']['2026-11'])

    def test_no_publication_or_future_month_does_not_query_raw_data(self):
        for dates in [(), ('2026-10-31',)]:
            session = Session([raw('2026-11-01', 10)])
            self.assertTrue(all(value is None for value in query(session, published=dates)['values'].values()))
            self.assertEqual(session.calls, [])

    def test_group_sums_same_metric_across_members_without_adding_other_metrics(self):
        session = Session([raw('2026-11-01', 2), raw('2026-11-01', 3, 'XiangHai'),
                           raw('2026-11-01', 999, item='amount_power_sales', unit='万kWh')])
        result = query(session, company='Group', published=('2026-11-01',))
        self.assertEqual(result['values']['2026-11-01'], 5)

    def test_derived_rate_reuses_group_area_weighting_and_unit_conversion(self):
        rows = [raw('2026-11-01', 20, 'GongRe', 'consumption_station_heat', 'GJ'),
                raw('2026-11-01', 40, 'JinZhou', 'amount_heat_supply', 'GJ'),
                raw('2026-11-01', 10, 'JinZhou', 'amount_hot_water_sales', 'GJ')]
        constants = [{'company': c, 'item': 'amount_heating_fee_area', 'period': '26-27', 'value': v}
                     for c, v in [('GongRe', 2), ('JinZhou', 3), ('BeiFang', 1), ('JinPu', 1), ('ZhuangHe', 1), ('YanJiuYuan', 1)]]
        result = query(Session(rows, constants), company='Group', item='rate_heat_per_10k_m2',
                       unit='GJ/万㎡', published=('2026-11-01',))
        self.assertAlmostEqual(result['values']['2026-11-01'], 50 / 9)
        self.assertEqual(_convert(10000, '吨', '万吨'), 1)
        self.assertEqual(_convert(3, 'GJ/万㎡', 'GJ/万m²'), 3)
        self.assertIsNone(_convert(1, '吨', 'GJ'))

    def test_economic_metric_uses_price_formula(self):
        constants = [{'company': 'BeiHai', 'item': 'price_power_sales', 'period': '26-27', 'value': 0.5}]
        result = query(Session([raw('2026-11-01', 8, item='amount_power_sales', unit='万kWh')], constants),
                       item='eco_power_supply_income', unit='万元', published=('2026-11-01',))
        self.assertEqual(result['values']['2026-11-01'], 4)

    def test_calendar_month_does_not_clip_to_heating_season_start(self):
        rows = [raw(f'2026-10-{day:02}', 2) for day in range(1, 32)]
        result = query(Session(rows), 'month', '2026-10', '2026-10', ('2026-11-02',))
        self.assertEqual(result['values']['2026-10'], 62)

    def test_leap_month_and_invalid_ranges(self):
        result = query(Session([]), start='2028-02', end='2028-02', published=())
        self.assertEqual(len(result['values']), 29)
        for args in [('day', '2026-11', '2026-12'), ('month', '2027-01', '2026-11'),
                     ('month', '2025-01', '2027-01')]:
            with self.assertRaises(ValueError):
                query(Session([]), *args)
