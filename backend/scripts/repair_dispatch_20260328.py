"""定向修正 2026-03-28 调度记录中跨月误判的 27日17:30 为 17:30 (2026-03-28 17:30)；默认预览，--apply 备份并事务更新。"""

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import Json, RealDictCursor

from backend.projects.daily_report_25_26.services.dispatch_db_service import get_db_connection
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report

PROJECT = 'daily_report_25_26'
DAY = '2026-03-28'
FIELDS = ('operations_and_tickets', 'log_items_json')


def build_after(row):
    """将 2026-03-28 第2条操作时刻由 27日17:30 修正为 17:30，经 reconcile_report 固化并校验幂等。"""
    work = copy.deepcopy(dict(row))
    work['biz_date'] = DAY
    ops = work.get('operations_and_tickets') or []
    if len(ops) < 2 or ops[1].get('time') != '27日17:30':
        raise RuntimeError('2026-03-28 操作记录与预期不符，拒绝修改')
    ops[1]['time'] = '17:30'
    ops[1]['source_time'] = '17:30'
    work['operations_and_tickets'] = ops
    work['log_items_json'] = copy.deepcopy(ops)
    rec = reconcile_report(work)
    for ev in rec['operations_and_tickets']:
        ev['operation_split_version'] = 2
    rec['log_items_json'] = copy.deepcopy(rec['operations_and_tickets'])
    verify = reconcile_report(rec)
    if verify['operations_and_tickets'] != rec['operations_and_tickets']:
        raise RuntimeError('reconcile_report 幂等校验失败')
    return {k: rec[k] for k in FIELDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', default='data/projects/daily_report_25_26/runtime/dispatch-repair-20260328.json')
    parser.add_argument('--restore')
    args = parser.parse_args()

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT inet_server_port() AS port, current_database() AS database')
            identity = dict(cur.fetchone())
            if identity != {'port': 5432, 'database': 'phoenix'}:
                raise RuntimeError(f'拒绝连接非目标库: {identity}')
            cur.execute('SELECT * FROM public.dispatch_daily_reports WHERE project_key=%s AND biz_date=%s FOR UPDATE', (PROJECT, DAY))
            row = cur.fetchone()
            if not row:
                raise RuntimeError('未找到 2026-03-28 记录')
            before = {k: row[k] for k in FIELDS}
            if args.restore:
                snap = json.loads(Path(args.restore).read_text(encoding='utf-8'))
                if snap['biz_date'] != DAY or before != snap['after']:
                    raise RuntimeError('快照不匹配或已有后续修改，拒绝回滚')
                after = snap['before']
            else:
                after = build_after(row)

            if args.apply:
                if not args.restore:
                    p = Path(args.backup)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with p.open('x', encoding='utf-8') as stream:
                        json.dump({'time': datetime.now(timezone.utc).isoformat(), 'biz_date': DAY, 'database': identity,
                                   'before': before, 'after': after}, stream, ensure_ascii=False, indent=2, default=str)
                cur.execute(
                    'UPDATE public.dispatch_daily_reports SET operations_and_tickets=%s, log_items_json=%s, updated_at=NOW() WHERE project_key=%s AND biz_date=%s',
                    tuple(Json(after[k]) for k in FIELDS) + (PROJECT, DAY),
                )
                assert cur.rowcount == 1
                conn.commit()
            else:
                conn.rollback()
            print(json.dumps({'applied': args.apply, 'restored': bool(args.restore), 'biz_date': DAY,
                              'database': identity, 'after': after['operations_and_tickets']}, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
