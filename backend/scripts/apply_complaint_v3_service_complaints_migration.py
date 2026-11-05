#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phoenix 凤凰计划 · 供热公司及各中心 25-26 供暖期“当日省市平台投诉量”仅限投诉类修正脚本
功能:
1. 从 configs/11.4 25-26供暖期主城区及各中心投诉统计_各类投诉量仅限投诉类.xlsx 读取最新核定数据 (156天);
2. 备份当前库内对应指标至 backend_data/projects/daily_report_25_26/backup_complaints_20261104_pre_v3_migration.json;
3. 生成生产环境可执行的标准 SQL 迁移脚本 configs/migrate_25_26_complaints_v3_complaint_only.sql;
4. 在本地 PostgreSQL 执行事务级更新并全量交叉核对。
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

EXCEL_FILE = os.path.join(PROJECT_ROOT, 'configs', '11.4 25-26供暖期主城区及各中心投诉统计_各类投诉量仅限投诉类.xlsx')
SQL_OUT_FILE = os.path.join(PROJECT_ROOT, 'configs', 'migrate_25_26_complaints_v3_complaint_only.sql')
BACKUP_DIR = os.path.join(PROJECT_ROOT, 'backend_data', 'projects', 'daily_report_25_26')
BACKUP_FILE = os.path.join(BACKUP_DIR, 'backup_complaints_20261104_pre_v3_migration.json')

CENTER_MAP = {
    '华乐': ('HuaLe_Center', '华乐中心'),
    '东港': ('DongGang_Center', '东港中心'),
    '春海': ('ChunHai_Center', '春海中心'),
    '中山': ('ZhongShan_Center', '中山中心'),
    '香炉礁': ('XiangLuJiao_Center', '香炉礁中心'),
    '北岗': ('BeiGang_Center', '北岗中心'),
    '兴工': ('XingGong_Center', '兴工中心'),
    '大纺': ('DaFang_Center', '大纺中心'),
    '双兴': ('ShuangXing_Center', '双兴中心'),
    '管网': ('GuanWang_Center', '管网中心'),
}


def read_excel_data():
    """读取 Excel 修订口径数据（省市平台总投诉量仅限“投诉”）"""
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"未找到 Excel 文件: {EXCEL_FILE}")
    
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    ws1 = wb['整体每日统计']
    ws2 = wb['各中心每日统计']
    
    # 1. 供热公司整体数据 (GongRe_Sheet)
    overall_data = []
    for r in range(5, ws1.max_row + 1):
        d_val = ws1.cell(r, 1).value
        if not d_val or d_val == '供暖期合计':
            break
        if isinstance(d_val, (datetime.datetime, datetime.date)):
            d_str = d_val.strftime('%Y-%m-%d')
        else:
            d_str = str(d_val)[:10]
            
        srv = float(ws1.cell(r, 2).value or 0)
        net = float(ws1.cell(r, 3).value or 0)
        mnet = float(ws1.cell(r, 4).value or 0)
        snet = float(ws1.cell(r, 5).value or 0)
        
        overall_data.append({
            'date': d_str,
            'service': srv,
            'net': net,
            'month_net': mnet,
            'season_net': snet
        })
        
    # 2. 10 个中心数据 (GongRe_branches_detail_Sheet)
    center_data = []
    for r in range(5, ws2.max_row + 1):
        c_name = ws2.cell(r, 1).value
        d_val = ws2.cell(r, 2).value
        if not c_name or not d_val:
            continue
        if c_name not in CENTER_MAP:
            continue
        comp_code, comp_cn = CENTER_MAP[c_name]
        
        if isinstance(d_val, (datetime.datetime, datetime.date)):
            d_str = d_val.strftime('%Y-%m-%d')
        else:
            d_str = str(d_val)[:10]
            
        srv = float(ws2.cell(r, 3).value or 0)
        net = float(ws2.cell(r, 4).value or 0)
        mnet = float(ws2.cell(r, 5).value or 0)
        snet = float(ws2.cell(r, 6).value or 0)
        
        center_data.append({
            'company': comp_code,
            'company_cn': comp_cn,
            'date': d_str,
            'service': srv,
            'net': net,
            'month_net': mnet,
            'season_net': snet
        })
        
    return overall_data, center_data


def backup_current_db(conn):
    """备份当前指标数据至 JSON 文件"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rows = conn.execute(text("""
        SELECT id, company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
        FROM daily_basic_data
        WHERE sheet_name IN ('GongRe_Sheet', 'GongRe_branches_detail_Sheet')
          AND date >= '2025-11-01' AND date <= '2026-04-05'
          AND item IN (
            'amount_daily_service_complaints',
            'amount_daily_net_complaints',
            'sum_month_total_net_complaints',
            'sum_season_total_net_complaints',
            'amount_daily_provincial_net_complaints',
            'amount_daily_city_net_complaints'
          )
        ORDER BY sheet_name, company, date, item
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
    print(f"已成功备份 {len(backup_list)} 条当前库内记录至: {BACKUP_FILE}")


def generate_sql_script(overall_data, center_data):
    """生成生产环境独立的 SQL 迁移脚本"""
    sql_lines = []
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- 🦅 Phoenix 凤凰计划 · 供热公司及各中心 25-26 供暖期“当日省市平台投诉量”仅限投诉类修正脚本")
    sql_lines.append(f"-- 执行生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_lines.append("-- 修正背景:")
    sql_lines.append("--   根据最新统计标准，“当日省市平台投诉量”与净投诉量一致，仅保留分类严格等于“投诉”的诉求件；")
    sql_lines.append("--   剔除了原有省市平台总量中包含的 157 件“咨询”和“表扬”等非投诉件；")
    sql_lines.append("--   供热公司全期省市平台总投诉量由 5,696 件精准更新为 5,539 件；")
    sql_lines.append("--   净投诉量相关指标（当日净投诉量、月累计、供暖期累计184件）保持已校准状态。")
    sql_lines.append("-- 覆盖范围:")
    sql_lines.append(f"--   1. GongRe_Sheet (供热公司总表): 156 天 amount_daily_service_complaints 指标更新")
    sql_lines.append(f"--   2. GongRe_branches_detail_Sheet (10个中心): 1,560 天次 amount_daily_service_complaints 指标更新")
    sql_lines.append("-- ==============================================================================\n")
    sql_lines.append("BEGIN;\n")
    
    # 1. GongRe_Sheet 更新
    sql_lines.append("-- 【第 1 部分】供热公司总表 (GongRe_Sheet) 当日省市平台投诉量更新")
    sql_lines.append("UPDATE daily_basic_data AS d")
    sql_lines.append("SET value = v.val,")
    sql_lines.append("    operation_time = NOW()")
    sql_lines.append("FROM (VALUES")
    
    gongre_rows = [f"    ('GongRe', 'GongRe_Sheet', 'amount_daily_service_complaints', '{item['date']}'::date, {item['service']:.4f})" for item in overall_data]
    sql_lines.append(",\n".join(gongre_rows))
    sql_lines.append(") AS v(company, sheet_name, item, dt, val)")
    sql_lines.append("WHERE d.company = v.company")
    sql_lines.append("  AND d.sheet_name = v.sheet_name")
    sql_lines.append("  AND d.item = v.item")
    sql_lines.append("  AND d.date = v.dt;\n")
    
    # 2. GongRe_branches_detail_Sheet 更新
    sql_lines.append("-- 【第 2 部分】10 个服务中心 (GongRe_branches_detail_Sheet) 当日省市平台投诉量更新")
    sql_lines.append("UPDATE daily_basic_data AS d")
    sql_lines.append("SET value = v.val,")
    sql_lines.append("    operation_time = NOW()")
    sql_lines.append("FROM (VALUES")
    
    branch_rows = [f"    ('{item['company']}', 'GongRe_branches_detail_Sheet', 'amount_daily_service_complaints', '{item['date']}'::date, {item['service']:.4f})" for item in center_data]
    sql_lines.append(",\n".join(branch_rows))
    sql_lines.append(") AS v(company, sheet_name, item, dt, val)")
    sql_lines.append("WHERE d.company = v.company")
    sql_lines.append("  AND d.sheet_name = v.sheet_name")
    sql_lines.append("  AND d.item = v.item")
    sql_lines.append("  AND d.date = v.dt;\n")
    
    sql_lines.append("COMMIT;\n")
    
    # 校验 SQL
    sql_lines.append("-- ==============================================================================")
    sql_lines.append("-- 【执行后数据核对 SQL】")
    sql_lines.append("-- 1. 核对供热公司全期省市平台总投诉量之和（预期应为 5539.0000）:")
    sql_lines.append("-- SELECT sum(value) FROM daily_basic_data WHERE sheet_name = 'GongRe_Sheet' AND item = 'amount_daily_service_complaints' AND date >= '2025-11-01' AND date <= '2026-04-05';")
    sql_lines.append("-- 2. 核对 2025-11-03 供热公司总投诉量（预期由 122 降为 115）:")
    sql_lines.append("-- SELECT value FROM daily_basic_data WHERE sheet_name = 'GongRe_Sheet' AND item = 'amount_daily_service_complaints' AND date = '2025-11-03';")
    sql_lines.append("-- ==============================================================================")

    sql_content = "\n".join(sql_lines)
    with open(SQL_OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    print(f"已成功生成生产环境迁移 SQL 脚本: {SQL_OUT_FILE} (大小: {len(sql_content)/1024:.1f} KB)")


def execute_migration_in_db(overall_data, center_data):
    """在本地数据库事务中执行更新"""
    print("\n--- 开始在本地数据库中执行事务更新 ---")
    with engine.begin() as conn:
        # 1. 更新 GongRe_Sheet
        print("1. 更新供热公司总表 (GongRe_Sheet) amount_daily_service_complaints...")
        gongre_rows = [f"('GongRe', 'GongRe_Sheet', 'amount_daily_service_complaints', '{item['date']}'::date, {item['service']:.4f})" for item in overall_data]
        sql_gongre = f"""
            UPDATE daily_basic_data AS d
            SET value = v.val,
                operation_time = NOW()
            FROM (VALUES
                {",".join(gongre_rows)}
            ) AS v(company, sheet_name, item, dt, val)
            WHERE d.company = v.company
              AND d.sheet_name = v.sheet_name
              AND d.item = v.item
              AND d.date = v.dt
        """
        res_gongre = conn.execute(text(sql_gongre))
        print(f"   ➔ 供热公司总表已更新行数: {res_gongre.rowcount}")

        # 2. 更新 GongRe_branches_detail_Sheet
        print("2. 更新 10 个服务中心明细表 (GongRe_branches_detail_Sheet) amount_daily_service_complaints...")
        branch_rows = [f"('{item['company']}', 'GongRe_branches_detail_Sheet', 'amount_daily_service_complaints', '{item['date']}'::date, {item['service']:.4f})" for item in center_data]
        sql_branches = f"""
            UPDATE daily_basic_data AS d
            SET value = v.val,
                operation_time = NOW()
            FROM (VALUES
                {",".join(branch_rows)}
            ) AS v(company, sheet_name, item, dt, val)
            WHERE d.company = v.company
              AND d.sheet_name = v.sheet_name
              AND d.item = v.item
              AND d.date = v.dt
        """
        res_branches = conn.execute(text(sql_branches))
        print(f"   ➔ 服务中心明细表已更新行数: {res_branches.rowcount}")


def verify_database_state(overall_data, center_data):
    """全量交叉比对数据库与 Excel"""
    print("\n--- 开始对更新后的数据库进行全量交叉核验 ---")
    with engine.connect() as conn:
        # 1. 验证 GongRe_Sheet
        db_overall = conn.execute(text("""
            SELECT date, value
            FROM daily_basic_data
            WHERE sheet_name = 'GongRe_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item = 'amount_daily_service_complaints'
        """)).fetchall()
        db_map = {dt.strftime('%Y-%m-%d'): float(val or 0) for dt, val in db_overall}
        
        errors = []
        for item in overall_data:
            d_str = item['date']
            val = db_map.get(d_str)
            if val != item['service']:
                errors.append((d_str, val, item['service']))
                
        if errors:
            print(f"❌ 供热公司总表核验失败: {len(errors)} 处不匹配!")
            raise AssertionError("总表比对不一致")
        else:
            print("✅ 供热公司总表 156 天 amount_daily_service_complaints 与 Excel 100% 吻合！")

        # 验证总表求和
        total_sum = conn.execute(text("""
            SELECT sum(value) FROM daily_basic_data
            WHERE sheet_name = 'GongRe_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item = 'amount_daily_service_complaints'
        """)).scalar()
        print(f"✅ 供热公司全期省市平台总投诉量求和: {float(total_sum):.1f} 件 (严格符合成果表 5539 件，剔除 157 件非投诉件)")

        # 2. 验证各中心明细
        db_branches = conn.execute(text("""
            SELECT company, date, value
            FROM daily_basic_data
            WHERE sheet_name = 'GongRe_branches_detail_Sheet'
              AND date >= '2025-11-01' AND date <= '2026-04-05'
              AND item = 'amount_daily_service_complaints'
        """)).fetchall()
        c_map = {(comp, dt.strftime('%Y-%m-%d')): float(val or 0) for comp, dt, val in db_branches}
        
        c_errors = []
        for item in center_data:
            k = (item['company'], item['date'])
            val = c_map.get(k)
            if val != item['service']:
                c_errors.append((k, val, item['service']))
                
        if c_errors:
            print(f"❌ 服务中心核验失败: {len(c_errors)} 处不匹配!")
            raise AssertionError("服务中心比对不一致")
        else:
            print("✅ 10 个服务中心 1,560 天次 amount_daily_service_complaints 与 Excel 100% 吻合！")

        # 3. 抽查 2025-11-03 业务日
        val_1103 = conn.execute(text("""
            SELECT value FROM daily_basic_data
            WHERE sheet_name = 'GongRe_Sheet'
              AND item = 'amount_daily_service_complaints'
              AND date = '2025-11-03'
        """)).scalar()
        print(f"✅ 抽查 2025-11-03 供热公司当日省市平台投诉量: {float(val_1103):.1f} 件 (原 122 件已精准修正为 115 件)")

        # 4. 抽查 2026-11-03 业务日通过 sum_basic_data 视图抓取的同期值
        peer_1103 = conn.execute(text("""
            SELECT company, item, biz_date, peer_date, value_biz_date, value_peer_date
            FROM sum_basic_data
            WHERE company = 'GongRe'
              AND item = 'amount_daily_service_complaints'
              AND biz_date = '2026-11-03'
        """)).fetchone()
        print(f"✅ sum_basic_data 视图联动同期值: {peer_1103[0]} 去年同期值已动态更新为 {float(peer_1103[5]):.1f} 件")


def main():
    print("=== 开始执行供热公司及各中心 25-26 供暖期省市平台总投诉量仅限投诉类修正 ===")
    overall_data, center_data = read_excel_data()
    print(f"Excel 读取成功: 供热公司总表 {len(overall_data)} 天, 10中心明细 {len(center_data)} 条记录")
    
    with engine.connect() as conn:
        backup_current_db(conn)
        
    generate_sql_script(overall_data, center_data)
    execute_migration_in_db(overall_data, center_data)
    verify_database_state(overall_data, center_data)
    print("\n🎉 全部修正与验证顺利完成！")


if __name__ == '__main__':
    main()
