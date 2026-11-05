"""计划图表实际值：独立于计划模型，按最新发布日截断，支持同一窗口多指标。"""
from calendar import monthrange
from datetime import date, timedelta
import math

from sqlalchemy import text

from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine
from backend.services.heating_metrics.season_utils import get_season_period, get_season_windows
from .daily_brief import BriefEvidence


class _BufferedAnalysisEngine(HeatingAnalysisEngine):
    """一次读取业务底表，日序列与月累计复用既有公式，避免逐日查询数据库。"""

    def __init__(self, session, raw, constants):
        super().__init__(session)
        self.raw = raw
        self.constants = constants

    def fetch_constants(self, biz_period, peer_period):
        return tuple({(r['company'], r['item']): float(r['value'])
                      for r in self.constants if r['period'] == period and r['value'] is not None}
                     for period in (biz_period, peer_period))

    def fetch_base_aggregated_range(self, biz_start, biz_end, peer_start, peer_end,
                                    companies=None, counter_anchor=None):
        # 图表不需要同期列。仅将当前窗口的原始量送入标准计算引擎。
        result = {}
        for row in self.raw:
            if not biz_start <= row['date'] <= biz_end or row['value'] is None:
                continue
            if companies and row['company'] not in companies:
                continue
            key = (row['company'], row['item'])
            entry = result.setdefault(key, {'company_cn': row['company_cn'], 'item_cn': row['item_cn'],
                                             'unit': row['unit'], 'biz': 0.0, 'peer': 0.0})
            entry['biz'] += float(row['value'])
        return result


def _convert(value, source_unit, target_unit):
    """只转换已明确的等价单位，未知单位不强行放在同一纵轴上。"""
    if value is None:
        return None
    source, target = (str(label or '').strip().replace('m²', '㎡').replace('m2', '㎡')
                      for label in (source_unit, target_unit))
    scales = {'吨': ('mass', 1), '吨标煤': ('mass', 1), '万吨': ('mass', 10000),
              '万吨标煤': ('mass', 10000), 'GJ': ('heat', 1), '万GJ': ('heat', 10000),
              'kWh': ('power', 1), '万kWh': ('power', 10000), '元': ('money', 1), '万元': ('money', 10000)}
    number = float(value)
    if not math.isfinite(number):
        return None
    if source == target:
        return number
    if source in scales and target in scales and scales[source][0] == scales[target][0]:
        return number * scales[source][1] / scales[target][1]
    return None


def get_dynamic_plan_actuals(session, company, item, unit, start_month, end_month,
                             granularity, published_dates):
    """兼容原有单指标接口；底表读取和计算统一复用批量服务。"""
    result = get_dynamic_plan_actuals_batch(session, company, [{'item': item, 'unit': unit}],
                                           start_month, end_month, granularity, published_dates)
    return {key: value for key, value in result.items() if key != 'metrics'} | result['metrics'][item]


def get_dynamic_plan_actuals_batch(session, company, metrics, start_month, end_month,
                                   granularity, published_dates):
    """日模式按日取值，月模式各月独立从月初累计；所有底表查询均不超过发布日。"""
    start = date.fromisoformat(f'{start_month}-01')
    last = date.fromisoformat(f'{end_month}-01')
    end = last.replace(day=monthrange(last.year, last.month)[1])
    if start > end or (last.year - start.year) * 12 + last.month - start.month > 23:
        raise ValueError('月份范围须按顺序且不超过24个月')
    if granularity not in {'day', 'month'} or (granularity == 'day' and start_month != end_month):
        raise ValueError('日实际值仅支持一个月份')
    buckets = []
    cursor = start
    while cursor <= end:
        bucket_end = cursor if granularity == 'day' else cursor.replace(day=monthrange(cursor.year, cursor.month)[1])
        buckets.append((cursor.isoformat() if granularity == 'day' else cursor.strftime('%Y-%m'), cursor, bucket_end))
        cursor = bucket_end + timedelta(days=1)
    cutoff = date.fromisoformat(max(published_dates)) if published_dates else None
    result = {'ok': True, 'company': company, 'granularity': granularity,
              'latest_published_date': cutoff.isoformat() if cutoff else None,
              'metrics': {metric['item']: {'item': metric['item'], 'unit': metric['unit'],
                          'values': {key: None for key, _, _ in buckets}} for metric in metrics}}
    if cutoff is None or cutoff < start or not metrics:
        return result
    effective_end = min(end, cutoff)
    raw = session.execute(text('''
        SELECT company, MAX(company_cn) AS company_cn, item, MAX(item_cn) AS item_cn,
               MAX(unit) AS unit, date,
               CASE WHEN COUNT(*) = COUNT(value) THEN SUM(value) ELSE NULL END AS value
        FROM daily_basic_data WHERE date BETWEEN :start AND :end
        GROUP BY company, item, date
    '''), {'start': start, 'end': effective_end}).mappings().all()
    periods = {get_season_period(first) for _, first, _ in buckets if first <= effective_end}
    constants = session.execute(text('''SELECT company, item, period, value FROM constant_data
        WHERE period IN :periods'''), {'periods': tuple(periods)}).mappings().all()
    expected = []
    for period in sorted(periods):
        days = [first for _, first, _ in buckets if first <= effective_end and get_season_period(first) == period]
        period_end = min(effective_end, max(last for _, first, last in buckets if get_season_period(first) == period))
        expected.extend(session.execute(text('''SELECT DISTINCT company, item, :period AS period
            FROM daily_basic_data WHERE date BETWEEN :first AND :last AND value IS NOT NULL'''),
            {'period': period, 'first': min(start, get_season_windows(days[0])['biz_season_start']),
             'last': period_end}).mappings().all())
    evidence = BriefEvidence(raw, expected, constants)
    engine = _BufferedAnalysisEngine(session, raw, constants)
    for key, first, last_day in buckets:
        if first > effective_end:
            continue
        last_day = min(last_day, effective_end)
        # 每项独立判断完整性，某项缺报不会清空其他指标；同一窗口只计算一次。
        complete_items = []
        for metric in metrics:
            day = first
            while day <= last_day and not evidence.check(company, metric['item'], day):
                day += timedelta(days=1)
            if day > last_day:
                complete_items.append(metric['item'])
        rows = engine.compute_analysis_rows(company, complete_items, first, last_day,
                                             aggregate=granularity == 'month', clip_to_season=False)
        for metric in metrics:
            row = rows.get(metric['item'])
            if row:
                result['metrics'][metric['item']]['values'][key] = _convert(row.get('value_biz_date'), row.get('unit'), metric['unit'])
    return result
