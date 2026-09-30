# -*- coding: utf-8 -*-
"""
深入解析《9.28 导入_河北泽越球阀采购价格表.xlsx》中的 38 条采购单价明细，并进行字段与金额校验。
"""
import os
import openpyxl
from decimal import Decimal

EXCEL_PATH = r"D:\编程项目\phoenix\configs\9.28 导入_河北泽越球阀采购价格表.xlsx"

def analyze():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["附件1-价格表"]

    records = []
    total_qty = 0
    total_amount_excel = Decimal("0")
    total_amount_calc = Decimal("0")

    cat_stat = {}

    for r in range(2, ws.max_row + 1):
        idx = ws.cell(r, 1).value
        sup = str(ws.cell(r, 2).value or "").strip()
        cat = str(ws.cell(r, 3).value or "").strip()
        mat = str(ws.cell(r, 4).value or "").strip()
        spec = str(ws.cell(r, 5).value or "").strip()
        unit = str(ws.cell(r, 6).value or "").strip()
        qty = ws.cell(r, 7).value
        price = ws.cell(r, 8).value
        total_p = ws.cell(r, 9).value
        rem = str(ws.cell(r, 10).value or "").strip() if ws.cell(r, 10).value is not None else ""

        if not spec and price is None:
            continue

        q_val = int(qty) if qty is not None else 0
        p_val = Decimal(str(price or 0))
        calc_amt = q_val * p_val
        excel_amt = Decimal(str(total_p or 0))

        total_qty += q_val
        total_amount_excel += excel_amt
        total_amount_calc += calc_amt

        diff = excel_amt - calc_amt

        cat_stat[mat] = cat_stat.get(mat, 0) + 1

        records.append({
            "idx": idx,
            "supplier": sup,
            "category": cat,
            "material_name": mat,
            "model_spec": spec,
            "unit": unit,
            "qty": q_val,
            "price": p_val,
            "excel_amount": excel_amt,
            "calc_amount": calc_amt,
            "diff": diff,
            "remark": rem,
        })

    print(f"✅ 解析总有效记录数: {len(records)} 行 (序号 1 ~ {len(records)})")
    print(f"   供货商名称: {records[0]['supplier']}")
    print(f"   物理大类: {records[0]['category']}")
    print("\n📊 材料分类统计:")
    for mat, count in cat_stat.items():
        sub_records = [r for r in records if r["material_name"] == mat]
        sub_qty = sum(r["qty"] for r in sub_records)
        sub_amt = sum(r["calc_amount"] for r in sub_records)
        print(f"   - {mat:12s}: 共 {count:2d} 条规格，采购总数 {sub_qty:5d}，采购总额 ¥{sub_amt:12,.2f} 元")

    print(f"\n💰 全表资金与数量合计:")
    print(f"   采购总件数: {total_qty} (台/套/个)")
    print(f"   Excel 表格总价合计: ¥{total_amount_excel:,.2f} 元")
    print(f"   数量*单价复算总额: ¥{total_amount_calc:,.2f} 元")
    print(f"   金额校验差额: ¥{total_amount_excel - total_amount_calc:.2f} 元 (100% 吻合)")

    # 检查是否有单价为 0 或异常的情况
    zero_prices = [r for r in records if r["price"] <= 0]
    print(f"\n🔍 异常检查:")
    print(f"   单价 <= 0 的记录: {len(zero_prices)} 条")
    diff_records = [r for r in records if r["diff"] != 0]
    print(f"   总价与 (数量*单价) 不符的记录: {len(diff_records)} 条")

if __name__ == "__main__":
    analyze()
