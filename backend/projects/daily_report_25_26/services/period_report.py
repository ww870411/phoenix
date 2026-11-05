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
    (2, 'eco_power_supply_income', '售电收入', '万元'),
    (2, 'eco_heating_supply_income', '供暖收入', '万元'),
    (2, 'eco_hot_water_supply_income', '售高温水收入', '万元'),
    (2, 'eco_steam_supply_income', '售汽收入', '万元'),
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


def compute_period_weather(db, start, end, peer_start, peer_end, prev_start, prev_end, prev_valid):
    """从数据库真实读取指定统计周期、去年同期及上期的实际气温极值与均值。"""
    if db is None:
        return {
            'avgTemp': None, 'minTemp': None, 'maxTemp': None, 'minTempMainCity': '—',
            'peerAvgTemp': None, 'prevAvgTemp': None, 'yoyDiff': None, 'momDiff': None
        }
    try:
        from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
        engine = DailyDashboardEngine(db)
        curr_rows = engine.compute_temperature_data(start, end)
        peer_rows = engine.compute_temperature_data(peer_start, peer_end)
        prev_rows = engine.compute_temperature_data(prev_start, prev_end) if prev_valid and prev_start and prev_end else []

        curr_avgs = [r['aver_temp'] for r in curr_rows if r.get('aver_temp') is not None]
        peer_avgs = [r['aver_temp'] for r in peer_rows if r.get('aver_temp') is not None]
        prev_avgs = [r['aver_temp'] for r in prev_rows if r.get('aver_temp') is not None]

        curr_mins = [r['min_temp'] for r in curr_rows if r.get('min_temp') is not None]
        curr_maxs = [r['max_temp'] for r in curr_rows if r.get('max_temp') is not None]

        avg_temp = round(sum(curr_avgs) / len(curr_avgs), 2) if curr_avgs else None
        min_temp = round(min(curr_mins), 1) if curr_mins else None
        max_temp = round(max(curr_maxs), 1) if curr_maxs else None

        peer_avg = round(sum(peer_avgs) / len(peer_avgs), 2) if peer_avgs else None
        prev_avg = round(sum(prev_avgs) / len(prev_avgs), 2) if prev_avgs else None

        yoy_diff = round(avg_temp - peer_avg, 2) if avg_temp is not None and peer_avg is not None else None
        mom_diff = round(avg_temp - prev_avg, 2) if avg_temp is not None and prev_avg is not None else None

        return {
            'avgTemp': avg_temp,
            'minTemp': min_temp,
            'maxTemp': max_temp,
            'minTempMainCity': f"{min_temp}℃" if min_temp is not None else "—",
            'peerAvgTemp': peer_avg,
            'prevAvgTemp': prev_avg,
            'yoyDiff': yoy_diff,
            'momDiff': mom_diff,
        }
    except Exception:
        return {
            'avgTemp': None, 'minTemp': None, 'maxTemp': None, 'minTempMainCity': '—',
            'peerAvgTemp': None, 'prevAvgTemp': None, 'yoyDiff': None, 'momDiff': None
        }


def compute_period_plans(db, start, end):
    """从月度计划底表按周期天数合理折算本期计划值，单耗指标按目标均值。"""
    if db is None:
        return {}
    try:
        from decimal import Decimal
        from sqlalchemy import text
        cursor = start.replace(day=1)
        plan_dict = {}
        while cursor <= end:
            cutoff = min(end, cursor.replace(day=monthrange(cursor.year, cursor.month)[1]))
            month_days = monthrange(cursor.year, cursor.month)[1]
            period_days = (cutoff - max(start, cursor)).days + 1
            ratio = Decimal(period_days) / Decimal(month_days)

            rows = db.execute(text("""
                SELECT company, item, value, unit FROM paln_and_real_month_data
                WHERE period = :period AND type = 'plan'
            """), {'period': cursor.isoformat()}).mappings().all()

            for r in rows:
                c, it = r['company'], r['item']
                val = r['value']
                if val is not None:
                    if 'rate_' in it:
                        plan_dict[(c, it)] = float(val)
                    else:
                        prorated = float(Decimal(str(val)) * ratio)
                        plan_dict[(c, it)] = plan_dict.get((c, it), 0.0) + prorated

            cursor = cutoff.replace(day=1) + timedelta(days=32)
            cursor = cursor.replace(day=1)
        return plan_dict
    except Exception:
        return {}


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
    prev_in_season = include_prev and get_season_period(prev_start) == get_season_period(end)
    peer_days = [get_peer_date(d) for d in days]
    windows = [('curr', start, end), ('sync', min(peer_days), max(peer_days))]
    if prev_in_season:
        windows.append(('prev', prev_start, prev_end))
    engine = HeatingAnalysisEngine(db)
    keys = [m[1] for m in METRICS]
    values = {}
    for side, begin, finish in windows:
        for company in SUBJECTS:
            calculated = engine.compute_analysis_rows(company, keys, begin, finish, aggregate=True, clip_to_season=False)
            for key in keys:
                values[side, company, key] = report_value(calculated.get(key, {}).get('value_biz_date'))

    # 供暖期首周/无上期判定：若上期区间在系统内核心生产指标全为0或空，判定为无上期数据
    has_prev_data = prev_in_season and any(
        (values.get(('prev', 'Group', k)) or 0) > 0
        for k in ['consumption_std_coal', 'eco_direct_income', 'amount_power_generation']
    )
    prev_valid = has_prev_data

    # 计算真实天气与折算计划
    peer_start_date = min(peer_days)
    peer_end_date = max(peer_days)
    weather = compute_period_weather(db, start, end, peer_start_date, peer_end_date, prev_start, prev_end, prev_valid)
    period_plans = compute_period_plans(db, start, end)

    pages = []
    for chapter, key, label, unit in METRICS:
        rows = []
        for company in SUBJECTS:
            row = {'name': COMPANIES[company], 'company': company,
                   'curr': values.get(('curr', company, key)),
                   'plan': round(period_plans.get((company, key)), 2) if period_plans.get((company, key)) is not None else None,
                   'sync': values.get(('sync', company, key)),
                   'prev': values.get(('prev', company, key)) if prev_valid else None}
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
            rows.append({'name': item['company_cn'], 'unit': '吨', 'plan': report_value(item['plan_value']), 'curr': report_value(item['actual_value']),
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
            'peerStart': peer_start_date.isoformat(), 'peerEnd': peer_end_date.isoformat(),
            'prevStart': prev_start.isoformat() if prev_valid else None, 'prevEnd': prev_end.isoformat() if prev_valid else None,
            'weather': weather,
            'pages': pages}
