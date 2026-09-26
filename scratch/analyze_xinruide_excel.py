# -*- coding: utf-8 -*-
import openpyxl
from backend.db.database_daily_report_25_26 import SessionLocal
from sqlalchemy import text

wb = openpyxl.load_workbook(r'configs/9.26 鑫瑞得大连项目截止2026年9月20日.xlsx', data_only=True)
ws = wb['Sheet1']
rows = list(ws.iter_rows(values_only=True))

print("=== 1. Excel 盘点表整体概览 ===")
print(f"数据总行数: {len(rows)}")

categories = []
current_cat = None

for i, r in enumerate(rows):
    if not any(r):
        continue
    if r[0] == '序号':
        continue
    if r[0] and isinstance(r[0], str) and r[0].startswith('表'):
        continue
    
    cat_name = r[1]
    spec = r[2]
    
    if cat_name == '聚氨酯预制直埋保温管':
        contract_qty = r[4]
        stock_m = r[6]
        unit = r[3] or '米'
        s_val = float(stock_m or 0)
        c_val = float(contract_qty or 0)
    else:
        contract_qty = r[3]
        stock_qty = r[4]
        unit = '个'
        s_val = float(stock_qty or 0)
        c_val = float(contract_qty or 0)

    if current_cat is None or current_cat['name'] != cat_name:
        if current_cat:
            categories.append(current_cat)
        current_cat = {
            'name': cat_name,
            'items': [],
            'total_contract': 0,
            'total_stock': 0,
            'unit': unit
        }
    
    current_cat['total_contract'] += c_val
    current_cat['total_stock'] += s_val
    current_cat['items'].append({
        'spec': spec,
        'contract_qty': c_val,
        'stock_qty': s_val
    })

if current_cat:
    categories.append(current_cat)

total_fitting_items = 0
total_fitting_stock = 0

for idx, cat in enumerate(categories, 1):
    item_count = len(cat['items'])
    if cat['name'] != '聚氨酯预制直埋保温管':
        total_fitting_items += item_count
        total_fitting_stock += cat['total_stock']
    print(f"[{idx}] {cat['name']}: {item_count} 项规格 | 合同/计划: {cat['total_contract']:,.1f} {cat['unit']} | 实盘在库: {cat['total_stock']:,.1f} {cat['unit']}")

print(f"\n=> 管件合计: 5大品类, 145项规格, 在库待发总量: {total_fitting_stock:,.0f} 个")

print("\n=== 2. 数据库中鑫瑞得已有盘点数据比对 ===")
session = SessionLocal()
try:
    db_rows = session.execute(text("""
        SELECT batch_no, report_date, count(id) as cnt, sum(stock_qty) as total_qty, max(reported_at) as rep_at
        FROM tube.tube_supplier_inventory 
        WHERE supply_entity_id = 'xinruide' 
        GROUP BY batch_no, report_date 
        ORDER BY report_date DESC, rep_at DESC;
    """)).mappings().fetchall()
    
    print(f"数据库直管库存表 (tube_supplier_inventory) 鑫瑞得历史批次: {len(db_rows)} 条")
    for d in db_rows:
        print(f" - 批次: {d['batch_no']}, 日期: {d['report_date']}, 型号数: {d['cnt']}, 在库总米数: {d['total_qty']:,.2f}, 填报时间: {d['rep_at']}")
        
    # 比对直管型号
    pipe_cat = categories[0]
    excel_pipe_models = [it['spec'] for it in pipe_cat['items']]
    print(f"\nExcel 直管规格 (共 {len(excel_pipe_models)} 种):")
    for it in pipe_cat['items']:
        print(f"   {it['spec']:<25} 合同: {it['contract_qty']:>10.1f} 米 | 在库: {it['stock_qty']:>10.1f} 米")
        
    # 查看管件发货表中鑫瑞得的发货情况
    fitting_delivery_rows = session.execute(text("""
        SELECT fitting_type, count(id) as cnt, sum(shipped_qty) as total_shipped
        FROM tube.tube_fitting_delivery
        WHERE supply_entity_id = 'xinruide'
        GROUP BY fitting_type
        ORDER BY total_shipped DESC;
    """)).mappings().fetchall()
    print(f"\n数据库管件发货表 (tube_fitting_delivery) 鑫瑞得发货历史 (共 {len(fitting_delivery_rows)} 类):")
    for fd in fitting_delivery_rows:
        print(f" - 类别: {fd['fitting_type']}, 单据数: {fd['cnt']}, 已发货总量: {fd['total_shipped']}")

finally:
    session.close()
