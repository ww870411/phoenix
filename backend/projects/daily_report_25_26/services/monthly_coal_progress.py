"""静态全月标煤计划执行：只读月计划及月初至业务日实际，不调用动态分解。"""

from datetime import date
from decimal import Decimal, InvalidOperation
from sqlalchemy import text


def _tons(value, unit):
    if value is None:
        return None
    factor = {'吨': 1, '吨标煤': 1, 't': 1, 'tce': 1, '万吨': 10000, '万吨标煤': 10000}.get(str(unit or '').strip())
    if factor is None:
        return None
    try:
        result = Decimal(str(value)) * factor
        return result if result.is_finite() and result >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def build_monthly_coal_progress(biz_date, plan_rows, actual_rows, units, hierarchy, *, actual_start=None):
    """保持集团/主城区直报计划优先；汇总行不与下属单位重复相加。"""
    anchor = date.fromisoformat(biz_date)
    expected = max(0, (anchor - actual_start).days + 1) if actual_start else anchor.day
    plans, actuals = {}, {}
    for row in plan_rows:
        code = row['company']
        if code in plans:
            plans[code] = None
        else:
            plans[code] = _tons(row['value'], row['unit'])
    for row in actual_rows:
        entry = actuals.setdefault(row['company'], {'value': Decimal(0), 'days': set(), 'invalid': False})
        value = _tons(row['value'], row['unit'])
        if value is None:
            entry['invalid'] = True
        else:
            entry['value'] += value
        entry['days'].update(str(day)[:10] for day in (row.get('dates') or []))
    applicable = set(plans) | set(actuals)
    results = []
    for unit in units:
        code = unit['company']
        # 与现有看板一致：研究院不参与标煤统计；供热公司有标煤记录时才列示。
        if code == 'YanJiuYuan' or (code == 'GongRe' and code not in applicable):
            continue
        members = [member for member in hierarchy.get(code, []) if member in applicable]
        plan = plans.get(code)
        plan_source = 'direct' if code in plans else 'missing'
        if code not in plans and members and all(plans.get(m) is not None for m in members):
            plan = sum((plans[m] for m in members), Decimal(0))
            plan_source = 'rollup'
        if code in hierarchy:
            entries = [actuals.get(m) for m in members]
            available = [e for e in entries if e is not None and e['days']]
            actual = sum((e['value'] for e in available), Decimal(0)) if available else None
            complete = bool(entries) and all(e is not None and not e['invalid'] and len(e['days']) == expected for e in entries)
            days = min((len(e['days']) if e is not None else 0 for e in entries), default=0)
            invalid = any(e is not None and e['invalid'] for e in entries)
        else:
            entry = actuals.get(code)
            actual = entry['value'] if entry is not None and entry['days'] else None
            days = len(entry['days']) if entry else 0
            invalid = bool(entry and entry['invalid'])
            complete = days == expected and not invalid
        if invalid:
            actual = None
        if plan is None:
            status = 'missing_plan'
        elif plan == 0:
            status = 'zero_plan'
        elif actual is None:
            status = 'missing_actual'
        elif not complete:
            status = 'incomplete_actual'
        else:
            status = 'over_plan' if actual > plan else 'ready'
        ratio = actual / plan * 100 if status in ('ready', 'over_plan') else None
        remaining = plan - actual if plan is not None and actual is not None and complete else None
        results.append({'company': code, 'company_cn': unit['company_cn'], 'is_rollup': code in hierarchy,
                        'plan_value': float(plan) if plan is not None else None, 'plan_source': plan_source,
                        'actual_value': float(actual) if actual is not None else None,
                        'completion_percent': float(ratio) if ratio is not None else None,
                        'remaining_value': float(remaining) if remaining is not None else None,
                        'status': status, 'reported_days': days, 'expected_days': expected})
    return {'ok': True, 'biz_date': biz_date, 'month': biz_date[:7], 'unit': '吨标煤', 'items': results}


def get_monthly_coal_progress(session, biz_date, units, hierarchy, *, include_season=False):
    anchor = date.fromisoformat(biz_date)
    month_start = anchor.replace(day=1)
    plans = session.execute(text('''SELECT company,value,unit FROM paln_and_real_month_data
        WHERE period=:month_start AND type='plan' AND item='consumption_std_coal' '''), {'month_start': month_start.isoformat()}).mappings().all()
    # 原生标煤耗量与现有DailyDashboardEngine的公司/集团月累计采用同一底表和指标。
    actuals = session.execute(text('''SELECT company,unit,SUM(value) AS value,
        ARRAY_AGG(DISTINCT date) FILTER (WHERE value IS NOT NULL) AS dates
        FROM daily_basic_data WHERE item='consumption_std_coal' AND date BETWEEN :month_start AND :biz_date
        GROUP BY company,unit'''), {'month_start': month_start, 'biz_date': anchor}).mappings().all()
    result = build_monthly_coal_progress(biz_date, plans, actuals, units, hierarchy)
    if include_season:
        result['season'] = get_season_coal_progress(session, biz_date, units, hierarchy)
    return result


def get_season_coal_progress(session, biz_date, units, hierarchy):
    """实际复用看板统计边界，计划按该期编制月份求和，缺编制月不冒充完整计划。"""
    from backend.services.heating_metrics.season_utils import get_season_windows
    windows = get_season_windows(biz_date)
    start, end = windows['biz_season_start'], windows['biz_season_end']
    cutoff = min(date.fromisoformat(biz_date), end)
    months = []
    cursor = start.replace(day=1)
    while cursor <= end:
        months.append(cursor.isoformat())
        cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    # 用户已确认：25—26全期计划仅编制11月至3月；统计截止日4月5日不增加计划月份。
    # 只限定该历史期的计划范围，实际累计边界与其他供暖期均保持原规则。
    if windows['biz_period'] == '25-26':
        months = ['2025-11-01', '2025-12-01', '2026-01-01', '2026-02-01', '2026-03-01']
    plans = session.execute(text('''SELECT company,period,value,unit FROM paln_and_real_month_data
        WHERE period BETWEEN :first_month AND :last_month AND type='plan' AND item='consumption_std_coal' '''),
        {'first_month': months[0], 'last_month': months[-1]}).mappings().all()
    actuals = session.execute(text('''SELECT company,unit,SUM(value) AS value,
        ARRAY_AGG(DISTINCT date) FILTER (WHERE value IS NOT NULL) AS dates
        FROM daily_basic_data WHERE item='consumption_std_coal' AND date BETWEEN :season_start AND :biz_date
        GROUP BY company,unit'''), {'season_start': start, 'biz_date': cutoff}).mappings().all()
    # 每个月先按既有“直报优先、成员兜底”口径求计划，再合并全期，避免父子重复。
    month_results = [build_monthly_coal_progress(month, [r for r in plans if str(r['period'])[:10] == month], [], units, hierarchy)['items'] for month in months]
    applicable = {r['company'] for r in plans} | {r['company'] for r in actuals} | set(hierarchy)
    totals = []
    for unit in units:
        code = unit['company']
        if code not in applicable:
            continue
        values = [next((r['plan_value'] for r in rows if r['company'] == code), None) for rows in month_results]
        total = sum((Decimal(str(v)) for v in values), Decimal(0)) if all(v is not None for v in values) else None
        totals.append({'company': code, 'value': total, 'unit': '吨标煤'})
    result = build_monthly_coal_progress(cutoff.isoformat(), totals, actuals, units, hierarchy, actual_start=start)
    result.update({'period': windows['biz_period'], 'start_date': start.isoformat(), 'end_date': end.isoformat(), 'actual_end_date': cutoff.isoformat(), 'plan_months': months})
    return result
