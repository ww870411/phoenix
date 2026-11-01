"""简报事实规则、缺报保护、发布日期及权限回归；不写业务库。"""
import sqlite3
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.projects.daily_report_25_26.api.daily_brief import router
from backend.projects.daily_report_25_26.services.daily_brief import (
    BriefEvidence, GROUP_COMPANIES, METRICS, comparison, describe_change, number,
    trend_summary, build_daily_brief, _optional, read_spot, read_dispatch, read_inventory, _temperature, _plans,
)
from backend.services.auth_manager import get_current_session
from backend.services.workflow_status import WorkflowStatusManager, WorkflowSnapshot, PublishState

SERVICE = 'backend.projects.daily_report_25_26.services.daily_brief'
API = 'backend.projects.daily_report_25_26.api.daily_brief'


def points(values, peers=None):
    anchor = date(2026, 3, 19)
    return [{'date': (anchor + timedelta(days=i)).isoformat(), 'value': value,
             'peer': (peers or [10] * len(values))[i]} for i, value in enumerate(values)]


class BriefFactsTests(TestCase):
    def test_missing_and_nonfinite_are_not_zero(self):
        for value in [None, 'bad', float('nan'), float('inf')]:
            self.assertIsNone(number(value))
        self.assertEqual(number(0), 0)
        self.assertIsNone(comparison(None, 10)['delta'])

    def test_zero_negative_and_sign_crossing_do_not_invent_percent(self):
        for current, peer in [(4, 0), (-2, -4), (2, -4), (-4, 2), (1, .00001)]:
            self.assertIsNone(comparison(current, peer)['percent'])
        self.assertEqual(comparison(0, 4)['percent'], -100)
        self.assertIn('由亏转盈', describe_change('利润', 2, -4, '万元', 2))
        self.assertIn('由盈转亏', describe_change('利润', -2, 4, '万元', 2))
        self.assertIn('亏损额收窄', describe_change('利润', -2, -4, '万元', 2))

    def test_single_day_never_becomes_persistent_headline(self):
        result = trend_summary(points([10, 10, 10, 10, 10, 10, 100]), '煤耗', '吨', 2)
        self.assertEqual(result['yoy_run'], 1)
        self.assertEqual(result['text'], '')

    def test_persistent_yoy_and_opposite_recent_direction_can_coexist(self):
        result = trend_summary(points([30, 29, 28, 27, 26, 25, 24]), '煤耗', '吨', 2)
        self.assertEqual(result['yoy_run'], 7)
        self.assertIn('高于各自同期', result['text'])
        self.assertIn('日间比较减少', result['text'])
        self.assertNotIn('改善', result['text'])

    def test_gap_interrupts_run_and_suppresses_full_window_average(self):
        result = trend_summary(points([30, 29, 28, 27, None, 25, 24]), '煤耗', '吨', 2)
        self.assertEqual(result['yoy_run'], 2)
        self.assertEqual(result['comparable_days'], 6)
        self.assertIsNone(result['current_average'])

    def test_subprecision_noise_is_not_trend(self):
        result = trend_summary(points([10.0001] * 7), '煤耗', '吨', 2)
        self.assertEqual(result['yoy_run'], 0)

    def test_missing_peer_breaks_yoy_even_with_complete_current(self):
        result = trend_summary(points([20] * 7, [10, 10, 10, 10, 10, None, 10]), '煤耗', '吨', 2)
        self.assertEqual(result['yoy_run'], 1)
        self.assertIsNone(result['peer_average'])


class EvidenceTests(TestCase):
    day = date(2026, 3, 25)

    def evidence(self, raw=(), expected=(), constants=()):
        return BriefEvidence(raw, expected, constants)

    def test_explicit_zero_is_reported_and_null_is_missing(self):
        expected = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'period': '25-26'}]
        row = {'company': 'BeiHai', 'item': 'consumption_std_coal', 'date': self.day, 'value': 0}
        self.assertEqual(self.evidence([row], expected).check('BeiHai', 'consumption_std_coal', self.day), [])
        self.assertTrue(self.evidence([], expected).check('BeiHai', 'consumption_std_coal', self.day))

    def test_rollup_requires_applicable_members_but_not_noncoal_institute(self):
        expected = [{'company': c, 'item': 'consumption_std_coal', 'period': '25-26'} for c in ['BeiHai', 'XiangHai']]
        rows = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'date': self.day, 'value': 0}]
        missing = self.evidence(rows, expected).check('Group', 'consumption_std_coal', self.day)
        self.assertTrue(any('香海' in line for line in missing))
        self.assertFalse(any('研究院' in line for line in missing))

    def test_nonapplicable_auxiliary_from_other_season_is_not_missing(self):
        expected = [{'company': 'BeiHai', 'item': 'consumption_acid', 'period': '24-25'},
                    {'company': 'BeiHai', 'item': 'consumption_std_coal', 'period': '25-26'}]
        rows = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'date': self.day, 'value': 0}]
        self.assertEqual(self.evidence(rows, expected).check('BeiHai', 'eco_marginal_profit', self.day), [])

    def test_positive_quantity_without_price_is_marked(self):
        expected = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'period': '25-26'}]
        rows = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'date': self.day, 'value': 10}]
        missing = self.evidence(rows, expected).check('BeiHai', 'eco_comparable_marginal_profit', self.day)
        self.assertTrue(any('price_std_coal_comparable' in line for line in missing))

    def test_heat_source_does_not_require_retail_area_but_retail_company_does(self):
        expected = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'period': '25-26'}]
        rows = [{'company': 'BeiHai', 'item': 'consumption_std_coal', 'date': self.day, 'value': 10}]
        self.assertEqual(self.evidence(rows, expected).check('BeiHai', 'rate_std_coal_per_heat', self.day), [])
        self.assertTrue(any('供暖面积' in item for item in self.evidence().check('GongRe', 'rate_heat_per_10k_m2', self.day)))

    def test_special_station_heat_checks_the_two_actual_operands(self):
        expected = [{'company': 'JinZhou', 'item': key, 'period': '25-26'} for key in ['amount_heat_supply', 'amount_hot_water_sales']]
        rows = [{'company': 'JinZhou', 'item': 'amount_heat_supply', 'date': self.day, 'value': 10}]
        missing = self.evidence(rows, expected).check('JinZhou', 'consumption_station_heat', self.day)
        self.assertTrue(any('amount_hot_water_sales' in line for line in missing))

    def test_whole_company_missing_never_gets_manufactured_profit(self):
        self.assertFalse(self.evidence().has_profit_source('Group', self.day))
        rows = [{'company': c, 'item': 'consumption_std_coal', 'date': self.day, 'value': 0} for c in GROUP_COMPANIES]
        self.assertTrue(self.evidence(rows).has_profit_source('Group', self.day))
        self.assertFalse(self.evidence(rows[:-1]).has_profit_source('Group', self.day))


class PublicationTests(TestCase):
    def test_dates_are_sorted_deduplicated_project_scoped_and_readonly(self):
        manager = WorkflowStatusManager()
        manager._ensure_loaded_locked = MagicMock()
        manager._persist_locked = MagicMock()
        manager._storage = {
            ('daily_report_25_26', datetime(2026, 3, 24)): WorkflowSnapshot(publish=PublishState(status='published')),
            ('daily_report_25_26', datetime(2026, 3, 25)): WorkflowSnapshot(publish=PublishState(status='published')),
            ('daily_report_25_26', datetime(2026, 3, 26)): WorkflowSnapshot(),
            ('other', datetime(2026, 3, 27)): WorkflowSnapshot(publish=PublishState(status='published')),
        }
        self.assertEqual(manager.list_published_dates('daily_report_25_26'), ['2026-03-25', '2026-03-24'])
        manager._persist_locked.assert_not_called()


class BriefAssemblyTests(TestCase):
    def test_profit_follows_dashboard_but_missing_physical_quantity_never_becomes_zero(self):
        """整条装配链验证经确认的利润例外、同期缺项、主体层级和查询截止日。"""
        anchor = date(2026, 3, 25)
        days = [anchor - timedelta(days=i) for i in range(6, -1, -1)]
        peers = [d.replace(year=2025) for d in days]
        raw = [{'company': c, 'item': 'consumption_std_coal', 'date': d, 'value': 1}
               for c in GROUP_COMPANIES for d in days + peers]
        # 当日北海煤耗缺报，但售电仍有申报：利润可沿用看板，煤耗不能补零。
        raw = [r for r in raw if not (r['company'] == 'BeiHai' and r['date'] == anchor)]
        raw.append({'company': 'BeiHai', 'item': 'amount_power_sales', 'date': anchor, 'value': 1})
        session = MagicMock()
        def execute(statement, params=None):
            query = str(statement)
            if 'GROUP BY company, item, date' in query:
                values = raw
            elif 'SELECT DISTINCT company, item' in query:
                values = [{'company': c, 'item': 'consumption_std_coal', 'period': params['period']} for c in GROUP_COMPANIES]
                self.assertLessEqual(params['last'], anchor)
            elif 'FROM constant_data' in query:
                values = []
            else:
                self.fail(f'非预期的主流程查询：{query}')
            result = MagicMock()
            result.mappings.return_value.all.return_value = values
            return result
        session.execute.side_effect = execute
        engine = MagicMock()
        engine.compute_all_metrics.return_value = [
            {'company': c, 'item': key, 'value_biz_date': 100, 'value_peer_date': 90}
            for c in ['Group', 'ZhuChengQu'] + GROUP_COMPANIES for key, *_ in METRICS
        ]
        with patch(f'{SERVICE}.DailyDashboardEngine', return_value=engine), \
             patch(f'{SERVICE}._optional', side_effect=lambda db, title, reader: {'title': title, 'status': 'missing'}):
            result = build_daily_brief(session, anchor)
        metrics = {m['key']: m for m in result['group']['metrics']}
        self.assertEqual(metrics['eco_comparable_marginal_profit']['value'], 100)
        self.assertTrue(metrics['eco_comparable_marginal_profit']['missing_current'])
        self.assertNotIn('calculation_note', metrics['eco_comparable_marginal_profit'])
        self.assertIsNone(metrics['consumption_std_coal']['value'])
        self.assertEqual(metrics['consumption_std_coal']['trend']['yoy_run'], 0)
        self.assertEqual([item['key'] for item in result['highlights']], [
            'eco_comparable_marginal_profit', 'consumption_std_coal', 'consumption_station_heat',
            'amount_daily_service_complaints', 'amount_daily_net_complaints',
        ])
        self.assertEqual(result['highlights'][1]['text'], '标煤耗量：—。')
        self.assertEqual(result['highlights'][1]['detail'], '')
        self.assertIn('，已连续7日高于同期。', result['highlights'][0]['text'])
        self.assertEqual(result['highlights'][0]['text'].count('可比煤价边际利润'), 1)
        self.assertEqual(result['highlights'][0]['detail'], '')
        self.assertEqual([s['company'] for s in result['main_city_units']], ['BeiHai', 'XiangHai', 'GongRe'])
        self.assertNotIn('BeiHai', [s['company'] for s in result['other_units']])
        self.assertEqual([call.args[0] for call in engine.compute_all_metrics.call_args_list], days)
        session.commit.assert_not_called()


class BriefApiTests(TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        self.app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        self.data_dates = patch(f'{API}.list_data_dates', return_value=['2026-10-29', '2026-03-26', '2026-03-25', '2026-03-24'])
        self.data_dates.start()
        self.addCleanup(self.data_dates.stop)

    def test_non_global_admin_is_rejected_before_reading_dates(self):
        for role in ['admin', 'unit_admin', 'global_admin', 'Global_admin_extra']:
            self.app.dependency_overrides[get_current_session] = lambda role=role: SimpleNamespace(group=role)
            with patch(f'{API}.workflow_status_manager.list_published_dates') as dates:
                self.assertEqual(self.client.get('/daily-brief').status_code, 403)
                dates.assert_not_called()

    def test_anonymous_is_not_allowed(self):
        self.app.dependency_overrides.clear()
        self.assertIn(self.client.get('/daily-brief').status_code, (401, 403))

    def test_defaults_to_latest_published_not_latest_raw(self):
        with patch(f'{API}.workflow_status_manager.list_published_dates', return_value=['2026-03-25', '2026-03-24']), \
             patch(f'{API}.SessionLocal') as factory, patch(f'{API}.build_daily_brief', return_value={'date': '2026-03-25'}) as build:
            response = self.client.get('/daily-brief')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(build.call_args.args[1], date(2026, 3, 25))
            self.assertEqual(response.json()['latest_published_date'], '2026-03-25')
            self.assertIn('2026-10-29', response.json()['available_dates'])

    def test_historical_and_unpublished_data_dates_are_selectable(self):
        with patch(f'{API}.workflow_status_manager.list_published_dates', return_value=['2026-03-25', '2026-03-24']), \
             patch(f'{API}.SessionLocal'), patch(f'{API}.build_daily_brief', return_value={'date': '2026-03-24'}) as build:
            self.assertEqual(self.client.get('/daily-brief?show_date=2026-03-24').status_code, 200)
            self.assertEqual(build.call_args.args[1], date(2026, 3, 24))
            self.assertEqual(self.client.get('/daily-brief?show_date=2026-03-26').status_code, 200)
            self.assertEqual(build.call_args.args[1], date(2026, 3, 26))
            self.assertFalse(self.client.get('/daily-brief?show_date=2026-10-29').json()['is_published'])
            build.reset_mock()
            self.assertEqual(self.client.get('/daily-brief?show_date=2026-03-27').status_code, 422)
            build.assert_not_called()
            self.assertEqual(self.client.get('/daily-brief?show_date=invalid').status_code, 422)

    def test_no_data_or_publication_returns_empty_without_building(self):
        with patch(f'{API}.workflow_status_manager.list_published_dates', return_value=[]), patch(f'{API}.SessionLocal'), \
             patch(f'{API}.list_data_dates', return_value=[]), patch(f'{API}.build_daily_brief') as build:
            response = self.client.get('/daily-brief')
            self.assertIsNone(response.json()['date'])
            self.assertEqual(response.json()['available_dates'], [])
            build.assert_not_called()

    def test_no_publication_defaults_to_latest_data_date(self):
        with patch(f'{API}.workflow_status_manager.list_published_dates', return_value=[]), patch(f'{API}.SessionLocal'), \
             patch(f'{API}.build_daily_brief', return_value={'date': '2026-10-29'}) as build:
            response = self.client.get('/daily-brief')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(build.call_args.args[1], date(2026, 10, 29))
            self.assertIsNone(response.json()['latest_published_date'])


class SupplementTests(TestCase):
    def test_missing_data_does_not_claim_stability(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = []
        session.execute.return_value.mappings.return_value.first.return_value = None
        for reader in [read_spot, read_dispatch, read_inventory]:
            result = reader(session, date(2026, 3, 25))
            self.assertEqual(result['status'], 'missing')
            self.assertEqual(result['facts'], [])

    def test_failed_optional_table_does_not_abort_other_sections(self):
        session = MagicMock()
        def broken():
            raise RuntimeError('模拟可选表不可用')
        with self.assertLogs(SERVICE, level='WARNING'):
            result = _optional(session, '库存', broken)
        self.assertEqual(result['status'], 'unavailable')
        self.assertNotIn('平稳', result['summary'])

    def test_partial_spot_prices_are_labeled_and_not_compared_to_yesterday(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'trade_date': date(2026, 3, 25), 'points': 95, 'da_points': 95, 'rt_points': 94,
             'da': 100, 'rt': 200, 'low': -5, 'high': 300, 'negative': 1},
        ]
        result = read_spot(session, date(2026, 3, 25))
        self.assertEqual(result['status'], 'partial')
        self.assertIn('95/96', result['summary'])
        self.assertFalse(any('较昨日' in fact for fact in result['facts']))

    def test_inventory_null_does_not_become_zero(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'storage_type': 'coal_at_plant', 'value': None},
        ]
        result = read_inventory(session, date(2026, 3, 25))
        self.assertEqual(result['status'], 'missing')
        self.assertEqual(result['facts'], ['全口径总库存：—', '在途库存：—', '港口库存：—', '厂内库存：—'])

    def test_inventory_blank_coal_type_does_not_hide_existing_sum(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'storage_type': 'coal_at_plant', 'value': 8136.28},
            {'storage_type': 'coal_at_port', 'value': None},
        ]
        result = read_inventory(session, date(2026, 3, 25))
        self.assertEqual(result['facts'][0], '全口径总库存：8,136.28 吨')
        self.assertEqual(result['facts'][2], '港口库存：—')
        self.assertEqual(result['facts'][3], '厂内库存：8,136.28 吨')
        self.assertEqual(result['status'], 'ready')

    def test_explicit_zero_inventory_is_displayed_as_zero(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'storage_type': 'coal_at_plant', 'value': 0},
        ]
        result = read_inventory(session, date(2026, 3, 25))
        self.assertEqual(result['facts'][0], '全口径总库存：0.00 吨')
        self.assertEqual(result['facts'][3], '厂内库存：0.00 吨')
        self.assertEqual(result['status'], 'ready')

    def test_inventory_total_uses_three_storage_categories_and_only_leaf_scope(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'storage_type': 'coal_at_plant', 'value': 100},
            {'storage_type': 'coal_in_transit', 'value': 20},
            {'storage_type': 'coal_at_port', 'value': 30},
        ]
        result = read_inventory(session, date(2026, 3, 25))
        self.assertEqual(result['facts'], ['全口径总库存：150.00 吨', '在途库存：20.00 吨', '港口库存：30.00 吨', '厂内库存：100.00 吨'])
        params = session.execute.call_args.args[1]
        self.assertEqual(set(params['companies']), set(GROUP_COMPANIES))
        self.assertNotIn('Group', params['companies'])
        self.assertNotIn('ZhuChengQu', params['companies'])

    def test_negative_spot_points_count_only_real_time_prices(self):
        """执行实际聚合SQL，验证日前负价、实时零值和空值都不进入实时负价统计。"""
        with sqlite3.connect(':memory:') as connection:
            connection.execute('CREATE TABLE spot_electricity_15min_data (trade_date TEXT, point_index INTEGER, day_ahead_price REAL, real_time_price REAL)')
            connection.executemany('INSERT INTO spot_electricity_15min_data VALUES (?, ?, ?, ?)', [
                ('2026-03-25', 1, -100, 10), ('2026-03-25', 2, 10, -20),
                ('2026-03-25', 3, -10, -30), ('2026-03-25', 4, -10, 0), ('2026-03-25', 5, -10, None),
            ])
            session = MagicMock()
            def execute(statement, params):
                cursor = connection.execute(str(statement), {key: value.isoformat() for key, value in params.items()})
                records = [dict(zip([column[0] for column in cursor.description], values)) for values in cursor.fetchall()]
                for record in records:
                    record['trade_date'] = date.fromisoformat(record['trade_date'])
                result = MagicMock()
                result.mappings.return_value.all.return_value = records
                return result
            session.execute.side_effect = execute
            result = read_spot(session, date(2026, 3, 25))
        self.assertIn('实时负价时点 2 个', result['facts'])

    def test_complete_spot_prices_support_previous_day_difference(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.all.return_value = [
            {'trade_date': date(2026, 3, day), 'points': 96, 'da_points': 96, 'rt_points': 96,
             'da': 100, 'rt': price, 'low': -5, 'high': 300, 'negative': 1}
            for day, price in [(25, 90), (24, 100)]
        ]
        result = read_spot(session, date(2026, 3, 25))
        self.assertEqual(result['status'], 'ready')
        self.assertIn('较昨日减少 10.00', result['facts'][-1])

    def test_dispatch_cross_day_records_and_unresolved_conflicts_are_not_hidden(self):
        session = MagicMock()
        session.execute.return_value.mappings.return_value.first.return_value = {'biz_date': date(2026, 3, 25), 'file_name': '调度原始报告.docx'}
        report = {'operations_and_tickets': [
            {'event_date': '2026-03-25', 'event_clock': '08:00', 'responsible_org': '北海', 'raw_description': '1号炉点火'},
            {'event_date': '2026-03-26', 'event_clock': '01:00', 'raw_description': '1号炉并网'},
        ], 'status_conflicts': [{'resolution': None}]}
        with patch('backend.projects.daily_report_25_26.services.dispatch_reconciliation.reconcile_report', return_value=report):
            result = read_dispatch(session, date(2026, 3, 25))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['facts']), 1)
        self.assertIn('跨日', result['summary'])
        self.assertIn('待核对', result['summary'])
        self.assertIn('北海', result['facts'][0])

    def test_temperature_missing_peer_keeps_current_and_does_not_claim_cause(self):
        engine = MagicMock()
        engine.get_temperature_daily_avg_map.side_effect = [{'2026-03-25': 5}, {}]
        result = _temperature(engine, date(2026, 3, 25), date(2025, 3, 25))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['value'], 5)
        self.assertIsNone(result['peer'])
        self.assertIn('同期 —', result['summary'])

    def test_monthly_and_daily_plans_remain_distinct_and_preserve_unavailable_reason(self):
        session = MagicMock()
        with patch('backend.projects.daily_report_25_26.services.monthly_coal_progress.get_monthly_coal_progress', return_value={'items': [{'company': 'Group', 'plan_value': 3000}]}), \
             patch('backend.services.dynamic_decomposition_service.get_coal_plan_comparison', return_value={'daily': {'plan_value': None}, 'reason': '历史日期不展示动态计划'}):
            result = _plans(session, date(2026, 3, 25))
        self.assertIsNone(result['daily']['plan_value'])
        self.assertEqual(result['monthly']['items'][0]['plan_value'], 3000)
        self.assertIn('历史日期', result['daily_note'])
