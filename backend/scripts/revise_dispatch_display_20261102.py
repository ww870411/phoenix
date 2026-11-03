"""按用户口径恢复 11 月 2 日状态，并移除补水卡片中的累计替代值。

默认预览；--apply 保存快照后执行。--restore 预览回滚，追加 --apply 执行。
不批量补填历史高温水数据，不修改累计原字段、网口指标或事件日期。
"""

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import Json, RealDictCursor
from backend.projects.daily_report_25_26.services.dispatch_db_service import get_db_connection
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report


PROJECT = 'daily_report_25_26'
STATUS_FIELDS = ('boiler_turbine_status', 'eqp_status_json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore')
    parser.add_argument('--backup', default='/app/data/projects/daily_report_25_26/runtime/dispatch-display-revision-20261103.json')
    args = parser.parse_args()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT inet_server_port() AS port, current_database() AS database')
            if dict(cur.fetchone()) != {'port': 5432, 'database': 'phoenix'}:
                raise ValueError('请在页面后端容器的 phoenix 库执行')
            changes = []
            if args.restore:
                changes = json.loads(Path(args.restore).read_text(encoding='utf-8'))['changes']
                for change in changes:
                    cur.execute('SELECT * FROM dispatch_daily_reports WHERE project_key=%s AND biz_date=%s FOR UPDATE', (PROJECT, change['date']))
                    row = cur.fetchone()
                    if not row or any(row[k] != v for k, v in change['after'].items()):
                        raise ValueError('修复字段已有后续修改，拒绝回滚')
                    change['before'], change['after'] = change['after'], change['before']
            else:
                cur.execute('SELECT * FROM dispatch_daily_reports WHERE project_key=%s AND (biz_date=%s OR (water_sup_accum IS NOT NULL AND total_water_replenished=water_sup_accum)) ORDER BY biz_date FOR UPDATE', (PROJECT, '2026-11-02'))
                for original in cur.fetchall():
                    row = dict(original)
                    day = str(row['biz_date'])
                    if day == '2026-11-02':
                        revised = copy.deepcopy(row)
                        target = [f for f in revised['boiler_turbine_status'] if f['unit_or_plant'] == '香海电厂' and f['standard_name'] == '#3汽炉']
                        if len(target) != 1 or target[0].get('status_confirmed'):
                            raise ValueError('目标设备异常或已有人工确认')
                        target[0]['status'] = target[0]['table_status'] = '运行'
                        revised = reconcile_report(revised)
                        before = {k: row[k] for k in STATUS_FIELDS}
                        after = {k: revised[k] for k in STATUS_FIELDS}
                    else:
                        # 累计数据仍保留在 water_sup_accum，只停止用它充当高温水值。
                        before = {'total_water_replenished': float(row['total_water_replenished'])}
                        after = {'total_water_replenished': None}
                    if before != after:
                        changes.append({'date': day, 'before': before, 'after': after})
            if args.apply and changes:
                if not args.restore:
                    with Path(args.backup).open('x', encoding='utf-8') as stream:
                        json.dump({'time': datetime.now(timezone.utc).isoformat(), 'project': PROJECT, 'changes': changes}, stream, ensure_ascii=False, indent=2)
                for change in changes:
                    keys = list(change['after'])
                    assignments = ', '.join(f'{k}=%s' for k in keys)
                    values = [Json(change['after'][k]) if k in STATUS_FIELDS else change['after'][k] for k in keys]
                    cur.execute(f'UPDATE dispatch_daily_reports SET {assignments}, updated_at=NOW() WHERE project_key=%s AND biz_date=%s', values + [PROJECT, change['date']])
                    if cur.rowcount != 1:
                        raise ValueError('更新行数异常')
                conn.commit()
            else:
                conn.rollback()
            print(json.dumps({'applied': args.apply, 'changes': [{'date': c['date'], 'fields': list(c['after'])} for c in changes], 'backup': args.backup}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
