"""综述事实边界：不把缺报写成平稳，不混用日期、口径及设备动作。"""
from datetime import date
from unittest import TestCase

from backend.projects.daily_report_25_26.services.daily_brief import comparison
from backend.projects.daily_report_25_26.services.daily_brief_overview import build_brief_overview

DAY = date(2026, 3, 25)


def metric(key, label, value, peer, *, run=0):
    change = comparison(value, peer)
    return {"key": key, "label": label, "value": value, "peer": peer, "comparison": change,
            "trend": {"yoy_run": run, "direction": change["direction"]}}


def dispatch(equipment=(), operations=(), pending=0, day='2026-03-25'):
    return {"overview_evidence": {"date": day, "equipment": list(equipment),
                                  "operations": list(operations), "pending_count": pending}}


def operation(description, time='08:00', plant='北海电厂', day='2026-03-25', ticket=False):
    return {"description": description, "time": time, "plant": plant, "date": day, "is_ticket": ticket}


class OverviewTests(TestCase):
    def overview(self, metrics=(), weather=None, record=None):
        return build_brief_overview(DAY, metrics, weather or {}, record or {})['paragraphs']

    def test_production_combines_same_direction_and_keeps_opposite_generation_separate(self):
        rows = [metric('amount_heat_supply', '供热量', 120, 100),
                metric('amount_power_generation', '发电量', 80, 100),
                metric('consumption_std_coal', '标煤耗量', 110, 100, run=5)]
        result = self.overview(rows, {'value': 3, 'peer': 5})[0]
        self.assertIn('当日日均气温3.0℃，同比减少2.0℃', result['text'])
        self.assertIn('供热量与标煤耗量同比增加，发电量同比减少', result['text'])
        self.assertIn('已连续5日高于同期', result['text'])
        self.assertEqual(set(result['metric_keys']), {r['key'] for r in rows})
        self.assertNotIn('导致', result['text'])
        self.assertNotIn('供热量120', result['text'])

    def test_comparable_and_actual_profit_disagreement_is_described_without_choosing_a_cause(self):
        rows = [metric('eco_comparable_marginal_profit', '可比煤价边际利润', 80, 100),
                metric('eco_marginal_profit', '实际边际利润', 110, 100),
                metric('amount_daily_service_complaints', '省市平台投诉量', 1, 2),
                metric('amount_daily_net_complaints', '净投诉量', 0, 1)]
        result = self.overview(rows)[1]['text']
        self.assertIn('同比减少20.00万元', result)
        self.assertIn('同比增加10.00万元', result)
        self.assertIn('两种利润口径同比方向不同', result)
        self.assertIn('省市平台投诉量与净投诉量同比减少', result)
        self.assertNotIn('改善', result)
        self.assertNotIn('煤价上涨', result)

    def test_missing_and_nonfinite_comparisons_are_not_written_as_zero_or_stable(self):
        rows = [metric('amount_heat_supply', '供热量', None, 10),
                metric('eco_marginal_profit', '实际边际利润', 10, None)]
        rows.append({**metric('amount_power_generation', '发电量', 1, 1), 'value': float('nan')})
        paragraphs = self.overview(rows)
        self.assertEqual(paragraphs[0]['metric_keys'], [])
        self.assertEqual(paragraphs[1]['metric_keys'], [])
        text = ''.join(p['text'] for p in paragraphs)
        for invented in ['受控稳定', '安全平稳', '出力均衡', '同比持平', '机组正常']:
            self.assertNotIn(invented, text)

    def test_zero_weather_and_values_are_real_data(self):
        rows = [metric('amount_heat_supply', '供热量', 0, 0),
                metric('rate_heat_per_10k_m2', '供暖热单耗', 1, 1)]
        result = self.overview(rows, {'value': 0, 'peer': 0})[0]['text']
        self.assertIn('当日日均气温0.0℃，同比持平', result)
        self.assertIn('供热量同比持平', result)
        self.assertIn('供暖热单耗同比持平', result)

    def test_weather_without_peer_is_reported_without_invented_comparison(self):
        result = self.overview(weather={'value': -5, 'peer': None})[0]['text']
        self.assertEqual(result, '当日日均气温-5.0℃。')

    def test_profit_sign_changes_and_flat_profit_are_factual(self):
        for value, peer, expected in [(1, -1, '由亏转盈'), (-1, 1, '由盈转亏'), (0, 0, '同比持平')]:
            with self.subTest(value=value, peer=peer):
                result = self.overview([metric('eco_marginal_profit', '实际边际利润', value, peer)])[1]['text']
                self.assertIn(expected, result)
                self.assertNotIn('方向不同', result)

    def test_dispatch_counts_recorded_equipment_and_quotes_actual_auxiliary_operations(self):
        device = {'key': '北海|#1机', 'kind': '汽机', 'status': '运行'}
        equipment = [device, device.copy(), {'key': '北海|#1炉', 'kind': '汽炉', 'status': '运行'},
                     {'key': '北海|#2炉', 'kind': '汽炉', 'status': '检修'}]
        records = [operation('关闭南北网联络门，南网停运。', '10:15'), operation('#2高减停运。', '14:30')]
        result = self.overview(record=dispatch(equipment, records))[2]
        self.assertIn('运行设备：汽机1台、汽炉1台', result['text'])
        self.assertIn('检修设备：汽炉1台', result['text'])
        self.assertIn('北海电厂 10:15“关闭南北网联络门，南网停运”', result['text'])
        self.assertIn('#2高减停运', result['text'])
        self.assertEqual(result['operations'], records)
        self.assertNotIn('全集团', result['text'])

    def test_cross_day_events_tickets_and_duplicate_operations_do_not_enter_excerpts(self):
        actual = operation('#1炉并汽。')
        records = [actual, actual.copy(), operation('#2机停机。', day='2026-03-26'),
                   operation('工作票：检修#1炉', ticket=True), operation('')]
        result = self.overview(record=dispatch(operations=records))[2]
        self.assertEqual(result['operations'], [actual])
        self.assertNotIn('#2机', result['text'])
        self.assertNotIn('工作票', result['text'])

    def test_plan_and_negation_in_log_are_not_rewritten_as_completed_operations(self):
        record = operation('计划明日启动#1机，尚未并网。')
        result = self.overview(record=dispatch(operations=[record]))[2]['text']
        self.assertIn('“计划明日启动#1机，尚未并网”', result)
        self.assertNotIn('已并网', result)

    def test_pending_or_conflicting_statuses_do_not_become_running_counts(self):
        scenarios = [dispatch([{'key': '北海|#1机', 'kind': '汽机', 'status': '运行', 'pending': True}], pending=1),
                     dispatch([{'key': '北海|#1机', 'kind': '汽机', 'status': '运行'},
                               {'key': '北海|#1机', 'kind': '汽机', 'status': '停运'}])]
        for record in scenarios:
            result = self.overview(record=record)[2]['text']
            self.assertIn('1项设备状态待核对', result)
            self.assertNotIn('运行设备', result)

    def test_a_different_dispatch_day_is_never_reused_as_current(self):
        result = self.overview(record=dispatch(operations=[operation('#1机并网')], day='2026-03-24'))[2]
        self.assertEqual(result['text'], '当日暂无设备调度记录。')
        self.assertEqual(result['operations'], [])

    def test_excerpts_include_fault_record_and_remain_in_source_order(self):
        records = [operation('开启联络门', '08:00'), operation('首站启动循环泵', '09:00'),
                   operation('#1泵停运切换至#2泵', '10:00'), operation('工业水管漏，正在处理中', '11:00')]
        result = self.overview(record=dispatch(operations=records))[2]
        self.assertEqual([record['time'] for record in result['operations']], ['09:00', '10:00', '11:00'])
        self.assertIn('正在处理中', result['text'])
        self.assertNotIn('已修复', result['text'])

    def test_standby_is_described_as_recorded_not_as_running(self):
        record = dispatch([{'key': '北海|#1机', 'kind': '汽机', 'status': '备用'}])
        result = self.overview(record=record)[2]['text']
        self.assertEqual(result, '调度状态表列示备用设备1台。')

    def test_empty_or_unnamed_status_records_do_not_invent_device_counts(self):
        record = dispatch([{'key': '', 'kind': '汽机', 'status': '运行'}, {'key': '北海|#1机', 'status': None}])
        result = self.overview(record=record)[2]['text']
        self.assertEqual(result, '当日调度日报已记录。')
