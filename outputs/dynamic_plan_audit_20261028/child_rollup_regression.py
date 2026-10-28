"""只读验证聚合总量逐日等于子口径逐日之和，单耗维持自身模型。"""
from datetime import date
import calendar
from unittest.mock import patch
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services import dynamic_decomposition_service as svc

checked = 0
with SessionLocal() as db:
    db.execute(text('SET TRANSACTION READ ONLY'))
    deleted = db.execute(text("SELECT count(*) FROM paln_and_real_month_data WHERE company='GongRe' AND item='amount_heat_supply' AND type='plan' AND period>='2026-10-01'")).scalar()
    print('供热公司当期供热量计划记录数:', deleted)
    for ym in ['2026-10','2026-11','2026-12','2027-01','2027-02','2027-03','2027-04']:
        y, m = map(int, ym.split('-'))
        n = calendar.monthrange(y,m)[1]
        # 非11月使用合成气温，只测试聚合代数关系，不声称远期预报已齐全。
        rows = [dict(date=date(y,m,d).isoformat(), aver_temp=5 + d % 8) for d in range(1,n+1)]
        for company, children in svc.ROLLUP_HIERARCHY.items():
            with patch.object(svc, 'check_temperature_completeness', return_value=(True,rows,[],n)):
                parent = svc.get_dynamic_daily_decomposition(company,ym,db)
                subs = [svc.get_dynamic_daily_decomposition(c,ym,db) for c in children]
            for metric in parent['metrics']:
                if metric['is_rate']:
                    assert metric.get('aggregation_method') != 'sum_children'
                    continue
                assert metric['aggregation_method'] == 'sum_children'
                child_metrics = [v for sub in subs for v in sub['metrics'] if v['item'] == metric['item']]
                expected = [round(sum(v['daily_plans'][i] for v in child_metrics),2) for i in range(n)]
                assert metric['daily_plans'] == expected, (company,ym,metric['item'])
                checked += n
    live = svc.get_dynamic_daily_decomposition('Group','2026-11',db)
    heat = next(v for v in live['metrics'] if v['item']=='amount_heat_supply')
    print('实际11月集团供热量:',heat['month_plan'],'直报:',heat['reported_month_plan'],'差额:',heat['month_plan_difference'])
    db.rollback()
print('逐日汇总核对通过，检查日值数:',checked)
