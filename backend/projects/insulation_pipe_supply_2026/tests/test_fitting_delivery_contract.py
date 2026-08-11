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

    def test_arrival_rejects_legacy_mismatched_fields(self):
        with self.assertRaises(ValidationError):
            FittingArrivalConfirmPayload(
                ids=[1],
                arrived_qty_map={"1": 1},
                arrived_qty=1,
                arrival_remark="旧字段不应再被静默忽略",
            )

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


if __name__ == "__main__":
    unittest.main()
