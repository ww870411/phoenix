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

    def test_group_meeting_reject_reverts_order_and_fails_negotiation(self):
        """现场小组会有人提出异议时：立即判定协商失败，会审终结为 rejected，订单原子恢复发起前状态。"""
        self.seed('pipe', 1, status='pending_arrival')
        created = self.ns['create_joint_review'](
            'pipe', 1, {'shipped_qty': 8}, '现场协同修正数量', [],
            'manager-a', '张经理', 'tube_site_manager',
            review_type='group_meeting', invited_users=['supplier-a']
        )
        rid = created['review_id']
        self.assertEqual(self.rows('tube_delivery')[0]['status'], 'under_review')

        # 成员投反对票
        res = self.ns['vote_joint_review'](
            rid, 'reject', '现场实测数量确实只有10米，不同意改为8米',
            'supplier-a', '李厂家', 'tube_supplier'
        )
        self.assertTrue(res['ok'])
        self.assertEqual(res['review_status'], 'rejected')
        self.assertEqual(res['status_display'], '协商失败')
        self.assertTrue(res['is_finalized'])
        self.assertEqual(res['restored_status'], 'pending_arrival')

        # 验证业务单据直接恢复原状
        self.assertEqual(self.rows('tube_delivery')[0]['status'], 'pending_arrival')

        # 验证会审表状态
        rev_row = self.rows('tube_order_reviews')[0]
        self.assertEqual(rev_row['review_status'], 'rejected')
        self.assertIn('协商失败', rev_row['resolution_summary'])

        # 验证操作审计与系统消息
        self.assertEqual(self.audit[-1]['action_type'], 'GROUP_MEETING_REJECTED')
        self.assertTrue(any('协商失败' in m.get('title', '') for m in self.messages))

    def test_group_meeting_privacy_masking_for_third_party(self):
        """小组会议隐私保护：非当事人/非超管仅能见基本条目，具体内容脱敏掩码。"""
        self.seed('pipe', 1, status='pending_arrival')
        created = self.ns['create_joint_review'](
            'pipe', 1, {'shipped_qty': 8}, '现场小范围修正事由（保密）', [],
            'manager-a', '张经理', 'tube_site_manager',
            review_type='group_meeting', invited_users=['supplier-a']
        )
        rid = created['review_id']

        # 1. 发起人视角：能看完整内容
        res_init = self.ns['list_joint_reviews'](tab='all', review_id=rid, session_username='manager-a', session_group='tube_site_manager')
        item_init = res_init['items'][0]
        self.assertFalse(item_init['is_private_masked'])
        self.assertEqual(item_init['review_reason'], '现场小范围修正事由（保密）')
        self.assertEqual(str(item_init['proposed_patch']['shipped_qty']), '8')

        # 2. 受邀成员视角：能看完整内容
        res_inv = self.ns['list_joint_reviews'](tab='all', review_id=rid, session_username='supplier-a', session_group='tube_supplier')
        item_inv = res_inv['items'][0]
        self.assertFalse(item_inv['is_private_masked'])
        self.assertEqual(item_inv['review_reason'], '现场小范围修正事由（保密）')

        # 3. Global_admin 视角：能看完整内容
        res_adm = self.ns['list_joint_reviews'](tab='all', review_id=rid, session_username='ww870411', session_group='Global_admin')
        item_adm = res_adm['items'][0]
        self.assertFalse(item_adm['is_private_masked'])
        self.assertEqual(item_adm['review_reason'], '现场小范围修正事由（保密）')

        # 4. 第三方无关用户（如 manager-b）视角：脱敏受保护
        res_other = self.ns['list_joint_reviews'](tab='all', review_id=rid, session_username='manager-b', session_group='tube_site_manager')
        item_other = res_other['items'][0]
        self.assertTrue(item_other['is_private_masked'])
        # 基本信息依然可见
        self.assertEqual(item_other['id'], rid)
        self.assertEqual(item_other['review_type'], 'group_meeting')
        self.assertEqual(item_other['order_no'], 'TEST-1')
        self.assertEqual(item_other['review_status'], 'voting')
        # 敏感具体内容被脱敏遮蔽
        self.assertIn('保密事项', item_other['review_reason'])
        self.assertTrue(item_other['proposed_patch'].get('_masked'))
        self.assertTrue(item_other['original_snapshot'].get('_masked'))
        self.assertEqual(item_other['attachments'], [])
        self.assertFalse(item_other['can_i_vote'])
        self.assertFalse(item_other['can_cancel'])
        self.assertFalse(item_other['can_arbitrate'])

    def test_group_meeting_full_consensus_and_voter_clean_name(self):
        """小组会议全员一致核准、签署人防标段串清洗及订单原子修单验证。"""
        self.seed('pipe', 1, status='pending_arrival')
        created = self.ns['create_joint_review'](
            'pipe', 1, {'shipped_qty': 12.5}, '现场随车磅单核实，实发12.5米', [],
            'manager-a', '张主管', 'tube_site_manager',
            review_type='group_meeting', invited_users=['supplier-a']
        )
        rid = created['review_id']

        # 1. 验证未受邀者（例如 manager-b）尝试签署会被拦截 403
        with self.assertRaises(HTTPException) as ctx:
            self.ns['vote_joint_review'](
                rid, 'approve', '我来替他通过', 'manager-b', 'manager-b', 'tube_site_manager'
            )
        self.assertEqual(ctx.exception.status_code, 403)

        # 2. 受邀人 supplier-a 表决通过，且模拟 session_name 传了逗号标段串（如 'high_lot_1,low_lot_2'）
        res_vote = self.ns['vote_joint_review'](
            rid, 'approve', '供方核对随车磅单无误，同意更正',
            'supplier-a', 'high_lot_1,high_lot_2,low_lot_1', 'tube_supplier'
        )
        self.assertEqual(res_vote['review_status'], 'approved')
        self.assertTrue(res_vote['is_finalized'])

        # 3. 验证数据库中入库的 voter_name 被清洗为纯净 username，无逗号标段残留
        vote_rows = self.rows('tube_review_votes')
        self.assertEqual(len(vote_rows), 1)
        self.assertEqual(vote_rows[0]['voter_username'], 'supplier-a')
        self.assertEqual(vote_rows[0]['voter_name'], 'supplier-a')

        # 4. 验证业务订单数据已原子更新
        del_row = self.rows('tube_delivery')[0]
        self.assertEqual(del_row['status'], 'pending_arrival')
        self.assertEqual(float(del_row['shipped_qty']), 12.5)

        # 5. 验证会审单终结决议文本
        rev_row = self.rows('tube_order_reviews')[0]
        self.assertEqual(rev_row['review_status'], 'approved')
        self.assertIn('小组会议', rev_row['resolution_summary'])
        self.assertIn('小组成员一致同意通过', rev_row['resolution_summary'])

        # 6. 验证列表查询 votes 装配的 voter_name 也为纯净人名
        list_res = self.ns['list_joint_reviews'](tab='all', review_id=rid, session_username='manager-a', session_group='tube_site_manager')
        item = list_res['items'][0]
        self.assertEqual(item['votes'][0]['voter_name'], 'supplier-a')
        self.assertEqual(item['approval_type'], 'consensus')

    def test_group_meeting_candidate_range_and_invitation_restriction(self):
        """小组会议候选人范围与受邀资格拦截验证：仅允许供给方人员、Global_admin和仲裁人员。"""
        self.seed('pipe', 1, status='pending_arrival')
        cand_res = self.ns['get_order_meeting_candidates'](
            'pipe', 1, 'manager-a', '张主管', 'tube_site_manager'
        )
        cands = cand_res['candidates']
        self.assertTrue(len(cands) > 0)
        # 验证所有候选人的 entity_type 只能是 supplier, global_admin, arbitrator
        valid_types = {'supplier', 'global_admin', 'arbitrator'}
        for c in cands:
            self.assertIn(c['entity_type'], valid_types)
            self.assertNotIn(c['entity_type'], {'site_manager', 'warehouse_keeper', 'construction_unit'})

        # 尝试越界邀请未被允许的现场负责人（如 manager-b），必须被 422 拦截
        with self.assertRaises(HTTPException) as ctx:
            self.ns['create_joint_review'](
                'pipe', 1, {'shipped_qty': 11}, '尝试越权邀请现场主管', [],
                'manager-a', '张主管', 'tube_site_manager',
                review_type='group_meeting',
                invited_users=[{'username': 'manager-b', 'entity_type': 'site_manager'}]
            )
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn('不符合受邀资质', ctx.exception.detail)

        # 正常邀请供给方人员（supplier-a）或 Global_admin（ww870411），创建成功
        created = self.ns['create_joint_review'](
            'pipe', 1, {'shipped_qty': 11}, '正常邀请供方和超管协同', [],
            'manager-a', '张主管', 'tube_site_manager',
            review_type='group_meeting',
            invited_users=[
                {'username': 'supplier-a', 'entity_type': 'supplier'},
                {'username': 'ww870411', 'entity_type': 'global_admin'},
            ]
        )
        self.assertTrue(created['ok'])

    def test_arbitrator_rights_split_between_joint_review_and_group_meeting(self):
        """仲裁员权限分流验证：对多方联合会审拥有裁决权，对小组会议只享有受邀表决权而无仲裁权。"""
        # 1. 场景 A: 多方联合会审 (joint_review)
        self.seed('pipe', 1, status='pending_arrival')
        jr_created = self.ns['create_joint_review'](
            'pipe', 1, {'shipped_qty': 13}, '联合会审事由', [],
            'manager-a', '张主管', 'tube_site_manager',
            review_type='joint_review'
        )
        jr_id = jr_created['review_id']

        # 特许仲裁员（王玮，非超管）查看联合会审：拥有仲裁权 can_arbitrate == True
        res_jr = self.ns['list_joint_reviews'](
            tab='all', review_id=jr_id, session_username='王玮', session_group='tube_site_manager'
        )
        self.assertTrue(res_jr['items'][0]['can_arbitrate'])

        # 王玮可以成功执行终局裁决
        arb_res = self.ns['admin_arbitrate_joint_review'](
            review_id=jr_id,
            arbitration_decision='force_approve',
            arbitration_reason='事实清楚，准予裁决更正',
            session_username='王玮',
            session_group='tube_site_manager'
        )
        self.assertTrue(arb_res['ok'])
        self.assertEqual(arb_res['review_status'], 'approved')

        # 2. 场景 B: 小组会议 (group_meeting)
        self.seed('pipe', 2, status='pending_arrival')
        gm_created = self.ns['create_joint_review'](
            'pipe', 2, {'shipped_qty': 15}, '小组会议事由', [],
            'manager-a', '张主管', 'tube_site_manager',
            review_type='group_meeting',
            invited_users=[{'username': '王玮', 'entity_type': 'arbitrator'}]
        )
        gm_id = gm_created['review_id']

        # 特许仲裁员（王玮）查看小组会议：
        res_gm = self.ns['list_joint_reviews'](
            tab='all', review_id=gm_id, session_username='王玮', session_group='tube_site_manager'
        )
        item_gm = res_gm['items'][0]
        # 核心断言：只有表决权（can_i_vote == True），而无仲裁权（can_arbitrate == False）！
        self.assertTrue(item_gm['can_i_vote'])
        self.assertFalse(item_gm['can_arbitrate'])

        # 若尝试以仲裁员身份对小组会进行终局裁决强裁，接口必须抛出 403 明确拦截
        with self.assertRaises(HTTPException) as ctx:
            self.ns['admin_arbitrate_joint_review'](
                review_id=gm_id,
                arbitration_decision='force_approve',
                arbitration_reason='尝试强行裁决小组会',
                session_username='王玮',
                session_group='tube_site_manager'
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn('小组会议不设特许仲裁权', ctx.exception.detail)

        # 王玮作为受邀参会人员，正常行使表决权进行投票核准
        vote_res = self.ns['vote_joint_review'](
            review_id=gm_id,
            vote_decision='approve',
            vote_opinion='王玮核对无误，以小组成员身份同意',
            session_username='王玮',
            session_name='王玮',
            session_group='tube_site_manager'
        )
        self.assertTrue(vote_res['ok'])
        self.assertEqual(vote_res['review_status'], 'approved')

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
