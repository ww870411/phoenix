# -*- coding: utf-8 -*-
"""
单元测试：供给主体保温管厂区成品库存盘点服务
"""

import unittest
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text
from backend.projects.insulation_pipe_supply_2026.services.supplier_inventory_service import (
    ensure_supplier_inventory_table,
    list_standard_pipe_models,
    get_supplier_inventory_for_date,
    save_supplier_inventory,
    get_latest_all_suppliers_inventory,
)


class TestSupplierInventoryService(unittest.TestCase):
    def setUp(self):
        ensure_supplier_inventory_table()
        self.session = SessionLocal()
        # 清理测试数据
        self.session.execute(text("DELETE FROM tube.tube_supplier_inventory WHERE supply_entity_id = 'test_supplier';"))
        self.session.commit()

    def tearDown(self):
        self.session.execute(text("DELETE FROM tube.tube_supplier_inventory WHERE supply_entity_id = 'test_supplier';"))
        self.session.commit()
        self.session.close()

    def test_crud_flow(self):
        # 1. 查询初始空记录
        init_res = get_supplier_inventory_for_date('test_supplier')
        self.assertFalse(init_res['has_previous_record'])
        self.assertEqual(init_res['total_stock_qty'], 0.0)
        self.assertGreater(len(init_res['items']), 0)

        # 2. 第一次提交盘点 (批次 1)
        items_1 = [
            {'pipe_model_id': 'Φ1120×13/Φ1260×16', 'stock_qty': 200.0, 'remark': '第一次盘点'},
            {'pipe_model_id': 'Φ1020×13/Φ1155×14', 'stock_qty': 150.0, 'remark': ''},
        ]
        save_res_1 = save_supplier_inventory('test_supplier', '2026-09-21', items_1, 'tester')
        self.assertTrue(save_res_1['ok'])
        self.assertIsNotNone(save_res_1.get('batch_no'))
        self.assertEqual(save_res_1['total_stock_qty'], 350.0)

        # 3. 再次查询：此时“上次”应为第一次盘点的结果 (350 米)
        check_res_1 = get_supplier_inventory_for_date('test_supplier')
        self.assertTrue(check_res_1['has_previous_record'])
        self.assertEqual(check_res_1['total_previous_stock_qty'], 350.0)
        self.assertEqual(check_res_1['latest_previous_batch_no'], save_res_1['batch_no'])

        # 4. 同一天内进行第二次提交盘点 (批次 2，不覆盖批次 1)
        items_2 = [
            {'pipe_model_id': 'Φ1120×13/Φ1260×16', 'stock_qty': 280.0, 'remark': '第二次盘点增量'},
            {'pipe_model_id': 'Φ1020×13/Φ1155×14', 'stock_qty': 150.0, 'remark': ''},
        ]
        save_res_2 = save_supplier_inventory('test_supplier', '2026-09-21', items_2, 'tester')
        self.assertTrue(save_res_2['ok'])
        self.assertNotEqual(save_res_1['batch_no'], save_res_2['batch_no'])
        self.assertEqual(save_res_2['total_stock_qty'], 430.0)

        # 5. 验证数据库中两次批次记录共存（并未覆盖）
        total_rows = self.session.execute(text(
            "SELECT COUNT(*) FROM tube.tube_supplier_inventory WHERE supply_entity_id = 'test_supplier';"
        )).scalar()
        self.assertEqual(total_rows, 4)  # 两次各 2 行，共 4 行

        # 6. 查询最新盘点：此时“上次”应变为第二次盘点的结果 (430 米)
        check_res_2 = get_supplier_inventory_for_date('test_supplier')
        self.assertTrue(check_res_2['has_previous_record'])
        self.assertEqual(check_res_2['total_previous_stock_qty'], 430.0)
        self.assertEqual(check_res_2['latest_previous_batch_no'], save_res_2['batch_no'])

        # 7. 测试大屏汇总接口：取到的是最新批次 (430 米)
        latest_all = get_latest_all_suppliers_inventory()
        test_sup_items = [it for it in latest_all if it['supply_entity_id'] == 'test_supplier']
        self.assertEqual(len(test_sup_items), 2)
        total_latest_stock = sum(it['stock_qty'] for it in test_sup_items)
        self.assertEqual(total_latest_stock, 430.0)

    def test_list_models_for_supply_entity(self):
        from backend.projects.insulation_pipe_supply_2026.services.supplier_inventory_service import (
            list_models_for_supply_entity,
            _extract_dn_number,
        )

        # 1. 大连开元：仅供应高温水标段 (high_lot_1, high_lot_2, high_lot_4) -> 21 种高温水型号
        kaiyuan_models = list_models_for_supply_entity('kaiyuan')
        self.assertEqual(len(kaiyuan_models), 21)
        self.assertTrue(any('Φ1120' in m for m in kaiyuan_models))
        self.assertFalse(any('Φ32×4.0' in m for m in kaiyuan_models))

        # 2. 河北鑫瑞得：仅供应低温水标段 (low_lot_1 ~ low_lot_6) -> 14 种低温水型号
        xinruide_models = list_models_for_supply_entity('xinruide')
        self.assertEqual(len(xinruide_models), 14)
        self.assertTrue(any('Φ32×4.0' in m for m in xinruide_models))
        self.assertFalse(any('Φ1120' in m for m in xinruide_models))

        # 3. 能源集团保温管厂 (吴近)：未限制标段 -> 全部需求型号并集 (35 种)
        wujin_models = list_models_for_supply_entity('吴近')
        self.assertEqual(len(wujin_models), 35)

        # 4. 验证默认按口径降序排列
        for m_list in [kaiyuan_models, xinruide_models, wujin_models]:
            dns = [_extract_dn_number(m) for m in m_list]
            for i in range(len(dns) - 1):
                self.assertGreaterEqual(dns[i], dns[i + 1])


if __name__ == '__main__':
    unittest.main()

