"""会审真实 PostgreSQL 回归：独立随机测试 schema，结束后删除，不写业务表。

运行：docker exec phoenix_backend python -m unittest backend.projects.insulation_pipe_supply_2026.tests.test_joint_review_postgres -v
通过 AST 加载真实函数，跳过模块导入时的业务 DDL，通知与审计采用捕获接口。
"""
import ast
import json
import logging
import re
import sys
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    get_config_list, resolve_accessible_section_1_ids, resolve_accessible_supply_entity_ids,
)


class JointReviewPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = 'jr_test_' + uuid4().hex
        session = SessionLocal()
        cls.engine = session.get_bind()
        session.close()
        cls.tables = ['tube_delivery', 'tube_fitting_delivery', 'tube_order_reviews', 'tube_review_votes']
        with cls.engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {cls.schema}'))
            for table in cls.tables:
                connection.execute(text(f'CREATE TABLE {cls.schema}.{table} (LIKE tube.{table} INCLUDING ALL)'))
                connection.execute(text(f'CREATE SEQUENCE {cls.schema}.{table}_seq'))
                connection.execute(text(f"ALTER TABLE {cls.schema}.{table} ALTER COLUMN id SET DEFAULT nextval('{cls.schema}.{table}_seq')"))
        source = Path(__file__).resolve().parents[1] / 'services/joint_review_service.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        nodes = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)]
        nodes += [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.Assign, ast.AnnAssign))]
        cls.cfg = {
            'manager_assignments': [{'username': 'manager-a', 'section_1_ids': ['A']}, {'username': 'manager-b', 'section_1_ids': ['B']}],
            'construction_units': [{'username': 'builder-a', 'section_1_ids': ['A']}],
            'warehouse_keepers': [{'username': 'keeper-a', 'section_1_ids': ['A']}],
            'supply_entities': [{'username': 'supplier-a', 'entity_id': 'SUP-A', 'entity_name': '测试厂家'}],
        }
        cls.messages, cls.audit = [], []
        message_module = types.ModuleType('backend.projects.insulation_pipe_supply_2026.services.system_message_service')
        message_module.create_system_message = lambda **kwargs: cls.messages.append(kwargs)
        sys.modules[message_module.__name__] = message_module
        auth_module = types.ModuleType('backend.services.auth_manager')
        identities = [{'username': u, 'group': g} for u, g in [
            ('manager-a', 'tube_site_manager'), ('manager-b', 'tube_site_manager'), ('supplier-a', 'tube_supplier')]]
        auth_module.auth_manager = types.SimpleNamespace(list_user_identities=lambda: identities)
        sys.modules[auth_module.__name__] = auth_module

        def isolated_text(sql):
            rewritten = re.sub(r'\btube\.(tube_delivery|tube_fitting_delivery|tube_order_reviews|tube_review_votes)\b',
                               lambda match: cls.schema + '.' + match.group(1), str(sql))
            return text(rewritten.replace("n.nspname = 'tube'", f"n.nspname = '{cls.schema}'"))

        cls.ns = dict(json=json, logging=logging, datetime=datetime, date=date, Decimal=Decimal,
                      ZoneInfo=ZoneInfo, uuid4=uuid4, HTTPException=HTTPException, text=isolated_text,
                      get_config_list=get_config_list, resolve_accessible_section_1_ids=resolve_accessible_section_1_ids,
                      resolve_accessible_supply_entity_ids=resolve_accessible_supply_entity_ids,
                      load_tube_config=lambda: cls.cfg, save_operation_log=lambda **kw: cls.audit.append(kw),
                      SessionLocal=sessionmaker(bind=cls.engine))
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(source), 'exec'), cls.ns)
        # 对隔离表执行真实初始化，兼容尚未增加会审字段的恢复数据库结构。
        cls.ns['ensure_joint_review_tables']()

    @classmethod
    def tearDownClass(cls):
        # schema 名称仅来自本测试生成的 UUID，清理范围固定为本次隔离制品。
        if not re.fullmatch(r'jr_test_[0-9a-f]{32}', cls.schema):
            raise RuntimeError('测试 schema 名称异常，拒绝清理')
        with cls.engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {cls.schema} CASCADE'))

    def setUp(self):
        with self.engine.begin() as connection:
            for table in reversed(self.tables):
                connection.execute(text(f'DELETE FROM {self.schema}.{table}'))
        self.messages.clear()
        self.audit.clear()

    def seed(self, category='pipe', row_id=1, status='pending_arrival', shipment='TEST-SHIP', section='A', remark='原备注'):
        values = dict(id=row_id, supply_entity_id='SUP-A', section_1_id=section, order_no=f'TEST-{row_id}',
                      shipment_no=shipment, vehicle_plate_no='TEST-PLATE', shipped_qty=10,
                      shipped_at=datetime.now(ZoneInfo('Asia/Shanghai')), status=status, ship_remark=remark)
        values.update(dict(pipe_model_id='TEST-MODEL') if category == 'pipe' else dict(fitting_type='测试管件', model_spec='TEST', unit='件'))
        if status in ('pending_receive', 'pending_diff_approve', 'pending_warehouse', 'completed'):
            values.update(arrived_qty=10, arrived_confirm_at=values['shipped_at'])
        if status in ('pending_warehouse', 'completed'):
            values['received_confirm_at'] = values['shipped_at']
            if category == 'pipe':
                values['received_qty'] = 10
        if status == 'completed':
            values['warehouse_confirm_at'] = values['shipped_at']
        if status == 'cancelled':
            values['cancel_at'] = values['shipped_at']
        table = 'tube_delivery' if category == 'pipe' else 'tube_fitting_delivery'
        with self.engine.begin() as connection:
            connection.execute(text(f"INSERT INTO {self.schema}.{table} ({','.join(values)}) VALUES ({','.join(':'+key for key in values)})"), values)

    def create(self, category='pipe', row_id=1, patch=None, user='manager-a', group='tube_site_manager'):
        return self.ns['create_joint_review'](category, row_id, patch if patch is not None else {'shipped_qty': 8},
                                              '现场核对更正', [], user, user, group)

    def vote(self, rid, decision='approve', user='supplier-a', group='tube_supplier'):
        return self.ns['vote_joint_review'](rid, decision, '核对现场意见', user, user, group)

    def rows(self, table):
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(text(f'SELECT * FROM {self.schema}.{table} ORDER BY id')).mappings()]

    def test_cross_section_and_foreign_duplicate_items(self):
        self.seed('fitting')
        self.seed('fitting', 2, shipment='OTHER')
        for patch, user in [({'shipped_qty': 8}, 'manager-b'), ({'items': [{'id': 2, 'shipped_qty': 8}]}, 'manager-a'),
                            ({'items': [{'id': 1, 'shipped_qty': 8}, {'id': 1, 'shipped_qty': 9}]}, 'manager-a')]:
            with self.assertRaises(HTTPException):
                self.create('fitting', patch=patch, user=user)
        self.assertEqual(self.rows('tube_order_reviews'), [])
        self.assertTrue(all(row['status'] == 'pending_arrival' for row in self.rows('tube_fitting_delivery')))

    def test_nonfinite_precision_and_text_length(self):
        self.seed()
        for qty in [float('nan'), float('inf'), -1, 0, '0.001', '10000000000000000']:
            with self.assertRaises(HTTPException):
                self.create(patch={'shipped_qty': qty})
        with self.assertRaises(HTTPException):
            self.create(patch={'vehicle_plate_no': 'x' * 33})
        self.assertEqual(self.rows('tube_order_reviews'), [])

    def test_all_stages_all_lifecycles(self):
        for category in ['pipe', 'fitting']:
            for status, user, group in [('pending_arrival', 'manager-a', 'tube_site_manager'),
                                        ('pending_receive', 'builder-a', 'tube_construction_unit'),
                                        ('pending_diff_approve', 'builder-a', 'tube_construction_unit'),
                                        ('pending_warehouse', 'keeper-a', 'tube_warehouse_keeper')]:
                for outcome in ['consensus', 'cancel', 'force_approve', 'force_reject']:
                    with self.subTest(category=category, status=status, outcome=outcome):
                        self.setUp()
                        self.seed(category, status=status)
                        rid = self.create(category, user=user, group=group)['review_id']
                        if outcome == 'consensus':
                            self.vote(rid, 'reject')
                            self.assertTrue(self.ns['get_joint_review_detail'](rid, 'supplier-a', 'tube_supplier')['data']['can_i_vote'])
                            self.vote(rid)
                            if status != 'pending_arrival':
                                with self.assertRaises(HTTPException):
                                    self.vote(rid, user='manager-b', group='tube_site_manager')
                                self.vote(rid, user='manager-a', group='tube_site_manager')
                        elif outcome == 'cancel':
                            self.ns['cancel_joint_review'](rid, '现场撤回', user, group)
                        else:
                            self.ns['admin_arbitrate_joint_review'](rid, outcome, '现场终局核实', 'admin', 'Global_admin')
                        table = 'tube_delivery' if category == 'pipe' else 'tube_fitting_delivery'
                        row = self.rows(table)[0]
                        self.assertEqual(row['status'], status)
                        self.assertIsNone(row['pre_review_status'])
                        self.assertEqual(row['shipped_qty'], Decimal(8 if outcome in ['consensus', 'force_approve'] else 10))
                        with self.assertRaises(HTTPException):
                            self.vote(rid)

    def test_mixed_shipment_fields_snapshot_and_revert(self):
        for outcome in ['approve', 'cancel']:
            self.setUp()
            for rid, status in [(1, 'pending_arrival'), (2, 'pending_arrival'), (3, 'completed'), (4, 'cancelled'), (5, 'pending_warehouse')]:
                self.seed('fitting', rid, status=status, remark=f'原备注{rid}')
            before = self.rows('tube_fitting_delivery')
            patch = {'items': [{'id': 2, 'shipped_qty': 6}], 'ship_contact_name': '新联系人',
                     'ship_contact_phone': '123', 'vehicle_plate_no': 'NEW-PLATE'}
            rid = self.create('fitting', patch=patch)['review_id']
            self.assertEqual(len(self.rows('tube_order_reviews')[0]['original_snapshot']['items']), 2)
            if outcome == 'approve':
                self.vote(rid)
            else:
                self.ns['cancel_joint_review'](rid, '撤回', 'manager-a', 'tube_site_manager')
            after = self.rows('tube_fitting_delivery')
            self.assertEqual(before[2:], after[2:])
            for row in after[:2]:
                self.assertEqual(row['status'], 'pending_arrival')
                self.assertIn(f"原备注{row['id']}", row['ship_remark'])
                if outcome == 'approve':
                    self.assertEqual(row['ship_contact_name'], '新联系人')
                    self.assertEqual(row['ship_contact_phone'], '123')
                    self.assertEqual(row['vehicle_plate_no'], 'NEW-PLATE')

    def test_remarks_and_empty_clarification(self):
        for category in ['pipe', 'fitting']:
            self.setUp()
            self.seed(category)
            rid = self.create(category, patch={'ship_remark': '更正备注'})['review_id']
            self.vote(rid)
            table = 'tube_delivery' if category == 'pipe' else 'tube_fitting_delivery'
            self.assertTrue(self.rows(table)[0]['ship_remark'].startswith('更正备注\n'))
        self.setUp()
        self.seed()
        self.vote(self.create(patch={})['review_id'])
        self.assertEqual(self.rows('tube_delivery')[0]['shipped_qty'], 10)

    def test_pending_pagination_notifications_and_detail(self):
        for rid in range(1, 5):
            self.seed(row_id=rid, shipment=f'SHIP-{rid}')
            self.create(row_id=rid)
        args = dict(tab='pending_my_vote', limit=1, session_username='supplier-a', session_group='tube_supplier')
        first = self.ns['list_joint_reviews'](**args)
        second = self.ns['list_joint_reviews'](**args, page=2)
        self.assertEqual(first['total'], 4)
        self.assertNotEqual(first['items'][0]['id'], second['items'][0]['id'])
        self.assertEqual({msg['receiver_username'] for msg in self.messages}, {'supplier-a'})
        self.setUp()
        self.seed(status='pending_receive')
        rid = self.create(user='builder-a', group='tube_construction_unit')['review_id']
        self.assertEqual({msg['receiver_username'] for msg in self.messages}, {'supplier-a', 'manager-a'})
        self.assertEqual(self.ns['get_pending_review_notifications']('manager-b', 'tube_site_manager')['pending_count'], 0)
        self.assertEqual(self.ns['get_joint_review_detail'](rid, 'manager-b', 'tube_site_manager')['data']['can_i_vote'], False)

    def test_two_transactions_same_shipment(self):
        for category, ids in [('pipe', [1, 1]), ('fitting', [1, 1]), ('fitting', [1, 2])]:
            with self.subTest(category=category, ids=ids):
                self.setUp()
                self.seed(category)
                if 2 in ids:
                    self.seed(category, 2)
                gate = Barrier(2)

                def run(row_id):
                    gate.wait(timeout=10)
                    try:
                        return self.create(category, row_id=row_id)['ok']
                    except HTTPException as exc:
                        return exc.status_code

                with ThreadPoolExecutor(max_workers=2) as pool:
                    outcomes = list(pool.map(run, ids))
                self.assertEqual(sorted(str(value) for value in outcomes), ['409', 'True'])
                self.assertEqual(len(self.rows('tube_order_reviews')), 1)

    def test_last_vote_cancel_race(self):
        self.seed()
        rid = self.create()['review_id']
        gate = Barrier(2)

        def run(action):
            gate.wait(timeout=10)
            try:
                if action == 'vote':
                    return self.vote(rid)['ok']
                return self.ns['cancel_joint_review'](rid, '撤回', 'manager-a', 'tube_site_manager')['ok']
            except HTTPException as exc:
                return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(run, ['vote', 'cancel']))
        self.assertEqual(sum(value is True for value in outcomes), 1)
        self.assertIn(self.rows('tube_order_reviews')[0]['review_status'], ['approved', 'cancelled'])
        self.assertEqual(self.rows('tube_delivery')[0]['status'], 'pending_arrival')

    def test_final_apply_revalidates_freeze_and_previous_vote_audit(self):
        self.seed()
        rid = self.create()['review_id']
        self.vote(rid, 'reject')
        with self.engine.begin() as connection:
            connection.execute(text(f"UPDATE {self.schema}.tube_delivery SET status='pending_arrival' WHERE id=1"))
        with self.assertRaises(HTTPException):
            self.vote(rid)
        self.assertEqual(self.rows('tube_review_votes')[0]['vote_decision'], 'reject')
        with self.engine.begin() as connection:
            connection.execute(text(f"UPDATE {self.schema}.tube_delivery SET status='under_review' WHERE id=1"))
        self.vote(rid)
        self.assertEqual(self.audit[-1]['before_value']['previous_vote']['vote_decision'], 'reject')

    def test_initialization_failure_is_not_swallowed(self):
        previous_factory, previous_state = self.ns['SessionLocal'], self.ns['_tables_initialized']

        class BrokenSession:
            def execute(self, *args):
                raise RuntimeError('模拟DDL失败')
            def rollback(self):
                pass
            def close(self):
                pass

        self.ns['SessionLocal'] = BrokenSession
        self.ns['_tables_initialized'] = False
        try:
            with self.assertRaises(RuntimeError):
                self.ns['ensure_joint_review_tables']()
            self.assertFalse(self.ns['_tables_initialized'])
        finally:
            self.ns['SessionLocal'], self.ns['_tables_initialized'] = previous_factory, previous_state


if __name__ == '__main__':
    unittest.main()
