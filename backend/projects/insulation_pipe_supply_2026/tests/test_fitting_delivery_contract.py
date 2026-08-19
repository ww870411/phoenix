"""管件物流接口契约与基础校验测试。"""

import unittest
from datetime import datetime

from fastapi import HTTPException
from pydantic import ValidationError

from backend.projects.insulation_pipe_supply_2026.api.workspace import (
    FittingArrivalConfirmPayload,
    FittingCancelPayload,
    FittingDeliverySubmitPayload,
)
from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
    normalize_delivery_ids,
)


class FittingDeliveryContractTests(unittest.TestCase):
    def test_submit_requires_positive_integer_quantity(self):
        with self.assertRaises(ValidationError):
            FittingDeliverySubmitPayload(
                supply_entity_id="KAIYUAN",
                vehicle_plate_no="辽A12345",
                section_1_id="lot_1",
                shipped_at=datetime.now(),
                items=[
                    {
                        "fitting_type": "弯头",
                        "model_spec": "DN300",
                        "shipped_qty": 1.5,
                    }
                ],
            )

    def test_arrival_supports_extra_frontend_ui_fields(self):
        payload = FittingArrivalConfirmPayload(
            ids=[1],
            arrived_qty_map={"1": 1},
            unit="个",
            extra_ui_meta="支持前端辅助字段传入不阻断",
        )
        self.assertEqual(payload.ids, [1])

    def test_arrival_zero_quantity_is_rejected(self):
        with self.assertRaises(ValidationError):
            FittingArrivalConfirmPayload(ids=[1], arrived_qty_map={"1": 0})

    def test_cancel_requires_reason(self):
        with self.assertRaises(ValidationError):
            FittingCancelPayload(ids=[1], remark="")

    def test_delivery_ids_are_deduplicated_without_silent_skip(self):
        self.assertEqual(normalize_delivery_ids({"ids": [3, 3, 4]}), [3, 4])
        with self.assertRaises(HTTPException):
            normalize_delivery_ids({"ids": ["invalid"]})

    def test_submit_supports_multiple_units(self):
        payload = FittingDeliverySubmitPayload(
            supply_entity_id="BH",
            vehicle_plate_no="鲁B-88888",
            section_1_id="high_lot_1",
            shipped_at=datetime.now(),
            items=[
                {"fitting_type": "补偿器", "model_spec": "DN1000", "shipped_qty": 2, "unit": "套"},
                {"fitting_type": "弯头", "model_spec": "90°DN1100", "shipped_qty": 5, "unit": "个"},
            ],
        )
        self.assertEqual(payload.items[0].unit, "套")
        self.assertEqual(payload.items[1].unit, "个")

    def test_submit_shipped_at_permission_rules(self):
        from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
            submit_fitting_delivery,
            list_fitting_deliveries,
        )
        from sqlalchemy import text
        from backend.db.database_daily_report_25_26 import SessionLocal

        # 1. 普通供给主体 (tube_supplier) 提交时，即使传入了 2020 年的旧时间，后端也强制落库为当前真实时间
        past_time = "2020-01-01T08:00:00+08:00"
        payload = {
            "supply_entity_id": "KAIYUAN",
            "vehicle_plate_no": "鲁B-TEST-999",
            "section_1_id": "high_lot_1",
            "shipped_at": past_time,
            "items": [{"fitting_type": "弯头", "model_spec": "DN300", "shipped_qty": 1, "unit": "个"}],
        }
        try:
            res = submit_fitting_delivery(payload, operator="supplier_test_user", operator_group="tube_supplier")
            self.assertTrue(res["ok"])
            items = list_fitting_deliveries(search_keyword="鲁B-TEST-999", page_size=1).get("items", [])
            self.assertTrue(len(items) > 0)
            # 验证没有落库为 2020 年，而是当前的 2026 年
            self.assertTrue(items[0]["shipped_at"].startswith("2026-"))
        finally:
            # 必须即时清理测试注入的数据，防止污染生产库大屏战报
            clean_session = SessionLocal()
            try:
                clean_session.execute(text("DELETE FROM tube.tube_fitting_delivery WHERE vehicle_plate_no = '鲁B-TEST-999' OR created_by = 'supplier_test_user'"))
                clean_session.commit()
            finally:
                clean_session.close()

    def test_super_update_fitting_delivery_contract_and_flow(self):
        from backend.projects.insulation_pipe_supply_2026.api.workspace import SuperUpdateFittingDeliveryPayload
        from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
            submit_fitting_delivery,
            super_update_fitting_delivery_record,
            list_fitting_deliveries,
        )
        from sqlalchemy import text
        from backend.db.database_daily_report_25_26 import SessionLocal

        # 1. 契约校验：发货件数必须 >= 1
        with self.assertRaises(ValidationError):
            SuperUpdateFittingDeliveryPayload(
                section_1_id="high_lot_1",
                fitting_type="弯头",
                model_spec="DN300",
                shipped_qty=0,
                shipped_at=datetime.now(),
                status="pending_arrival",
            )

        # 2. 真实数据库流转与不变量自洽测试
        submit_payload = {
            "supply_entity_id": "KAIYUAN",
            "vehicle_plate_no": "鲁B-TEST-SUPER",
            "section_1_id": "high_lot_1",
            "shipped_at": datetime.now().isoformat(),
            "items": [{"fitting_type": "90°弯头", "model_spec": "DN300*8", "shipped_qty": 5, "unit": "个"}],
        }
        test_delivery_id = None
        try:
            sub_res = submit_fitting_delivery(submit_payload, operator="super_test_user", operator_group="Global_admin")
            self.assertTrue(sub_res["ok"])
            items = list_fitting_deliveries(search_keyword="鲁B-TEST-SUPER", page_size=5).get("items", [])
            self.assertTrue(len(items) > 0)
            test_delivery_id = items[0]["id"]

            # 执行编辑覆盖：直接强改状态为 pending_receive (实到 4 个)
            up_res = super_update_fitting_delivery_record(
                delivery_id=test_delivery_id,
                section_1_id="high_lot_2",
                fitting_type="变径管",
                model_spec="DN300/200",
                shipped_qty=6,
                unit="件",
                shipped_at=datetime.now(),
                status="pending_receive",
                arrived_qty=4,
                operator="admin_tester",
                operator_group="Global_admin",
            )
            self.assertTrue(up_res["ok"])
            self.assertEqual(up_res["record"]["status"], "pending_receive")
            self.assertEqual(up_res["record"]["arrived_qty"], 4)
            self.assertEqual(up_res["record"]["section_1_id"], "high_lot_2")
            self.assertIsNotNone(up_res["record"]["arrived_confirm_at"])

            # 再次编辑覆盖：回滚状态为 pending_arrival (验证自动清空到货时间戳和到货数量)
            rollback_res = super_update_fitting_delivery_record(
                delivery_id=test_delivery_id,
                section_1_id="high_lot_2",
                fitting_type="变径管",
                model_spec="DN300/200",
                shipped_qty=6,
                unit="件",
                shipped_at=datetime.now(),
                status="pending_arrival",
                operator="admin_tester",
                operator_group="Global_admin",
            )
            self.assertTrue(rollback_res["ok"])
            self.assertEqual(rollback_res["record"]["status"], "pending_arrival")
            self.assertIsNone(rollback_res["record"]["arrived_qty"])
            self.assertIsNone(rollback_res["record"]["arrived_confirm_at"])

        finally:
            clean_session = SessionLocal()
            try:
                clean_session.execute(text("DELETE FROM tube.tube_fitting_delivery WHERE vehicle_plate_no = '鲁B-TEST-SUPER' OR created_by = 'super_test_user'"))
                clean_session.commit()
            finally:
                clean_session.close()


if __name__ == "__main__":
    unittest.main()
