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

    def test_whole_shipment_batch_confirm_and_healing_flow(self):
        from backend.db.database_daily_report_25_26 import SessionLocal
        from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
            submit_fitting_delivery,
            confirm_fitting_delivery_arrival,
            confirm_fitting_delivery_construction,
            confirm_fitting_delivery_warehouse,
            list_fitting_deliveries,
        )
        from sqlalchemy import text

        try:
            # 1. 模拟供给方整车发货 3 个不同管件
            sub_res = submit_fitting_delivery(
                {
                    "supply_entity_id": "BH",
                    "vehicle_plate_no": "鲁B-TEST-BATCH",
                    "section_1_id": "lot_batch_1",
                    "shipped_at": datetime.now().isoformat(),
                    "items": [
                        {"fitting_type": "90°弯头", "model_spec": "DN300", "shipped_qty": 5, "unit": "个"},
                        {"fitting_type": "变径管", "model_spec": "DN300/200", "shipped_qty": 3, "unit": "个"},
                        {"fitting_type": "三通", "model_spec": "DN300", "shipped_qty": 2, "unit": "个"},
                    ],
                },
                operator="batch_supplier",
                operator_group="tube_supplier_admin",
            )
            self.assertTrue(sub_res["ok"])
            items = list_fitting_deliveries(search_keyword="鲁B-TEST-BATCH", page_size=10).get("items", [])
            self.assertEqual(len(items), 3)
            all_ids = [it["id"] for it in items]

            # 2. 现场整车到货确认：一键提交整车 3 项
            arrived_map = {str(it["id"]): int(it["shipped_qty"]) for it in items}
            arr_res = confirm_fitting_delivery_arrival(
                {
                    "ids": all_ids,
                    "arrived_qty_map": arrived_map,
                    "remark": "现场整车清点到货",
                },
                operator="site_leader",
                operator_group="construction_unit",
            )
            self.assertTrue(arr_res["ok"])
            self.assertEqual(arr_res["updated_count"], 3)

            # 3. 施工单位整车施工接收确认：一键接收
            rec_res = confirm_fitting_delivery_construction(
                {"ids": all_ids, "remark": "施工班组整车领用接收"},
                operator="construct_leader",
                operator_group="construction_unit",
            )
            self.assertTrue(rec_res["ok"])
            self.assertEqual(rec_res["updated_count"], 3)

            # 4. 库管整车入库归档确认：一键归档
            wh_res = confirm_fitting_delivery_warehouse(
                {"ids": all_ids, "remark": "库管整车批量归档结清"},
                operator="warehouse_keeper",
                operator_group="warehouse_admin",
            )
            self.assertTrue(wh_res["ok"])
            self.assertEqual(wh_res["updated_count"], 3)

            # 验证最终全部为 completed
            final_items = list_fitting_deliveries(search_keyword="鲁B-TEST-BATCH", page_size=10).get("items", [])
            for it in final_items:
                self.assertEqual(it["status"], "completed")
                self.assertIsNotNone(it["arrived_confirm_at"])
                self.assertIsNotNone(it["received_confirm_at"])
                self.assertIsNotNone(it["warehouse_confirm_at"])

        finally:
            clean_session = SessionLocal()
            try:
                clean_session.execute(text("DELETE FROM tube.tube_fitting_delivery WHERE vehicle_plate_no = '鲁B-TEST-BATCH' OR created_by = 'batch_supplier'"))
                clean_session.commit()
            finally:
                clean_session.close()

    def test_recent_shipment_check_and_merge_flow(self):
        """测试 20 分钟内同车牌发货预检、合并追加及订单子序号顺延。"""
        from backend.db.database_daily_report_25_26 import SessionLocal
        from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
            submit_fitting_delivery,
            check_recent_fitting_shipment,
            list_fitting_deliveries,
        )
        from sqlalchemy import text

        test_plate = "辽B-TEST-MERGE"
        try:
            # 1. 第一次发货：车牌 辽B-TEST-MERGE 发 1 个弯头
            res1 = submit_fitting_delivery(
                {
                    "supply_entity_id": "BH",
                    "vehicle_plate_no": test_plate,
                    "section_1_id": "lot_merge_1",
                    "shipped_at": datetime.now().isoformat(),
                    "items": [
                        {"fitting_type": "90°弯头", "model_spec": "DN300", "shipped_qty": 3, "unit": "个"},
                    ],
                },
                operator="merge_tester",
                operator_group="tube_supplier_admin",
            )
            self.assertTrue(res1["ok"])
            shipment_no = res1["shipment_no"]
            self.assertFalse(res1.get("merged", False))

            # 2. 预检：同车牌、同标段、同供给主体 -> 预期命中（默认 60 分钟/1小时时间窗口）
            check_hit = check_recent_fitting_shipment(
                vehicle_plate_no=test_plate,
                section_1_id="lot_merge_1",
                supply_entity_id="BH",
                time_window_minutes=60,
            )
            self.assertTrue(check_hit["has_recent"])
            self.assertEqual(check_hit["shipment_no"], shipment_no)
            self.assertEqual(check_hit["items_count"], 1)

            # 预检：不同标段 -> 预期不命中
            check_diff_sec = check_recent_fitting_shipment(
                vehicle_plate_no=test_plate,
                section_1_id="lot_other_sec",
                supply_entity_id="BH",
                time_window_minutes=60,
            )
            self.assertFalse(check_diff_sec["has_recent"])

            # 3. 第二次发货：模拟用户确认自动合并入该车次
            res2 = submit_fitting_delivery(
                {
                    "supply_entity_id": "BH",
                    "vehicle_plate_no": test_plate,
                    "section_1_id": "lot_merge_1",
                    "merge_to_shipment_no": shipment_no,
                    "shipped_at": datetime.now().isoformat(),
                    "items": [
                        {"fitting_type": "三通", "model_spec": "DN300/150", "shipped_qty": 2, "unit": "个"},
                        {"fitting_type": "变径管", "model_spec": "DN300/200", "shipped_qty": 1, "unit": "个"},
                    ],
                },
                operator="merge_tester",
                operator_group="tube_supplier_admin",
            )
            self.assertTrue(res2["ok"])
            self.assertTrue(res2["merged"])
            self.assertEqual(res2["shipment_no"], shipment_no)
            self.assertEqual(res2["count"], 2)

            # 4. 验证合并后车次内所有记录：同一车次号，订单号顺延为 -01, -02, -03
            items = list_fitting_deliveries(search_keyword=test_plate, page_size=10).get("items", [])
            self.assertEqual(len(items), 3)
            orders = sorted([it["order_no"] for it in items])
            self.assertTrue(orders[0].endswith("-01"))
            self.assertTrue(orders[1].endswith("-02"))
            self.assertTrue(orders[2].endswith("-03"))
            for it in items:
                self.assertEqual(it["shipment_no"], shipment_no)

        finally:
            clean_session = SessionLocal()
            try:
                clean_session.execute(text(f"DELETE FROM tube.tube_fitting_delivery WHERE vehicle_plate_no = '{test_plate}' OR created_by = 'merge_tester'"))
                clean_session.commit()
            finally:
                clean_session.close()


if __name__ == "__main__":
    unittest.main()
