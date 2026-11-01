"""原文保留、跨日、限定主语承接及旧拆分记录的回归；不写数据库。"""

import unittest
from backend.projects.daily_report_25_26.services.dispatch_operations import split_operations, split_timed_clauses, event_time_fields
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report
from backend.projects.daily_report_25_26.services.dispatch_extractor import UnifiedDispatchExtractor


def operation(time, text, org='北海电厂', **extra):
    return dict(time=time, raw_description=text, responsible_org=org, **extra)


class DispatchOperationTests(unittest.TestCase):
    def test_comments_and_auxiliary_actions_are_not_split_at_punctuation(self):
        for text in ('#2高减投运。首站开始加热提温,东、西网厂内部分暖管。', '香北联络管开始暖管,送汽。', '#1机低真空尖峰加热器投运。'):
            result = split_operations([operation('20:50', text)], '2026-10-31')
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['raw_description'], text)
            self.assertTrue(result[0]['exclude_main_inference'])

    def test_network_restoration_keeps_date_subject_and_reason(self):
        text = '高温水网唐山支线停运,处理漏点,1日1:40恢复。'
        result = split_operations([operation('20:00', text, '供热公司')], '2026-10-31')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['raw_description'], '高温水网唐山支线停运,处理漏点')
        self.assertEqual(result[1]['raw_description'], '高温水网唐山支线恢复')
        self.assertEqual((result[1]['time'], result[1]['event_date'], result[1]['event_clock']), ('1日1:40', '2026-11-01', '01:40'))
        self.assertTrue(all(e['source_description'] == text for e in result))
        self.assertEqual(split_operations(result, '2026-10-31'), result)

    def test_adjacent_legacy_main_operations_inherit_with_trace(self):
        result = split_operations([operation('15:40', '#1机并热网'), operation('15:46', '与系统并列')], '2026-10-31')
        self.assertEqual(result[1]['raw_description'], '#1机并列')
        self.assertTrue(result[1]['subject_inferred'])
        self.assertIn('相邻', result[1]['subject_inference_basis'])
        self.assertEqual(result[1]['source_description'], '与系统并列')

    def test_cross_org_time_gap_auxiliary_or_distinct_source_rows_block_inheritance(self):
        cases = [
            [operation('15:40', '#1机并热网'), operation('15:46', '与系统并列', '香海电厂')],
            [operation('15:40', '#1机并热网'), operation('17:00', '与系统并列')],
            [operation('15:40', '#1机并热网'), operation('15:41', '#2泵投运'), operation('15:46', '与系统并列')],
            [operation('15:40', '#1机并热网', source_group='a'), operation('15:46', '与系统并列', source_group='b')],
        ]
        for events in cases:
            self.assertTrue(split_operations(events, '2026-10-31')[-1]['exclude_main_inference'])

    def test_extractor_and_reconciler_share_time_splitting_without_losing_subject(self):
        text = '#4汽炉并汽,17:30 粉仓烧空停炉。'
        parts = UnifiedDispatchExtractor.split_compound_event('10:30', text)
        source = [operation(time, desc, source_group='row1', source_description=text, source_time='10:30') for time, desc in parts]
        result = split_operations(source, '2026-03-23')
        self.assertEqual([(e['time'], e['raw_description']) for e in result], [('10:30', '#4汽炉并汽'), ('17:30', '#4汽炉停炉')])
        self.assertEqual(split_operations(result, '2026-03-23'), result)

    def test_legacy_fragmented_and_v1_records_rebuild_once(self):
        text = '高温水网唐山支线停运,处理漏点,1日1:40恢复。'
        fragments = [operation(time, desc, '供热公司', source_description=text, exclude_main_inference=True) for time, desc in [('20:00', '高温水网唐山支线停运'), ('20:00', '处理漏点'), ('20:00', '1日'), ('1:40', '恢复')]]
        result = split_operations(fragments, '2026-10-31')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[-1]['event_date'], '2026-11-01')
        text = '#4汽炉并汽,17:30 粉仓烧空停炉。'
        old = [operation('10:30', '#4汽炉并汽', source_description=text, operation_split_version=1), operation('17:30', '#4汽炉停炉', source_description=text, operation_split_version=1)]
        self.assertEqual(len(split_operations(old, '2026-03-23')), 2)

    def test_date_prefixes_month_year_leap_and_invalid_clock(self):
        for text, biz, expected in [('1日3:00', '2026-10-31', '2026-11-01'), ('次日03:00', '2026-12-31', '2027-01-01'), ('1日01:40', '2026-12-31', '2027-01-01'), ('29日1:00', '2028-02-28', '2028-02-29'), ('11月1日1:40', '2026-10-31', '2026-11-01')]:
            self.assertEqual(event_time_fields(text, biz)['event_date'], expected)
        self.assertEqual(event_time_fields('1日26:00', '2026-10-31'), {})
        self.assertEqual(event_time_fields('30日1:00', '2026-02-28'), {})

    def test_tickets_keep_duration_and_body_intact(self):
        text = '签发工作票，工期10/31 20:00至11/1 1:40，抢修管线。'
        result = split_operations([operation('20:00', text, is_ticket=True)], '2026-10-31')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['raw_description'], text)
        self.assertEqual(split_timed_clauses('20:00', text), [('20:00', text)])

    def test_plan_before_clock_stays_with_operation_and_never_becomes_fact(self):
        result = split_operations([operation('', '预计17:30#1机并列')], '2026-10-31')
        self.assertEqual(len(result), 1)
        self.assertIn('预计', result[0]['raw_description'])
        self.assertTrue(result[0]['exclude_main_inference'])

    def test_next_day_main_action_does_not_override_report_day_state(self):
        r = reconcile_report({'biz_date': '2026-10-31', 'boiler_turbine_status': [{'unit_or_plant': '北海热电联产', 'standard_name': '#1汽机', 'facility_type': '汽机', 'status': '备用'}], 'operations_and_tickets': [operation('1日03:00', '#1机并列')]})
        self.assertEqual(r['boiler_turbine_status'][0]['status'], '备用')
        self.assertFalse(r['status_conflicts'])
        self.assertEqual(r['boiler_turbine_status'][0]['main_events'][0]['event_date'], '2026-11-01')

    def test_unbound_main_action_or_invalid_date_emits_review_warning(self):
        result = split_operations([operation('15:46', '与系统并列')], '2026-10-31')
        self.assertTrue(result[0]['parse_warnings'])
        invalid = split_operations([operation('1日26:00', '#1机并列')], '2026-10-31')
        self.assertNotIn('event_date', invalid[0])
        self.assertTrue(invalid[0]['parse_warnings'])


if __name__ == '__main__':
    unittest.main()
