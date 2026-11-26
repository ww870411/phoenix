"""批量修复 public.dispatch_daily_reports 中跨行断句、无主语残片及工作票起止时间戳；默认仅预览，--apply 保存快照并事务更新，--restore 回滚。"""

import argparse
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import Json, RealDictCursor

from backend.projects.daily_report_25_26.services.dispatch_db_service import get_db_connection
from backend.projects.daily_report_25_26.services.dispatch_operations import _attach_time
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report

PROJECT = 'daily_report_25_26'
FIELDS = ('operations_and_tickets', 'log_items_json')

# 第二类无主语残片定点补全映射：(biz_date, time, 原raw_description) -> 补全后raw_description
CAT2_FIXES = {
    ('2025-11-01', '2日3:30', '送汽结束'): '香北联络管蒸汽管网暖管送汽结束',
    ('2025-11-02', '16:47', '恢复'): '#1水炉恢复',
    ('2025-11-02', '14:30', '送汽结束,投运'): '兴工DN500管送汽结束,投运',
    ('2025-11-04', '16:20', '恢复送汽'): '老造船支线DN400恢复送汽',
    ('2025-11-07', '18:20', '投运'): '#1首站南环#1热网循环泵投运',
    ('2025-11-11', '12日1:45', '恢复'): '高温水唐山支线恢复',
    ('2025-11-14', '14:00', '投运'): '北海南网至造船新厂投运',
    ('2025-11-16', '16:55', '点火'): '#3蒸汽炉点火',
    ('2025-11-16', '18:00', '并汽'): '#3蒸汽炉并汽',
    ('2025-11-16', '18:27', '点火停止退出运行'): '#3水炉点火停止退出运行',
    ('2025-11-25', '14:20', '恢复正常'): '#1蒸汽炉乙吸风机恢复正常',
    ('2025-11-27', '20:40', '锅炉解汽'): '#1蒸汽炉解汽',
    ('2025-11-27', '21:45', '点火'): '#1蒸汽炉点火',
    ('2025-11-27', '22:25', '并汽'): '#1蒸汽炉并汽',
    ('2025-12-01', '19:08', '并热网运行'): '#1水炉并热网运行',
    ('2025-12-05', '19:50', '恢复'): '高温水公安局支线恢复',
    ('2025-12-05', '6日0:20', '恢复'): '高温水恒隆东体育场站支线恢复',
    ('2025-12-13', '23:35', '处理好负荷恢复'): '#1汽炉捞渣机处理好负荷恢复',
    ('2025-12-29', '30日2:25', '恢复'): '高温水宏大支线恢复',
    ('2026-01-07', '13:15', '并热网运行'): '#2水炉并热网运行',
    ('2026-01-15', '22:00', '退出运行'): '#2高减退出运行',
    ('2026-01-17', '16:15', '并汽'): '#2炉并汽',
    ('2026-02-11', '23:46', '恢复'): '唐山站支线DN300门恢复',
    ('2026-02-22', '4:50', '并热网运行'): '#3水炉并热网运行',
    ('2026-02-26', '16:20', '恢复'): '银监局支线恢复',
    ('2026-02-26', '27日6:00', '停运'): '#2高减停运',
    ('2026-03-02', '18:10', '退出运行'): '#1高减退出运行',
    ('2026-03-02', '22:20', '退出运行'): '#2高减退出运行',
    ('2026-03-05', '13:20', '恢复'): '莲花山支线恢复',
    ('2026-03-05', '15:10', '恢复'): '海涵庄园支线恢复',
    ('2026-03-12', '24:00', '投运'): '#2高减投运',
    ('2026-03-15', '11:30', '点火'): '#2炉点火',
    ('2026-03-15', '11:40', '并汽'): '#2炉并汽',
    ('2026-03-15', '20:20', '退出运行'): '#2高减退出运行',
    ('2026-03-15', '20:00', '退出运行'): '#2高减退出运行',
    ('2026-03-18', '16:05', '停运'): '#2高减停运',
    ('2026-03-18', '24:00', '停运'): '#2高减停运',
    ('2026-03-19', '20日0:40', '退出运行'): '#2高减退出运行',
    ('2026-03-19', '23:00', '退出运行'): '#2高减退出运行',
    ('2026-03-22', '14:05', '停运'): '#2高减停运',
    ('2026-04-02', '17:00', '停运'): '#2高减停运',
    ('2026-10-23', '12:00', '上满水定压'): '#3机低真空系统上满水定压',
    ('2026-10-24', '13:00', '上满水定压'): '#1机低真空系统上满水定压',
    ('2026-10-25', '14:28', '停油枪接带负荷'): '#1水炉停油枪接带负荷',
    ('2026-11-01', '11:35', '二段抽汽管道有漏点,停止冲转'): '#3机二段抽汽管道有漏点,停止冲转',
    ('2026-11-01', '22:00', '恢复'): '万众里支线恢复',
    ('2026-11-05', '15:15', '停运'): '#2高减停运',
    ('2026-11-05', '15:20', '接带负荷'): '#2水炉接带负荷',
    ('2026-11-06', '15:00', '处理好投入运行'): '#1汽炉引风机乙处理好投入运行',
    ('2026-11-06', '19:55', '接带负荷'): '#3水炉接带负荷',
    ('2026-11-07', '17:50', '并电网'): '#2机并电网',
    ('2026-11-09', '10日3:05', '恢复'): '高温水菜市街DN350隔离门恢复',
    ('2026-11-09', '20:05', '恢复'): '高温水公安局支线恢复',
    ('2026-11-10', '11日5:30', '开始暖管恢复'): '蒸汽网兴工DN500隔离门开始暖管恢复',
    ('2026-11-12', '20:00', '恢复'): '中心医院支线DN300隔离门恢复',
    ('2026-11-13', '10:05', '恢复'): '#4炉#1引风机恢复',
    ('2026-11-15', '14:40', '并电网'): '#2机并电网',
    ('2026-11-16', '14:00', '恢复'): '宏大支线恢复',
    ('2026-11-17', '15:10', '接带负荷'): '#3水炉接带负荷',
    ('2026-11-18', '14:40', '缺陷处理好恢复运行'): '#3水炉引风机B缺陷处理好恢复运行',
    ('2026-11-21', '21:00', '恢复'): '民运街DN350隔离门恢复',
    ('2026-11-22', '23日6:00', '退出运行'): '#3高减退出运行',
}


def _make_event(base, **overrides):
    """基于已有事件构造规范化事件并清理内部重建标记。"""
    ev = copy.deepcopy(base)
    ev.update(overrides)
    ev.setdefault('exclude_main_inference', True)
    ev['operation_split_version'] = 2
    return ev


def _fix_ticket_start_time_and_range(ev, biz_date):
    """若工作票缺少操作时刻但包含工期起始时间，则补全起始时刻与规范工期范围。"""
    raw = ev.get('raw_description') or ''
    if not (ev.get('is_ticket') or '工作票' in raw or '工期' in raw):
        return
    # 提取完整工期文本并规范化 time_range
    m_range = re.search(
        r'工期\s*[:：]?\s*((?:\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2})[\s.]*\d{1,2}[:：]\d{2}\s*(?:~|～|--|-|至|到)\s*(?:(?:\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2})[\s.]*)?\d{1,2}[:：]\d{2})',
        raw,
    )
    if m_range:
        tr = re.sub(r'(\d{1,2}/\d{1,2})\.', r'\1 ', m_range.group(1))
        tr = re.sub(r'\s*(~|～|--|-|至|到)\s*', ' ~ ', tr)
        tr = re.sub(r'\s+', ' ', tr).strip()
        ev['time_range'] = tr

    if not (ev.get('time') or '').strip():
        m_start = re.search(
            r'工期\s*[:：]?\s*(?:(?P<mon>\d{1,2})月(?P<day>\d{1,2})日?|(?P<d2>\d{1,2})/(?P<m2>\d{1,2}))[\s.]*(?P<hm>\d{1,2}[:：]\d{2})',
            raw,
        )
        if m_start:
            hm = m_start.group('hm').replace('：', ':')
            if m_start.group('mon'):
                month, day = int(m_start.group('mon')), int(m_start.group('day'))
            else:
                day, month = int(m_start.group('d2')), int(m_start.group('m2'))
            biz_m, biz_d = int(biz_date[5:7]), int(biz_date[8:10])
            t_str = hm if (month == biz_m and day == biz_d) else f'{day}日{hm}'
            ev['time'] = t_str
            _attach_time(ev, biz_date)


def _apply_structural_fixes(day, events):
    """对第一类跨行断句、工作票起止拆分及附注条目进行定点合并与拆分。"""
    evs = copy.deepcopy(events)

    if day == '2025-11-04':
        evs[4]['raw_description'] = '因东西网压力变送器故障,故网口压力、流量显示不正确,今晚无法处理好,明天继续处理。'
        evs[4]['source_description'] = evs[4]['raw_description']
        evs.pop(5)
    elif day == '2025-11-05':
        evs[4]['raw_description'] = '#1机冲转。'
        evs[4]['source_description'] = '#1机冲转。'
        # 5、6 两条工作票均内含恢复时间，拆出独立的结束恢复事件
        t5 = copy.deepcopy(evs[5])
        t5['raw_description'] = '签发“芙蓉国际酒店DN150管线泄漏挖掘抢修”工作票,工期 5/11 22:30至6/11 8:00。'
        t5['source_description'] = t5['raw_description']
        r5 = _make_event(
            t5, time='23:20', is_ticket=False, action='开启倒闸', time_range='',
            raw_description='芙蓉国际酒店DN150管线抢修恢复。',
            source_description='芙蓉国际酒店DN150管线抢修恢复。',
        )
        t6 = copy.deepcopy(evs[6])
        t6['raw_description'] = '签发“高温水五四路查漏抢修（五四路交民运街）”工作票,工期 5/11 19:00至6/11 11:00。'
        t6['source_description'] = t6['raw_description']
        r6 = _make_event(
            t6, time='5日7:30', is_ticket=False, action='开启倒闸', time_range='',
            raw_description='高温水五四路（五四路交民运街）查漏抢修恢复。',
            source_description='高温水五四路（五四路交民运街）查漏抢修恢复。',
        )
        evs = evs[:5] + [t5, r5, t6, r6] + evs[7:]
    elif day == '2025-11-13':
        evs[1]['raw_description'] = '签发“DN1000主线（东环）泄漏抢修（带压堵漏）”工作票,工期 13/11 21:00至14/11 21:00。'
        evs[1]['source_description'] = evs[1]['raw_description']
        evs.pop(2)
    elif day == '2025-11-15':
        t0 = copy.deepcopy(evs[0])
        t0['action'] = '关闭倒闸'
        t0['raw_description'] = '因工作票“DN1000主线（东环）泄漏抢修（带压堵漏）”需要,关闭特勤大队事故办及港湾隽景DN1000东环隔离门。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='18:25', is_ticket=False, action='开启倒闸', time_range='',
            raw_description='特勤大队事故办及港湾隽景DN1000东环隔离门恢复。',
            source_description='特勤大队事故办及港湾隽景DN1000东环隔离门恢复。',
        )
        evs = [t0, r0] + evs[1:]
    elif day == '2025-12-22':
        t0 = copy.deepcopy(evs[0])
        t0['raw_description'] = '签发工作票“成大DN400门故障处理（东港）”,工期 22/12 09:00~13:00。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='11:00', is_ticket=False, action='运行操作', time_range='',
            raw_description='成大DN400门（东港）故障处理好,管网恢复运行。',
            source_description='成大DN400门（东港）故障处理好,管网恢复运行。',
        )
        t2 = copy.deepcopy(evs[2])
        t2['raw_description'] = '签发工作票“高温水网新开路交福德街（DN400）查漏抢修”,工期 22/12 19:00~23/12 9:00。'
        t2['source_description'] = t2['raw_description']
        evs = [t0, r0, t2]
    elif day == '2025-12-26':
        evs[1]['raw_description'] = '签发工作票“和和大厦（香洲花园酒店）支线查漏抢修”,工期 26/12 17:00~23:00。'
        evs[1]['source_description'] = evs[1]['raw_description']
        evs.pop(2)
    elif day == '2025-12-27':
        t0 = copy.deepcopy(evs[0])
        t0['raw_description'] = '签发“高温水网香洲花园支线查漏抢修”工作票,工期 27/12 20:30至28/12 1:30。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='23:30', is_ticket=False, action='运行操作', time_range='',
            raw_description='高温水网香洲花园支线查漏抢修恢复。',
            source_description='高温水网香洲花园支线查漏抢修恢复。',
        )
        evs = [t0, r0]
    elif day == '2026-01-04':
        evs[3]['raw_description'] = '签发“DN600蒸汽管道漏泄抢修（远洋供应东侧）”工作票,工期 4/1 13:00至5/1 13:00。'
        evs[3]['source_description'] = evs[3]['raw_description']
        evs.pop(4)
    elif day == '2026-01-06':
        evs[3]['raw_description'] = '签发工作票 《高温水体育场换热站支线DN100查漏抢修》,工期 1月6日 19:30至24:00。'
        evs[3]['source_description'] = evs[3]['raw_description']
        evs.pop(4)
    elif day == '2026-01-07':
        evs[2]['raw_description'] = '签发工作票“高温水网润德换热站支线DN200查漏抢修”,工期 7/1 19:30~24:00。'
        evs[2]['source_description'] = evs[2]['raw_description']
        evs.pop(3)
    elif day == '2026-01-11':
        s0 = _make_event(
            evs[0], time='8:55', action='点火', raw_description='#3蒸汽炉点火',
            source_description='#3蒸汽炉点火,12:30因粉仓内的煤粉自燃造成其防爆门爆,15:30#3炉停炉。',
            source_time='8:55', main_description='#3蒸汽炉点火', main_context_device='#3蒸汽炉',
            subject_inferred=False, operation_fragment='#3蒸汽炉点火', exclude_main_inference=False,
        )
        s1 = _make_event(
            evs[0], time='12:30', action='运行操作', raw_description='因粉仓内的煤粉自燃造成其防爆门爆',
            source_description='#3蒸汽炉点火,12:30因粉仓内的煤粉自燃造成其防爆门爆,15:30#3炉停炉。',
            source_time='8:55', exclude_main_inference=True,
        )
        s2 = _make_event(
            evs[0], time='15:30', action='停炉', raw_description='#3蒸汽炉停炉',
            source_description='#3蒸汽炉点火,12:30因粉仓内的煤粉自燃造成其防爆门爆,15:30#3炉停炉。',
            source_time='8:55', main_description='#3蒸汽炉停炉', main_context_device='#3蒸汽炉',
            subject_inferred=True, operation_fragment='#3炉停炉',
            subject_inference_basis='承接同句前文#3蒸汽炉并合并跨行停炉残片', exclude_main_inference=False,
        )
        s3 = _make_event(
            evs[2], time='19:25', action='点火', raw_description='#3蒸汽炉点火（不并汽运行）',
            source_description=evs[2].get('raw_description', ''), source_time='19:25', exclude_main_inference=True,
        )
        s4 = _make_event(
            evs[2], time='12日2:50', action='停炉', raw_description='#3蒸汽炉粉仓烧空后停炉',
            source_description=evs[2].get('raw_description', ''), source_time='19:25', exclude_main_inference=True,
        )
        evs = [s0, s1, s2, s3, s4]
    elif day == '2026-01-12':
        t3 = copy.deepcopy(evs[3])
        t3['raw_description'] = '签发《更换1m供水管（高温水网新开路交福德街DN400）》工作票,工期 12/1 19:30至13/1 14:00。'
        t3['source_description'] = t3['raw_description']
        r3 = _make_event(
            t3, time='13日2:38', is_ticket=False, action='运行操作', time_range='',
            raw_description='高温水网新开路交福德街DN400供水管更换恢复。',
            source_description='高温水网新开路交福德街DN400供水管更换恢复。',
        )
        evs = evs[:3] + [t3, r3]
    elif day == '2026-01-16':
        evs[7]['raw_description'] = '签发“DN600高温蒸汽管道泄漏抢修（东网）”工作票,工期 16/1 12:00至17/1 17:00。'
        evs[7]['source_description'] = evs[7]['raw_description']
        evs.pop(8)
    elif day == '2026-01-23':
        t0 = copy.deepcopy(evs[0])
        t0['raw_description'] = '签发“高温水管道泄漏抢修（国滨苑支线）”工作票,工期 23/1 9:30-24:00。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='24日1:10', is_ticket=False, action='运行操作', time_range='',
            raw_description='高温水管道（国滨苑支线）抢修结束系统恢复。',
            source_description='高温水管道（国滨苑支线）抢修结束系统恢复。',
        )
        t2 = copy.deepcopy(evs[2])
        t2['raw_description'] = '签发“高温水管道（DN500）泄露抢修（东港第支线）”工作票,工期 24/1 9:30-25/1 17:00。'
        t2['source_description'] = t2['raw_description']
        evs = [t0, r0, t2]
    elif day == '2026-01-24':
        evs[0]['raw_description'] = '“高温水管道（DN500）泄漏抢修（东港第支线）”,抢修工作结束,恢复供热。'
        evs[0]['source_description'] = evs[0]['raw_description']
        evs.pop(1)
    elif day == '2026-01-27':
        t0 = copy.deepcopy(evs[0])
        t0['raw_description'] = '签发工作票一份:“高温水民众换热站支线查漏抢修”,工期 27/1 10:30至17:30。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='12:48', is_ticket=False, action='运行操作', time_range='',
            raw_description='高温水民众换热站支线查漏抢修恢复。',
            source_description='高温水民众换热站支线查漏抢修恢复。',
        )
        t2 = copy.deepcopy(evs[2])
        t2['raw_description'] = '签发工作票一份:“高温水建民换热站支线查漏抢修”,工期 27/1 20:30至28/1 5:00。'
        t2['source_description'] = t2['raw_description']
        evs = [t0, r0, t2]
    elif day == '2026-02-01':
        t0 = copy.deepcopy(evs[0])
        t0['raw_description'] = '签发“高温水唐山换热站支线查漏抢修”工作票,工期 1/2 20:30至2/2 5:00。'
        t0['source_description'] = t0['raw_description']
        r0 = _make_event(
            t0, time='2日3:23', is_ticket=False, action='运行操作', time_range='',
            raw_description='高温水唐山换热站支线查漏抢修恢复。',
            source_description='高温水唐山换热站支线查漏抢修恢复。',
        )
        evs = [t0, r0]
    elif day == '2026-02-03':
        evs[2]['time'] = '4日0:00'
        evs[2]['raw_description'] = '高温水银监局支线恢复。'
        evs[2]['source_description'] = '4日0:00 高温水银监局支线恢复。'
        evs[2]['operation_split_version'] = 2
    elif day == '2026-02-04':
        evs[0]['raw_description'] = '#2炉点火。'
        evs[0]['source_description'] = '#2炉点火。'
        evs[1]['raw_description'] = '#1炉点火。'
        evs[1]['source_description'] = '#1炉点火。'
    elif day == '2026-03-14':
        evs[5]['raw_description'] = '签发《大商步行街利旧管线更换》工作票,工期 14/3 12:30至17/3 24:00。'
        evs[5]['source_description'] = evs[5]['raw_description']
        evs.pop(6)
    elif day == '2026-03-18':
        evs[3]['raw_description'] = '签发《五四广场百盛（DN100天河大厦）支线查漏抢修》工作票,工期 18/3 20:30至19/3 6:00。'
        evs[3]['source_description'] = evs[3]['raw_description']
        evs.pop(4)
    elif day == '2026-03-20':
        t2 = copy.deepcopy(evs[2])
        t2['raw_description'] = '签发工作票“汇利家园换热站支线查漏抢修”,工期 20/3 19:30--21/3 5:00。'
        t2['source_description'] = t2['raw_description']
        r2 = _make_event(
            t2, time='21日00:28', is_ticket=False, action='运行操作', time_range='',
            raw_description='汇利家园换热站支线查漏抢修恢复。',
            source_description='汇利家园换热站支线查漏抢修恢复。',
        )
        evs = evs[:2] + [t2, r2]
    elif day == '2026-03-24':
        t3 = copy.deepcopy(evs[3])
        t3['raw_description'] = '签发工作票“中长街换热站支线查漏抢修”（DN250）,工期 24/3 19:30--25/3 8:30。'
        t3['source_description'] = t3['raw_description']
        r3 = _make_event(
            t3, time='24:00', is_ticket=False, action='运行操作', time_range='',
            raw_description='中长街换热站支线（DN250）查漏抢修恢复。',
            source_description='中长街换热站支线（DN250）查漏抢修恢复。',
        )
        evs = evs[:3] + [t3, r3]
    elif day == '2026-10-28':
        evs[4]['raw_description'] = '签发《嘉州阳光支线DN350供水管线泄漏抢修》工作票,工期 29/10 6:00至29/10 24:00。'
        evs[4]['source_description'] = evs[4]['raw_description']
        evs.pop(5)
    elif day == '2026-11-11':
        evs[0]['raw_description'] = '签发工作票一份“高温水唐山支线泄漏抢修（五四路交市场街西侧）”,工期 11/11 20:00至12/11 8:00。'
        evs[0]['source_description'] = evs[0]['raw_description']
        evs.pop(1)
    elif day == '2026-11-14':
        evs[5]['raw_description'] = '签发“高温水网民众换热站DN200支线抢修（北京街交民众街西侧）”工作票,工期 14/11 12:00--14/11 18:00。'
        evs[5]['source_description'] = evs[5]['raw_description']
        evs.pop(6)
    elif day == '2026-11-21':
        # #3高减 22日1:00投运 后 3:30停运 应归属 22日
        evs[4]['time'] = '22日3:30'
        evs[4]['raw_description'] = '#3高减停运'
        evs[4]['action'] = '运行操作'
        warns = [w for w in (evs[4].get('parse_warnings') or []) if '主设备操作缺少明确主体' not in w]
        if warns:
            evs[4]['parse_warnings'] = warns
        else:
            evs[4].pop('parse_warnings', None)
        _attach_time(evs[4], day)
    elif day == '2026-11-23':
        op_start = _make_event(
            evs[2], time='21:53', is_ticket=False, action='关闭倒闸',
            location='人民广场公安局门前街', pipe_size='DN400',
            time_range='23/11 19:30 ~ 24/11 8:30',
            raw_description='工期: 23/11 19:30~24/11 8:30。21:53关闭人民广场公安局门前街DN400大门',
            source_description='工期: 23/11 19:30~24/11 8:30。21:53关闭人民广场公安局门前街DN400大门',
        )
        op_end = _make_event(
            evs[4], time='23:30', is_ticket=False, action='运行操作',
            location='人民广场公安局门前街', pipe_size='DN400', time_range='',
            raw_description='人民广场公安局门前街DN400大门工作结束系统恢复。',
            source_description='人民广场公安局门前街DN400大门工作结束系统恢复。',
        )
        evs = [evs[0], evs[1], op_start, op_end]
    elif day == '2026-11-24':
        t5 = copy.deepcopy(evs[5])
        t5['location'] = '丹东街交兴平街路口北侧'
        t5['raw_description'] = '签发“DN80高温水管线漏泄抢修（丹东街交兴平街路口北侧）”工作票,工期 24/11 12:00~24:00。'
        t5['source_description'] = t5['raw_description']
        r5 = _make_event(
            t5, time='16:20', is_ticket=False, action='运行操作', time_range='',
            raw_description='DN80高温水管线（丹东街交兴平街路口北侧）抢修恢复。',
            source_description='DN80高温水管线（丹东街交兴平街路口北侧）抢修恢复。',
        )
        evs = evs[:5] + [t5, r5]

    for ev in evs:
        _fix_ticket_start_time_and_range(ev, day)
    if evs != events:
        for ev in evs:
            _attach_time(ev, day)
    return evs


def transform_report(row, matched_cat2_keys):
    """仅对存在断句、无主语残片、工作票时间或附注问题的日期执行修复并校验幂等性。"""
    day = str(row['biz_date'])
    orig_ops = row.get('operations_and_tickets') or []
    fixed_ops = _apply_structural_fixes(day, orig_ops)
    structural_or_ticket_changed = fixed_ops != orig_ops

    work = copy.deepcopy(dict(row))
    work['biz_date'] = day
    work['operations_and_tickets'] = fixed_ops
    work['log_items_json'] = copy.deepcopy(fixed_ops)

    # 先按线上读取口径拆分，再检查是否命中第二类无主语残片
    rec = reconcile_report(work)
    cat2_changed = False
    for ev in rec['operations_and_tickets']:
        key = (day, ev.get('time', ''), (ev.get('raw_description') or '').strip())
        if key in CAT2_FIXES:
            ev['raw_description'] = CAT2_FIXES[key]
            warns = [w for w in (ev.get('parse_warnings') or []) if '主设备操作缺少明确主体' not in w]
            if warns:
                ev['parse_warnings'] = warns
            else:
                ev.pop('parse_warnings', None)
            matched_cat2_keys.add(key)
            cat2_changed = True
        if day == '2026-10-31' and ev.get('time') == '15:46' and ev.get('raw_description') == '#1机并列':
            cat2_changed = True

    if not structural_or_ticket_changed and not cat2_changed:
        return None

    # 对命中的日期：保证所有拆分后事件带 operation_split_version=2，防止读取时再次丢失主语
    for ev in rec['operations_and_tickets']:
        if not (ev.get('is_ticket') or '工作票' in (ev.get('raw_description') or '') or '工期' in (ev.get('raw_description') or '')):
            ev['operation_split_version'] = 2
    rec['log_items_json'] = copy.deepcopy(rec['operations_and_tickets'])
    rec2 = reconcile_report(rec)

    if rec2['operations_and_tickets'] != rec2['log_items_json']:
        raise RuntimeError(f'{day}: operations_and_tickets 与 log_items_json 不一致')
    verify = reconcile_report(rec2)
    if verify['operations_and_tickets'] != rec2['operations_and_tickets']:
        raise RuntimeError(f'{day}: reconcile_report 幂等校验失败')

    # 对比修复前后实时 reconcile 的设备冲突差异，确保不破坏既有人工确认
    base_rec = reconcile_report(dict(row))
    old_confirmed = {(f.get('unit_or_plant'), f.get('standard_name')) for f in (row.get('boiler_turbine_status') or []) if f.get('status_confirmed')}
    new_confirmed = {(f.get('unit_or_plant'), f.get('standard_name')) for f in (rec2.get('boiler_turbine_status') or []) if f.get('status_confirmed')}
    if not old_confirmed.issubset(new_confirmed):
        raise RuntimeError(f'{day}: 人工确认设备状态丢失 {old_confirmed - new_confirmed}')

    return {
        'after': {k: rec2[k] for k in FIELDS},
        'conflicts_before_rec': len(base_rec.get('status_conflicts') or []),
        'conflicts_after_rec': len(rec2.get('status_conflicts') or []),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', default='data/projects/daily_report_25_26/runtime/dispatch-ops-repair-20261126.json')
    parser.add_argument('--restore')
    args = parser.parse_args()

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT inet_server_port() AS port, current_database() AS database')
            identity = dict(cur.fetchone())
            if identity != {'port': 5432, 'database': 'phoenix'}:
                raise RuntimeError(f'拒绝连接非目标库: {identity}')

            cur.execute('SELECT * FROM public.dispatch_daily_reports WHERE project_key=%s ORDER BY biz_date FOR UPDATE', (PROJECT,))
            rows = [dict(r) for r in cur.fetchall()]
            snapshot = json.loads(Path(args.restore).read_text(encoding='utf-8')) if args.restore else None
            changes = []
            matched_cat2_keys = set()

            for row in rows:
                day = str(row['biz_date'])
                before = {k: row[k] for k in FIELDS}
                if snapshot:
                    saved = next((x for x in snapshot['changes'] if x['biz_date'] == day), None)
                    if not saved:
                        continue
                    if before != saved['after']:
                        raise RuntimeError(f'{day} 已有后续修改，拒绝覆盖回滚')
                    after = saved['before']
                    meta = {}
                else:
                    res = transform_report(row, matched_cat2_keys)
                    if not res:
                        continue
                    after = res['after']
                    meta = {k: v for k, v in res.items() if k != 'after'}
                if before != after:
                    changes.append({'biz_date': day, 'before': before, 'after': after, **meta})

            if not snapshot:
                unmatched = set(CAT2_FIXES) - matched_cat2_keys
                if unmatched:
                    raise RuntimeError(f'存在未命中的第二类修复规则 ({len(unmatched)}): {sorted(unmatched)}')

            if args.apply and changes:
                if not snapshot:
                    backup_path = Path(args.backup)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    with backup_path.open('x', encoding='utf-8') as stream:
                        json.dump(
                            {
                                'time': datetime.now(timezone.utc).isoformat(),
                                'database': identity,
                                'changes': [{'biz_date': c['biz_date'], 'before': c['before'], 'after': c['after']} for c in changes],
                            },
                            stream, ensure_ascii=False, indent=2, default=str,
                        )
                for ch in changes:
                    cur.execute(
                        '''UPDATE public.dispatch_daily_reports
                           SET operations_and_tickets=%s, log_items_json=%s, updated_at=NOW()
                           WHERE project_key=%s AND biz_date=%s''',
                        tuple(Json(ch['after'][k]) for k in FIELDS) + (PROJECT, ch['biz_date']),
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError(f"{ch['biz_date']} 更新行数异常: {cur.rowcount}")
                conn.commit()
            else:
                conn.rollback()

            summary = [
                {
                    'biz_date': ch['biz_date'],
                    'before_count': len(ch['before']['operations_and_tickets'] or []),
                    'after_count': len(ch['after']['operations_and_tickets'] or []),
                    'conflicts_before_rec': ch.get('conflicts_before_rec'),
                    'conflicts_after_rec': ch.get('conflicts_after_rec'),
                }
                for ch in changes
            ]
            print(json.dumps({
                'applied': args.apply,
                'restored': bool(snapshot),
                'database': identity,
                'changed_days': len(changes),
                'matched_cat2': len(matched_cat2_keys),
                'backup': args.backup if args.apply and not snapshot else None,
                'details': summary,
            }, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
