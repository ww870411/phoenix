"""联合会审上线检查：隔离执行真实函数，不导入业务模块、不连接数据库。

轻量探针验证有限数量与标段资格；完整生命周期及并发使用独立 PostgreSQL 回归。
"""
import ast
import contextlib
import io
import json
import logging
import sys
import types
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'backend/projects/insulation_pipe_supply_2026/services/joint_review_service.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
names = {
    '_json_serialize_default', '_dumps_json', '_generate_review_no', '_get_delivery_info',
    'create_joint_review', 'get_arbitrator_accounts', '_check_user_can_vote_entity', '_apply_review_patch_to_order',
    '_revert_review_order_status', 'list_joint_reviews', '_validate_patch', '_lock_review_rows', '_restore_rows',
}
nodes = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
nodes += [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
nodes += [node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
          and any(isinstance(part, ast.Name) and part.id in {
              'PIPE_ALLOWED_PATCH_FIELDS', 'FITTING_ALLOWED_PATCH_FIELDS', 'FROZEN_FIELDS', 'PROJECT_KEY', 'DEFAULT_ARBITRATOR_ACCOUNTS'
          } for part in ast.walk(node))]


class HttpError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


class Result:
    def __init__(self, rows=(), scalar=None):
        self.rows, self.value = list(rows), scalar

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows

    def scalar(self):
        return self.value


class Session:
    def __init__(self):
        self.calls, self.commits = [], 0
        self.delivery = {
            'id': 1, 'order_no': 'TEST-1', 'shipment_no': 'SHIP-A',
            'supply_entity_id': 'SUP-A', 'section_1_id': 'LOT-A',
            'status': 'pending_arrival', 'shipped_qty': 10, 'arrived_qty': 10,
        }
        self.review_rows = []

    def execute(self, sql, params=None):
        sql, params = str(sql), dict(params or {})
        self.calls.append((sql, params))
        if 'SELECT COUNT(*)' in sql:
            return Result(scalar=len(self.review_rows))
        if 'SELECT r.*' in sql:
            offset, limit = params.get('offset', 0), params.get('limit', len(self.review_rows))
            return Result(self.review_rows[offset:offset + limit])
        if 'SELECT' in sql and ('FROM tube.tube_delivery' in sql or 'FROM tube.tube_fitting_delivery' in sql):
            return Result([self.delivery], scalar='旧备注')
        if 'INSERT INTO tube.tube_order_reviews' in sql:
            return Result(scalar=42)
        return Result()

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


ns = {
    'json': json, 'datetime': datetime, 'date': date, 'Decimal': Decimal, 'uuid4': uuid4,
    'logger': logging.getLogger('joint-review-audit-probe'),
    'BEIJING_TZ': ZoneInfo('Asia/Shanghai'), 'HTTPException': HttpError, 'text': str,
    'ensure_joint_review_tables': lambda: None,
    'resolve_accessible_section_1_ids': lambda cfg, user, group: {'LOT-A'},
    'resolve_accessible_supply_entity_ids': lambda cfg, user, group: {'SUP-A'},
    'load_tube_config': lambda: {'manager_assignments': [{'username': 'LOT-A经理', 'section_1_ids': ['LOT-A']}]},
    '_resolve_supplier_name': lambda cfg, key: key,
    '_resolve_section_name': lambda cfg, key: key,
    'check_user_can_arbitrate': lambda *args: False,
    'save_operation_log': lambda **kwargs: None,
}
exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(SOURCE), 'exec'), ns)

messages = []
message_module = types.ModuleType('backend.projects.insulation_pipe_supply_2026.services.system_message_service')
message_module.create_system_message = lambda **kwargs: messages.append(kwargs)
sys.modules[message_module.__name__] = message_module
auth_module = types.ModuleType('backend.services.auth_manager')
auth_module.auth_manager = types.SimpleNamespace(list_user_identities=lambda: [
    {'username': '测试供方', 'group': 'Global_admin'},
])
sys.modules[auth_module.__name__] = auth_module


def emit(name, symptom, evidence):
    print(json.dumps({'probe': name, 'symptom': bool(symptom), 'evidence': evidence}, ensure_ascii=False))


def create(patch):
    session = Session()
    ns['SessionLocal'] = lambda: session
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        response = ns['create_joint_review']('pipe', 1, patch, '现场核对差异', [], 'LOT-A经理', '测试经理', 'tube_site_manager')
    return session, response, output.getvalue()


if __name__ == '__main__':
    session, response, output = create({'shipped_qty': 8})
    emit('提请通知署名异常', not messages or bool(output), output)
    emit('发起缺少事务与行锁', not any('pg_advisory_xact_lock' in sql for sql, _ in session.calls)
         or not any('FOR UPDATE' in sql for sql, _ in session.calls), '真实函数锁语句检查')
    for value in [float('nan'), float('inf'), 0, '0.001']:
        rejected = False
        try:
            create({'shipped_qty': value})
        except HttpError:
            rejected = True
        emit('非法数量被接受', not rejected, str(value))
    emit('跨标段主管表决被接受', ns['_check_user_can_vote_entity'](
        {'entity_type': 'site_manager', 'entity_id': 'site_manager'}, 'LOT-A经理',
        'tube_site_manager', {}, 'LOT-B'), '标段B不在责任集合内')
    print('完整回归：docker exec phoenix_backend python -m unittest backend.projects.insulation_pipe_supply_2026.tests.test_joint_review_postgres -v')
