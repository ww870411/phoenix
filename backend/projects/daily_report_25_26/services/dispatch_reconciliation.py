"""调度主设备事件归属、状态冲突检测和用户选择留痕。"""

import copy
import re
from datetime import datetime, timezone


def device_key(facility):
    """同厂同类型编号才视为同一设备。"""
    return f"{facility.get('unit_or_plant', '')}|{facility.get('standard_name') or facility.get('raw_name', '')}"


def _org_family(value):
    for name in ('北海', '香海', '北方', '金州', '庄河'):
        if name in value or (name == '北海' and '燃气' in value):
            return name
    return value


def _time_minutes(event):
    match = re.fullmatch(r'(\d{1,2}):(\d{2})', str(event.get('time', '')).strip())
    if not match or int(match[1]) > 23 or int(match[2]) > 59:
        return None
    return int(match[1]) * 60 + int(match[2])


def reconcile_report(report, choices=None):
    """仅按直接作用于主设备的动作推断；没有选择时保留表格口径。"""
    result = copy.deepcopy(report)
    facilities = result.get('boiler_turbine_status') or []
    events = result.get('operations_and_tickets') or []
    assigned = {device_key(f): [] for f in facilities}
    warnings = []
    # 动作必须紧邻设备，避免把“#1机低真空系统循环水泵投运”当作汽机投运。
    pattern = re.compile(
        r'#?(\d+)\s*(汽炉|水炉|燃气炉|蒸汽炉|锅炉|炉|汽机|机组|机)\s*'
        r'(?:与系统|与电网|已|开始)?\s*'
        r'(点火|点炉|启动|冲转|投运|并汽|并网|并列|并热网|恢复运行|停运|停炉|停机|灭火|解列|跳闸)'
    )
    for event in events:
        if event.get('is_ticket'):
            continue
        desc = event.get('raw_description') or ''
        for match in pattern.finditer(desc):
            # 计划、否定和条件语句不能当作已发生事实。
            prefix = re.split(r'[，,。；;]', desc[:match.start()])[-1]
            if re.search(r'计划|拟|预计|待|未|禁止|取消|若|如需', prefix):
                continue
            if re.match(r'\s*(?:失败|未成功|取消|条件|试验|准备)', desc[match.end():]):
                continue
            num, kind, action = match.groups()
            candidates = []
            for fac in facilities:
                name = fac.get('standard_name') or fac.get('raw_name', '')
                number = re.search(r'\d+', name)
                if not number or int(number[0]) != int(num):
                    continue
                if _org_family(fac.get('unit_or_plant', '')) != _org_family(event.get('responsible_org', '')):
                    continue
                turbine = '机' in kind
                if turbine != (fac.get('facility_type') == '汽机'):
                    continue
                if kind in ('汽炉', '蒸汽炉', '水炉', '燃气炉'):
                    expected = '汽炉' if kind == '蒸汽炉' else kind
                    if fac.get('boiler_type') != expected:
                        continue
                candidates.append(fac)
            if len(candidates) != 1:
                warnings.append(f"{event.get('time', '')} {desc}：主设备归属不唯一，未自动推断状态")
                continue
            state = ('启动中' if action in ('点火', '点炉', '启动', '冲转') else
                     '运行' if action in ('投运', '并汽', '并网', '并列', '并热网', '恢复运行') else '停运')
            assigned[device_key(candidates[0])].append({
                'time': event.get('time', ''), 'action': action, 'status': state,
                'raw_description': desc,
            })

    conflicts = []
    for fac in facilities:
        key = device_key(fac)
        table_status = fac.get('table_status') or fac.get('status', '')
        fac['table_status'] = table_status
        timeline = assigned[key]
        timeline.sort(key=lambda e: _time_minutes(e) if _time_minutes(e) is not None else -1)
        fac['main_events'] = timeline
        inferred = timeline[-1]['status'] if timeline and all(_time_minutes(e) is not None for e in timeline) else None
        if inferred and len({e['status'] for e in timeline if _time_minutes(e) == _time_minutes(timeline[-1])}) > 1:
            inferred = None
            warnings.append(f"{key}：同一末次时间存在不同状态，未自动选择")
        if timeline and inferred is None:
            warnings.append(f"{key}：事件时间或先后关系不明确，未推断最终状态")
        conflict_id = f"{result.get('file_name', '')}|{result.get('biz_date', '')}|{key}"
        saved_source = fac.get('status_source') if fac.get('status_confirmed') else None
        choice = (choices or {}).get(conflict_id) or saved_source
        if inferred and inferred != table_status:
            conflicts.append({
                'id': conflict_id, 'device': key, 'table_status': table_status,
                'table_text': fac.get('table_text', ''), 'event_status': inferred,
                'events': timeline, 'resolution': choice if choice in ('table', 'events') else None,
            })
        fac['status'] = inferred if inferred and choice == 'events' else table_status
        fac['status_source'] = choice if choice in ('table', 'events') else 'table'
        fac['status_confirmed'] = choice in ('table', 'events')
        if (choices or {}).get(conflict_id) in ('table', 'events'):
            fac['status_decision_at'] = datetime.now(timezone.utc).isoformat()

    result['status_conflicts'] = conflicts
    result['extraction_warnings'] = list(dict.fromkeys(warnings))
    if not isinstance(result.get('eqp_status_json'), dict):
        result['eqp_status_json'] = {}
    stored = result['eqp_status_json']
    stored['facilities'] = copy.deepcopy(facilities)
    stored['status_conflicts'] = copy.deepcopy(conflicts)
    stored['extraction_warnings'] = result['extraction_warnings']
    # 保持三种设备表示同步；表格原始状态保存在每台设备的 table_status/table_text。
    matrix, flat_map = {}, {}
    for fac in facilities:
        plant = fac.get('unit_or_plant', '其他')
        category = '机' if fac.get('facility_type') == '汽机' else '炉'
        states = matrix.setdefault(plant, {
            kind: {state: [] for state in ('运行', '备用', '检修', '启动中', '停运')}
            for kind in ('机', '炉')
        })[category]
        number = re.search(r'#?\d+', fac.get('standard_name', ''))
        states.setdefault(fac['status'], []).append(number[0] if number else fac.get('raw_name', ''))
        # 保持历史汽机键名“#1机”，锅炉键名仍为“#1汽炉”等标准名称。
        name = (fac.get('raw_name') or fac.get('standard_name', '').replace('汽机', '机')) if category == '机' else fac.get('standard_name', '')
        flat_map[f"{plant}_{name}"] = fac['status']
    stored['matrix'], stored['flat_map'] = matrix, flat_map
    return result
