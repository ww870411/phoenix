"""调度 PDF 合并单元格、显式状态、跨行工期及补水口径回归。"""

from pathlib import Path
import unittest

from backend.projects.daily_report_25_26.services.dispatch_extractor import (
    UnifiedDispatchExtractor, extract_single_file,
)
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report


class DispatchPdfLayoutTests(unittest.TestCase):
    def test_unparenthesized_start_note_keeps_original_running_column(self):
        for annotation in ('#3炉启动中',):
            extractor = UnifiedDispatchExtractor([], [
                [['分类', '运行', '备用', '检修'],
                 ['香海', '#3、4机\n#4炉\n' + annotation, '', '']],
            ])
            report = extractor.extract_all()
            facilities = {f['standard_name']: f['status'] for f in report['boiler_turbine_status']}
            self.assertEqual(facilities, {'#3汽机': '运行', '#4汽机': '运行', '#3汽炉': '运行', '#4汽炉': '运行'})
            self.assertIn('#3', report['eqp_status_json']['matrix']['香海电厂']['炉']['运行'])

    def test_network_heat_handles_trailing_merged_cells_blank_and_zero(self):
        extractor = UnifiedDispatchExtractor([], [[
            ['网口热量', '', '', ''], ['高温水', '', '17784', ''],
            ['#1低真空', '', '4512', ''], ['#3低真空', '', '0', ''],
            ['北海南网供汽量（t)', '', '', ''],
            ['香海东西网供汽量（t)', '', '1389', ''], ['香北联络（t)', '', '1214', ''],
        ]])
        report = extractor.extract_all()
        self.assertEqual(report['gw_high_temp_water'], 17784)
        self.assertEqual(report['gw_lv1_heat'], 4512)
        self.assertEqual(report['gw_lv3_heat'], 0)
        self.assertIsNone(report['gw_bh_south_steam'])
        self.assertEqual(report['gw_xh_ew_steam'], 1389)
        self.assertEqual(report['gw_xb_link_steam'], 1214)

    def test_ticket_continuation_and_distinct_water_scope(self):
        extractor = UnifiedDispatchExtractor([], [[
            ['时间', '生产运行情况'], ['', '供热公司：'],
            ['', '签发“高温水管道泄漏抢修”工作票，工期02/11.20:00'],
            ['', '至03/11.08:00。'], ['', '高温水补水量：4147吨'],
            ['9:00', '兴工DN500管开始暖管送汽。'],
        ]])
        report = extractor.extract_all()
        self.assertEqual(len(report['operations_and_tickets']), 2)
        ticket = report['operations_and_tickets'][0]
        self.assertTrue(ticket['is_ticket'])
        self.assertEqual(ticket['time_range'], '02/11.20:00至03/11.08:00')
        self.assertIn('至03/11.08:00', ticket['source_description'])
        self.assertEqual(report['total_water_replenished'], 4147)
        self.assertIsNone(report['water_sup_accum'])
        self.assertIsNone(report['water_sup_bh_s1'])

    def test_high_temp_water_is_not_replaced_with_accumulated_water(self):
        report = UnifiedDispatchExtractor([], [[
            ['时间', '生产运行情况'], ['', '高温水补水量：4147吨'], ['', '累计补水量：50000吨'],
        ]]).extract_all()
        self.assertEqual(report['total_water_replenished'], 4147)
        self.assertEqual(report['water_sup_accum'], 50000)

    def test_accumulated_water_alone_does_not_fill_high_temp_metric(self):
        report = UnifiedDispatchExtractor([], [[
            ['时间', '生产运行情况'], ['', '累计补水量：50000吨'],
        ]]).extract_all()
        self.assertIsNone(report['total_water_replenished'])
        self.assertEqual(report['water_sup_accum'], 50000)

    def test_explicit_next_day_does_not_change_following_unmarked_date(self):
        report = UnifiedDispatchExtractor([], [[
            ['时间', '生产运行情况'], ['', '香海电厂：'],
            ['3日6:10', '#3炉点火。'], ['', '供热公司：'],
            ['8:40', '兴工DN500管开始暖管送汽。'],
        ]], file_name='2026年11月2日生产信息.pdf').extract_all()
        first, second = report['operations_and_tickets']
        self.assertEqual((first['event_date'], first['event_clock']), ('2026-11-03', '06:10'))
        self.assertEqual((second['event_date'], second['event_clock']), ('2026-11-02', '08:40'))

    def test_original_november_2_pdf_when_available(self):
        source = Path(__file__).resolve().parents[4] / 'configs/2026年11月2日生产信息.pdf'
        if not source.exists():
            self.skipTest('原始业务 PDF 未随源码分发；合成布局回归仍执行')
        report = extract_single_file(str(source))
        self.assertEqual(report['biz_date'], '2026-11-02')
        boiler = next(f for f in report['boiler_turbine_status']
                      if f['unit_or_plant'] == '香海电厂' and f['standard_name'] == '#3汽炉')
        self.assertEqual(boiler['status'], '备用')
        self.assertEqual(boiler['table_status'], '运行')
        self.assertEqual(boiler['status_source'], 'date_boundary')
        turbine = next(f for f in report['boiler_turbine_status']
                       if f['unit_or_plant'] == '香海电厂' and f['standard_name'] == '#3汽机')
        self.assertEqual(turbine['status'], '运行')
        self.assertEqual(reconcile_report(report), report)
        self.assertEqual(boiler['main_events'][0]['event_date'], '2026-11-03')
        self.assertEqual(report['gw_lv3_heat'], 1200)
        self.assertEqual(report['total_water_replenished'], 4147)
        self.assertEqual(len(report['operations_and_tickets']), 4)
        events = report['operations_and_tickets']
        self.assertEqual((events[1]['event_date'], events[1]['event_clock']), ('2026-11-03', '06:10'))
        self.assertEqual((events[2]['event_date'], events[2]['event_clock']), ('2026-11-02', '08:40'))
        self.assertEqual(report['prod_main_heat_act'], 27595)

    def test_future_start_does_not_override_current_day_operation_or_manual_choice(self):
        base = dict(biz_date='2026-11-02', file_name='测试.pdf', boiler_turbine_status=[
            dict(unit_or_plant='香海电厂', standard_name='#3汽炉', facility_type='锅炉',
                 boiler_type='汽炉', status='运行', table_text='#4炉 #3炉启动中')],
            operations_and_tickets=[dict(responsible_org='香海电厂', time='3日6:10', raw_description='#3炉点火。')])
        report = reconcile_report(base)
        self.assertEqual(report['boiler_turbine_status'][0]['status'], '备用')
        key = '测试.pdf|2026-11-02|香海电厂|#3汽炉'
        manual = reconcile_report(report, {key: 'status:检修'})
        self.assertEqual(manual['boiler_turbine_status'][0]['status'], '检修')
        base['operations_and_tickets'].insert(0, dict(responsible_org='香海电厂', time='10:00', raw_description='#3炉并汽。'))
        self.assertEqual(reconcile_report(base)['boiler_turbine_status'][0]['status'], '运行')

    def test_ambiguous_device_suffix_infers_boiler_by_topology_and_events(self):
        # 模拟金州热电表格中检修列漏写“炉”字（写成“#2”）的场景
        extractor = UnifiedDispatchExtractor([], [
            [['分类', '运行', '备用', '检修'],
             ['金州', '#1、3机\n#1、3、4炉', '#2机\n#6炉', '#2']],
            [['时间', '生产运行情况'],
             ['', '金州电厂：'],
             ['9:22', '#2炉停炉消缺。'],
             ['17:48', '#3炉并汽。']]
        ])
        report = extractor.extract_all()
        jz_facilities = [f for f in report['boiler_turbine_status'] if f['unit_or_plant'] == '金州热电']
        turbines = [f for f in jz_facilities if f['facility_type'] == '汽机']
        boilers = [f for f in jz_facilities if f['facility_type'] == '锅炉']

        # 汽机应为 #1、#3（运行），#2（备用），不应存在重复的 #2汽机
        self.assertEqual(len(turbines), 3)
        self.assertEqual({f['standard_name']: f['status'] for f in turbines}, {
            '#1汽机': '运行',
            '#2汽机': '备用',
            '#3汽机': '运行'
        })

        # 锅炉中 #2 应被正确推导为 #2汽炉，且状态为检修
        self.assertEqual(len(boilers), 5)
        boiler_dict = {f['standard_name']: f['status'] for f in boilers}
        self.assertEqual(boiler_dict['#2汽炉'], '检修')
        self.assertEqual(boiler_dict['#6水炉'], '备用')
        self.assertEqual(boiler_dict['#1汽炉'], '运行')
        self.assertEqual(boiler_dict['#3汽炉'], '运行')
        self.assertEqual(boiler_dict['#4汽炉'], '运行')

        # 检查 #2汽炉的事件是否关联到 9:22 停炉
        b2 = next(f for f in boilers if f['standard_name'] == '#2汽炉')
        self.assertEqual(len(b2['main_events']), 1)
        self.assertEqual(b2['main_events'][0]['action'], '停炉')
        self.assertEqual(b2['main_events'][0]['time'], '9:22')

    def test_november_10_pdf_when_available(self):
        source = Path(__file__).resolve().parents[4] / 'configs/2026年11月10日生产信息.pdf'
        if not source.exists():
            self.skipTest('2026年11月10日生产信息.pdf 未在 configs 目录下找到')
        report = extract_single_file(str(source))
        self.assertEqual(report['biz_date'], '2026-11-10')
        jz_facilities = [f for f in report['boiler_turbine_status'] if f['unit_or_plant'] == '金州热电']
        turbines = [f for f in jz_facilities if f['facility_type'] == '汽机']
        boilers = [f for f in jz_facilities if f['facility_type'] == '锅炉']
        self.assertEqual(len(turbines), 3)
        self.assertEqual({f['standard_name']: f['status'] for f in turbines}, {
            '#1汽机': '运行', '#2汽机': '备用', '#3汽机': '运行'
        })
        b2 = next(f for f in boilers if f['standard_name'] == '#2汽炉')
        self.assertEqual(b2['table_status'], '检修')
        self.assertEqual(b2['main_events'][0]['time'], '9:22')


if __name__ == '__main__':
    unittest.main()
