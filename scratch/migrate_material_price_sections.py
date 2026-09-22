# -*- coding: utf-8 -*-
"""
为 tube.tube_material_price 表新增 applicable_sections 与 section_name_scope 字段，
并将开元（kaiyuan）的历史记录更新为 high_lot_1,high_lot_2（高温水1、2标段），
其他供货商记录更新为 all（全标段通用）。
"""
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal


def main():
    print("🚀 开始执行 tube.tube_material_price 标段字段扩充与数据回填...")
    session = SessionLocal()
    try:
        # 1. 扩充列定义
        session.execute(text("""
            ALTER TABLE tube.tube_material_price 
                ADD COLUMN IF NOT EXISTS applicable_sections VARCHAR(255) NOT NULL DEFAULT 'all',
                ADD COLUMN IF NOT EXISTS section_name_scope VARCHAR(255) NOT NULL DEFAULT '全标段通用';
        """))

        # 2. 列注释
        session.execute(text("""
            COMMENT ON COLUMN tube.tube_material_price.applicable_sections IS '适用标段代码列表 (如 all 或 high_lot_1,high_lot_2)';
            COMMENT ON COLUMN tube.tube_material_price.section_name_scope IS '适用标段中文范围描述 (如 全标段通用 或 高温水1、2标段)';
        """))

        # 3. 索引
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_material_price_sections 
                ON tube.tube_material_price (applicable_sections);
        """))

        # 4. 回填数据：kaiyuan 设置为 high_lot_1,high_lot_2
        kaiyuan_updated = session.execute(text("""
            UPDATE tube.tube_material_price 
            SET applicable_sections = 'high_lot_1,high_lot_2',
                section_name_scope = '高温水1、2标段',
                updated_at = NOW()
            WHERE supply_entity_id = 'kaiyuan' 
               OR supplier_name ILIKE '%开元%';
        """)).rowcount

        # 5. 回填数据：其他厂家设置为 all
        other_updated = session.execute(text("""
            UPDATE tube.tube_material_price 
            SET applicable_sections = 'all',
                section_name_scope = '全标段通用',
                updated_at = NOW()
            WHERE NOT (supply_entity_id = 'kaiyuan' OR supplier_name ILIKE '%开元%');
        """)).rowcount

        session.commit()
        print(f"✅ 执行成功并已提交事务！")
        print(f"   开元（kaiyuan）更新行数: {kaiyuan_updated} 行 (设置 applicable_sections='high_lot_1,high_lot_2')")
        print(f"   其他厂家更新行数: {other_updated} 行 (设置 applicable_sections='all')")

        # 6. 查询核验
        stats = session.execute(text("""
            SELECT supplier_name, applicable_sections, section_name_scope, COUNT(*) 
            FROM tube.tube_material_price 
            GROUP BY supplier_name, applicable_sections, section_name_scope
            ORDER BY supplier_name;
        """)).fetchall()

        print("\n📊 核验分组统计:")
        for r in stats:
            print(f"   - 厂家: {r[0]} | 标段代码: {r[1]} | 标段描述: {r[2]} | 条数: {r[3]}")

    except Exception as e:
        session.rollback()
        print(f"❌ 执行失败并已回滚: {e}")
        raise e
    finally:
        session.close()


if __name__ == "__main__":
    main()
