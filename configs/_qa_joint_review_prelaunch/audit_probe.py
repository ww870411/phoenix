"""联合会审上线检查：隔离执行真实函数，不导入业务模块、不连接数据库。

退出码 0 表示诊断探针完成，不表示上线验收通过；输出 symptom=true 表示问题复现。
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
    '_revert_review_order_status', 'list_joint_reviews',
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
            'supply_entity_id': 'SUP-A', 'section_1_id': 'LOT-B',
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


def emit(name, symptom, evidence):
    print(json.dumps({'probe': name, 'symptom': bool(symptom), 'evidence': evidence}, ensure_ascii=False))


def create(patch):
    session = Session()
    ns['SessionLocal'] = lambda: session
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        response = ns['create_joint_review']('pipe', 1, patch, '现场核对差异', [], 'LOT-A经理', '测试经理', 'tube_site_manager')
    return session, response, output.getvalue()


session, response, output = create({'shipped_qty': 8})
emit('跨标段发起被接受', response['ok'], 'LOT-A经理成功为LOT-B单据创建会审')
emit('到货量大于拟发货量仍可提请', response['ok'], 'arrived_qty=10，proposed shipped_qty=8，创建成功')
emit('发起通知阶段未定义变量', not messages and 'initiator_name' in output, output.strip())
emit('发起缺少订单行锁', not any('FOR UPDATE' in sql for sql, _ in session.calls), 'create查询和冻结之间无行锁；并发风险需数据库双事务验收')

session, response, output = create({'shipped_qty': float('nan')})
emit('非有限数量被接受', response['ok'], 'NaN通过>0校验，JSON序列化包含NaN')

emit('现场主管表决不检查标段', ns['_check_user_can_vote_entity'](
    {'entity_type': 'site_manager', 'entity_id': 'site_manager'}, 'LOT-A经理', 'tube_site_manager', {}
), '角色符合即可返回True，不接收议案section_1_id')

session = Session()
ns['SessionLocal'] = lambda: session
review = {'order_category': 'fitting', 'delivery_id': 1, 'pre_status': 'pending_arrival'}
ns['_apply_review_patch_to_order'](session, review, {'items': [{'id': 999, 'shipped_qty': 3}]}, '测试决议')
foreign_updates = [(sql, params) for sql, params in session.calls if params.get('it_id') == 999]
emit('明细ID缺少车次归属核验', bool(foreign_updates) and 'shipment_no' not in foreign_updates[0][0], 'UPDATE WHERE id=999，无车次/标段/状态限定')
state_updates = [sql for sql, _ in session.calls if 'SET status = :restored_status' in sql]
emit('整车恢复覆盖非挂起明细', bool(state_updates) and "status = 'under_review'" not in state_updates[0], '恢复WHERE只有shipment_no，同车完成/撤销明细也进入更新范围')

session = Session()
ns['_apply_review_patch_to_order'](session, review, {'ship_contact_name': '新联系人', 'ship_contact_phone': 'TEST', 'ship_remark': '新备注'}, '测试决议')
emit('管件联系人和拟更正备注未生效', not any('新联系人' in params.values() or '新备注' in params.values() for _, params in session.calls), '白名单允许字段，实际执行未应用这些patch值')

session = Session()
session.review_rows = [
    {'id': i, 'review_status': 'voting', 'initiator_username': '测试人', 'section_1_id': 'LOT-B',
     'supply_entity_id': 'SUP-A', 'required_entities': [{'entity_type': 'site_manager', 'entity_id': 'site_manager'}],
     'approved_entities': [], 'rejected_entities': []}
    for i in range(3)
]
ns['SessionLocal'] = lambda: session
one = ns['list_joint_reviews'](tab='pending_my_vote', limit=1, session_username='测试经理', session_group='tube_site_manager')
emit('个人待办总数受limit影响', one['total'] == 1, {'真实夹具待办总数': 3, 'limit': 1, '返回total': one['total']})

class FrozenDatetime:
    ticks = iter([datetime(2026, 10, 9, 10, 0, 0, 120001), datetime(2026, 10, 9, 10, 0, 0, 129999)])

    @classmethod
    def now(cls, tz):
        return next(cls.ticks)

ns['datetime'] = FrozenDatetime
first, second = ns['_generate_review_no'](), ns['_generate_review_no']()
emit('同10毫秒窗口会审编号重复', first == second, [first, second])
ns['datetime'] = datetime
