"""验证公用账号能查看报表，但提交与审批等写操作在读取请求或落库前被拒绝。"""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from backend.projects.daily_report_25_26.api import legacy_full as api
from backend.services.auth_manager import AuthManager


class ViewerReadonlyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = AuthManager()
        cls.manager._ensure_loaded()
        record = cls.manager._users_by_name['nyjt']
        cls.session = cls.manager._build_session(
            record, cls.manager._groups[record.group], 'readonly-test',
            datetime.now(timezone.utc), None, False,
        )

    def test_report_pages_visible_and_all_write_actions_disabled(self):
        """三个入口与表单可查看，原有动作权限全部保持关闭。"""
        permission = self.session.resolve_project_permissions('daily_report_25_26')
        for page in ('data_entry', 'data_approval', 'constant_data'):
            with self.subTest(page=page):
                self.assertIn(page, permission.page_access)
                self.assertEqual(permission.sheet_rules[page].mode, 'all')
        self.assertFalse(any(vars(permission.actions).values()))

    def test_daily_inventory_and_constant_submit_denied_before_reading_body(self):
        """使用真实提交调度函数，拒绝发生在请求体解析和任何处理器调用之前。"""
        for sheet in ('BeiHai_co_generation_Sheet', 'Coal_inventory_Sheet', 'constant_test'):
            with self.subTest(sheet=sheet):
                request = SimpleNamespace(json=AsyncMock(side_effect=AssertionError('不应读取提交内容')))
                with patch.object(api, 'SessionLocal') as database:
                    with self.assertRaises(HTTPException) as rejected:
                        asyncio.run(api.submit_debug(request, sheet, self.session))
                    self.assertEqual(rejected.exception.status_code, 403)
                    request.json.assert_not_awaited()
                    database.assert_not_called()

    def test_workflow_mutations_and_management_switches_denied(self):
        """审批、撤销、发布及配置开关均按现有后端权限拒绝。"""
        payload = SimpleNamespace(unit='BeiHai', confirm=True)
        with patch.object(api, 'workflow_status_manager') as workflow:
            for endpoint in (api.approve_unit_workflow, api.revoke_unit_workflow, api.publish_daily_report):
                with self.subTest(endpoint=endpoint.__name__):
                    with self.assertRaises(HTTPException) as rejected:
                        endpoint(payload, self.session)
                    self.assertEqual(rejected.exception.status_code, 403)
            self.assertEqual(workflow.mock_calls, [])
        for guard in (api._ensure_manage_validation_permission, api._ensure_manage_ai_settings_permission,
                      api._ensure_manage_ai_sheet_switch_permission):
            with self.subTest(guard=guard.__name__):
                with self.assertRaises(HTTPException) as rejected:
                    guard(self.session)
                self.assertEqual(rejected.exception.status_code, 403)

    def test_all_units_accessible_for_data_analysis(self):
        """验证 nyjt 账号具备全口径查询权限（units_access 配置 * 展开为全部单位），Schema 返回完整单位字典。"""
        allowed = self.session.resolve_allowed_units('daily_report_25_26')
        target_units = ('Group', 'ZhuChengQu', 'BeiHai', 'JinZhou', 'BeiFang', 'JinPu', 'ZhuangHe', 'XiangHai', 'GongRe', 'YanJiuYuan')
        for unit in target_units:
            with self.subTest(unit_allowed=unit):
                self.assertIn(unit, allowed)
        response = api.get_data_analysis_schema(config=None, session=self.session)
        import json
        body = json.loads(response.body)
        unit_dict = body.get('unit_dict', {})
        for unit in target_units:
            with self.subTest(unit_schema=unit):
                self.assertIn(unit, unit_dict)
