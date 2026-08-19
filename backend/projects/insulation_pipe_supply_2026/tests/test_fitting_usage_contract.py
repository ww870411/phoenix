"""管件安装使用量填报、现场动态库存实时计算与撤回机制的契约测试。"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.fitting_delivery_service import (
    submit_fitting_delivery,
    confirm_fitting_delivery_arrival,
    list_fitting_deliveries,
)
from backend.projects.insulation_pipe_supply_2026.services.fitting_usage_service import (
    cancel_fitting_usage_record,
    get_fitting_inventory_summary,
    list_fitting_usage_history,
    submit_fitting_usage_batch,
    _ensure_fitting_usage_table_structures,
)


BEIJING_TZ = ZoneInfo("Asia/Shanghai")
TEST_PROJECT_KEY = "insulation_pipe_supply_2026"
TEST_SEC_ID = "test_sec_usage_01"
TEST_SUPPLY_ID = "test_sup_usage_01"


class FittingUsageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _ensure_fitting_usage_table_structures()

    def setUp(self) -> None:
        self.cleanup_test_data()

    def tearDown(self) -> None:
        self.cleanup_test_data()

    def cleanup_test_data(self) -> None:
        session = SessionLocal()
        try:
            session.execute(
                text("DELETE FROM tube.tube_fitting_daily_usage WHERE section_1_id = :sec_id"),
                {"sec_id": TEST_SEC_ID},
            )
            session.execute(
                text("DELETE FROM tube.tube_fitting_delivery WHERE section_1_id = :sec_id"),
                {"sec_id": TEST_SEC_ID},
            )
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def _create_and_arrive_delivery(self, fitting_type: str, model_spec: str, qty: int, unit: str = "个") -> int:
        """辅助方法：发货并直接确认到货。"""
        ship_res = submit_fitting_delivery(
            {
                "supply_entity_id": TEST_SUPPLY_ID,
                "section_1_id": TEST_SEC_ID,
                "vehicle_plate_no": "京A99999",
                "items": [
                    {
                        "fitting_type": fitting_type,
                        "model_spec": model_spec,
                        "shipped_qty": qty,
                        "unit": unit,
                    }
                ],
            },
            operator="test_supplier",
            operator_group="tube_supplier",
        )
        items = list_fitting_deliveries(section_1_id=TEST_SEC_ID, page_size=10).get("items", [])
        delivery_id = items[0]["id"]
        # 确认到货
        confirm_fitting_delivery_arrival(
            {
                "ids": [delivery_id],
                "arrived_qty_map": {str(delivery_id): qty},
                "remark": "测试到货",
            },
            operator="test_site_mgr",
            operator_group="tube_site_manager",
        )
        return delivery_id

    def test_inventory_summary_and_usage_flow(self) -> None:
        """测试已到货物料动态汇总为现场库存，填报使用后扣减，撤回后恢复。"""
        # 1. 到货两种管件：弯头 10 个，三通 5 个
        self._create_and_arrive_delivery("弯头", "90°DN1100 R=1.5DN", 10)
        self._create_and_arrive_delivery("三通", "DN1000/DN900", 5)

        # 2. 查询当前标段现场库存
        summary_res = get_fitting_inventory_summary(TEST_SEC_ID)
        self.assertTrue(summary_res["ok"])
        items = summary_res["items"]
        self.assertEqual(len(items), 2)
        summary = summary_res["summary"]
        self.assertEqual(summary["arrived_sum"], 15)
        self.assertEqual(summary["used_sum"], 0)
        self.assertEqual(summary["stock_sum"], 15)

        item_elbow = next(it for it in items if it["fitting_type"] == "弯头")
        self.assertEqual(item_elbow["arrived_qty"], 10)
        self.assertEqual(item_elbow["stock_qty"], 10)

        # 3. 提交使用量：使用弯头 4 个，三通 2 个
        today_str = date.today().isoformat()
        submit_res = submit_fitting_usage_batch(
            section_1_id=TEST_SEC_ID,
            usage_date=today_str,
            items=[
                {
                    "fitting_type": "弯头",
                    "model_spec": "90°DN1100 R=1.5DN",
                    "unit": "个",
                    "usage_qty": 4,
                    "remark": "主线焊接 K1+200",
                },
                {
                    "fitting_type": "三通",
                    "model_spec": "DN1000/DN900",
                    "unit": "个",
                    "usage_qty": 2,
                    "remark": "#3支线",
                },
            ],
            operator="worker_zhang",
            user_group="tube_construction_unit",
        )
        self.assertTrue(submit_res["ok"])
        self.assertEqual(len(submit_res["inserted_ids"]), 2)
        elbow_usage_id = submit_res["inserted_ids"][0]

        # 4. 再次查询库存：弯头剩余 6 个，三通剩余 3 个
        summary_res2 = get_fitting_inventory_summary(TEST_SEC_ID)
        items2 = summary_res2["items"]
        item_elbow2 = next(it for it in items2 if it["fitting_type"] == "弯头")
        self.assertEqual(item_elbow2["used_qty"], 4)
        self.assertEqual(item_elbow2["stock_qty"], 6)
        self.assertEqual(item_elbow2["usage_rate_pct"], 40.0)

        # 5. 查询流水台账
        history = list_fitting_usage_history(TEST_SEC_ID)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["status"], "active")

        # 6. 填报人本人撤回弯头的使用记录 (4个)
        cancel_res = cancel_fitting_usage_record(
            usage_id=elbow_usage_id,
            operator="worker_zhang",
            user_group="tube_construction_unit",
            cancel_reason="桩号录入有误需要重填",
        )
        self.assertTrue(cancel_res["ok"])

        # 7. 再次查询库存：弯头恢复至 10 个可用，三通仍为 3 个可用
        summary_res3 = get_fitting_inventory_summary(TEST_SEC_ID)
        items3 = summary_res3["items"]
        item_elbow3 = next(it for it in items3 if it["fitting_type"] == "弯头")
        self.assertEqual(item_elbow3["used_qty"], 0)
        self.assertEqual(item_elbow3["stock_qty"], 10)
        item_tee3 = next(it for it in items3 if it["fitting_type"] == "三通")
        self.assertEqual(item_tee3["used_qty"], 2)
        self.assertEqual(item_tee3["stock_qty"], 3)

    def test_submit_exceeding_stock_is_rejected(self) -> None:
        """测试填报超过当前可用库存时严格拦截拒绝。"""
        # 到货 5 个
        self._create_and_arrive_delivery("大小头", "DN1000/DN800", 5)

        today_str = date.today().isoformat()
        # 尝试填报 6 个
        with self.assertRaises(HTTPException) as ctx:
            submit_fitting_usage_batch(
                section_1_id=TEST_SEC_ID,
                usage_date=today_str,
                items=[
                    {
                        "fitting_type": "大小头",
                        "model_spec": "DN1000/DN800",
                        "unit": "个",
                        "usage_qty": 6,
                    }
                ],
                operator="worker_li",
                user_group="tube_construction_unit",
            )
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("现场当前可用库存仅剩 5 个", ctx.exception.detail)

    def test_cancel_permission_rules(self) -> None:
        """测试非本人且非管理员撤回被 403 拦截，超管可无条件撤回。"""
        self._create_and_arrive_delivery("直缝弯管", "DN1100 5°R=138.7", 8)
        today_str = date.today().isoformat()
        submit_res = submit_fitting_usage_batch(
            section_1_id=TEST_SEC_ID,
            usage_date=today_str,
            items=[
                {
                    "fitting_type": "直缝弯管",
                    "model_spec": "DN1100 5°R=138.7",
                    "unit": "个",
                    "usage_qty": 3,
                }
            ],
            operator="worker_a",
            user_group="tube_construction_unit",
        )
        usage_id = submit_res["inserted_ids"][0]

        # 他人 (worker_b) 尝试撤回 -> 403
        with self.assertRaises(HTTPException) as ctx:
            cancel_fitting_usage_record(
                usage_id=usage_id,
                operator="worker_b",
                user_group="tube_construction_unit",
                cancel_reason="我想撤回",
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("您无权撤回他人填报", ctx.exception.detail)

        # 超级管理员 (admin) 撤回 -> 成功
        admin_cancel_res = cancel_fitting_usage_record(
            usage_id=usage_id,
            operator="super_admin",
            user_group="global_admin",
            cancel_reason="超管后台纠错",
        )
        self.assertTrue(admin_cancel_res["ok"])


if __name__ == "__main__":
    unittest.main()
