"""修复回归：月计划跨接口对账、首次保存替身、气温临时表；不提交业务数据。"""
import asyncio
import inspect
from types import SimpleNamespace
from unittest.mock import patch
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.daily_report_25_26.api import dynamic_plan as api
from backend.services import dynamic_decomposition_service as service
from backend.services import ensemble_weather_service as weather

with SessionLocal() as db:
    db.execute(text('SET TRANSACTION READ ONLY'))
    for company in service.COMPANY_CN_MAP:
        monthly = api.get_dynamic_plan_data(company=company, start_month='2026-11', end_month='2026-11', plan_type='plan')
        daily = service.get_dynamic_daily_decomposition(company, '2026-11', db)
        expected = {m['item']: m['values']['2026-11'] for m in monthly['metrics']}
        for m in daily['metrics']:
            if m['item'] in expected and m.get('aggregation_method') != 'sum_children':
                assert abs(expected[m['item']] - m['month_plan']) < .011, (company, m['item'])
            assert abs(sum(m['daily_plans']) - m['month_plan']) < .0051
    db.rollback()
print('通过：10 个口径的月计划与逐日分解基数及合计一致')

class FakeDatabase:
    def execute(self, sql, params):
        if str(sql).lstrip().startswith('INSERT'):
            assert params['k_val'] == 0 and params['m_val'] == 1.1
        return SimpleNamespace(fetchone=lambda: None)
    def commit(self): pass
    def rollback(self): raise AssertionError('新增参数不应失败')
    def close(self): pass

async def save():
    payload = api.UpdateKParametersPayload(updates=[dict(company='Group',month=11,item='consumption_water',m_value=1.1)])
    with patch.object(api, 'SessionLocal', return_value=FakeDatabase()):
        result = await api.update_k_parameters_endpoint(payload, session=SimpleNamespace(group='Global_admin'), authorization=None)
        assert result['ok'] and result['updated_count'] == 1
asyncio.run(save())
print('通过：首次保存缺失参数行，新增分支正常')

# 使用真实 PostgreSQL ON CONFLICT 语义，但所有记录仅存在临时表且最后回滚。
sql = next(c for c in weather.fetch_and_import_ensemble_weather.__code__.co_consts if isinstance(c,str) and 'INSERT INTO public.temperature_data' in c)
with SessionLocal() as db:
    db.execute(text('CREATE TEMP TABLE temperature_data (date_time timestamptz PRIMARY KEY, value numeric, type text, operation_time timestamptz) ON COMMIT DROP'))
    db.execute(text("INSERT INTO pg_temp.temperature_data VALUES ('2026-11-01 00:00+08',10,'near',now()),('2026-11-01 01:00+08',11,'far',now()),('2026-11-01 02:00+08',12,NULL,now())"))
    from psycopg2.extras import execute_values
    from datetime import datetime
    conn = db.connection().connection.driver_connection
    with conn.cursor() as cur:
        written = execute_values(cur, sql.replace('public.temperature_data','pg_temp.temperature_data'), [(datetime.fromisoformat(f'2026-11-01T0{i}:00:00+08:00'),99) for i in range(4)], template="(%s,%s,'far',CURRENT_TIMESTAMP)", fetch=True)
        assert len(written) == 3
    rows = db.execute(text('SELECT value,type FROM pg_temp.temperature_data ORDER BY date_time')).all()
    assert rows[0] == (10,'near') and all(r == (99,'far') for r in rows[1:]), rows
    db.rollback()
print('通过：near 保持原值和类型，far/NULL 更新，新时刻插入；临时事务已回滚')
