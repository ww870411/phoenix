"""真实 PDF 和跨端导入口径回归：全部只读或模拟，不写业务数据库。"""

import copy
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock

from backend.projects.daily_report_25_26.services.dispatch_extractor import (
    extract_pdf_file, UnifiedDispatchExtractor,
)
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report
from backend.projects.daily_report_25_26.services.dispatch_db_service import save_dispatch_reports


def sample(events, status='备用'):
    return {'file_name': '测试.pdf', 'biz_date': '2026-10-30',
            'boiler_turbine_status': [{'unit_or_plant': '北方热电', 'standard_name': '#1汽机',
                                     'facility_type': '汽机', 'status': status}],
            'operations_and_tickets': [dict(responsible_org='北方电厂', **e) for e in events]}


class DispatchReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pdf_path = Path(__file__).resolve().parents[4] / 'configs' / '2026年10月30日生产信息.pdf'
        cls.report = extract_pdf_file(str(cls.pdf_path))

    def test_real_pdf_weather(self):
        w = self.report['weather']
        self.assertEqual(w['forecast_date'], '2026-10-31')
        self.assertEqual((w['temp_min'], w['temp_max']), (4, 14))
        self.assertEqual(w['weather_desc'], '多云转阴天有阵雨或雷阵雨')
        self.assertEqual(w['humidity'], '30%~90%')
        self.assertEqual(w['wind'], '东南风4~5级转偏南风5~6级阵风7级')
        self.assertIn('相对 湿度', w['raw_text'])

    def test_real_pdf_starting_and_auxiliary(self):
        facilities = self.report['boiler_turbine_status']
        self.assertEqual(len(facilities), 41)
        starting = [f for f in facilities if f['status'] == '启动中']
        self.assertEqual(len(starting), 2)
        self.assertTrue(all('启动中' in f['table_text'] for f in starting))
        turbines = [f for f in facilities if f['unit_or_plant'] == '香海电厂' and f['facility_type'] == '汽机']
        self.assertTrue(all(not f['main_events'] for f in turbines))

    def test_real_pdf_conflicts_remain_unresolved(self):
        conflicts = self.report['status_conflicts']
        self.assertEqual({c['device'] for c in conflicts}, {'北方热电|#1汽机', '北方热电|#2汽炉'})
        self.assertTrue(all(c['resolution'] is None for c in conflicts))
        self.assertTrue(all(c['resolution'] is None for c in reconcile_report(self.report)['status_conflicts']))

    def test_explicit_choices_survive_roundtrip(self):
        original = copy.deepcopy(self.report)
        for source, expected in [('table', '备用'), ('events', '运行')]:
            choices = {c['id']: source for c in original['status_conflicts']}
            result = reconcile_report(original, choices)
            result = reconcile_report(result)
            for c in result['status_conflicts']:
                self.assertEqual(c['resolution'], source)
                f = next(f for f in result['boiler_turbine_status'] if f['unit_or_plant']+'|'+f['standard_name'] == c['device'])
                self.assertEqual(f['status'], expected)
                self.assertEqual(f['table_status'], '备用')
                self.assertIn('status_decision_at', f)
                name = f['raw_name'] if f['facility_type'] == '汽机' else f['standard_name']
                self.assertEqual(result['eqp_status_json']['flat_map'][f['unit_or_plant']+'_'+name], expected)
            self.assertEqual(result['boiler_turbine_status'], result['eqp_status_json']['facilities'])
        self.assertEqual(original, self.report)

    def test_chronological_last_action_not_first_array_item(self):
        result = reconcile_report(sample([
            {'time': '16:00', 'raw_description': '#1机停机'},
            {'time': '9:00', 'raw_description': '#1机与系统并列'},
        ]))
        self.assertEqual(result['status_conflicts'][0]['event_status'], '停运')

    def test_auxiliary_negative_plan_and_ticket_do_not_change_main_unit(self):
        for desc, extra in [('#1机低真空系统泵投运', {}), ('计划#1机启动', {}),
                            ('#1机未启动', {}), ('#1机启动失败', {}), ('#1机启动试验', {}),
                            ('#1机启动', {'is_ticket': True})]:
            r = reconcile_report(sample([{'time': '9:00', 'raw_description': desc, **extra}]))
            self.assertFalse(r['status_conflicts'])
            self.assertFalse(r['boiler_turbine_status'][0]['main_events'])

    def test_missing_or_invalid_time_never_infers_final_status(self):
        for time in ['', '26:00', '9:99', '10/30 9:00']:
            r = reconcile_report(sample([{'time': time, 'raw_description': '#1机启动'}]))
            self.assertFalse(r['status_conflicts'])
            self.assertTrue(r['extraction_warnings'])

    def test_cross_plant_does_not_match(self):
        r = sample([{'time': '9:00', 'raw_description': '#1机启动'}])
        r['operations_and_tickets'][0]['responsible_org'] = '香海电厂'
        self.assertFalse(reconcile_report(r)['boiler_turbine_status'][0]['main_events'])

    def test_legacy_empty_json_store_is_supported(self):
        for old in (None, [], {}):
            r = sample([])
            r['eqp_status_json'] = old
            result = reconcile_report(r)
            self.assertEqual(result['eqp_status_json']['flat_map']['北方热电_#1机'], '备用')
            self.assertEqual(result['eqp_status_json']['matrix']['北方热电']['炉']['运行'], [])

    def test_ambiguous_boiler_does_not_guess(self):
        r = {'boiler_turbine_status': [
            {'unit_or_plant': '北海热电联产', 'standard_name': '#1汽炉', 'facility_type': '锅炉', 'boiler_type': '汽炉', 'status': '备用'},
            {'unit_or_plant': '北海水炉', 'standard_name': '#1水炉', 'facility_type': '锅炉', 'boiler_type': '水炉', 'status': '备用'}],
            'operations_and_tickets': [{'responsible_org': '北海电厂', 'time': '9:00', 'raw_description': '#1炉点火'}]}
        self.assertTrue(reconcile_report(r)['extraction_warnings'])
        self.assertFalse(reconcile_report(r)['status_conflicts'])

    def test_starting_note_only_applies_to_named_boiler(self):
        extractor = UnifiedDispatchExtractor([], [[['分类', '运行', '备用', '检修'],
            ['香海', '#1炉（启动中）、#2炉', '', '']]])
        f = extractor.extract_boiler_turbine_status()['facilities']
        self.assertEqual([x['status'] for x in f], ['启动中', '运行'])

    def test_service_blocks_unconfirmed_import_without_database_access(self):
        with patch('backend.projects.daily_report_25_26.services.dispatch_db_service.ensure_dispatch_table_exists') as ensure:
            result = save_dispatch_reports([self.report])
            self.assertTrue(result['has_status_conflict'])
            ensure.assert_not_called()

    def test_api_requires_choice_and_passes_resolved_status(self):
        from backend.projects.daily_report_25_26.api.dispatch_info import save_dispatch_data
        target = 'backend.projects.daily_report_25_26.api.dispatch_info.save_dispatch_reports'
        with patch(target, return_value={'ok': True}) as save:
            self.assertTrue(save_dispatch_data({'reports': [self.report]})['has_status_conflict'])
            save.assert_not_called()
            choices = {c['id']: 'events' for c in self.report['status_conflicts']}
            self.assertTrue(save_dispatch_data({'reports': [self.report], 'status_resolutions': choices, 'overwrite': True})['ok'])
            saved = save.call_args.args[0][0]
            self.assertTrue(all(c['resolution'] == 'events' for c in saved['status_conflicts']))
            self.assertTrue(save.call_args.kwargs['overwrite'])

    def test_confirmed_report_persists_original_and_effective_states(self):
        choices = {c['id']: 'events' for c in self.report['status_conflicts']}
        report = reconcile_report(self.report, choices)
        prefix = 'backend.projects.daily_report_25_26.services.dispatch_db_service.'
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)
        with patch(prefix+'ensure_dispatch_table_exists'), patch(prefix+'check_existing_dates', return_value=[]), patch(prefix+'get_db_connection', return_value=conn):
            result = save_dispatch_reports([report])
        self.assertTrue(result['ok'])
        from backend.projects.daily_report_25_26.services.dispatch_db_service import PHYSICAL_COLUMNS
        values = cursor.execute.call_args.args[1]
        facilities = values[PHYSICAL_COLUMNS.index('boiler_turbine_status')].adapted
        for fac in facilities:
            if fac.get('status_confirmed'):
                self.assertEqual((fac['table_status'], fac['status']), ('备用', '运行'))
        conn.commit.assert_called_once()

    def test_conflicting_actions_at_same_time_are_not_arbitrarily_ordered(self):
        r = reconcile_report(sample([{'time': '9:00', 'raw_description': '#1机启动'},
                                     {'time': '9:00', 'raw_description': '#1机停机'}]))
        self.assertFalse(r['status_conflicts'])
        self.assertTrue(r['extraction_warnings'])


if __name__ == '__main__':
    unittest.main()
