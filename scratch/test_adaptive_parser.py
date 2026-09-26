# -*- coding: utf-8 -*-
"""
智能多区块 Excel 盘点表解析器原型
验证对混合型、非标多区块报表的自动识别与清洗分流能力。
"""
import re
import openpyxl
from datetime import datetime

def normalize_pipe_model(raw_spec: str) -> str:
    """直管规格清洗标准化: Φ377X7.0 Φ471X7.0 -> Φ377×7/Φ471×7"""
    s = str(raw_spec or "").strip()
    s = s.replace("X", "×").replace("x", "×").replace("*", "×")
    # 去除无意义的 .0
    s = re.sub(r'(\d+)\.0\b', r'\1', s)
    # 将两个钢管与外护管之间的连续空格替换为斜杠
    s = re.sub(r'\s+', '/', s)
    return s

def parse_supplier_inventory_excel(file_path: str):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    
    pipe_items = []
    fitting_items = []
    unrecognized_rows = []
    
    # 状态机当前上下文
    current_col_map = {}
    current_block_type = None  # 'pipe' or 'fitting'
    
    for row_idx, r in enumerate(rows, start=1):
        # 1. 过滤全空行
        if not any(r):
            continue
            
        # 2. 判断是否是杂质大标题行 (如 "表五：预制保温直三通管")
        first_cell = str(r[0] or "").strip()
        if first_cell.startswith("表") and ("管" in first_cell or "三通" in first_cell or "弯头" in first_cell):
            continue
            
        # 3. 判断是否是区块表头行 (包含 '序号' 或 '规格' 等)
        row_str = " ".join([str(c or "") for c in r])
        if "序号" in row_str and ("规格" in row_str or "型号" in row_str or "材料" in row_str or "分项" in row_str):
            # 重新构建当前区块的列映射
            current_col_map = {}
            for col_idx, cell in enumerate(r):
                val = str(cell or "").strip()
                if not val:
                    continue
                if "分项" in val or "材料" in val or "名称" in val:
                    current_col_map["name"] = col_idx
                elif "规格" in val or "型号" in val:
                    current_col_map["spec"] = col_idx
                elif "单位" in val:
                    current_col_map["unit"] = col_idx
                elif "库存米数" in val:
                    current_col_map["stock_pipe"] = col_idx
                elif "库存" in val and "支" not in val:
                    current_col_map["stock_fitting"] = col_idx
                elif "合同" in val or "数量" in val:
                    current_col_map["contract_qty"] = col_idx
                    
            # 探测当前区块是大类直管还是管件
            if "库存米数" in row_str or "分项名称" in row_str:
                current_block_type = "pipe"
            else:
                current_block_type = "fitting"
            continue
            
        # 4. 数据行解析 (第一列通常为正整数序号)
        is_data_row = False
        try:
            if isinstance(r[0], (int, float)) or (isinstance(r[0], str) and r[0].strip().isdigit()):
                is_data_row = True
        except Exception:
            pass
            
        if not is_data_row:
            unrecognized_rows.append({"row": row_idx, "content": r})
            continue
            
        name_idx = current_col_map.get("name", 1)
        spec_idx = current_col_map.get("spec", 2)
        
        name_val = str(r[name_idx] or "").strip() if len(r) > name_idx else ""
        spec_val = str(r[spec_idx] or "").strip() if len(r) > spec_idx else ""
        
        if not spec_val:
            continue
            
        if current_block_type == "pipe" or "保温管" in name_val:
            # 直管逻辑: 优先取 stock_pipe (通常是第7列/索引6)
            stock_idx = current_col_map.get("stock_pipe", 6)
            stock_qty = float(r[stock_idx] or 0) if len(r) > stock_idx and r[stock_idx] is not None else 0.0
            norm_spec = normalize_pipe_model(spec_val)
            pipe_items.append({
                "row_idx": row_idx,
                "category": name_val or "聚氨酯预制直埋保温管",
                "raw_spec": spec_val,
                "norm_model": norm_spec,
                "unit": "米",
                "stock_qty": stock_qty
            })
        else:
            # 管件逻辑: 优先取 stock_fitting (第5列/索引4)
            stock_idx = current_col_map.get("stock_fitting", 4)
            stock_qty = float(r[stock_idx] or 0) if len(r) > stock_idx and r[stock_idx] is not None else 0.0
            
            # 智能提取管件类别
            fitting_type = name_val
            if "弯头" in name_val:
                fitting_type = "弯头"
            elif "三通" in name_val:
                fitting_type = "三通"
            elif "变径" in name_val:
                fitting_type = "变径管"
                
            fitting_items.append({
                "row_idx": row_idx,
                "raw_name": name_val,
                "fitting_type": fitting_type,
                "model_spec": spec_val,
                "unit": "个",
                "stock_qty": stock_qty
            })
            
    return pipe_items, fitting_items, unrecognized_rows

if __name__ == "__main__":
    p_items, f_items, un_rows = parse_supplier_inventory_excel(r'configs/9.26 鑫瑞得大连项目截止2026年9月20日.xlsx')
    print(f"✅ 解析成功: 直管项数 = {len(p_items)}, 管件项数 = {len(f_items)}, 未识别行 = {len(un_rows)}")
    print(f"   直管前 2 项: {p_items[:2]}")
    print(f"   管件前 2 项: {f_items[:2]}")
    total_p = sum(x['stock_qty'] for x in p_items)
    total_f = sum(x['stock_qty'] for x in f_items)
    print(f"   直管在库总米数: {total_p:,.1f} 米 | 管件在库总数: {total_f:,.0f} 个")
