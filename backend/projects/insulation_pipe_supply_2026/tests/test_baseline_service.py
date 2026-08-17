# -*- coding: utf-8 -*-
"""测试基准量数据表创建及基本 CRUD 操作。"""

import os
import sys

# 确保项目根路径在 sys.path 中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.projects.insulation_pipe_supply_2026.services.baseline_service import (
    ensure_baseline_tables,
    list_pipe_baselines,
    save_pipe_baselines,
    list_fitting_baselines,
    save_fitting_baselines,
)
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text


def test_baseline_tables():
    print("[1/4] 执行 ensure_baseline_tables()...")
    ensure_baseline_tables()

    session = SessionLocal()
    try:
        print("[2/4] 验证数据库表与索引是否存在...")
        res_pipe = session.execute(text("SELECT to_regclass('tube.tube_pipe_baseline')")).scalar()
        res_fitting = session.execute(text("SELECT to_regclass('tube.tube_fitting_baseline')")).scalar()
        assert res_pipe is not None, "tube.tube_pipe_baseline 表未找到！"
        assert res_fitting is not None, "tube.tube_fitting_baseline 表未找到！"
        print(f" -> 直管基准表: {res_pipe} [OK]")
        print(f" -> 管件基准表: {res_fitting} [OK]")

        print("[3/4] 测试直管基准写入与读取...")
        pipe_items = [
            {
                "section_1_id": "test_section_1",
                "pipe_model_id": "Φ1120×13/Φ1260×16",
                "unit": "米",
                "design_qty": 1000.5,
                "purchase_plan_qty": 1000.5,
                "remark": "测试直管",
            }
        ]
        saved_pipe = save_pipe_baselines(pipe_items, operator_name="tester")
        assert saved_pipe == 1
        fetched_pipes = list_pipe_baselines("test_section_1")
        assert len(fetched_pipes) >= 1
        print(f" -> 直管基准读取成功，返回 {len(fetched_pipes)} 条记录 [OK]")

        print("[4/4] 测试管件与物料基准（含多维工程参数+子型号）写入与读取...")
        fitting_items = [
            {
                "section_1_id": "test_section_1",
                "system_type": "高温水",
                "category": "弯头",
                "standard_name": "塑套钢预制保温弯头",
                "model_spec": "90° DN1000 R=1.5DN",
                "sub_model_spec": "90°",
                "unit": "个",
                "design_qty": 10,
                "purchase_plan_qty": 10,
                "main_dn": 1000,
                "angle": 90,
                "bending_radius_ratio": 1.5,
                "remark": "测试90度弯头",
            },
            {
                "section_1_id": "test_section_1",
                "system_type": "高温水",
                "category": "弯头",
                "standard_name": "塑套钢预制保温弯头",
                "model_spec": "45° DN1000 R=1.5DN",
                "sub_model_spec": "45°",
                "unit": "个",
                "design_qty": 6,
                "purchase_plan_qty": 6,
                "main_dn": 1000,
                "angle": 45,
                "bending_radius_ratio": 1.5,
                "remark": "测试45度弯头",
            },
            {
                "section_1_id": "test_section_1",
                "system_type": "低温水",
                "category": "三通",
                "standard_name": "塑套钢预制保温跨越三通",
                "model_spec": "DN1000/DN600",
                "sub_model_spec": "",
                "unit": "个",
                "design_qty": 2,
                "purchase_plan_qty": 2,
                "main_dn": 1000,
                "sub_dn": 600,
                "remark": "测试三通",
            },
        ]
        saved_fitting = save_fitting_baselines(fitting_items, operator_name="tester")
        assert saved_fitting == 3
        fetched_fittings = list_fitting_baselines("test_section_1")
        assert len(fetched_fittings) >= 3
        print(f" -> 管件基准读取成功，返回 {len(fetched_fittings)} 条记录 [OK]")
        assert fetched_fittings[0]["system_type"] in ("高温水", "低温水")
        assert fetched_fittings[0]["standard_name"] != ""

        # 清理测试数据
        session.execute(text("DELETE FROM tube.tube_pipe_baseline WHERE section_1_id = 'test_section_1'"))
        session.execute(text("DELETE FROM tube.tube_fitting_baseline WHERE section_1_id = 'test_section_1'"))
        session.commit()
        print(" -> 测试数据清理完毕 [OK]")

    finally:
        session.close()

    print("\n✅ 所有基准表建表与读写测试 100% 通过！")


if __name__ == "__main__":
    test_baseline_tables()

