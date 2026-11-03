"""修复 2026-11-02 调度提取错误，默认预览；支持字段快照与定向回滚。

在页面后端容器中运行，--report 指向修正版提取 JSON，--apply 执行更新。
--restore 指向本脚本生成的快照；若目标字段已有后续修改则拒绝覆盖。
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
DAY = '2026-11-02'
METRICS = ('gw_high_temp_water', 'gw_lv1_heat', 'gw_lv3_heat',
           'gw_xh_ew_steam', 'gw_xb_link_steam', 'total_water_replenished')
JSON_FIELDS = ('boiler_turbine_status', 'eqp_status_json', 'operations_and_tickets', 'log_items_json')
FIELDS = METRICS + JSON_FIELDS


def repaired_fields(row, report):
    """仅修正已核对的字段；保留其他设备的人工确认及原有指标。"""
    if report.get('biz_date') != DAY or report.get('file_name') != '2026年11月2日生产信息.pdf':
        raise ValueError('修复来源的业务日期或文件名不匹配')
    expected = (17784, 4512, 1200, 1389, 1214, 4147)
    if tuple(report.get(k) for k in METRICS) != expected or report.get('status_conflicts'):
        raise ValueError('原文提取值或状态冲突不符合已核对的证据')
    if len(report.get('operations_and_tickets', [])) != 4:
        raise ValueError('原文操作记录数量异常')
    result = copy.deepcopy(row)
    for key in METRICS:
        if row[key] is not None and float(row[key]) != report[key]:
            raise ValueError(f'{key} 已有不同数值，拒绝覆盖')
        result[key] = report[key]
    facilities = result['boiler_turbine_status']
    target = [f for f in facilities if f['unit_or_plant'] == '香海电厂' and f['standard_name'] == '#3汽炉']
    if len(target) != 1 or target[0].get('status_confirmed'):
        raise ValueError('目标设备缺失、重复或已人工确认，拒绝覆盖')
    # 运行列中的启动描述保留为证据，不据此改写运行列状态。
    target[0]['status'] = target[0]['table_status'] = '运行'
    # 只有被截断的工作票续行会合并；其他原始操作必须仍与新提取一致。
    old_events = row['operations_and_tickets']
    new_events = report['operations_and_tickets']
    if [e['source_description'] for e in old_events[:3]] != [e['source_description'] for e in new_events[:3]]:
        raise ValueError('操作记录已有后续修改，拒绝覆盖')
    old_ticket = ''.join(e.get('source_description', e.get('raw_description', '')) for e in old_events[3:])
    if old_ticket != new_events[3]['source_description']:
        raise ValueError('工作票原文与修复来源不一致，拒绝覆盖')
    result['operations_and_tickets'] = copy.deepcopy(new_events)
    result = reconcile_report(result)
    return {key: result[key] for key in FIELDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', default='data/projects/daily_report_25_26/runtime/dispatch-repair-20261102.json')
    parser.add_argument('--restore')
    args = parser.parse_args()
    if not args.restore and not args.report:
        parser.error('需要 --report 或 --restore')
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT inet_server_port() AS port, current_database() AS database')
            identity = dict(cur.fetchone())
            if identity != {'port': 5432, 'database': 'phoenix'}:
                raise RuntimeError('请在页面后端容器内连接 phoenix 库执行，不使用备用库')
            cur.execute('SELECT * FROM public.dispatch_daily_reports WHERE project_key=%s AND biz_date=%s FOR UPDATE', (PROJECT, DAY))
            row = cur.fetchone()
            if not row:
                raise ValueError('目标日报不存在')
            before = {k: row[k] for k in FIELDS}
            if args.restore:
                snapshot = json.loads(Path(args.restore).read_text(encoding='utf-8'))
                if snapshot['biz_date'] != DAY or snapshot['project_key'] != PROJECT or before != snapshot['after']:
                    raise ValueError('快照不匹配或已有后续修改，拒绝回滚')
                after = snapshot['before']
            else:
                report = json.loads(Path(args.report).read_text(encoding='utf-8'))
                after = repaired_fields(dict(row), report)
            changed = [k for k in FIELDS if before[k] != after[k]]
            if args.apply and changed:
                if not args.restore:
                    with Path(args.backup).open('x', encoding='utf-8') as stream:
                        json.dump({'time': datetime.now(timezone.utc).isoformat(), 'project_key': PROJECT,
                                   'biz_date': DAY, 'database': identity, 'before': before, 'after': after},
                                  stream, ensure_ascii=False, indent=2, default=str)
                assignments = ', '.join(f'{k}=%s' for k in FIELDS)
                values = tuple(Json(after[k]) if k in JSON_FIELDS else after[k] for k in FIELDS)
                cur.execute(f'UPDATE public.dispatch_daily_reports SET {assignments}, updated_at=NOW() WHERE project_key=%s AND biz_date=%s', values + (PROJECT, DAY))
                if cur.rowcount != 1:
                    raise RuntimeError('更新行数异常')
                conn.commit()
            else:
                conn.rollback()
            print(json.dumps({'applied': args.apply, 'biz_date': DAY, 'changed_fields': changed,
                              'backup': args.backup}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
