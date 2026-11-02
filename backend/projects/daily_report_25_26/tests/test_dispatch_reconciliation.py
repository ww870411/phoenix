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
            self.assertIsNone(r['status_conflicts'][0]['event_status'])
            self.assertIsNone(r['status_conflicts'][0]['resolution'])
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
        conflicts = reconcile_report(r)['status_conflicts']
        self.assertEqual(len(conflicts), 2)
        self.assertTrue(all(c['event_status'] is None and c['reason'] for c in conflicts))

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
        self.assertIsNone(r['status_conflicts'][0]['event_status'])
        self.assertIsNone(r['status_conflicts'][0]['resolution'])
        self.assertTrue(r['extraction_warnings'])

    def test_normalized_operations_keep_two_rows_and_original(self):
        from backend.projects.daily_report_25_26.services.dispatch_operations import split_operations
        text = '10:30#4汽炉并汽,17:30 粉仓烧空停炉。'
        events = split_operations([{'raw_description': text, 'responsible_org': '北海电厂'}])
        self.assertEqual([(e['time'], e['raw_description']) for e in events], [('10:30', '#4汽炉并汽'), ('17:30', '#4汽炉停炉')])
        self.assertTrue(events[1]['subject_inferred'])
        self.assertTrue(all(e['source_description'] == text for e in events))
        self.assertEqual(split_operations(events), events)

    def test_auxiliary_subject_plan_and_trial_are_not_inherited(self):
        for suffix in ('给煤机启动', '启动备用电源', '17:30 停机未执行', '启动 失败', '计划停机'):
            r = reconcile_report(sample([{'time': '9:00', 'raw_description': '#1机并列,' + suffix}]))
            self.assertEqual(len(r['boiler_turbine_status'][0]['main_events']), 1, suffix)
        r = reconcile_report(sample([{'time': '9:00', 'raw_description': '计划进行操作，#1机并列'}]))
        self.assertFalse(r['boiler_turbine_status'][0]['main_events'])
        self.assertEqual(reconcile_report(r)['boiler_turbine_status'][0]['main_events'], [])

    def test_multiple_times_without_comma_use_last_actual_action(self):
        r = reconcile_report(sample([{'time': '9:00', 'raw_description': '#1机并列,17:30 停机后18:00并列'}]))
        self.assertEqual([(e['time'], e['action']) for e in r['boiler_turbine_status'][0]['main_events']], [('9:00', '并列'), ('17:30', '停机'), ('18:00', '并列')])
        self.assertEqual(r['status_conflicts'][0]['event_status'], '运行')

    def test_manual_state_and_changed_evidence_require_reconfirmation(self):
        r = reconcile_report(sample([{'time': '9:00', 'raw_description': '#1机并列'}]))
        key = r['status_conflicts'][0]['id']
        manual = reconcile_report(r, {key: 'status:备用'})
        self.assertEqual(reconcile_report(manual)['status_conflicts'][0]['resolution'], 'status:备用')
        confirmed = reconcile_report(r, {key: 'events'})
        confirmed['operations_and_tickets'].append({'time': '18:00', 'raw_description': '#1机停机', 'responsible_org': '北方电厂'})
        changed = reconcile_report(confirmed)
        self.assertIsNone(changed['status_conflicts'][0]['resolution'])
        self.assertEqual(changed['boiler_turbine_status'][0]['status'], '备用')

    def test_ambiguous_time_can_only_use_table_or_manual_state(self):
        r = reconcile_report(sample([{'time': '', 'raw_description': '#1机并列'}]))
        key = r['status_conflicts'][0]['id']
        self.assertIsNone(reconcile_report(r, {key: 'events'})['status_conflicts'][0]['resolution'])
        self.assertEqual(reconcile_report(r, {key: 'status:检修'})['boiler_turbine_status'][0]['status'], '检修')

    def test_history_resolution_only_updates_status_fields_and_rejects_stale_evidence(self):
        from backend.projects.daily_report_25_26.services.dispatch_db_service import update_dispatch_statuses
        report = reconcile_report(sample([{'time': '9:00', 'raw_description': '#1机并列'}]))
        conflict = report['status_conflicts'][0]
        prefix = 'backend.projects.daily_report_25_26.services.dispatch_db_service.'
        for evidence, expected in [({conflict['id']: '过期依据'}, False), ({conflict['id']: conflict['evidence']}, True)]:
            conn = MagicMock()
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = report
            with patch(prefix + 'get_db_connection', return_value=conn):
                result = update_dispatch_statuses('2026-10-30', {conflict['id']: 'events'}, evidence=evidence)
            self.assertEqual(result['ok'], expected)
            if expected:
                sql, values = cursor.execute.call_args.args
                self.assertNotIn('prod_', sql)
                self.assertEqual(values[0].adapted[0]['status'], '运行')
                self.assertEqual(values[1].adapted['facilities'], values[0].adapted)
                self.assertEqual(values[2].adapted, values[3].adapted)
                conn.commit.assert_called_once()
            else:
                self.assertEqual(cursor.execute.call_count, 1)
                conn.commit.assert_not_called()
            conn.close.assert_called_once()

    def test_history_resolution_api_validates_date_and_choices(self):
        from backend.projects.daily_report_25_26.api.dispatch_info import resolve_dispatch_status
        from fastapi import HTTPException
        admin_session = MagicMock(group='Global_admin')
        for payload in ({'biz_date': '错误', 'status_resolutions': {'a': 'table'}},
                        {'biz_date': '2026-03-23', 'status_resolutions': {'a': 'status:未知'}}):
            with self.assertRaises(HTTPException):
                resolve_dispatch_status(payload, session=admin_session)

        # 验证仅限 Global_admin 操作
        user_session = MagicMock(group='normal_user')
        with self.assertRaises(HTTPException) as ctx:
            resolve_dispatch_status({'biz_date': '2026-03-23', 'status_resolutions': {'a': 'table'}}, session=user_session)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn('Global_admin', ctx.exception.detail)

    def test_consecutive_actions_in_compound_sentence(self):
        # 针对复合句中主语省略的连动行为（如“#4汽炉并汽,17:30 粉仓烧空停炉”）
        report = {
            'file_name': '测试.docx', 'biz_date': '2026-03-23',
            'boiler_turbine_status': [{
                'unit_or_plant': '北海热电联产', 'standard_name': '#4汽炉', 'raw_name': '#4炉',
                'facility_type': '锅炉', 'boiler_type': '汽炉', 'status': '备用', 'table_status': '备用'
            }],
            'operations_and_tickets': [{
                'time': '10:30', 'responsible_org': '北海电厂',
                'raw_description': '#4汽炉并汽,17:30 粉仓烧空停炉。'
            }]
        }
        res = reconcile_report(report)
        fac = res['boiler_turbine_status'][0]
        self.assertEqual(len(fac['main_events']), 2)
        self.assertEqual((fac['main_events'][0]['time'], fac['main_events'][0]['action']), ('10:30', '并汽'))
        self.assertEqual((fac['main_events'][1]['time'], fac['main_events'][1]['action']), ('17:30', '停炉'))
        self.assertEqual(fac['main_events'][-1]['status'], '停运')


    def test_reconcile_report_supports_date_object_biz_date(self):
        from datetime import date
        report_str = sample([{'time': '08:00', 'raw_description': '#1汽机启动'}], status='备用')
        report_str['biz_date'] = '2026-10-30'
        res_str = reconcile_report(report_str)

        report_date = copy.deepcopy(report_str)
        report_date['biz_date'] = date(2026, 10, 30)
        res_date = reconcile_report(report_date)

        self.assertEqual(res_str['status_conflicts'][0]['evidence'], res_date['status_conflicts'][0]['evidence'])
        self.assertEqual(res_str['boiler_turbine_status'][0]['main_events'], res_date['boiler_turbine_status'][0]['main_events'])


if __name__ == '__main__':
    unittest.main()
