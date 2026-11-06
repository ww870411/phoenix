# -*- coding: utf-8 -*-
"""
周期运行汇报多维生产经营数据 XLSX 导出服务。

功能：
1. 针对自选起止日期（start ~ end），提取全集团、主城区及下属各单位的生产、经营、单耗、客服与气温指标；
2. 忠实对齐系统底层物理字段，支持按天拆解的月度计划测算值（标煤耗量、供热量等）；
3. 严格排除非白名单及用户指定剔除的 9 项指标、瞬时工况与服务中心级细分；
4. 智能追溯同期值与上期值（支持整月自然月对标与非整月向前等长对标）；
5. 整合调度主设备运行状态、电力现货 15 分钟 96 点电价走势及调度日志/抢修记录；
6. 生成标准 4 个 Sheet 的 XLSX 报表，支持直接下载与一键保存至【材料仓库】供 Agent 深度分析。
"""

from __future__ import annotations

import io
import os
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import DATA_DIRECTORY
from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine
from backend.services.heating_metrics.daily_engine import DailyDashboardEngine
from backend.services.heating_metrics.season_utils import get_peer_date, get_season_period
from .daily_brief import number
from .period_report import compute_period_plans, compute_period_weather, report_value
from .period_report_files import format_beijing_time, format_file_size, sanitize_filename

# 10 家标准主体口径定义（顺序保持一致）
SUBJECTS: List[Tuple[str, str]] = [
    ("Group", "集团全口径汇总"),
    ("ZhuChengQu", "主城区汇总"),
    ("BeiHai", "北海热电厂"),
    ("XiangHai", "香海热电厂"),
    ("GongRe", "供热公司"),
    ("JinZhou", "金州热电"),
    ("BeiFang", "北方热电"),
    ("JinPu", "金普热电"),
    ("ZhuangHe", "庄河环海"),
    ("YanJiuYuan", "研究院"),
]

# 保留指标白名单（严格排除剔除项，指标名称忠实对齐系统定义）
# 格式: (类别, 字段键, 中文名称, 单位, 是否计算计划分解测算值, 小数位数)
METRICS_WHITELIST: List[Tuple[str, str, str, str, bool, int]] = [
    # 生产产销与耗用核心指标（均支持月计划值与期间计划分解测算）
    ("生产指标", "amount_heat_supply", "供热量", "GJ", True, 2),
    ("生产指标", "amount_power_generation", "发电量", "万kWh", True, 2),
    ("生产指标", "amount_power_sales", "售电量", "万kWh", True, 2),
    ("生产指标", "amount_hot_water_sales", "高温水销售量", "GJ", True, 2),
    ("生产指标", "amount_steam_sales", "售汽量", "吨", True, 2),
    ("生产指标", "consumption_std_coal", "标煤耗量", "吨", True, 2),
    ("生产指标", "consumption_amount_raw_coal", "原煤耗量", "吨", True, 2),
    ("生产指标", "consumption_water", "耗水量", "吨", True, 2),
    ("生产指标", "consumption_purchased_power", "耗电量", "万kWh", True, 2),
    ("生产指标", "consumption_outer_purchased_heat", "外购热量", "GJ", True, 2),
    ("生产指标", "consumption_station_heat", "站内耗热量", "GJ", True, 2),

    # 经营指标
    ("经营指标", "eco_direct_income", "直接收入", "万元", False, 2),
    ("经营指标", "eco_marginal_profit", "实际边际利润", "万元", False, 2),
    ("经营指标", "eco_comparable_marginal_profit", "可比煤价边际利润", "万元", False, 2),
    ("经营指标", "eco_power_supply_income", "售电收入", "万元", False, 2),
    ("经营指标", "eco_heating_supply_income", "供暖收入", "万元", False, 2),
    ("经营指标", "eco_hot_water_supply_income", "售高温水收入", "万元", False, 2),
    ("经营指标", "eco_steam_supply_income", "售汽收入", "万元", False, 2),
    ("经营指标", "eco_coal_cost", "煤成本", "万元", False, 2),
    ("经营指标", "eco_purchased_power_cost", "外购电成本", "万元", False, 2),
    ("经营指标", "eco_purchased_water_cost", "购水成本", "万元", False, 2),
    ("经营指标", "eco_measurable_auxiliary_materials", "可计量辅材成本", "万元", False, 2),

    # 单耗指标（支持月度考核目标与期间基准）
    ("单耗指标", "rate_std_coal_per_heat", "供热标煤单耗", "吨/万㎡", True, 3),
    ("单耗指标", "rate_heat_per_10k_m2", "供暖热单耗", "GJ/万㎡", True, 2),
    ("单耗指标", "rate_power_per_10k_m2", "供暖电单耗", "kWh/万㎡", True, 2),
    ("单耗指标", "rate_water_per_10k_m2", "供暖水单耗", "吨/万㎡", True, 2),

    # 服务质量指标
    ("服务质量", "amount_daily_net_complaints", "当日净投诉量", "件", False, 0),
    ("服务质量", "amount_daily_service_complaints", "省市平台投诉量", "件", False, 0),
    ("服务质量", "amount_daily_net_complaints_per_10k_m2", "万平方米净投诉量", "件/万㎡", False, 4),
]


def compute_comparison_dates(start: date, end: date, include_prev: bool = False) -> Dict[str, Any]:
    """
    计算本期、同期（去年对标）和上期（环比对标）日期区间。
    - 同期：通过 get_peer_date 逐日映射
    - 上期：
      * 若当前选择整月（start 为 1 日且 end 为该月最后一天）：
        上期也自动对齐上一个自然整月（如 3.1~3.31 的上期对齐 2.1~2.28/29，即使天数不同）
      * 若为非整月：按相同天数向前追溯
    """
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    days_count = len(days)

    peer_days = [get_peer_date(d) for d in days]
    peer_start = min(peer_days)
    peer_end = max(peer_days)

    # 检查是否为完整自然整月
    month_last_day = monthrange(start.year, start.month)[1]
    is_full_month = (start.day == 1 and end.day == month_last_day and start.year == end.year and start.month == end.month)

    prev_start: Optional[date] = None
    prev_end: Optional[date] = None

    if include_prev:
        if is_full_month:
            # 整月模式：上一个月整月
            prev_end = start - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
        else:
            # 非整月模式：向前等长追溯
            prev_end = start - timedelta(days=1)
            prev_start = prev_end - timedelta(days=days_count - 1)

    return {
        "curr_start": start,
        "curr_end": end,
        "days_count": days_count,
        "is_full_month": is_full_month,
        "peer_start": peer_start,
        "peer_end": peer_end,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "include_prev": include_prev and (prev_start is not None),
    }


def _calc_diff_and_rate(curr: Optional[float], base: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """计算增减绝对值与增幅百分比（以小数形式返回，如 0.052 表示 +5.2%）。"""
    if curr is None or base is None:
        return None, None
    diff = round(curr - base, 4)
    if abs(base) < 1e-9:
        rate = None
    else:
        rate = round(diff / abs(base), 6)
    return diff, rate


def _apply_styles_to_sheet(ws, title_text: str, header_row_idx: int = 2) -> None:
    """为工作表统一应用工程级美观样式与冻结首行/表头。"""
    # 颜色与字体定义
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Microsoft YaHei", size=10, bold=True, color="FFFFFF")
    title_font = Font(name="Microsoft YaHei", size=13, bold=True, color="1F4E79")
    sub_font = Font(name="Microsoft YaHei", size=9, italic=True, color="595959")
    
    thin_border_side = Side(border_style="thin", color="D9D9D9")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    # 标题行（若第 1 行为大标题）
    if header_row_idx > 1:
        ws.row_dimensions[1].height = 28
        cell_a1 = ws.cell(row=1, column=1)
        cell_a1.font = title_font
        cell_a1.alignment = Alignment(vertical="center")

    # 表头行高度与样式
    ws.row_dimensions[header_row_idx].height = 24
    max_col = ws.max_column
    for col_idx in range(1, max_col + 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border

    # 冻结表头下方
    ws.freeze_panes = ws.cell(row=header_row_idx + 1, column=1)

    # 自动列宽自适应
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            if cell.row < header_row_idx:
                continue
            val_str = str(cell.value or "")
            # 中文字符长度折算
            cell_len = sum(2 if ord(c) > 127 else 1 for c in val_str)
            if cell_len > max_len:
                max_len = cell_len
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)


def compute_period_and_month_plans(
    db: Session,
    start: date,
    end: date
) -> Tuple[Dict[Tuple[str, str], float], Dict[Tuple[str, str], float]]:
    """
    从 paln_and_real_month_data 读取并计算：
    1. month_plans: 统计周期跨越各月的月度计划总额（全月目标原值）
    2. period_plans: 按照周期天数占当月比例折算的本期计划分解测算值
    
    层级智能聚合规则：
    - 主城区 (ZhuChengQu) 成员: BeiHai, XiangHai, GongRe
    - 集团全口径 (Group) 成员: BeiHai, XiangHai, GongRe, JinZhou, BeiFang, JinPu, ZhuangHe, YanJiuYuan
    - 若底表中 ZhuChengQu 或 Group 缺失某项产销总量指标（如发电量、售电量、售汽量、高温水销售量、站内耗热量、外购热量等），
      自动自下而上由各成员单位求和补齐；
    - 单耗指标（rate_ 开头）采用底表既有基准，不作简单累加。
    """
    if db is None:
        return {}, {}
    try:
        from decimal import Decimal
        from sqlalchemy import text

        cursor = start.replace(day=1)
        month_plans: Dict[Tuple[str, str], float] = {}
        period_plans: Dict[Tuple[str, str], float] = {}

        zcq_members = ["BeiHai", "XiangHai", "GongRe"]
        group_members = ["BeiHai", "XiangHai", "GongRe", "JinZhou", "BeiFang", "JinPu", "ZhuangHe", "YanJiuYuan"]

        while cursor <= end:
            cutoff = min(end, cursor.replace(day=monthrange(cursor.year, cursor.month)[1]))
            month_days = monthrange(cursor.year, cursor.month)[1]
            period_days = (cutoff - max(start, cursor)).days + 1
            ratio = Decimal(period_days) / Decimal(month_days)

            rows = db.execute(text("""
                SELECT company, item, value, unit FROM paln_and_real_month_data
                WHERE period = :period AND type = 'plan'
            """), {"period": cursor.isoformat()}).mappings().all()

            cur_m: Dict[Tuple[str, str], float] = {}
            cur_p: Dict[Tuple[str, str], float] = {}

            for r in rows:
                c, it = r["company"], r["item"]
                val = r["value"]
                if val is not None:
                    f_val = float(val)
                    cur_m[(c, it)] = f_val
                    if "rate_" in it:
                        cur_p[(c, it)] = f_val
                    else:
                        prorated = float(Decimal(str(val)) * ratio)
                        cur_p[(c, it)] = prorated

            # 智能补齐主城区 (ZhuChengQu) 与全集团 (Group) 产销指标
            all_items = set(it for (c, it) in cur_m.keys())
            for it in all_items:
                if "rate_" in it:
                    continue
                # 补齐主城区
                if ("ZhuChengQu", it) not in cur_m:
                    sub_m = sum(cur_m.get((c, it), 0.0) for c in zcq_members)
                    sub_p = sum(cur_p.get((c, it), 0.0) for c in zcq_members)
                    if sub_m > 0:
                        cur_m[("ZhuChengQu", it)] = sub_m
                        cur_p[("ZhuChengQu", it)] = sub_p
                # 补齐集团全口径
                if ("Group", it) not in cur_m:
                    sub_m = sum(cur_m.get((c, it), 0.0) for c in group_members)
                    sub_p = sum(cur_p.get((c, it), 0.0) for c in group_members)
                    if sub_m > 0:
                        cur_m[("Group", it)] = sub_m
                        cur_p[("Group", it)] = sub_p

            for k, v in cur_m.items():
                month_plans[k] = month_plans.get(k, 0.0) + v
                period_plans[k] = period_plans.get(k, 0.0) + cur_p[k]

            cursor = cutoff.replace(day=1) + timedelta(days=32)
            cursor = cursor.replace(day=1)

        return month_plans, period_plans
    except Exception:
        return {}, {}


def generate_period_report_xlsx(
    db: Session,
    start: date,
    end: date,
    include_prev: bool = True
) -> io.BytesIO:
    """
    生成周期运行汇报综合多维数据分析 XLSX 报表（包含 4 个标准 Sheet）。
    返回内存中的二进制字节流。
    """
    comp_dates = compute_comparison_dates(start, end, include_prev)
    peer_start = comp_dates["peer_start"]
    peer_end = comp_dates["peer_end"]
    prev_start = comp_dates["prev_start"]
    prev_end = comp_dates["prev_end"]
    has_prev = comp_dates["include_prev"]

    wb = openpyxl.Workbook()
    # 移除默认创建的空 Sheet
    default_sheet = wb.active
    if default_sheet is not None:
        wb.remove(default_sheet)

    # 边框与字体
    data_font = Font(name="Microsoft YaHei", size=9)
    bold_data_font = Font(name="Microsoft YaHei", size=9, bold=True)
    thin_side = Side(border_style="thin", color="E0E0E0")
    data_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    alt_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    summary_fill = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")

    # =========================================================================
    # Sheet 1: 指标对标全景总表
    # =========================================================================
    ws1 = wb.create_sheet(title="指标对标全景总表")
    
    # 1. 标题与说明
    date_desc = f"统计周期: {start.isoformat()} ~ {end.isoformat()} (共{comp_dates['days_count']}天) | 去年同期: {peer_start.isoformat()} ~ {peer_end.isoformat()}"
    if has_prev and prev_start and prev_end:
        mode_str = "整月对标" if comp_dates["is_full_month"] else f"等长追溯{comp_dates['days_count']}天"
        date_desc += f" | 环比上期: {prev_start.isoformat()} ~ {prev_end.isoformat()} ({mode_str})"
    ws1.cell(row=1, column=1, value=f"供暖集团周期生产运行多维指标对标全景表 [{date_desc}]")

    # 2. 表头构建
    headers1 = [
        "主体编码", "单位名称", "指标分类", "系统字段名", "指标名称", "单位",
        "本期实际值", "月度计划值", "期间计划分解测算", "计划完成率", "计划进度偏差",
        "同期实际值", "同比增减", "同比增幅"
    ]
    if has_prev:
        headers1.extend(["上期实际值", "环比增减", "环比增幅"])

    ws1.append(headers1)  # 第2行表头

    # 3. 提取业务数据
    engine = HeatingAnalysisEngine(db)
    keys = [m[1] for m in METRICS_WHITELIST]
    windows = [("curr", start, end), ("sync", peer_start, peer_end)]
    if has_prev and prev_start and prev_end:
        windows.append(("prev", prev_start, prev_end))

    # 批量计算各主体、各窗口指标值
    values: Dict[Tuple[str, str, str], Optional[float]] = {}
    for side, w_start, w_end in windows:
        for comp_code, _ in SUBJECTS:
            try:
                calculated = engine.compute_analysis_rows(comp_code, keys, w_start, w_end, aggregate=True, clip_to_season=False)
                for k in keys:
                    values[(side, comp_code, k)] = report_value(calculated.get(k, {}).get("value_biz_date"))
            except Exception:
                for k in keys:
                    values[(side, comp_code, k)] = 0.0

    # 计算所跨月份的月度计划原值与本期分解测算值（含主城区与集团层级智能聚合）
    month_plans, period_plans = compute_period_and_month_plans(db, start, end)

    # 写入指标明细行
    row_idx = 3
    for comp_code, comp_cn in SUBJECTS:
        is_summary_comp = comp_code in ("Group", "ZhuChengQu")
        for category, key, label, unit, has_plan, decimals in METRICS_WHITELIST:
            curr_val = values.get(("curr", comp_code, key))
            sync_val = values.get(("sync", comp_code, key))
            prev_val = values.get(("prev", comp_code, key)) if has_prev else None

            # 计划测算项与对比
            m_plan_val: Optional[float] = None
            p_plan_val: Optional[float] = None
            plan_rate: Optional[float] = None
            plan_diff: Optional[float] = None
            if has_plan:
                raw_m = month_plans.get((comp_code, key))
                raw_p = period_plans.get((comp_code, key))
                if raw_m is not None:
                    m_plan_val = round(float(raw_m), decimals)
                if raw_p is not None:
                    p_plan_val = round(float(raw_p), decimals)
                    if curr_val is not None and p_plan_val and p_plan_val > 0:
                        plan_rate = round(curr_val / p_plan_val, 4)
                        plan_diff = round(curr_val - p_plan_val, decimals)

            # 同比对比
            yoy_diff, yoy_rate = _calc_diff_and_rate(curr_val, sync_val)
            # 环比对比
            mom_diff, mom_rate = _calc_diff_and_rate(curr_val, prev_val) if has_prev else (None, None)

            row_data: List[Any] = [
                comp_code, comp_cn, category, key, label, unit,
                curr_val, m_plan_val, p_plan_val, plan_rate, plan_diff,
                sync_val, yoy_diff, yoy_rate
            ]
            if has_prev:
                row_data.extend([prev_val, mom_diff, mom_rate])

            ws1.append(row_data)

            # 单元格格式化与样式
            for col_i in range(1, len(row_data) + 1):
                cell = ws1.cell(row=row_idx, column=col_i)
                cell.font = bold_data_font if is_summary_comp else data_font
                cell.border = data_border
                if is_summary_comp:
                    cell.fill = summary_fill
                elif row_idx % 2 == 1:
                    cell.fill = alt_fill

                # 对齐与数字格式化
                if col_i in (1, 3, 4, 6):
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_i in (2, 5):
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    # 百分比列：计划完成率(10), 同比增幅(14), 环比增幅(17)
                    if col_i in (10, 14, 17):
                        if cell.value is not None:
                            cell.number_format = "0.0%"
                    elif col_i in (7, 8, 9, 11, 12, 13, 15, 16):
                        if cell.value is not None:
                            fmt = "#,##0" if decimals == 0 else f"#,##0.{'0' * decimals}"
                            cell.number_format = fmt

            row_idx += 1

    # 添加气象环境行至 Sheet 1 末尾作为基准环境事实
    weather_info = compute_period_weather(
        db, start, end, peer_start, peer_end,
        prev_start or start, prev_end or end, has_prev
    )
    weather_rows = [
        ("Group", "集团全口径汇总", "气象气温", "aver_temp_main_city", "主城区平均气温", "℃",
         weather_info.get("avgTemp"), None, None, None, None,
         weather_info.get("peerAvgTemp"), weather_info.get("yoyDiff"), None,
         weather_info.get("prevAvgTemp"), weather_info.get("momDiff"), None),
        ("Group", "集团全口径汇总", "气象气温", "min_temp_main_city", "主城区最低气温", "℃",
         weather_info.get("minTemp"), None, None, None, None, None, None, None, None, None, None),
        ("Group", "集团全口径汇总", "气象气温", "max_temp_main_city", "主城区最高气温", "℃",
         weather_info.get("maxTemp"), None, None, None, None, None, None, None, None, None, None),
    ]
    for w_row in weather_rows:
        w_data = list(w_row[:14])
        if has_prev:
            w_data.extend(w_row[14:17])
        ws1.append(w_data)
        for col_i in range(1, len(w_data) + 1):
            cell = ws1.cell(row=row_idx, column=col_i)
            cell.font = bold_data_font
            cell.border = data_border
            cell.fill = summary_fill
            if col_i in (1, 3, 4, 6):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_i in (2, 5):
                cell.alignment = Alignment(horizontal="left", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if cell.value is not None and isinstance(cell.value, (int, float)):
                    cell.number_format = "0.0"
        row_idx += 1

    _apply_styles_to_sheet(ws1, "指标对标全景总表", header_row_idx=2)

    # =========================================================================
    # Sheet 2: 设备运行与开停机
    # =========================================================================
    ws2 = wb.create_sheet(title="设备运行与开停机")
    ws2.cell(row=1, column=1, value=f"生产调度主设备工况与开停机时序记录表 [{start.isoformat()} ~ {end.isoformat()}]")
    headers2 = ["业务日期", "所属单位/厂区", "设备类型", "锅炉细分", "设备规范名", "原始名称", "运行状态", "状态来源", "操作时刻", "调度操作与动态描述"]
    ws2.append(headers2)

    dispatch_sql = text("""
        SELECT biz_date, boiler_turbine_status, operations_and_tickets
        FROM public.dispatch_daily_reports
        WHERE project_key = 'daily_report_25_26'
          AND biz_date >= :start AND biz_date <= :end
        ORDER BY biz_date ASC
    """)
    dispatch_rows = db.execute(dispatch_sql, {"start": start.isoformat(), "end": end.isoformat()}).mappings().all()

    row_idx2 = 3
    for d_row in dispatch_rows:
        b_date_str = str(d_row["biz_date"])
        facilities = d_row.get("boiler_turbine_status") or []
        events = d_row.get("operations_and_tickets") or []

        # 整理当天的操作事件说明（按设备匹配）
        op_map: Dict[str, List[str]] = {}
        for ev in events:
            if not isinstance(ev, dict):
                continue
            desc = ev.get("raw_description") or ev.get("source_description") or ""
            tm = ev.get("time") or ev.get("event_clock") or ""
            full_txt = f"{tm} {desc}".strip()
            org = ev.get("responsible_org") or ""
            op_map.setdefault(org, []).append(full_txt)

        if isinstance(facilities, list) and facilities:
            for fac in facilities:
                if not isinstance(fac, dict):
                    continue
                unit = fac.get("unit_or_plant") or ""
                f_type = fac.get("facility_type") or ""
                b_type = fac.get("boiler_type") or "-"
                std_name = fac.get("standard_name") or ""
                raw_name = fac.get("raw_name") or ""
                st = fac.get("status") or fac.get("table_status") or "—"
                src = fac.get("status_source") or "table"

                # 提取关联的设备动态说明
                matched_ops = op_map.get(unit, [])
                op_notes = "；".join(matched_ops) if matched_ops else ""

                r_data = [b_date_str, unit, f_type, b_type, std_name, raw_name, st, src, "-", op_notes]
                ws2.append(r_data)
                for col_i in range(1, len(r_data) + 1):
                    cell = ws2.cell(row=row_idx2, column=col_i)
                    cell.font = data_font
                    cell.border = data_border
                    if row_idx2 % 2 == 1:
                        cell.fill = alt_fill
                    cell.alignment = Alignment(horizontal="center" if col_i in (1, 3, 4, 7, 8, 9) else "left", vertical="center")
                row_idx2 += 1
        else:
            # 当日无设备明细但有操作记录时的保底
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                r_data = [b_date_str, ev.get("responsible_org") or "调度中心", "调度事项", "-", "-", "-", "正常", "log", ev.get("time") or "", ev.get("raw_description") or ""]
                ws2.append(r_data)
                row_idx2 += 1

    _apply_styles_to_sheet(ws2, "设备运行与开停机", header_row_idx=2)

    # =========================================================================
    # Sheet 3: 电力现货电价走势
    # =========================================================================
    ws3 = wb.create_sheet(title="电力现货电价走势")
    ws3.cell(row=1, column=1, value=f"辽宁电力现货 15 分钟日前与实时电价时序明细表 [{start.isoformat()} ~ {end.isoformat()}]")
    headers3 = ["交易日期", "点位序号", "点位时刻", "日前电价(元/MWh)", "实时电价(元/MWh)", "实时与日前价差(元/MWh)"]
    ws3.append(headers3)

    spot_sql = text("""
        SELECT trade_date, point_index, time_label, day_ahead_price, real_time_price
        FROM public.spot_electricity_15min_data
        WHERE trade_date >= :start AND trade_date <= :end
        ORDER BY trade_date ASC, point_index ASC
    """)
    spot_rows = db.execute(spot_sql, {"start": start.isoformat(), "end": end.isoformat()}).mappings().all()

    row_idx3 = 3
    for s_row in spot_rows:
        t_date = str(s_row["trade_date"])
        p_idx = s_row["point_index"]
        t_lbl = s_row["time_label"] or ""
        da_p = float(s_row["day_ahead_price"]) if s_row["day_ahead_price"] is not None else None
        rt_p = float(s_row["real_time_price"]) if s_row["real_time_price"] is not None else None
        spread = round(rt_p - da_p, 2) if (da_p is not None and rt_p is not None) else None

        r_data = [t_date, p_idx, t_lbl, da_p, rt_p, spread]
        ws3.append(r_data)
        for col_i in range(1, len(r_data) + 1):
            cell = ws3.cell(row=row_idx3, column=col_i)
            cell.font = data_font
            cell.border = data_border
            if row_idx3 % 2 == 1:
                cell.fill = alt_fill
            if col_i in (1, 2, 3):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if cell.value is not None:
                    cell.number_format = "#,##0.00"
        row_idx3 += 1

    _apply_styles_to_sheet(ws3, "电力现货电价走势", header_row_idx=2)

    # =========================================================================
    # Sheet 4: 调度日志与抢修记录
    # =========================================================================
    ws4 = wb.create_sheet(title="调度日志与抢修记录")
    ws4.cell(row=1, column=1, value=f"生产调度发令事件与管网抢修/检修工作票记录表 [{start.isoformat()} ~ {end.isoformat()}]")
    headers4 = ["业务日期", "发生时刻", "责任单位", "事项类型", "涉及管线/设备", "调度指令与工况描述", "工期或抢修说明"]
    ws4.append(headers4)

    row_idx4 = 3
    for d_row in dispatch_rows:
        b_date_str = str(d_row["biz_date"])
        events = d_row.get("operations_and_tickets") or []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            tm = ev.get("time") or ev.get("event_clock") or "-"
            org = ev.get("responsible_org") or "调度中心"
            is_ticket = ev.get("is_ticket", False)
            ev_type = "抢修工作票" if is_ticket else "调度指令"
            pipe_or_dev = ev.get("pipe_size") or ev.get("location") or "-"
            desc = ev.get("raw_description") or ev.get("source_description") or ""
            time_range = ev.get("time_range") or "-"

            r_data = [b_date_str, tm, org, ev_type, pipe_or_dev, desc, time_range]
            ws4.append(r_data)
            for col_i in range(1, len(r_data) + 1):
                cell = ws4.cell(row=row_idx4, column=col_i)
                cell.font = data_font
                cell.border = data_border
                if row_idx4 % 2 == 1:
                    cell.fill = alt_fill
                cell.alignment = Alignment(horizontal="center" if col_i in (1, 2, 4) else "left", vertical="center")
            row_idx4 += 1

    _apply_styles_to_sheet(ws4, "调度日志与抢修记录", header_row_idx=2)

    # 保存至内存流
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def save_period_report_xlsx(
    db: Session,
    start: date,
    end: date,
    include_prev: bool = True,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    生成并在服务器物理持久化保存 XLSX 报表至【材料仓库】空间。
    路径: backend_data/projects/daily_report_25_26/period_report/材料仓库/
    """
    store_dir = (DATA_DIRECTORY / "projects" / "daily_report_25_26" / "period_report" / "材料仓库").resolve()
    store_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        tag = "_生产数据明细(含上期).xlsx" if include_prev else "_生产数据明细.xlsx"
        filename = f"{start.isoformat()}_{end.isoformat()}{tag}"
    else:
        filename = sanitize_filename(filename)
        if not filename.lower().endswith(".xlsx"):
            filename = os.path.splitext(filename)[0] + ".xlsx"

    target_path = store_dir / filename
    stream = generate_period_report_xlsx(db, start, end, include_prev)
    target_path.write_bytes(stream.getvalue())

    stat = target_path.stat()
    return {
        "ok": True,
        "name": filename,
        "rel_path": filename,
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "created_at": format_beijing_time(stat.st_ctime),
        "updated_at": format_beijing_time(stat.st_mtime),
        "is_template": False,
        "kind": "excel",
        "message": f"生产数据明细已成功保存至材料仓库: {filename}"
    }
