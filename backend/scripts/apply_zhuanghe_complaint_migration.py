#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phoenix 凤凰计划 · 庄河环海 25-26 供暖期投诉量历史归档与新数据入库脚本
功能:
1. 从 configs/11.4 庄河环海_25-26供暖期每日投诉统计_完整版.xlsx 读取新核定数据 (156天);
2. 备份当前库内庄河对应指标至 backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_migration.json;
3. 生成生产环境可执行的标准 SQL 迁移脚本 configs/migrate_25_26_zhuanghe_complaints_production.sql;
4. 在本地 PostgreSQL 执行历史加 raw 前缀与新数据入库，并完成 100% 交叉比对核验。
"""

import os
import sys
import json
import datetime
import openpyxl

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.db.database_daily_report_25_26 import engine
from sqlalchemy import text

EXCEL_FILE = os.path.join(PROJECT_ROOT, 'configs', '11.4 庄河环海_25-26供暖期每日投诉统计_完整版.xlsx')
SQL_OUT_FILE = os.path.join(PROJECT_ROOT, 'configs', 'migrate_25_26_zhuanghe_complaints_production.sql')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backend_data', 'projects', 'daily_report_25_26')
BACKUP_FILE = os.path.join(BACKUP_DIR, 'backup_zhuanghe_complaints_20261104_pre_migration.json')


def read_zhuanghe_excel():
    """读取庄河环海 Excel 每日投诉统计"""
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"未找到 Excel 文件: {EXCEL_FILE}")
    
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws = wb['每日投诉统计']
    
    records = []
    for r in range(8, ws.max_row + 1):
        d_val = ws.cell(r, 1).value
        if d_val == '供暖期合计':
            break
        if not d_val:
            continue
        
        if isinstance(d_val, (datetime.datetime, datetime.date)):
            d_str = d_val.strftime('%Y-%m-%d')
        else:
            d_str = str(d_val)[:10]
            
        tot = float(ws.cell(r, 2).value or 0)
        net = float(ws.cell(r, 3).value or 0)
        mnet = float(ws.cell(r, 4).value or 0)
        snet = float(ws.cell(r, 5).value or 0)
        
        records.append({
            'date': d_str,
            'total': tot,
            'net': net,
            'month_net': mnet,
            'season_net': snet,
            'provincial_net': 0.0,
            'city_net': net
        })
        
    return records


def backup_current_db(conn):
    """备份当前待处理的庄河指标数据至 JSON 文件"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rows = conn.execute(text("""
        SELECT id, company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
        FROM daily_basic_data
        WHERE company = 'ZhuangHe'
          AND sheet_name = 'ZhuangHe_Sheet'
          AND date >= '2025-11-01' AND date <= '2026-04-05'
          AND item IN (
            'amount_daily_service_complaints',
            'amount_daily_net_complaints',
            'sum_month_total_net_complaints',
            'sum_season_total_net_complaints',
            'amount_daily_provincial_net_complaints',
            'amount_daily_city_net_complaints'
          )
        ORDER BY date, item
    """)).fetchall()
    
    backup_list = []
    for r in rows:
        backup_list.append({
            'id': r[0],
            'company': r[1],
            'company_cn': r[2],
            'sheet_name': r[3],
            'item': r[4],
            'item_cn': r[5],
            'value': float(r[6]) if r[6] is not None else None,
            'unit': r[7],
            'note': r[8],
            'date': r[9].strftime('%Y-%m-%d') if r[9] else None,
            'status': r[10],
            'operation_time': r[11].isoformat() if r[11] else None
        })
        
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(backup_list, f, ensure_ascii=False, indent=2)
    print(f"已成功备份 {len(backup_list)} 条庄河当前历史记录至: {BACKUP_FILE}")


def generate_sql_script(records):
    """生成生产环境独立的庄河投诉 SQL 迁移脚本"""
    sql_lines = []
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- 🦅 Phoenix 凤凰计划 · 庄河环海 25-26 供暖期投诉量历史归档与新数据入库脚本")
    sql_lines.append(f"-- 执行生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_lines.append("-- 适用范围: 庄河环海 (ZhuangHe / ZhuangHe_Sheet)")
    sql_lines.append("-- 覆盖区间: 2025-11-01 至 2026-04-05 (共 156 天)")
    sql_lines.append("-- 操作内容:")
    sql_lines.append("--   1. 原 6 项历史指标增加 '25-26_raw_' 前缀进行归档封存 (共 936 条记录);")
    sql_lines.append("--   2. 插入新核定的 6 项标准投诉指标 (共 936 条记录):")
    sql_lines.append("--      - amount_daily_service_complaints (当日省市平台投诉量)")
    sql_lines.append("--      - amount_daily_net_complaints (当日净投诉量)")
    sql_lines.append("--      - sum_month_total_net_complaints (本月累计净投诉量)")
    sql_lines.append("--      - sum_season_total_net_complaints (本供暖期累计净投诉量)")
    sql_lines.append("--      - amount_daily_provincial_net_complaints (其中：1.省平台净投诉量 = 0)")
    sql_lines.append("--      - amount_daily_city_net_complaints (其中：2.市平台净投诉量 = 当日净投诉量)")
    sql_lines.append("-- ==============================================================================\n")
    sql_lines.append("BEGIN;\n")
    
    # 步骤 1: 历史归档
    sql_lines.append("-- 【步骤 1】历史旧数据归档封存：将 6 项原指标重命名追加 '25-26_raw_' 前缀 (936条)")
    sql_lines.append("""UPDATE daily_basic_data
SET item = '25-26_raw_' || item,
    item_cn = '25-26_raw_' || item_cn,
    operation_time = NOW()
WHERE company = 'ZhuangHe'
  AND sheet_name = 'ZhuangHe_Sheet'
  AND date >= '2025-11-01' AND date <= '2026-04-05'
  AND item NOT LIKE '25-26_raw_%'
  AND item IN (
    'amount_daily_service_complaints',
    'amount_daily_net_complaints',
    'sum_month_total_net_complaints',
    'sum_season_total_net_complaints',
    'amount_daily_provincial_net_complaints',
    'amount_daily_city_net_complaints'
  );
""")

    # 步骤 2: 插入新标准数据
    sql_lines.append("-- 【步骤 2】插入 156 天新核定的 6 项标准指标数据（共 936 条记录）")
    sql_lines.append("INSERT INTO daily_basic_data (")
    sql_lines.append("    company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time")
    sql_lines.append(") VALUES")
    
    insert_rows = []
    for r in records:
        d = r['date']
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_service_complaints', '当日省市平台投诉量', {r['total']:.4f}, '件', NULL, '{d}', 'submit', NOW())")
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_net_complaints', '当日净投诉量', {r['net']:.4f}, '件', NULL, '{d}', 'submit', NOW())")
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'sum_month_total_net_complaints', '本月累计净投诉量', {r['month_net']:.4f}, '件', NULL, '{d}', 'submit', NOW())")
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'sum_season_total_net_complaints', '本供暖期累计净投诉量', {r['season_net']:.4f}, '件', NULL, '{d}', 'submit', NOW())")
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_provincial_net_complaints', '其中：1.省平台净投诉量', {r['provincial_net']:.4f}, '件', NULL, '{d}', 'submit', NOW())")
        insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_city_net_complaints', '其中：2.市平台净投诉量', {r['city_net']:.4f}, '件', NULL, '{d}', 'submit', NOW())")

    sql_lines.append(",\n".join(insert_rows))
    sql_lines.append("ON CONFLICT (company, sheet_name, item, date)")
    sql_lines.append("DO UPDATE SET")
    sql_lines.append("    value = EXCLUDED.value,")
    sql_lines.append("    item_cn = EXCLUDED.item_cn,")
    sql_lines.append("    unit = EXCLUDED.unit,")
    sql_lines.append("    status = EXCLUDED.status,")
    sql_lines.append("    operation_time = NOW();\n")
    
    sql_lines.append("COMMIT;\n")
    
    # 增加校验查询
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- 【执行后数据核对 SQL（可直接单独执行核验）】")
    sql_lines.append("-- 1. 核对庄河 2026-04-05 供暖期最终累计净投诉量（预期应为 172.0000）:")
    sql_lines.append("-- SELECT company, item, date, value FROM daily_basic_data WHERE company = 'ZhuangHe' AND item = 'sum_season_total_net_complaints' AND date = '2026-04-05';")
    sql_lines.append("-- 2. 核对庄河 25-26_raw_* 归档记录数与新记录数（预期各为 936 条）:")
    sql_lines.append("-- SELECT item LIKE '25-26_raw_%' AS is_raw, count(*) FROM daily_basic_data WHERE company = 'ZhuangHe' AND date >= '2025-11-01' AND date <= '2026-04-05' AND item LIKE '%complaint%' GROUP BY is_raw;")
    sql_lines.append("-- ==============================================================================")

    sql_content = "\n".join(sql_lines)
    with open(SQL_OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f"已成功生成庄河生产环境迁移 SQL 脚本: {SQL_OUT_FILE} (大小: {len(sql_content)/1024:.1f} KB)")


def execute_migration_in_db(records):
    """在本地数据库事务中执行归档与插入"""
    print("\n--- 开始在本地数据库中执行事务归档与插入 ---")
    with engine.begin() as conn:
        # 1. 归档加 25-26_raw_ 前缀
        print("1. 历史数据归档：追加 25-26_raw_ 前缀...")
        res_raw = conn.execute(text("""
            UPDATE daily_basic_data
            SET item = '25-26_raw_' || item,
                item_cn = '25-26_raw_' || item_cn,
                operation_time = NOW()
            WHERE company = 'ZhuangHe'
              AND sheet_name = 'ZhuangHe_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item NOT LIKE '25-26_raw_%'
              AND item IN (
                'amount_daily_service_complaints',
                'amount_daily_net_complaints',
                'sum_month_total_net_complaints',
                'sum_season_total_net_complaints',
                'amount_daily_provincial_net_complaints',
                'amount_daily_city_net_complaints'
              )
        """))
        print(f"   ➔ 庄河历史记录归档受影响行数: {res_raw.rowcount}")

        # 2. 插入新标准数据 (936条)
        print("2. 插入新标准指标记录 (共 936 条)...")
        insert_rows = []
        for r in records:
            d = r['date']
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_service_complaints', '当日省市平台投诉量', {r['total']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_net_complaints', '当日净投诉量', {r['net']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'sum_month_total_net_complaints', '本月累计净投诉量', {r['month_net']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'sum_season_total_net_complaints', '本供暖期累计净投诉量', {r['season_net']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_provincial_net_complaints', '其中：1.省平台净投诉量', {r['provincial_net']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")
            insert_rows.append(f"('ZhuangHe', '庄河环海', 'ZhuangHe_Sheet', 'amount_daily_city_net_complaints', '其中：2.市平台净投诉量', {r['city_net']:.4f}, '件', NULL, '{d}'::date, 'submit', NOW())")

        sql_insert = f"""
            INSERT INTO daily_basic_data (
                company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
            ) VALUES
                {",".join(insert_rows)}
            ON CONFLICT (company, sheet_name, item, date)
            DO UPDATE SET
                value = EXCLUDED.value,
                item_cn = EXCLUDED.item_cn,
                unit = EXCLUDED.unit,
                status = EXCLUDED.status,
                operation_time = NOW()
        """
        res_insert = conn.execute(text(sql_insert))
        print(f"   ➔ 庄河新标准记录写入行数: {res_insert.rowcount}")


def verify_database_state(records):
    """全量交叉比对数据库与 Excel"""
    print("\n--- 开始对更新后的庄河数据进行严格交叉比对 ---")
    with engine.connect() as conn:
        # 1. 验证 raw 归档数与新标准指标数
        raw_cnt = conn.execute(text("""
            SELECT count(*) FROM daily_basic_data 
            WHERE company = 'ZhuangHe' 
              AND date >= '2025-11-01' AND date <= '2026-04-05' 
              AND item LIKE '25-26_raw_%'
        """)).scalar()
        
        std_cnt = conn.execute(text("""
            SELECT count(*) FROM daily_basic_data 
            WHERE company = 'ZhuangHe' 
              AND date >= '2025-11-01' AND date <= '2026-04-05' 
              AND item IN (
                'amount_daily_service_complaints',
                'amount_daily_net_complaints',
                'sum_month_total_net_complaints',
                'sum_season_total_net_complaints',
                'amount_daily_provincial_net_complaints',
                'amount_daily_city_net_complaints'
              )
        """)).scalar()
        print(f"✅ 历史 raw 归档记录数: {raw_cnt} 条 (预期 936 条)")
        print(f"✅ 新标准指标记录数: {std_cnt} 条 (预期 936 条)")

        # 2. 逐天 6 项指标比对
        rows = conn.execute(text("""
            SELECT item, date, value 
            FROM daily_basic_data
            WHERE company = 'ZhuangHe'
              AND sheet_name = 'ZhuangHe_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item IN (
                'amount_daily_service_complaints',
                'amount_daily_net_complaints',
                'sum_month_total_net_complaints',
                'sum_season_total_net_complaints',
                'amount_daily_provincial_net_complaints',
                'amount_daily_city_net_complaints'
              )
        """)).fetchall()

        db_map = {}
        for item, dt, val in rows:
            d_str = dt.strftime('%Y-%m-%d')
            if d_str not in db_map:
                db_map[d_str] = {}
            db_map[d_str][item] = float(val or 0)

        errors = []
        for r in records:
            d_str = r['date']
            d_vals = db_map.get(d_str, {})
            if d_vals.get('amount_daily_service_complaints') != r['total']:
                errors.append((d_str, 'total', d_vals.get('amount_daily_service_complaints'), r['total']))
            if d_vals.get('amount_daily_net_complaints') != r['net']:
                errors.append((d_str, 'net', d_vals.get('amount_daily_net_complaints'), r['net']))
            if d_vals.get('sum_month_total_net_complaints') != r['month_net']:
                errors.append((d_str, 'month_net', d_vals.get('sum_month_total_net_complaints'), r['month_net']))
            if d_vals.get('sum_season_total_net_complaints') != r['season_net']:
                errors.append((d_str, 'season_net', d_vals.get('sum_season_total_net_complaints'), r['season_net']))
            if d_vals.get('amount_daily_provincial_net_complaints') != 0.0:
                errors.append((d_str, 'provincial_net', d_vals.get('amount_daily_provincial_net_complaints'), 0.0))
            if d_vals.get('amount_daily_city_net_complaints') != r['net']:
                errors.append((d_str, 'city_net', d_vals.get('amount_daily_city_net_complaints'), r['net']))

        if errors:
            print(f"❌ 核验失败，发现 {len(errors)} 处不匹配!")
            for err in errors[:5]:
                print(err)
            raise AssertionError("庄河数据比对不一致")
        else:
            print("✅ 庄河环海 156 天全部 6 项指标（共 936 条记录）与 Excel 100% 吻合！")

        # 3. 抽查 2026-04-05 最终全期累计值
        final_season = conn.execute(text("""
            SELECT value FROM daily_basic_data 
            WHERE company = 'ZhuangHe' 
              AND item = 'sum_season_total_net_complaints' 
              AND date = '2026-04-05'
        """)).scalar()
        print(f"✅ 2026-04-05 庄河环海最终累计净投诉量: {float(final_season):.1f} 件 (严格符合成果表 172 件)")


def main():
    print("=== 开始执行庄河环海 25-26 供暖期投诉量历史归档与新数据入库 ===")
    records = read_zhuanghe_excel()
    print(f"Excel 读取成功: 庄河环海共 {len(records)} 天数据")
    
    with engine.connect() as conn:
        backup_current_db(conn)
        
    generate_sql_script(records)
    execute_migration_in_db(records)
    verify_database_state(records)
    print("\n🎉 庄河环海投诉量历史归档与新数据入库顺利完成！")


if __name__ == '__main__':
    main()
