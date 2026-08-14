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
        # 1. 普通供给主体 (tube_supplier) 提交时，即使传入了 2020 年的旧时间，后端也强制落库为当前真实时间
        past_time = "2020-01-01T08:00:00+08:00"
        payload = {
            "supply_entity_id": "BH",
            "vehicle_plate_no": "鲁B-11111",
            "section_1_id": "high_lot_1",
            "shipped_at": past_time,
            "items": [{"fitting_type": "弯头", "model_spec": "DN300", "shipped_qty": 1, "unit": "个"}],
        }
        res = submit_fitting_delivery(payload, operator="supplier_user", operator_group="tube_supplier")
        self.assertTrue(res["ok"])
        items = list_fitting_deliveries(search_keyword="鲁B-11111", page_size=1).get("items", [])
        self.assertTrue(len(items) > 0)
        # 验证没有落库为 2020 年，而是当前的 2026 年
        self.assertTrue(items[0]["shipped_at"].startswith("2026-"))


if __name__ == "__main__":
    unittest.main()
