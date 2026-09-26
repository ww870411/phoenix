# -*- coding: utf-8 -*-
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

s = SessionLocal()
try:
    print("1. 添加 material_name 字段...")
    s.execute(text("ALTER TABLE tube.tube_fitting_supplier_inventory ADD COLUMN IF NOT EXISTS material_name VARCHAR(128) NOT NULL DEFAULT '';"))
    
    print("2. 重新构建联合唯一索引 (包含 material_name)...")
    s.execute(text("DROP INDEX IF EXISTS tube.uq_tube_fitting_supplier_inv_batch_item;"))
    s.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_supplier_inv_batch_item 
        ON tube.tube_fitting_supplier_inventory (batch_no, supply_entity_id, section_1_id, fitting_type, material_name, model_spec, unit);
    """))
    s.commit()
    print("✅ 表结构与唯一约束升级成功！")
except Exception as e:
    s.rollback()
    print("❌ 升级失败:", e)
finally:
    s.close()
