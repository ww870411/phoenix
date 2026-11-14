# -*- coding: utf-8 -*-
"""
daily_report_25_26 业务操作审计日志服务与前端客户端上报接口单元测试。
"""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from backend.projects.daily_report_25_26.api.global_management import (
    ClientOperationLogPayload,
    record_client_operation_log,
)
from backend.projects.daily_report_25_26.services import audit_log_service


class _MockResult:
    """模拟 SQLAlchemy execute() 返回结果。"""

    def __init__(self, rows=None, scalar_val=None, rowcount=0):
        self._rows = rows or []
        self._scalar = scalar_val
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def scalar(self):
        return self._scalar


class OperationAuditLogsTests(unittest.TestCase):
    """验证审计日志去种子化、单位归一化、白名单上报与幂等回填。"""

    def test_ensure_table_never_auto_seeds_empty_table(self) -> None:
        """初始化业务操作日志表时，绝不能向空表灌入虚构演示种子数据。"""
        fake_session = MagicMock()
        audit_log_service._table_ensured = False
        try:
            with patch.object(audit_log_service, "SessionLocal", return_value=fake_session):
                audit_log_service.ensure_daily_report_operation_logs_table()
        finally:
            audit_log_service._table_ensured = False

        sql_statements = [str(call.args[0]) for call in fake_session.execute.call_args_list]
        self.assertTrue(any("CREATE TABLE IF NOT EXISTS logs.daily_report_operation_logs" in s for s in sql_statements))
        self.assertFalse(any("INSERT INTO logs.daily_report_operation_logs" in s for s in sql_statements))
        fake_session.commit.assert_called_once()

    def test_normalize_unit_label(self) -> None:
        """单位代号应正确映射为标准中文单位名称。"""
        self.assertEqual(audit_log_service.normalize_unit_label("BeiHai"), "北海热电厂")
        self.assertEqual(audit_log_service.normalize_unit_label("Group"), "洁净能源集团")
        self.assertEqual(audit_log_service.normalize_unit_label("ZhuChengQu"), "主城区")
        self.assertEqual(audit_log_service.normalize_unit_label("系统管理员"), "集团全局管理")
        self.assertEqual(audit_log_service.normalize_unit_label("自定义中心"), "自定义中心")
        self.assertEqual(audit_log_service.normalize_unit_label(None), "")

    def test_client_operation_log_whitelist_accepts_and_rejects(self) -> None:
        """前端日志上报接口仅允许白名单内的纯客户端导出动作。"""
        session = SimpleNamespace(username="tester", user_group="Global_admin", unit="Group")
        request = SimpleNamespace(headers={"x-real-ip": "10.0.0.8"}, client=SimpleNamespace(host="127.0.0.1"))

        with patch("backend.projects.daily_report_25_26.api.global_management.log_session_operation") as mocked_log:
            res = record_client_operation_log(
                payload=ClientOperationLogPayload(
                    action_type="EXPORT_DASHBOARD_PDF",
                    action_desc="导出看板 PDF",
                    resource_id="dashboard:2026-11-13",
                    after_value={"biz_date": "2026-11-13"},
                ),
                request=request,
                session=session,
            )
            self.assertEqual(res, {"ok": True})
            mocked_log.assert_called_once()

        with self.assertRaises(HTTPException) as ctx:
            record_client_operation_log(
                payload=ClientOperationLogPayload(
                    action_type="APPROVE_UNIT",
                    action_desc="非法越权上报审批",
                ),
                request=request,
                session=session,
            )
        self.assertEqual(ctx.exception.status_code, 422)

    def test_map_system_audit_click(self) -> None:
        """前端点击埋点映射应覆盖导出 PDF/Excel、填报与忽略无效导航点击。"""
        pdf_row = SimpleNamespace(
            target="下载PDF",
            page="/projects/daily_report_25_26/pages/dashboard/dashboard",
            unit="系统管理员",
        )
        mapped_pdf = audit_log_service._map_system_audit_click(pdf_row)
        self.assertIsNotNone(mapped_pdf)
        self.assertEqual(mapped_pdf["action_type"], "EXPORT_DASHBOARD_PDF")

        submit_row = SimpleNamespace(
            target="提交",
            page="/projects/daily_report_25_26/data_entry/sheets/BeiHai_co_generation_sheet?date=2026-11-13",
            unit="BeiHai",
        )
        mapped_submit = audit_log_service._map_system_audit_click(submit_row)
        self.assertIsNotNone(mapped_submit)
        self.assertEqual(mapped_submit["action_type"], "SUBMIT_ENTRY")
        self.assertEqual(mapped_submit["resource_id"], "sheet:BeiHai_co_generation_sheet")

        noise_row = SimpleNamespace(target="返回首页", page="/home", unit="BeiHai")
        self.assertIsNone(audit_log_service._map_system_audit_click(noise_row))

    def test_backfill_idempotency_preserves_two_second_debounce(self) -> None:
        """首次回填被 2 秒防抖过滤的双击点击，在第二次回填时也绝不能被补录。"""
        t0 = datetime(2026, 11, 13, 9, 39, 53, tzinfo=timezone.utc)
        click_a = SimpleNamespace(
            id=75161,
            ts=t0,
            username="ww870411",
            user_group="Global_admin",
            unit="系统管理员",
            page="/projects/daily_report_25_26/pages/dashboard/dashboard",
            target="下载PDF",
            client_ip="10.0.0.1",
        )
        click_b_double = SimpleNamespace(
            id=75162,
            ts=t0 + timedelta(milliseconds=600),
            username="ww870411",
            user_group="Global_admin",
            unit="系统管理员",
            page="/projects/daily_report_25_26/pages/dashboard/dashboard",
            target="下载PDF",
            client_ip="10.0.0.1",
        )

        # 模拟第一次已经写入 75161，第二次扫描到 75161 和 75162 时 75162 仍应被抑制
        fake_session = MagicMock()
        fake_session.execute.side_effect = [
            _MockResult(rows=[("75161",)]),
            _MockResult(rows=[click_a, click_b_double]),
        ]

        with patch.object(audit_log_service, "ensure_daily_report_operation_logs_table"), \
             patch.object(audit_log_service, "SessionLocal", return_value=fake_session):
            inserted = audit_log_service.backfill_from_system_audit_logs(days=30)

        self.assertEqual(inserted, 0)
        # 仅有 2 次 SELECT 查询，没有执行 INSERT
        self.assertEqual(fake_session.execute.call_count, 2)
        fake_session.commit.assert_called_once()

    def test_query_auto_backfills_when_empty_and_recovers_missing_table(self) -> None:
        """表被外部删除或清空后，无筛选查询应自动重建表并从 system_audit_logs 回填真实历史。"""
        session_missing = MagicMock()
        session_missing.execute.side_effect = RuntimeError('relation "logs.daily_report_operation_logs" does not exist')

        sample_row = (
            1, "ww870411", "Global_admin", "集团全局管理", "EXPORT_DASHBOARD_PDF",
            "导出看板 PDF", "dashboard:pdf", None, {"source": "system_audit_logs_backfill"},
            "10.0.0.1", datetime(2026, 11, 14, 9, 12, 37, tzinfo=timezone.utc),
        )
        session_recovered = MagicMock()
        session_recovered.execute.side_effect = [
            _MockResult(scalar_val=0),   # 首次 COUNT 为 0
            _MockResult(scalar_val=1),   # 自动回填后重查 COUNT 为 1
            _MockResult(rows=[sample_row]),  # 明细列表
            _MockResult(scalar_val=sample_row[10]),  # MAX(created_at)
            _MockResult(scalar_val=1),   # recent_24h_count
            _MockResult(scalar_val=0),   # submission_24h_count
            _MockResult(scalar_val=0),   # workflow_24h_count
            _MockResult(scalar_val=1),   # query_24h_count
        ]

        with patch.object(audit_log_service, "ensure_daily_report_operation_logs_table") as mocked_ensure, \
             patch.object(audit_log_service, "backfill_from_system_audit_logs", return_value=1) as mocked_backfill, \
             patch.object(audit_log_service, "SessionLocal", side_effect=[session_missing, session_recovered]):
            audit_log_service._table_ensured = True
            try:
                res = audit_log_service.query_submission_logs(limit=50, offset=0)
            finally:
                audit_log_service._table_ensured = False

        self.assertEqual(res["total"], 1)
        self.assertEqual(len(res["logs"]), 1)
        self.assertEqual(res["logs"][0]["action_type"], "EXPORT_DASHBOARD_PDF")
        mocked_backfill.assert_called_once_with(days=30)
        # 初次跳过 + 捕获缺失表后 _recover_missing_operation_logs_table 触发重建
        self.assertEqual(mocked_ensure.call_count, 2)


if __name__ == "__main__":
    unittest.main()
