"""调度主设备事件归属、状态冲突检测和用户选择留痕。"""

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from .dispatch_operations import EXPLICIT, action_status, split_operations

DISPLAY_STATES = ('运行', '备用', '检修', '启动中', '停运')
RESOLUTIONS = ('table', 'events') + tuple('status:' + s for s in DISPLAY_STATES)


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
    """拆分操作、推断末次状态；无有效确认时保留表格，证据变更后重新确认。"""
    result = copy.deepcopy(report)
    raw_biz_date = result.get('biz_date')
    result['biz_date'] = raw_biz_date.isoformat() if hasattr(raw_biz_date, 'isoformat') else (str(raw_biz_date) if raw_biz_date else '')
    stored = result.get('eqp_status_json')
    stored = stored if isinstance(stored, dict) else {}
    facilities = result.get('boiler_turbine_status')
    if not isinstance(facilities, list) or not facilities:
        facilities = copy.deepcopy(stored.get('facilities') or [])
    result['boiler_turbine_status'] = facilities
    events = split_operations(result.get('operations_and_tickets') or result.get('log_items_json') or [], result.get('biz_date'))
    result['operations_and_tickets'] = events
    result['log_items_json'] = copy.deepcopy(events)
    assigned = {device_key(f): [] for f in facilities}
    uncertain = {device_key(f): [] for f in facilities}
    warnings = []
    for event in events:
        warnings.extend(event.get('parse_warnings') or [])
        if event.get('is_ticket') or event.get('exclude_main_inference'):
            continue
        for match in EXPLICIT.finditer(event.get('main_description') or event.get('raw_description') or ''):
            number = re.search(r'\d+', match['device'])[0]
            kind = re.sub(r'#?\d+\s*', '', match['device'])
            turbine = kind in ('汽机', '机组', '机')
            action = match['action']
            allowed = ('冲转', '并网', '并列', '并热网', '打闸停机', '停机', '解列', '跳闸', '恢复运行', '启动', '投运', '停运') if turbine else ('点火', '点炉', '并汽', '并热网', '灭火', '停炉', '恢复运行', '启动', '投运', '停运', '跳闸')
            if action not in allowed:
                warnings.append(f"{event.get('time', '')} {event['raw_description']}：动作与设备类型不匹配，未推断状态")
                continue
            candidates = []
            for fac in facilities:
                num = re.search(r'\d+', fac.get('standard_name') or fac.get('raw_name', ''))
                if not num or int(num[0]) != int(number):
                    continue
                if _org_family(fac.get('unit_or_plant', '')) != _org_family(event.get('responsible_org', '')):
                    continue
                if turbine != (fac.get('facility_type') == '汽机'):
                    continue
                if kind in ('汽炉', '蒸汽炉', '水炉', '燃气炉') and fac.get('boiler_type') != ('汽炉' if kind == '蒸汽炉' else kind):
                    continue
                candidates.append(fac)
            if len(candidates) != 1:
                warnings.append(f"{event.get('time', '')} {event['raw_description']}：主设备归属不唯一或缺失，未自动推断状态")
                for fac in candidates:
                    uncertain[device_key(fac)].append({'time': event.get('time', ''), 'action': action,
                        'status': action_status(action), 'raw_description': event['raw_description']})
                continue
            main_event = {
                'time': event.get('event_clock', event.get('time', '')) if event.get('event_date') and event['event_date'] != result.get('biz_date') else event.get('time', ''),
                'action': '停机' if action == '打闸停机' else action,
                'status': action_status(action), 'raw_description': f"{match['device']}{action}",
            }
            if event.get('event_date') and event['event_date'] != result.get('biz_date'):
                main_event['event_date'] = event['event_date']
            assigned[device_key(candidates[0])].append(main_event)

    conflicts = []
    for fac in facilities:
        key = device_key(fac)
        table_status = fac.get('table_status') or fac.get('status', '')
        fac['table_status'] = table_status
        timeline = assigned[key]
        timeline.sort(key=lambda e: (e.get('event_date') or str(result.get('biz_date', '')), _time_minutes(e) if _time_minutes(e) is not None else -1))
        current_day = [e for e in timeline if not e.get('event_date') or e['event_date'] == str(result.get('biz_date', ''))]
        inferred = current_day[-1]['status'] if current_day and all(_time_minutes(e) is not None for e in current_day) else None
        if inferred and len({e['status'] for e in current_day if _time_minutes(e) == _time_minutes(current_day[-1])}) > 1:
            inferred = None
        reason = ''
        if current_day and inferred is None:
            reason = '事件时间无效、缺失或同一末次时刻存在不同状态，请人工核对'
            warnings.append(f'{key}：{reason}')
        if uncertain[key]:
            inferred = None
            reason = '存在无法唯一归属的主设备操作，请核对设备类型后选择显示状态'
        fingerprint = hashlib.sha256(json.dumps([table_status, timeline, uncertain[key]], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        conflict_id = f"{result.get('file_name', '')}|{result.get('biz_date', '')}|{key}"
        saved_source = fac.get('status_source') if fac.get('status_confirmed') else None
        # 兼容旧记录；旧确认也必须与其保存的事件证据一致，不能无条件沿用。
        old_timeline = fac.get('main_events') or []
        old_evidence = [{k: e.get(k) for k in ('time', 'action', 'status', 'raw_description')} for e in old_timeline]
        if fac.get('status_decision_evidence'):
            valid_saved = fac['status_decision_evidence'] == fingerprint
        else:
            valid_saved = old_evidence == timeline
        choice = (choices or {}).get(conflict_id) or (saved_source if valid_saved else None)
        if choice not in RESOLUTIONS or (choice == 'events' and not inferred):
            choice = None
        fac['main_events'] = timeline
        # 时间歧义也形成可确认项，禁止悄悄采用表格后继续入库。
        if (current_day or uncertain[key]) and (not inferred or inferred != table_status):
            conflicts.append({
                'id': conflict_id, 'device': key, 'table_status': table_status,
                'table_text': fac.get('table_text', ''), 'event_status': inferred,
                'events': timeline + uncertain[key], 'reason': reason, 'resolution': choice,
                'evidence': fingerprint,
            })
        fac['status'] = choice[7:] if choice and choice.startswith('status:') else inferred if choice == 'events' else table_status
        fac['status_source'] = choice or 'table'
        fac['status_confirmed'] = bool(choice)
        if choice:
            fac['status_decision_evidence'] = fingerprint
        if (choices or {}).get(conflict_id) and choice:
            fac['status_decision_at'] = datetime.now(timezone.utc).isoformat()
        for conflict in conflicts:
            if conflict['id'] == conflict_id:
                conflict['display_status'] = fac['status']

    result['status_conflicts'] = conflicts
    result['extraction_warnings'] = list(dict.fromkeys(warnings))
    result['eqp_status_json'] = stored
    stored['facilities'] = copy.deepcopy(facilities)
    stored['status_conflicts'] = copy.deepcopy(conflicts)
    stored['extraction_warnings'] = result['extraction_warnings']
    matrix, flat_map = {}, {}
    for fac in facilities:
        plant = fac.get('unit_or_plant', '其他')
        category = '机' if fac.get('facility_type') == '汽机' else '炉'
        states = matrix.setdefault(plant, {kind: {state: [] for state in DISPLAY_STATES} for kind in ('机', '炉')})[category]
        number = re.search(r'#?\d+', fac.get('standard_name', ''))
        states.setdefault(fac['status'], []).append(number[0] if number else fac.get('raw_name', ''))
        name = (fac.get('raw_name') or fac.get('standard_name', '').replace('汽机', '机')) if category == '机' else fac.get('standard_name', '')
        flat_map[f'{plant}_{name}'] = fac['status']
    stored['matrix'], stored['flat_map'] = matrix, flat_map
    return result
