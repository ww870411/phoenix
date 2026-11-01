"""定向修正两日调度记录；默认只预览，--apply 后保存快照并事务更新。

在页面后端容器执行，避免连到本机备用库。仅更新四个 JSON 字段及更新时间。
--restore 可用本脚本生成的快照回滚；后续发生过业务修改时拒绝覆盖。
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from psycopg2.extras import Json, RealDictCursor
from backend.projects.daily_report_25_26.services.dispatch_db_service import get_db_connection
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report

FIELDS = ('boiler_turbine_status', 'eqp_status_json', 'operations_and_tickets', 'log_items_json')
PROJECT = 'daily_report_25_26'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', default='data/projects/daily_report_25_26/runtime/dispatch-repair-20261101.json')
    parser.add_argument('--restore')
    args = parser.parse_args()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT inet_server_port() AS port, current_database() AS database')
            identity = dict(cur.fetchone())
            if identity['port'] != 5432:
                raise RuntimeError('本脚本应在页面后端容器内执行，拒绝修正5434备用库')
            cur.execute('SELECT * FROM public.dispatch_daily_reports WHERE project_key=%s AND biz_date IN (%s,%s) ORDER BY biz_date FOR UPDATE',
                        (PROJECT, '2026-03-23', '2026-10-30'))
            rows = [dict(r) for r in cur.fetchall()]
            if len(rows) != 2:
                raise RuntimeError('目标日报数量异常，未修改')
            changes = []
            snapshot = json.loads(Path(args.restore).read_text(encoding='utf-8')) if args.restore else None
            for row in rows:
                day = str(row['biz_date'])
                before = {k: row[k] for k in FIELDS}
                if snapshot:
                    saved = next(x for x in snapshot['changes'] if x['biz_date'] == day)
                    if before != saved['after']:
                        raise RuntimeError(f'{day} 已有后续修改，拒绝覆盖')
                    after = saved['before']
                else:
                    report = reconcile_report(row)
                    if day == '2026-10-30':
                        choices = {c['id']: 'events' for c in report['status_conflicts'] if c['device'] in ('北方热电|#1汽机', '北方热电|#2汽炉')}
                        report = reconcile_report(report, choices)
                        target = [f for f in report['boiler_turbine_status'] if f['unit_or_plant'] == '北方热电' and f['standard_name'] in ('#1汽机', '#2汽炉')]
                        if len(target) != 2 or any(f['status'] != '运行' for f in target):
                            raise RuntimeError('目标设备事件依据不足，未修改')
                    else:
                        target = [e for e in report['operations_and_tickets'] if e['raw_description'].startswith('#4汽炉')]
                        if [(e['time'], e['action']) for e in target] != [('10:30', '并汽'), ('17:30', '停炉')]:
                            raise RuntimeError('事件拆分校验失败，未修改')
                        original_status = next(f['status'] for f in row['boiler_turbine_status'] if f['unit_or_plant'] == '北海热电联产' and f['standard_name'] == '#4汽炉')
                        assert next(f['status'] for f in report['boiler_turbine_status'] if f['unit_or_plant'] == '北海热电联产' and f['standard_name'] == '#4汽炉') == original_status
                    after = {k: report[k] for k in FIELDS}
                changes.append({'biz_date': day, 'before': before, 'after': after})
            if args.apply:
                if not snapshot:
                    path = Path(args.backup)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('x', encoding='utf-8') as backup:
                        json.dump({'time': datetime.now(timezone.utc).isoformat(), 'database': identity, 'changes': changes}, backup, ensure_ascii=False, indent=2)
                for change in changes:
                    cur.execute('''UPDATE public.dispatch_daily_reports SET boiler_turbine_status=%s,
                        eqp_status_json=%s, operations_and_tickets=%s, log_items_json=%s, updated_at=NOW()
                        WHERE project_key=%s AND biz_date=%s''',
                        tuple(Json(change['after'][k]) for k in FIELDS) + (PROJECT, change['biz_date']))
                    assert cur.rowcount == 1
                conn.commit()
            else:
                conn.rollback()
            print(json.dumps({'applied': args.apply, 'restored': bool(snapshot), 'database': identity,
                              'dates': [x['biz_date'] for x in changes], 'backup': args.backup}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
