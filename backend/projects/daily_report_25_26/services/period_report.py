"""自选周期运行汇报：复用既有引擎及缺项按零口径，生成确定性分析。"""
from datetime import date, timedelta
from calendar import monthrange

from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine
from backend.services.heating_metrics.season_utils import get_peer_date, get_season_period
from .daily_brief import COMPANIES, describe_change, comparison, number
from .monthly_coal_progress import get_monthly_coal_progress

SUBJECTS = ['Group', 'ZhuChengQu', 'JinZhou', 'BeiFang', 'JinPu', 'ZhuangHe', 'YanJiuYuan']
# 章节、指标键、展示名、单位；金额口径沿用现有经营分析，不作为财务结算数。
METRICS = [
    (0, 'eco_marginal_profit', '实际边际利润', '万元'),
    (0, 'eco_comparable_marginal_profit', '可比煤价边际利润', '万元'),
    (0, 'amount_power_generation', '发电量', '万kWh'),
    (0, 'amount_hot_water_sales', '高温水销售量', 'GJ'),
    (0, 'amount_steam_sales', '售汽量', '吨'),
    (1, 'consumption_std_coal', '标煤耗量', '吨'),
    (1, 'consumption_outer_purchased_heat', '外购热量', 'GJ'),
    (1, 'consumption_natural_gas', '天然气耗量', '立方米'),
    (2, 'eco_direct_income', '直接收入', '万元'),
    (2, 'eco_coal_cost', '煤成本', '万元'),
    (2, 'eco_purchased_power_cost', '外购电成本', '万元'),
    (2, 'eco_purchased_water_cost', '购水成本', '万元'),
    (2, 'eco_measurable_auxiliary_materials', '可计量辅材成本', '万元'),
    (3, 'rate_heat_per_10k_m2', '供暖热单耗', 'GJ/万㎡'),
    (3, 'rate_power_per_10k_m2', '供暖电单耗', 'kWh/万㎡'),
    (3, 'rate_water_per_10k_m2', '供暖水单耗', '吨/万㎡'),
]


def days_between(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def report_value(value):
    """用户确认：汇报找不到的指标按0，与现有引擎的缺项补零保持一致。"""
    result = number(value)
    return result if result is not None else 0.0


def validate_period(start, end):
    """单次报告限制在同一供暖年度，避免跨期常量被错用于整个窗口。"""
    if start > end:
        raise ValueError('开始日期不能晚于结束日期')
    if (end - start).days >= 366:
        raise ValueError('单次汇报最多选择366天')
    if get_season_period(start) != get_season_period(end):
        raise ValueError('请选择同一供暖年度内的日期；跨供暖年度请分别生成')


def metric_story(label, rows, unit, include_prev):
    """先整体、再主要增减单位；不从同步变化推断因果。"""
    group = rows[0]
    result = [describe_change(f'集团{label}', group['curr'], group['sync'], unit, 2)]
    if include_prev and group['curr'] is not None and group['prev'] is not None:
        result.append(describe_change(f'较上期对照，集团{label}', group['curr'], group['prev'], unit, 2).replace('同比', '较上期'))
    # 主城区及五家单位互不交叉；不把集团与主城区作为新增实体重复求贡献。
    comparable = [r for r in rows[1:] if r['curr'] is not None and r['sync'] is not None]
    if comparable:
        leader = max(comparable, key=lambda r: abs(r['curr'] - r['sync']))
        if round(leader['curr'] - leader['sync'], 2):
            result.append('可比单位中，' + describe_change(leader['name'] + label, leader['curr'], leader['sync'], unit, 2))
    if '单耗' in label:
        result.append('单位间差异需结合供热方式与供热质量判断；本页不直接据此评价运行优劣。')
    return result


def build_period_report(db, start, end, include_prev=True):
    validate_period(start, end)
    days = days_between(start, end)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=len(days) - 1)
    prev_valid = include_prev and get_season_period(prev_start) == get_season_period(end)
    peer_days = [get_peer_date(d) for d in days]
    windows = [('curr', start, end), ('sync', min(peer_days), max(peer_days))]
    if prev_valid:
        windows.append(('prev', prev_start, prev_end))
    engine = HeatingAnalysisEngine(db)
    keys = [m[1] for m in METRICS]
    values = {}
    for side, begin, finish in windows:
        for company in SUBJECTS:
            calculated = engine.compute_analysis_rows(company, keys, begin, finish, aggregate=True, clip_to_season=False)
            for key in keys:
                values[side, company, key] = report_value(calculated.get(key, {}).get('value_biz_date'))
    pages = []
    for chapter, key, label, unit in METRICS:
        rows = []
        for company in SUBJECTS:
            row = {'name': COMPANIES[company], 'company': company,
                   **{side: values.get((side, company, key)) for side in ('curr', 'sync', 'prev')}}
            row['delta'] = comparison(row['curr'], row['sync'])['delta']
            row['missing'] = {}
            rows.append(row)
        pages.append({'chapter': chapter, 'key': key, 'title': label, 'unit': unit,
                      'paragraphs': metric_story(label, rows, unit, prev_valid), 'rows': rows})
    # 跨月逐月展示正式标煤计划；截止日之前的月累计不与所选周期混淆。
    cursor = start.replace(day=1)
    units = [{'company': c, 'company_cn': COMPANIES[c]} for c in COMPANIES]
    hierarchy = {'Group': ['BeiHai', 'XiangHai', 'GongRe', 'JinZhou', 'BeiFang', 'JinPu', 'ZhuangHe', 'YanJiuYuan'],
                 'ZhuChengQu': ['BeiHai', 'XiangHai', 'GongRe']}
    while cursor <= end:
        cutoff = min(end, cursor.replace(day=monthrange(cursor.year, cursor.month)[1]))
        plan = get_monthly_coal_progress(db, cutoff.isoformat(), units, hierarchy)
        remaining_days = monthrange(cutoff.year, cutoff.month)[1] - cutoff.day
        rows = []
        for item in plan['items']:
            if item['company'] not in SUBJECTS:
                continue
            rows.append({'name': item['company_cn'], 'plan': report_value(item['plan_value']), 'curr': report_value(item['actual_value']),
                         'percent': item['completion_percent'],
                         'remaining': item['remaining_value'] / remaining_days if remaining_days and item['remaining_value'] is not None else None,
                         'status': item['status']})
        pages.append({'chapter': 4, 'key': f'plan-{cursor}', 'title': f'{cursor.month}月标煤计划执行', 'unit': '吨标煤',
                      'kind': 'plan', 'rows': rows, 'paragraphs': [
                          f'本页累计范围为{cursor.isoformat()}至{cutoff.isoformat()}，与所选本期范围分别统计。',
                          f'月内剩余{remaining_days}天。剩余日均额度按（月计划－月累计）÷剩余天数计算；负值表示已超计划，月末不再计算剩余日均。',
                          '仅使用正式月计划；计划为零时不计算完成率。未接入预报和调度原因分析，不据此下达负荷调整指令。']})
        cursor = cutoff.replace(day=1) + timedelta(days=32)
        cursor = cursor.replace(day=1)
    return {'start': start.isoformat(), 'end': end.isoformat(), 'days': len(days), 'hasPrev': prev_valid,
            'peerStart': min(peer_days).isoformat(), 'peerEnd': max(peer_days).isoformat(),
            'prevStart': prev_start.isoformat() if prev_valid else None, 'prevEnd': prev_end.isoformat() if prev_valid else None,
            'pages': pages}
