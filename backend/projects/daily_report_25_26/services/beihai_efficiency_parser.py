"""
北海热电厂能效报表（Excel）解析服务
严格仅抽取【本期】生产数据，严禁触碰或改变同期值数据。
分别映射到生产日报的 3 张子表：
1. BeiHai_co_generation_Sheet: 1.北海热电厂（热电联产）表
2. BeiHai_water_boiler_Sheet: 2.北海热电厂（水炉）表
3. BeiHai_gas_boiler_Sheet: 3.北海热电厂（天然气炉）表
"""

import io
import datetime
import re
from typing import Dict, Any, Optional, Tuple
import openpyxl


def _clean_val(v: Any) -> Optional[float]:
    """清洗数值：支持过滤异常公式错误字符与空值，规范为浮点数"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 4)
    s = str(v).strip()
    if not s or s.startswith('#') or s in ('-', 'None', 'null'):
        return None
    try:
        s_clean = s.replace(',', '')
        return round(float(s_clean), 4)
    except (ValueError, TypeError):
        return None


def _clean_str(v: Any) -> str:
    """清洗文本，过滤 Excel 常见错误码"""
    if v is None:
        return ""
    s = str(v).strip()
    # 仅过滤 Excel 错误公式字符串（如 #VALUE!, #DIV/0!, #REF!），不得过滤 #1炉、#2机 等设备工况
    if re.match(r"^#[A-Z/!?]+", s) or s in ('None', 'null'):
        return ""
    return s


def _parse_steam_boiler_and_turbine(s: str) -> Tuple[int, int]:
    """解析热电联产运行方式文本，获取运行汽炉数与运行汽轮机数。若为空、停运或无记录则识别为 (0, 0)"""
    if not s or s in ('0', '停', '无', 'None'):
        return 0, 0
    s_clean = s.replace('\n', ' ').strip()
    if not s_clean or s_clean in ('0', '停', '无'):
        return 0, 0
    
    # 查找汽炉数
    boiler_cnt = 0
    m_boiler = re.search(r'([^机]*?)炉', s_clean)
    if m_boiler:
        nums = re.findall(r'\d+', m_boiler.group(1))
        boiler_cnt = len(nums) if nums else 1
    elif '炉' in s_clean:
        boiler_cnt = 1
        
    # 查找汽轮机数
    turbine_cnt = 0
    m_turb = re.search(r'([^炉]*?)机', s_clean)
    if m_turb:
        nums = re.findall(r'\d+', m_turb.group(1))
        turbine_cnt = len(nums) if nums else 1
    elif '机' in s_clean:
        turbine_cnt = 1
        
    return boiler_cnt, turbine_cnt


def _parse_boiler_count(s: str) -> int:
    """解析水炉或燃气炉运行方式文本，获取运行台数。若为空、停运或无记录则识别为 0"""
    if not s or s in ('0', '停', '无', 'None'):
        return 0
    s_clean = s.replace('\n', ' ').strip()
    if not s_clean or s_clean in ('0', '停', '无'):
        return 0
    nums = re.findall(r'\d+', s_clean)
    return len(nums) if nums else (1 if '炉' in s_clean else 0)


def parse_beihai_efficiency_excel(
    file_bytes: bytes,
    biz_date_str: str,
) -> Dict[str, Any]:
    """
    解析北海能效分析表 Excel 文件，严格仅提取【本期】（当前业务年份）生产数据。
    严禁提取或覆盖任何历史同期数据。
    """
    try:
        dt = datetime.datetime.strptime(biz_date_str.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"无效的业务日期格式: {biz_date_str}，应为 YYYY-MM-DD")

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    
    # 1. 寻找匹配的工作表 (Sheet)
    target_year = dt.year
    target_month = dt.month
    target_day = dt.day
    
    candidate_sheet_names = [
        f"{target_year}.{target_month:02d}",
        f"{target_year}.{target_month}",
        f"{target_year}年{target_month}月",
        f"{target_year}-{target_month:02d}",
    ]
    
    sheet_name = None
    for name in candidate_sheet_names:
        if name in wb.sheetnames:
            sheet_name = name
            break
            
    if not sheet_name:
        for s in wb.sheetnames:
            if f"{target_year}" in s and f"{target_month}" in s:
                sheet_name = s
                break
                
    if not sheet_name:
        raise ValueError(
            f"未在上传的 Excel 中找到业务月份对应的工作表（需包含 {target_year}.{target_month:02d}），当前包含的工作表为: {', '.join(wb.sheetnames)}"
        )
        
    ws = wb[sheet_name]
    
    # 2. 在 Row 1 中寻找日期对应的列 (从第 3 列开始)
    date_col = None
    for col in range(3, ws.max_column + 1):
        cell_val = ws.cell(1, col).value
        if isinstance(cell_val, (datetime.datetime, datetime.date)):
            if cell_val.day == target_day:
                date_col = col
                break
        elif cell_val is not None:
            c_str = str(cell_val).strip()
            m = re.match(r"^(\d+)", c_str)
            if m and int(m.group(1)) == target_day:
                date_col = col
                break
                
    if not date_col:
        for r in (2, 3):
            for col in range(3, ws.max_column + 1):
                cell_val = ws.cell(r, col).value
                if isinstance(cell_val, (datetime.datetime, datetime.date)) and cell_val.day == target_day:
                    date_col = col
                    break
                if cell_val is not None:
                    m = re.match(r"^(\d+)", str(cell_val).strip())
                    if m and int(m.group(1)) == target_day:
                        date_col = col
                        break
            if date_col:
                break
                
    if not date_col:
        raise ValueError(
            f"在工作表【{sheet_name}】中未找到业务日期 {target_day} 日对应的列"
        )

    # 3. 抽取本期数据（只取 2026 本期专属行，严禁触碰 2025 年同期行）
    def get_current_num(row_idx: int) -> float:
        """严格获取当前本期行数值，若为空或不可解析则返回 0.0"""
        v = ws.cell(row_idx, date_col).value
        cleaned = _clean_val(v)
        return cleaned if cleaned is not None else 0.0

    def get_current_str(row_idx: int) -> str:
        """获取当前本期行文本"""
        return _clean_str(ws.cell(row_idx, date_col).value)

    # === 表 1: 热电联产表 (BeiHai_co_generation_Sheet) ===
    # 严格使用 2026 本期物理行号：
    boiler_str = get_current_str(171) # 2026 运行方式 炉/机
    boiler_count, turbine_count = _parse_steam_boiler_and_turbine(boiler_str)

    co_gen_water = get_current_num(222) # Row 222: 2026 电厂耗水量
    co_gen_power = get_current_num(235) # Row 235: 2026 外购电量
    
    co_gen_cells = [
        {"row_label": "发电量", "unit": "万kWh", "value": get_current_num(174)},       # Row 174: 2026本期发电量
        {"row_label": "供热量", "unit": "GJ", "value": get_current_num(199)},         # Row 199: 2026本期供热量
        {"row_label": "供汽量", "unit": "吨", "value": get_current_num(194)},         # Row 194: 2026本期供汽量
        {"row_label": "售电量", "unit": "万kWh", "value": get_current_num(179)},       # Row 179: 2026本期上网供电量
        {"row_label": "原煤耗量", "unit": "吨", "value": get_current_num(204)},       # Row 204: 2026本期耗原煤量
        {"row_label": "标煤耗量", "unit": "吨", "value": get_current_num(209)},       # Row 209: 2026本期耗标煤量
        {"row_label": "耗水量", "unit": "吨", "value": co_gen_water},
        {"row_label": "其中：电厂耗水量", "unit": "吨", "value": co_gen_water},
        {"row_label": "外购电量", "unit": "万kWh", "value": co_gen_power},
        {"row_label": "其中：电厂外购电量", "unit": "万kWh", "value": co_gen_power},
        {"row_label": "耗酸量", "unit": "吨", "value": get_current_num(252)},         # Row 252: 2026本期耗酸量
        {"row_label": "耗碱量", "unit": "吨", "value": get_current_num(257)},         # Row 257: 2026本期耗碱量
        {"row_label": "耗油量", "unit": "吨", "value": get_current_num(230)},         # Row 230: 2026本期耗柴油量
        {"row_label": "耗氨水量", "unit": "吨", "value": get_current_num(247)},       # Row 247: 2026本期氨水
        {"row_label": "耗石灰石粉量", "unit": "吨", "value": get_current_num(242)},   # Row 242: 2026本期石灰石
        {"row_label": "运行汽炉数", "unit": "台", "value": boiler_count},
        {"row_label": "运行汽轮机数", "unit": "台", "value": turbine_count},
    ]

    # === 表 2: 水炉表 (BeiHai_water_boiler_Sheet) ===
    # 严格使用 2026 本期物理行号：
    water_boiler_status = get_current_str(343) # Row 343: 2026 水炉运行方式
    water_boiler_count = _parse_boiler_count(water_boiler_status)

    wb_water = get_current_num(366) # Row 366: 2026 水炉耗水量
    wb_power = get_current_num(379) # Row 379: 2026 水炉耗电量
    
    water_boiler_cells = [
        {"row_label": "供热量", "unit": "GJ", "value": get_current_num(346)},         # Row 346: 2026本期炉侧供热量
        {"row_label": "原煤耗量", "unit": "吨", "value": get_current_num(351)},       # Row 351: 2026本期耗原煤量
        {"row_label": "标煤耗量", "unit": "吨", "value": get_current_num(356)},       # Row 356: 2026本期耗标煤量
        {"row_label": "耗水量", "unit": "吨", "value": wb_water},
        {"row_label": "其中：电厂耗水量", "unit": "吨", "value": wb_water},
        {"row_label": "外购电量", "unit": "万kWh", "value": wb_power},
        {"row_label": "其中：电厂外购电量", "unit": "万kWh", "value": wb_power},
        {"row_label": "耗酸量", "unit": "吨", "value": 0.0},
        {"row_label": "耗碱量", "unit": "吨", "value": 0.0},
        {"row_label": "耗油量", "unit": "吨", "value": get_current_num(374)},         # Row 374: 2026本期耗柴油量
        {"row_label": "耗氨水量", "unit": "吨", "value": get_current_num(389)},       # Row 389: 2026本期氨水
        {"row_label": "耗石灰石粉量", "unit": "吨", "value": get_current_num(384)},   # Row 384: 2026本期石灰石
        {"row_label": "运行水炉数", "unit": "台", "value": water_boiler_count},
    ]

    # === 表 3: 天然气炉表 (BeiHai_gas_boiler_Sheet) ===
    # 严格使用燃气炉本期物理行号：
    gas_boiler_status = get_current_str(429) # Row 429: 燃气炉运行方式
    gas_boiler_count = _parse_boiler_count(gas_boiler_status)

    gas_water = get_current_num(438) # Row 438: 燃气炉耗水量
    gas_power = get_current_num(441) # Row 441: 燃气炉耗电量
    
    gas_boiler_cells = [
        {"row_label": "供热量", "unit": "GJ", "value": get_current_num(435)},         # Row 435: 燃气炉供热量
        {"row_label": "供汽量", "unit": "吨", "value": get_current_num(432)},         # Row 432: 燃气炉供汽量
        {"row_label": "耗天然气量", "unit": "m³", "value": get_current_num(444)},       # Row 444: 燃气炉耗天然气量
        {"row_label": "耗水量", "unit": "吨", "value": gas_water},
        {"row_label": "其中：电厂耗水量", "unit": "吨", "value": gas_water},
        {"row_label": "外购电量", "unit": "万kWh", "value": gas_power},
        {"row_label": "其中：电厂外购电量", "unit": "万kWh", "value": gas_power},
        {"row_label": "运行天然气炉数", "unit": "台", "value": gas_boiler_count},
    ]

    total_matched = len(co_gen_cells) + len(water_boiler_cells) + len(gas_boiler_cells)

    return {
        "ok": True,
        "biz_date": biz_date_str,
        "sheet_name": sheet_name,
        "day": target_day,
        "data": {
            "BeiHai_co_generation_Sheet": {
                "sheet_name": "1.北海热电厂（热电联产）表",
                "matched_count": len(co_gen_cells),
                "cells": co_gen_cells,
            },
            "BeiHai_water_boiler_Sheet": {
                "sheet_name": "2.北海热电厂（水炉）表",
                "matched_count": len(water_boiler_cells),
                "cells": water_boiler_cells,
            },
            "BeiHai_gas_boiler_Sheet": {
                "sheet_name": "3.北海热电厂（天然气炉）表",
                "matched_count": len(gas_boiler_cells),
                "cells": gas_boiler_cells,
            },
        },
        "summary": {
            "total_matched": total_matched,
            "message": f"成功从工作表【{sheet_name}】第 {target_day} 日列提取北海 3 张表格【本期实际值】共 {total_matched} 项（同期值保持锁定未修改）！"
        }
    }
