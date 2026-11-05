#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phoenix 凤凰计划 · 庄河环海 25-26 供暖期投诉量修正脚本（口径：净投诉=已结案，去除省民心网）
功能:
1. 从 configs/11.4 庄河环海_25-26供暖期每日投诉统计_净投诉=已结案，去除省.xlsx 读取新核定数据 (156天);
2. 备份当前库内庄河对应指标至 backend_data/projects/daily_report_25_26/backup_zhuanghe_complaints_20261104_pre_exclude_province.json;
3. 生成生产环境可执行的标准 SQL 迁移脚本 configs/migrate_25_26_zhuanghe_complaints_v2_exclude_province.sql;
4. 在本地 PostgreSQL 事务中执行指标更新 (净投诉量、月累计、期累计、市平台净投诉量);
5. 执行 100% 逐日指标比对核验与跨表视图联动核验。
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

EXCEL_FILE = os.path.join(PROJECT_ROOT, 'configs', '11.4 庄河环海_25-26供暖期每日投诉统计_净投诉=已结案，去除省.xlsx')
SQL_OUT_FILE = os.path.join(PROJECT_ROOT, 'configs', 'migrate_25_26_zhuanghe_complaints_v2_exclude_province.sql')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backend_data', 'projects', 'daily_report_25_26')
BACKUP_FILE = os.path.join(BACKUP_DIR, 'backup_zhuanghe_complaints_20261104_pre_exclude_province.json')


def read_zhuanghe_excel():
    """读取庄河环海最新核定投诉统计 Excel"""
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"未找到 Excel 文件: {EXCEL_FILE}")
    
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws = wb['每日投诉统计']
    
    records = []
    # 逐行读取数据行，9 到 164
    for r in range(9, ws.max_row + 1):
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
        
    print(f"成功读取 Excel 数据，共计 {len(records)} 天。")
    return records


def backup_current_db(conn):
    """备份当前庄河对应指标数据至 JSON 文件"""
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
    print(f"已成功备份 {len(backup_list)} 条庄河当前数据至: {BACKUP_FILE}")


def generate_sql_script(records):
    """生成生产环境独立的庄河投诉 SQL 迁移脚本"""
    sql_lines = []
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- 🦅 Phoenix 凤凰计划 · 庄河环海 25-26 供暖期投诉量口径修正脚本（净投诉=已结案，剔除省民心网）")
    sql_lines.append(f"-- 执行生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_lines.append("-- 适用范围: 庄河环海 (ZhuangHe / ZhuangHe_Sheet)")
    sql_lines.append("-- 覆盖区间: 2025-11-01 至 2026-04-05 (共 156 天)")
    sql_lines.append("-- 口径调整说明:")
    sql_lines.append("--   1. 庄河原始台账混合了市平台(784件)与省民心网(75件);")
    sql_lines.append("--   2. 净投诉量口径修正为仅计非省平台且已结案工单，剔除省民心网已结案 75 件;")
    sql_lines.append("--   3. 全期累计净投诉量由 172 件修正为 97 件;")
    sql_lines.append("--   4. 当日净投诉量、本月累计净投诉量、本供暖期累计净投诉量全面更新;")
    sql_lines.append("--   5. 每日'其中：2.市平台净投诉量'保持与当日'当日净投诉量'完全相等;")
    sql_lines.append("--   6. '其中：1.省平台净投诉量'保持恒为 0，当日省市平台投诉量保持 859 件;")
    sql_lines.append("--   7. 保留既有 25-26_raw_* 归档数据，非投诉业务指标不受任何影响。")
    sql_lines.append("-- ==============================================================================\n")
    sql_lines.append("BEGIN;\n")
    
    # 采用高效幂等的 UPSERT 语句
    sql_lines.append("-- 【步骤 1】批量更新庄河 156 天的 4 项修正指标（净投诉量、月累计、期累计、市平台净投诉量）")
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
    sql_lines.append("-- 1. 核对庄河 2026-04-05 供暖期最终累计净投诉量（预期应为 97.0000）:")
    sql_lines.append("-- SELECT company, item, date, value FROM daily_basic_data WHERE company = 'ZhuangHe' AND item = 'sum_season_total_net_complaints' AND date = '2026-04-05';")
    sql_lines.append("-- 2. 核对庄河市平台净投诉量与当日净投诉量差值总和（预期应为 0 条不一致）:")
    sql_lines.append("-- SELECT a.date, a.value AS net, b.value AS city_net FROM daily_basic_data a JOIN daily_basic_data b ON a.company=b.company AND a.date=b.date WHERE a.company='ZhuangHe' AND a.item='amount_daily_net_complaints' AND b.item='amount_daily_city_net_complaints' AND a.value <> b.value;")
    sql_lines.append("-- 3. 核对庄河省平台净投诉量最大值（预期应恒为 0）:")
    sql_lines.append("-- SELECT max(value) FROM daily_basic_data WHERE company='ZhuangHe' AND item='amount_daily_provincial_net_complaints' AND date >= '2025-11-01' AND date <= '2026-04-05';")
    sql_lines.append("-- ==============================================================================")

    sql_content = "\n".join(sql_lines)
    with open(SQL_OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f"已成功生成庄河生产环境迁移 SQL 脚本: {SQL_OUT_FILE} (大小: {len(sql_content)/1024:.1f} KB)")


def execute_migration_in_db(records):
    """在本地数据库事务中执行更新"""
    print("\n--- 开始在本地数据库中执行事务更新 ---")
    with engine.begin() as conn:
        # 先备份
        backup_current_db(conn)
        
        # 执行更新
        print("执行指标数据批量 UPSERT...")
        update_stmt = text("""
            INSERT INTO daily_basic_data (
                company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
            ) VALUES (
                :company, :company_cn, :sheet_name, :item, :item_cn, :value, :unit, :note, :date, :status, NOW()
            )
            ON CONFLICT (company, sheet_name, item, date)
            DO UPDATE SET
                value = EXCLUDED.value,
                item_cn = EXCLUDED.item_cn,
                unit = EXCLUDED.unit,
                status = EXCLUDED.status,
                operation_time = NOW();
        """)
        
        params = []
        for r in records:
            d = r['date']
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'amount_daily_service_complaints', 'item_cn': '当日省市平台投诉量', 'value': r['total'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'amount_daily_net_complaints', 'item_cn': '当日净投诉量', 'value': r['net'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'sum_month_total_net_complaints', 'item_cn': '本月累计净投诉量', 'value': r['month_net'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'sum_season_total_net_complaints', 'item_cn': '本供暖期累计净投诉量', 'value': r['season_net'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'amount_daily_provincial_net_complaints', 'item_cn': '其中：1.省平台净投诉量', 'value': r['provincial_net'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            params.append({'company': 'ZhuangHe', 'company_cn': '庄河环海', 'sheet_name': 'ZhuangHe_Sheet', 'item': 'amount_daily_city_net_complaints', 'item_cn': '其中：2.市平台净投诉量', 'value': r['city_net'], 'unit': '件', 'note': None, 'date': d, 'status': 'submit'})
            
        conn.execute(update_stmt, params)
        print(f"成功处理 {len(params)} 项数据（156天 × 6指标）！")


def verify_migration(records):
    """100% 全量比对核验"""
    print("\n--- 开始对数据库中庄河指标进行 100% 全量交叉核验 ---")
    with engine.connect() as conn:
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
            
        mismatches = []
        for r in records:
            d = r['date']
            db_rec = db_map.get(d, {})
            
            checks = [
                ('amount_daily_service_complaints', r['total'], db_rec.get('amount_daily_service_complaints')),
                ('amount_daily_net_complaints', r['net'], db_rec.get('amount_daily_net_complaints')),
                ('sum_month_total_net_complaints', r['month_net'], db_rec.get('sum_month_total_net_complaints')),
                ('sum_season_total_net_complaints', r['season_net'], db_rec.get('sum_season_total_net_complaints')),
                ('amount_daily_provincial_net_complaints', r['provincial_net'], db_rec.get('amount_daily_provincial_net_complaints')),
                ('amount_daily_city_net_complaints', r['city_net'], db_rec.get('amount_daily_city_net_complaints')),
            ]
            
            for item_name, exp_val, act_val in checks:
                if act_val is None or abs(exp_val - act_val) > 1e-4:
                    mismatches.append((d, item_name, exp_val, act_val))
                    
        if mismatches:
            print(f"❌ 核验失败！发现 {len(mismatches)} 处不一致:")
            for m in mismatches[:10]:
                print(f"  日期: {m[0]}, 指标: {m[1]}, Excel预期: {m[2]}, 数据库实际: {m[3]}")
            raise ValueError("数据核验未通过！")
        else:
            print("✅ 156天 × 6项指标 = 936 项数据 100% 与 Excel 完全一致！")
            
        # 特别核验期末累计值
        final_season_net = db_map['2026-04-05']['sum_season_total_net_complaints']
        print(f"2026-04-05 最终全供暖期累计净投诉量: {final_season_net} (预期: 97.0)")
        assert abs(final_season_net - 97.0) < 1e-4, "最终累计净投诉量不等于 97.0！"
        
        # 核验市平台净投诉量与当日净投诉量是否完全一致
        city_diff_cnt = sum(1 for r in records if abs(db_map[r['date']]['amount_daily_net_complaints'] - db_map[r['date']]['amount_daily_city_net_complaints']) > 1e-4)
        print(f"市平台净投诉量与当日净投诉量不一致天数: {city_diff_cnt} (预期: 0)")
        assert city_diff_cnt == 0, "存在市平台净投诉量不等于当日净投诉量的情况！"
        
        # 核验省平台净投诉量是否全为 0
        prov_non_zero = sum(1 for r in records if abs(db_map[r['date']]['amount_daily_provincial_net_complaints']) > 1e-4)
        print(f"省平台净投诉量非零天数: {prov_non_zero} (预期: 0)")
        assert prov_non_zero == 0, "省平台净投诉量存在非零值！"
        
        # 核验 25-26_raw_* 是否安然无恙
        raw_cnt = conn.execute(text("""
            SELECT count(*)
            FROM daily_basic_data
            WHERE company = 'ZhuangHe'
              AND sheet_name = 'ZhuangHe_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item LIKE '25-26_raw_%'
        """)).scalar()
        print(f"庄河 25-26_raw_* 原始归档记录数: {raw_cnt} (预期: 936)")
        assert raw_cnt == 936, f"庄河 raw 归档记录数异常: {raw_cnt}"
        
        # 核验动态视图 sum_basic_data 中的反映 (检查 biz_date 或 peer_date 关联)
        view_row = conn.execute(text("""
            SELECT item, biz_date, value_biz_date
            FROM sum_basic_data
            WHERE company = 'ZhuangHe'
              AND biz_date = '2026-04-05'
              AND item = 'sum_season_total_net_complaints'
        """)).fetchone()
        if view_row:
            print(f"sum_basic_data 动态视图反映的期末累计净投诉量: {view_row[2]} (预期: 97.0)")
            assert abs(float(view_row[2]) - 97.0) < 1e-4, "动态视图未正确联动！"


def main():
    print("==================================================================")
    print("🦅 Phoenix 庄河环海 25-26 供暖期投诉量口径修正（净投诉=已结案，剔除省民心网）")
    print("==================================================================")
    records = read_zhuanghe_excel()
    generate_sql_script(records)
    execute_migration_in_db(records)
    verify_migration(records)
    print("\n🎉 全部迁移、更新与交叉核验顺利完成！")


if __name__ == '__main__':
    main()
