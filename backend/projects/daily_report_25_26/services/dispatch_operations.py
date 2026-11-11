"""调度操作语义分段、限定主语承接及跨日时间归属；原文始终保留。"""

import copy
import re
from datetime import date, timedelta

DEVICE = r'#?\d+\s*(?:蒸汽炉|燃气炉|汽炉|水炉|锅炉|汽机|机组|炉|机)'
ACTION = r'恢复运行|打闸停机|并热网|点火|点炉|启动|冲转|投运|并汽|并网|并列|停运|停炉|停机|灭火|解列|跳闸'
EXPLICIT = re.compile(rf'(?P<device>{DEVICE})\s*(?:与系统|与电网|已|开始)?\s*(?P<action>{ACTION})')
ACTION_RE = re.compile(ACTION)
DATE_PREFIX = r'(?:(?:\d{1,2}月)?\d{1,2}日|次日|翌日|当日)'
TIME_RE = re.compile(rf'(?<!\d)(?P<time>(?:{DATE_PREFIX}\s*)?\d{{1,2}}[:：]\d{{2}})(?!\d)')
NON_FACT = re.compile(r'计划|拟|预计|待|未|禁止|取消|若|如需|失败|试验|准备|不成功')
CONTINUATION = re.compile(r'^(?:随后|然后|后|已|开始|与系统|与电网|粉仓烧空|煤仓烧空|因故|故障|保护动作|\s)*$')
TAIL = re.compile(r'^(?:成功|完成|正常|后|消缺|检修|备用|保养|\s)*$')


def action_status(action):
    """操作动作与状态映射集中维护。"""
    if action in ('点火', '点炉', '启动', '冲转'):
        return '启动中'
    if action in ('投运', '并汽', '并网', '并列', '并热网', '恢复运行'):
        return '运行'
    return '停运'


def event_time_fields(time_text, biz_date=None):
    """将‘1日1:40’归属到业务日之后的对应日期，跨月/跨年同样处理。"""
    match = re.fullmatch(rf'(?P<prefix>{DATE_PREFIX})?\s*(?P<hour>\d{{1,2}})[:：](?P<minute>\d{{2}})', str(time_text or '').strip())
    if not match or int(match['hour']) > 23 or int(match['minute']) > 59:
        return {}
    clock = f"{int(match['hour']):02d}:{match['minute']}"
    if not biz_date:
        return {'event_clock': clock}
    try:
        base = date.fromisoformat(str(biz_date)[:10])
        prefix = match['prefix'] or ''
        target = base
        if prefix in ('次日', '翌日'):
            target += timedelta(days=1)
        elif prefix and prefix != '当日':
            numbers = [int(n) for n in re.findall(r'\d+', prefix)]
            if len(numbers) == 2:
                month, day = numbers
                target = date(base.year + int(base.month == 12 and month == 1), month, day)
            else:
                day = numbers[0]
                first = base.replace(day=1)
                if day < base.day:
                    first = (first + timedelta(days=32)).replace(day=1)
                target = first.replace(day=day)
        return {'event_date': target.isoformat(), 'event_clock': clock}
    except (ValueError, TypeError):
        return {}


def split_timed_clauses(time_text, description):
    """只按完整时刻切段；原因、标点、工期不会产生独立事件。"""
    if '工作票' in description or '工期' in description:
        return [(time_text, description)]
    matches = list(TIME_RE.finditer(description))
    if not matches:
        return [(time_text, description)]
    result, current, cursor, prefix = [], time_text, 0, ''
    for match in matches:
        part = description[cursor:match.start()].strip(' ，,。；;\n')
        if part:
            if re.fullmatch(r'(?:计划|预计|拟|待|于|将于|约|\s)+', part):
                prefix += part
            else:
                result.append((current, prefix + part))
                prefix = ''
        current = re.sub(r'\s+', '', match['time']).replace('：', ':')
        cursor = match.end()
    part = description[cursor:].strip(' ，,。；;\n')
    if part:
        result.append((current, prefix + part))
    elif result:
        # 尾部仅有时刻且无操作，留在原文中供核对，不生成空卡片。
        result[-1] = (result[-1][0], result[-1][1] + '，' + current)
    return result or [(time_text, description)]


def _attach_time(item, biz_date):
    for key in ('event_date', 'event_clock'):
        item.pop(key, None)
    fields = event_time_fields(item.get('time'), biz_date)
    item.update(fields)
    if biz_date and item.get('time') and not fields and not item.get('is_ticket'):
        warning = f"{item['time']} {item.get('raw_description', '')}：操作日期或时刻无法解析，请核对原文"
        item['parse_warnings'] = list(dict.fromkeys([*item.get('parse_warnings', []), warning]))
    return item


def _source_events(events):
    """重建旧版过度拆分的连续同源片段及上传端拆分的同一原始行。"""
    rebuilt = []
    for original in events:
        event = copy.deepcopy(original)
        if event.get('operation_split_version') == 2 or event.get('is_ticket') or re.search(r'工作票|工期', event.get('raw_description') or ''):
            rebuilt.append(event)
            continue
        source = event.get('source_description')
        can_rebuild = source and (event.get('source_group') or
            ((event.get('operation_split_version') == 1 or source != event.get('raw_description')) and re.search(r'[,，。；;]|\d+:\d+', source)))
        if can_rebuild:
            key = (event.get('responsible_org'), event.get('source_group'), source)
            if rebuilt and rebuilt[-1].get('_rebuild_key') == key:
                continue
            event['raw_description'] = source
            event['time'] = event.get('source_time') or event.get('time', '')
            event['_rebuild_key'] = key
        for key in ('exclude_main_inference', 'operation_split_version', 'main_description', 'subject_inferred', 'operation_fragment'):
            event.pop(key, None)
        rebuilt.append(event)
    return rebuilt


def _facts(text, current_device, planned=False):
    """内部按子句判定主设备事实，但说明性子句不拆成显示记录。"""
    facts, inferred = [], False
    for segment in re.split(r'[,，;；。]', text):
        segment = segment.strip()
        if not segment:
            continue
        if planned or NON_FACT.search(segment):
            planned = planned or bool(re.search(r'计划|拟|预计|待|若|如需', segment))
            current_device = None
            continue
        matches = list(EXPLICIT.finditer(segment))
        actions = list(ACTION_RE.finditer(segment))
        if not actions:
            current_device = None
            continue
        for index, action in enumerate(actions):
            explicit = next((m for m in matches if m.start('action') == action.start()), None)
            prefix = segment[actions[index - 1].end() if index else 0:action.start()]
            if explicit:
                current_device = explicit['device']
            elif not current_device or not CONTINUATION.fullmatch(prefix):
                current_device = None
                continue
            end = actions[index + 1].start() if index + 1 < len(actions) else len(segment)
            next_explicit = next((m for m in matches if m.start('action') == end), None)
            tail = segment[action.end():next_explicit.start() if next_explicit else end]
            if not TAIL.fullmatch(tail):
                current_device = None
                continue
            facts.append((current_device, action[0]))
            inferred = inferred or not bool(explicit)
    return facts, current_device, inferred, planned


def split_operations(events, biz_date=None):
    """上传与查询共用规范化；仅严格限定同源或相邻主设备操作承接主语。"""
    result, previous = [], None
    for event in _source_events(events):
        if event.get('is_ticket') or '工作票' in (event.get('raw_description') or '') or '工期' in (event.get('raw_description') or ''):
            item = copy.deepcopy(event)
            item['exclude_main_inference'] = True
            _attach_time(item, biz_date)
            result.append(item)
            previous = None
            continue
        if event.get('operation_split_version') == 2:
            item = copy.deepcopy(event)
            _attach_time(item, biz_date)
            result.append(item)
            previous = item if item.get('main_context_device') else None
            continue
        description = event.get('raw_description') or ''
        source = event.get('source_description') or description
        current_device, network_subject, planned = None, None, False
        inheritance_basis = ''
        # 兼容旧库中已按时刻拆成两行的‘#1机并热网 / 与系统并列’。
        if previous and event.get('responsible_org') and previous.get('responsible_org') == event.get('responsible_org'):
            old = event_time_fields(previous.get('time'), biz_date)
            new = event_time_fields(event.get('time'), biz_date)
            same_group = previous.get('source_group') == event.get('source_group')
            pure_action = re.fullmatch(rf'(?:与系统|与电网|已|开始)?\s*(?:{ACTION})[。\s]*', description)
            if same_group and pure_action and old.get('event_date') == new.get('event_date') and old.get('event_clock') and new.get('event_clock'):
                minutes = lambda clock: int(clock[:2]) * 60 + int(clock[3:])
                gap = minutes(new['event_clock']) - minutes(old['event_clock'])
                prior = list(EXPLICIT.finditer(previous.get('main_description', '')))
                if 0 <= gap <= 30 and len(prior) == 1:
                    current_device = prior[0]['device']
                    inheritance_basis = '同主体相邻主设备操作，间隔不超过30分钟，无其他设备主语'
        for time_text, body in split_timed_clauses(event.get('time', ''), description):
            facts, current_device, inferred, planned = _facts(body, current_device, planned)
            item = copy.deepcopy(event)
            item.pop('_rebuild_key', None)
            item.update(time=time_text, raw_description=body, source_description=source,
                        source_time=event.get('source_time', event.get('time', '')), operation_split_version=2)
            _attach_time(item, biz_date)
            if facts:
                canonical = '，'.join(f'{device}{action}' for device, action in facts)
                item['main_description'] = canonical
                item['main_context_device'] = current_device
                item['action'] = facts[-1][1]
                item['subject_inferred'] = inferred
                item['operation_fragment'] = body
                if inferred:
                    item['raw_description'] = canonical
                    item['subject_inference_basis'] = inheritance_basis or '同一原始描述内承接前文主设备'
                network_subject = None
            else:
                item['exclude_main_inference'] = True
                network = re.match(r'^(?P<subject>(?:高温水网|低温水网|蒸汽网)[^，,。；;]*?)(?:停运|停止|中断)', body)
                if network:
                    network_subject = network['subject']
                elif network_subject and re.fullmatch(r'(?:已)?恢复(?:运行|供热|送汽)?[。\s]*', body):
                    item['raw_description'] = network_subject + body
                    item['action'] = '恢复'
                    item['subject_inferred'] = True
                    item['operation_fragment'] = body
                    item['subject_inference_basis'] = '同一原始描述内恢复前述支线'
                elif not re.fullmatch(r'(?:处理|修复).*', body):
                    network_subject = None
                if not item.get('subject_inferred') and re.fullmatch(rf'(?:与系统|与电网|已|开始)?\s*(?:{ACTION})[。\s]*', body):
                    item['parse_warnings'] = [*item.get('parse_warnings', []), f'{time_text} {body}：主设备操作缺少明确主体，未自动绑定']
            result.append(item)
            previous = item if facts and current_device else None
    return result
