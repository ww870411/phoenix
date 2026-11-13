# -*- coding: utf-8 -*-
"""
供暖期指标竞赛 Excel 报表导出服务。

生成包含 3 张联动工作表的 .xlsx 工作簿：
1. 考评兑现汇总：参照《考评意见报告》正文兑现表（名次、单位、基数、指标结果、竞赛指标奖励金额[按5元倍数取整]、其他嘉奖、奖励合计）；
2. 指标得分矩阵：参照《考评意见报告》附图样式（灰底黑框、7家单位横向并列项目与分值，公式联动明细表）；
3. 计算过程明细：7家单位各项指标的计划值、实际完成值、达成率/排名、算式过程与数据来源，底部附5家供热单位投诉率横向排名依据。
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# 标准 7 家单位顺序与名称映射
STANDARD_UNIT_ORDER = [
    "BeiHai",
    "XiangHai",
    "GongRe",
    "JinZhou",
    "BeiFang",
    "JinPu",
    "ZhuangHe",
]

# 统一字体与边框样式
_FONT_FAMILY = "宋体"
_THIN_SIDE = Side(border_style="thin", color="000000")
_BORDER_ALL = Border(left=_THIN_SIDE, right=_THIN_SIDE, top=_THIN_SIDE, bottom=_THIN_SIDE)

_FILL_HEADER = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
_FILL_SUBHEADER = PatternFill(start_color="EEF2F7", end_color="EEF2F7", fill_type="solid")
_FILL_SUBTOTAL = PatternFill(start_color="F5F7FA", end_color="F5F7FA", fill_type="solid")
_FILL_DISQUALIFIED = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
_FILL_HIGHLIGHT = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
_FILL_MANUAL = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")

_FONT_TITLE = Font(name=_FONT_FAMILY, size=14, bold=True, color="111827")
_FONT_SUBTITLE = Font(name=_FONT_FAMILY, size=10, italic=False, color="475569")
_FONT_TH = Font(name=_FONT_FAMILY, size=10, bold=True, color="000000")
_FONT_TD = Font(name=_FONT_FAMILY, size=10, color="111827")
_FONT_TD_BOLD = Font(name=_FONT_FAMILY, size=10, bold=True, color="111827")
_FONT_TD_MUTED = Font(name=_FONT_FAMILY, size=9, color="64748B")
_FONT_TD_RED = Font(name=_FONT_FAMILY, size=10, bold=True, color="B91C1C")
_FONT_TD_GREEN = Font(name=_FONT_FAMILY, size=10, bold=True, color="15803D")
_FONT_TD_MANUAL = Font(name=_FONT_FAMILY, size=10, bold=True, color="92400E")
_FONT_MANUAL_TAG = Font(name=_FONT_FAMILY, size=9, bold=True, color="B45309")

_ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_ALIGN_RIGHT = Alignment(horizontal="right", vertical="center", wrap_text=True)


def _to_num(val: Any) -> Optional[float]:
    """安全转换为浮点数；空值返回 None。"""
    if val is None or val == "":
        return None
    try:
        num = float(val)
        return None if num != num else num
    except (TypeError, ValueError):
        return None


def _get_unit_extra_rewards(unit: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """提取单位的额外嘉奖明细与合计金额。"""
    raw_items = unit.get("extraRewards")
    cleaned_items: List[Dict[str, Any]] = []
    total = 0.0
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            remark = str(item.get("remark") or "").strip()
            amount = _to_num(item.get("amount"))
            if not title and amount is None and not remark:
                continue
            amt_val = float(amount) if amount is not None else 0.0
            total += amt_val
            cleaned_items.append(
                {
                    "title": title or "专项嘉奖",
                    "amount": amt_val,
                    "remark": remark,
                }
            )
    if not cleaned_items:
        fallback_total = _to_num(unit.get("extraRewardTotal"))
        if fallback_total is not None:
            total = float(fallback_total)
    return total, cleaned_items


def _normalize_excel_money(val: float) -> Any:
    """整型金额返回 int，含小数金额保留两位小数。"""
    rounded = round(float(val), 2)
    return int(rounded) if rounded == int(rounded) else rounded


def _format_num_str(val: Optional[float], decimals: int = 2) -> str:
    """将数字格式化为带千分位的展示字符串。"""
    if val is None:
        return "-"
    return f"{val:,.{decimals}f}"


def _build_rate_and_process(
    ind: Dict[str, Any],
    complaint_rank_map: Dict[str, Tuple[int, int]],
    unit_code: str,
) -> Tuple[str, str]:
    """根据指标计算类型，生成达成率/排名文本与简明算式过程说明。"""
    calc_type = str(ind.get("calcType") or "")
    weight = _to_num(ind.get("weight")) or 0.0
    target = _to_num(ind.get("targetValue"))
    actual = _to_num(ind.get("actualValue"))
    score = _to_num(ind.get("score"))

    if calc_type == "complaint_rank":
        if actual is None or score is None:
            return "-", "投诉率暂未出数，不参与排名"
        rank_info = complaint_rank_map.get(unit_code)
        if rank_info:
            rank_num, total_cnt = rank_info
            return (
                f"第 {rank_num} 名 (共{total_cnt}家)",
                f"5家供热单位投诉率升序第{rank_num}名 → 20 - ({rank_num}-1)×2 = {score:.2f}分",
            )
        return "-", f"横向排名得分 {score:.2f}分"

    if actual is None:
        return "-", "月报尚未出数，实际值留空（暂不计分）"

    if calc_type == "shutdown":
        times = max(0.0, actual)
        final_s = score if score is not None else max(0.0, weight - times * 5.0)
        return f"{int(times)} 次", f"基准0次，发生{int(times)}次：10 - {int(times)}×5 = {final_s:.2f}分"

    if calc_type == "civic":
        final_s = score if score is not None else max(0.0, min(weight, actual))
        return f"{actual:.1f} / 10", f"现场评定直接计入得分：{final_s:.2f}分"

    if target is None or target <= 0:
        return "-", "缺少计划基准值，暂不计分"

    if calc_type in ("energy_saving", "energy_saving_half"):
        rate = (1.0 + (target - actual) / target) * 100.0
        diff_pct = rate - 100.0
        step = 0.5 if calc_type == "energy_saving_half" else 1.0
        raw_score = weight + diff_pct * step
        cap = weight * 1.2
        final_s = score if score is not None else max(0.0, min(cap, raw_score))
        cap_note = f"（封顶{cap:.2f}）" if raw_score > cap else ("（不计负分）" if raw_score < 0 else "")
        return (
            f"{rate:.2f}%",
            f"完成率=1+({_format_num_str(target)}-{_format_num_str(actual)})/{_format_num_str(target)}={rate:.2f}%；"
            f"{weight:.0f}+({diff_pct:+.2f})×{step:g}={raw_score:.2f}{cap_note} → {final_s:.2f}分",
        )

    if calc_type == "consumption":
        rate = (1.0 + (target - actual) / target) * 100.0
        raw_score = (rate / 100.0) * weight
        cap = weight * 1.2
        final_s = score if score is not None else max(0.0, min(cap, raw_score))
        cap_note = f"（封顶{cap:.2f}）" if raw_score > cap else ("（不计负分）" if raw_score < 0 else "")
        return (
            f"{rate:.2f}%",
            f"完成率={rate:.2f}%；{weight:.0f}×{rate:.2f}%={raw_score:.2f}{cap_note} → {final_s:.2f}分",
        )

    if calc_type == "spot_price":
        rate = (actual / target) * 100.0
        diff_pct = rate - 100.0
        raw_score = weight + (diff_pct / 3.0)
        cap = weight * 1.2
        final_s = score if score is not None else max(0.0, min(cap, raw_score))
        cap_note = f"（封顶{cap:.2f}）" if raw_score > cap else ("（不计负分）" if raw_score < 0 else "")
        return (
            f"{rate:.2f}%",
            f"比值={actual:.2f}/{target:.2f}={rate:.2f}%；{weight:.0f}+({diff_pct:+.2f}÷3)={raw_score:.2f}{cap_note} → {final_s:.2f}分",
        )

    if calc_type == "efficiency":
        rate = (1.0 + (actual - target) / target) * 100.0
        diff_pct = rate - 100.0
        raw_score = weight + diff_pct * 2.0
        cap = weight * 1.1
        final_s = score if score is not None else max(0.0, min(cap, raw_score))
        cap_note = f"（封顶{cap:.2f}）" if raw_score > cap else ("（不计负分）" if raw_score < 0 else "")
        return (
            f"{rate:.2f}%",
            f"完成率=1+({actual:.2f}-{target:.2f})/{target:.2f}={rate:.2f}%；"
            f"{weight:.0f}+({diff_pct:+.2f})×2={raw_score:.2f}{cap_note} → {final_s:.2f}分",
        )

    if calc_type == "pipe_cutoff":
        rate_str = f"{actual:.2f}%"
        final_s = score if score is not None else (0.0 if actual < 95.0 else max(0.0, weight - max(0.0, target - actual)))
        if actual < 95.0:
            return rate_str, f"断管率 {actual:.2f}% < 95%，按规则直接得 0.00分"
        gap = max(0.0, target - actual)
        return rate_str, f"低于标准{gap:.2f}%：{weight:.0f} - {gap:.2f}×1 = {final_s:.2f}分"

    return "-", f"核算得分 {score:.2f}分" if score is not None else "-"


def _get_unit_by_code(units_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """按标准单位代码索引。"""
    unit_map: Dict[str, Dict[str, Any]] = {}
    for u in units_data:
        if isinstance(u, dict) and u.get("code"):
            unit_map[str(u["code"])] = u
    return unit_map


def _build_complaint_ranking(units_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建 5 家供热单位投诉率升序排名列表。"""
    rows: List[Dict[str, Any]] = []
    for unit in units_data:
        if not isinstance(unit, dict):
            continue
        inds = unit.get("indicators") or []
        c_ind = next((i for i in inds if isinstance(i, dict) and i.get("calcType") == "complaint_rank"), None)
        if not c_ind:
            continue
        val = _to_num(c_ind.get("actualValue"))
        base_score = _to_num(c_ind.get("score"))
        is_black = bool(unit.get("isBlackListed"))
        is_red = bool(unit.get("isRedListed"))
        final_score = 0.0 if is_black else ((base_score or 0.0) + (5.0 if is_red else 0.0) if base_score is not None else None)
        rows.append({
            "code": str(unit.get("code") or ""),
            "name": str(unit.get("name") or ""),
            "complaintCount": _to_num(c_ind.get("complaintCount")),
            "heatingArea": _to_num(c_ind.get("heatingArea")),
            "actualValue": val,
            "isManualActual": bool(c_ind.get("isManualActual")),
            "baseScore": base_score,
            "isBlackListed": is_black,
            "isRedListed": is_red,
            "finalScore": final_score,
        })
    rows.sort(key=lambda r: (r["actualValue"] is None, r["actualValue"] if r["actualValue"] is not None else 999999.0))
    for idx, r in enumerate(rows, start=1):
        r["rank"] = idx
    return rows


def _style_range(ws: Any, min_col: int, min_row: int, max_col: int, max_row: int, **kwargs: Any) -> None:
    """批量给区域单元格设置样式。"""
    for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
        for cell in row:
            for attr, val in kwargs.items():
                if val is not None:
                    setattr(cell, attr, val)


def _match_indicator(unit: Dict[str, Any], name_keywords: Tuple[str, ...]) -> Optional[Dict[str, Any]]:
    """按指标名称关键字匹配单位指标项。"""
    for ind in unit.get("indicators") or []:
        if not isinstance(ind, dict):
            continue
        ind_name = str(ind.get("name") or "")
        if any(kw in ind_name for kw in name_keywords):
            return ind
    return None


def _build_detail_sheet(
    wb: openpyxl.Workbook,
    month_label: str,
    status_note: str,
    units_data: List[Dict[str, Any]],
    complaint_rows: List[Dict[str, Any]],
    now_str: str,
) -> Tuple[Dict[Tuple[str, str], str], Dict[str, str]]:
    """
    构建 Sheet 3《计算过程明细》，返回：
    - indicator_coord_map: {(unit_code, item_key): "J5"} 用于 Sheet 2 链接
    - subtotal_coord_map: {unit_code: "J12"} 用于校验
    """
    ws = wb.create_sheet(title="计算过程明细")
    ws.views.sheetView[0].showGridLines = True

    complaint_rank_map: Dict[str, Tuple[int, int]] = {
        r["code"]: (r["rank"], len(complaint_rows)) for r in complaint_rows
    }

    # 标题
    ws.merge_cells("A1:K1")
    ws["A1"] = f"{month_label} 供暖期指标竞赛各单位得分计算过程明细表"
    ws["A1"].font = _FONT_TITLE
    ws["A1"].alignment = _ALIGN_CENTER
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:K2")
    ws["A2"] = f"状态说明：{status_note or '在线实时测算'}   |   导出时间：{now_str}"
    ws["A2"].font = _FONT_SUBTITLE
    ws["A2"].alignment = _ALIGN_CENTER
    ws.row_dimensions[2].height = 20

    ws.merge_cells("A3:K3")
    ws["A3"] = "着色说明：浅琥珀色底纹单元格表示该指标“实际完成值”经过人工填写或手动调整。"
    ws["A3"].font = _FONT_MANUAL_TAG
    ws["A3"].fill = _FILL_MANUAL
    ws["A3"].alignment = _ALIGN_CENTER
    ws.row_dimensions[3].height = 18

    headers = [
        "参评单位", "指标类别", "考核指标", "权重分",
        "计划值(标准)", "实际完成值", "计量单位", "达成率/排名",
        "得分计算过程（算式与规则说明）", "核算得分", "数据来源",
    ]
    ws.row_dimensions[4].height = 24
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = _FONT_TH
        cell.fill = _FILL_HEADER
        cell.border = _BORDER_ALL
        cell.alignment = _ALIGN_CENTER

    unit_map = _get_unit_by_code(units_data)
    indicator_coord_map: Dict[Tuple[str, str], str] = {}
    subtotal_coord_map: Dict[str, str] = {}

    cur_row = 5
    for unit_code in STANDARD_UNIT_ORDER:
        unit = unit_map.get(unit_code)
        if not unit:
            continue
        unit_name = str(unit.get("name") or unit_code)
        unit_start_row = cur_row

        # 1) 运营指标
        op_inds = [
            i for i in (unit.get("indicators") or [])
            if isinstance(i, dict) and i.get("calcType") != "civic"
        ]
        for ind in op_inds:
            ind_name = str(ind.get("name") or "")
            weight = _to_num(ind.get("weight"))
            target = _to_num(ind.get("targetValue")) if ind.get("hasTarget") else (0.0 if ind.get("calcType") == "shutdown" else None)
            actual = _to_num(ind.get("actualValue"))
            score = _to_num(ind.get("score"))
            is_manual_actual = bool(ind.get("isManualActual"))
            rate_str, proc_str = _build_rate_and_process(ind, complaint_rank_map, unit_code)
            source_text = str(ind.get("sourceLabel") or "")
            if is_manual_actual and "人工调整" not in source_text:
                source_text = f"{source_text}【人工调整】" if source_text else "人工调整"

            row_vals = [
                unit_name,
                "运营指标",
                ind_name,
                weight,
                target if target is not None else ("-" if ind.get("calcType") == "complaint_rank" else None),
                actual,
                str(ind.get("unit") or ""),
                rate_str,
                proc_str,
                round(score, 2) if score is not None else None,
                source_text,
            ]
            ws.row_dimensions[cur_row].height = 22
            for c_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=cur_row, column=c_idx, value=val)
                cell.font = _FONT_TD_BOLD if c_idx == 10 else (_FONT_TD_MUTED if c_idx == 11 else _FONT_TD)
                cell.border = _BORDER_ALL
                if is_manual_actual and c_idx in (6, 11):
                    cell.fill = _FILL_MANUAL
                    cell.font = _FONT_TD_MANUAL if c_idx == 6 else _FONT_MANUAL_TAG
                if c_idx in (1, 2, 4, 7, 8):
                    cell.alignment = _ALIGN_CENTER
                elif c_idx in (5, 6, 10):
                    cell.alignment = _ALIGN_RIGHT
                else:
                    cell.alignment = _ALIGN_LEFT
                if c_idx in (5, 6) and isinstance(val, (int, float)):
                    cell.number_format = "#,##0.0000" if ind.get("calcType") == "complaint_rank" else "#,##0.00"
                elif c_idx == 10 and isinstance(val, (int, float)):
                    cell.number_format = "0.00"

            # 记录精确坐标供 Sheet 2 矩阵表引用
            coord = f"J{cur_row}"
            if "标煤" in ind_name:
                indicator_coord_map[(unit_code, "coal")] = coord
            elif ind_name == "外购热量":
                indicator_coord_map[(unit_code, "coal")] = coord
            elif ind_name == "供暖热单耗":
                indicator_coord_map[(unit_code, "heat_unit")] = coord
            elif ind_name == "厂内水耗量":
                indicator_coord_map[(unit_code, "plant_water")] = coord
            elif ind_name == "供暖电单耗":
                indicator_coord_map[(unit_code, "elec_unit")] = coord
            elif ind_name == "现货电价":
                indicator_coord_map[(unit_code, "spot_price")] = coord
            elif ind_name == "供暖水单耗":
                indicator_coord_map[(unit_code, "water_unit")] = coord
            elif ind_name == "全厂热效率":
                indicator_coord_map[(unit_code, "heat_eff")] = coord
            elif ind_name == "服务投诉率":
                indicator_coord_map[(unit_code, "complaint")] = coord
            elif ind_name == "非计划停炉停机":
                indicator_coord_map[(unit_code, "shutdown")] = coord
            elif ind_name == "停供断管率":
                indicator_coord_map[(unit_code, "pipe_cutoff")] = coord

            cur_row += 1

        # 2) 安全文明生产
        civic_ind = next(
            (i for i in (unit.get("indicators") or []) if isinstance(i, dict) and i.get("calcType") == "civic"),
            {"name": "安全文明生产", "weight": 10, "unit": "分", "targetValue": 10, "actualValue": 10, "score": 10, "calcType": "civic", "sourceLabel": "手动填报"},
        )
        civic_actual = _to_num(civic_ind.get("actualValue"))
        civic_score = _to_num(civic_ind.get("score"))
        civic_is_manual = bool(civic_ind.get("isManualActual"))
        _, civic_proc = _build_rate_and_process(civic_ind, complaint_rank_map, unit_code)
        civic_source = str(civic_ind.get("sourceLabel") or "手动填报")
        if civic_is_manual and "人工调整" not in civic_source:
            civic_source = f"{civic_source}【人工调整】"
        civic_vals = [
            unit_name, "管理指标", "安全文明生产", 10.0, 10.0, civic_actual, "分",
            f"{civic_actual:.1f} / 10" if civic_actual is not None else "-",
            civic_proc,
            round(civic_score, 2) if civic_score is not None else None,
            civic_source,
        ]
        ws.row_dimensions[cur_row].height = 22
        for c_idx, val in enumerate(civic_vals, start=1):
            cell = ws.cell(row=cur_row, column=c_idx, value=val)
            cell.font = _FONT_TD_BOLD if c_idx == 10 else (_FONT_TD_MUTED if c_idx == 11 else _FONT_TD)
            cell.border = _BORDER_ALL
            if civic_is_manual and c_idx in (6, 11):
                cell.fill = _FILL_MANUAL
                cell.font = _FONT_TD_MANUAL if c_idx == 6 else _FONT_MANUAL_TAG
            cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 4, 7, 8) else (_ALIGN_RIGHT if c_idx in (5, 6, 10) else _ALIGN_LEFT)
            if c_idx in (5, 6, 10) and isinstance(val, (int, float)):
                cell.number_format = "0.00"
        indicator_coord_map[(unit_code, "civic")] = f"J{cur_row}"
        cur_row += 1

        # 3) 安全环保事故
        has_major = bool(unit.get("hasMajorAccident"))
        has_general = bool(unit.get("hasGeneralAccident"))
        acc_score = -10.0 if has_general else 0.0
        if has_major and has_general:
            acc_status, acc_proc = "较大及以上+一般事故", "一般事故扣10分，且较大及以上事故触发一票否决（取消当月资格）"
        elif has_major:
            acc_status, acc_proc = "较大及以上事故", "触发一票否决（取消当月奖金兑现资格）"
        elif has_general:
            acc_status, acc_proc = "一般安全事故", "发生一般安全事故，综合得分扣减 10.00 分"
        else:
            acc_status, acc_proc = "无异常", "未发生安全环保事故 → 0.00分"

        acc_vals = [unit_name, "管理指标", "安全环保事故", "-", "-", acc_status, "-", "-", acc_proc, acc_score, "手动认定"]
        ws.row_dimensions[cur_row].height = 21
        for c_idx, val in enumerate(acc_vals, start=1):
            cell = ws.cell(row=cur_row, column=c_idx, value=val)
            cell.font = _FONT_TD_RED if (has_major or has_general) and c_idx in (6, 9, 10) else (_FONT_TD_MUTED if c_idx == 11 else _FONT_TD)
            cell.border = _BORDER_ALL
            cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 4, 5, 6, 7, 8) else (_ALIGN_RIGHT if c_idx == 10 else _ALIGN_LEFT)
            if c_idx == 10:
                cell.number_format = "0.00"
        indicator_coord_map[(unit_code, "accident")] = f"J{cur_row}"
        cur_row += 1

        # 4) 红黑榜奖惩
        is_red = bool(unit.get("isRedListed"))
        is_black = bool(unit.get("isBlackListed"))
        rb_score = 5.0 if is_red else 0.0
        if is_black and is_red:
            rb_status, rb_proc = "红榜+黑榜", "进入民心网黑榜触发一票否决（取消当月资格）；红榜+5.00分"
        elif is_black:
            rb_status, rb_proc = "民心网黑榜", "进入民心网投诉黑榜，一票否决取消当月兑现资格"
        elif is_red:
            rb_status, rb_proc = "民心网红榜", "进入民心网投诉红榜，额外奖励 +5.00 分"
        else:
            rb_status, rb_proc = "无", "未进入民心网红黑榜 → 0.00分"

        rb_vals = [unit_name, "管理指标", "红黑榜奖惩", "-", "-", rb_status, "-", "-", rb_proc, rb_score, "手动认定"]
        ws.row_dimensions[cur_row].height = 21
        for c_idx, val in enumerate(rb_vals, start=1):
            cell = ws.cell(row=cur_row, column=c_idx, value=val)
            cell.font = _FONT_TD_RED if is_black and c_idx in (6, 9) else (_FONT_TD_GREEN if is_red and c_idx in (6, 9, 10) else (_FONT_TD_MUTED if c_idx == 11 else _FONT_TD))
            cell.border = _BORDER_ALL
            cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 4, 5, 6, 7, 8) else (_ALIGN_RIGHT if c_idx == 10 else _ALIGN_LEFT)
            if c_idx == 10:
                cell.number_format = "0.00"
        indicator_coord_map[(unit_code, "redblack")] = f"J{cur_row}"
        cur_row += 1

        # 5) 单位小计行
        unit_end_row = cur_row - 1
        pending_cnt = int(unit.get("pendingCount") or 0)
        eligible = bool(unit.get("eligible", True))
        disq_reason = str(unit.get("disqualifyReason") or "")
        status_desc = (
            disq_reason if not eligible
            else (f"阶段测算（尚有{pending_cnt}项待月报出数）" if pending_cnt > 0 else "正常兑现")
        )
        ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=8)
        ws.cell(row=cur_row, column=1, value=f"【{unit_name}】综合得分小计（基数：¥{int(unit.get('baseAmount') or 0):,}）")
        ws.cell(row=cur_row, column=9, value=f"资格状态：{status_desc}")
        ws.cell(row=cur_row, column=10, value=f"=MAX(0, SUM(J{unit_start_row}:J{unit_end_row}))")
        ws.cell(row=cur_row, column=11, value="公式汇总")
        ws.row_dimensions[cur_row].height = 22
        _style_range(
            ws, 1, cur_row, 11, cur_row,
            fill=_FILL_DISQUALIFIED if not eligible else _FILL_SUBTOTAL,
            font=_FONT_TD_BOLD,
            border=_BORDER_ALL,
        )
        ws.cell(row=cur_row, column=1).alignment = _ALIGN_LEFT
        ws.cell(row=cur_row, column=9).alignment = _ALIGN_LEFT
        ws.cell(row=cur_row, column=10).alignment = _ALIGN_RIGHT
        ws.cell(row=cur_row, column=10).number_format = "0.00"
        ws.cell(row=cur_row, column=11).alignment = _ALIGN_CENTER
        subtotal_coord_map[unit_code] = f"J{cur_row}"

        cur_row += 2  # 单位之间空一行，视觉更透气

    # 底部附表：5 家供热单位服务投诉率横向排名依据
    if complaint_rows:
        ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=8)
        ws.cell(row=cur_row, column=1, value="附表：供热单位服务投诉率横向排名计算依据（5 家参评供热单位）")
        ws.cell(row=cur_row, column=1).font = _FONT_TH
        ws.cell(row=cur_row, column=1).alignment = _ALIGN_LEFT
        ws.row_dimensions[cur_row].height = 22
        cur_row += 1

        c_headers = ["排名", "供热单位", "月末累计净投诉(件)", "供暖收费面积(万㎡)", "服务投诉率(件/万㎡)", "排名基础分", "红黑榜状态", "投诉最终计分"]
        ws.row_dimensions[cur_row].height = 22
        for c_idx, h in enumerate(c_headers, start=1):
            cell = ws.cell(row=cur_row, column=c_idx, value=h)
            cell.font = _FONT_TH
            cell.fill = _FILL_HEADER
            cell.border = _BORDER_ALL
            cell.alignment = _ALIGN_CENTER
        cur_row += 1

        for cr in complaint_rows:
            rb_text = "黑榜(否决)" if cr["isBlackListed"] else ("红榜(+5)" if cr["isRedListed"] else "无")
            c_vals = [
                cr["rank"],
                cr["name"],
                cr["complaintCount"],
                cr["heatingArea"],
                cr["actualValue"],
                cr["baseScore"],
                rb_text,
                cr["finalScore"],
            ]
            ws.row_dimensions[cur_row].height = 20
            for c_idx, val in enumerate(c_vals, start=1):
                cell = ws.cell(row=cur_row, column=c_idx, value=val)
                cell.font = _FONT_TD_BOLD if c_idx in (1, 8) else _FONT_TD
                cell.border = _BORDER_ALL
                if cr.get("isManualActual") and c_idx == 5:
                    cell.fill = _FILL_MANUAL
                    cell.font = _FONT_TD_MANUAL
                cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 7) else _ALIGN_RIGHT
                if c_idx == 3 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0"
                elif c_idx == 4 and isinstance(val, (int, float)):
                    cell.number_format = "#,##0.00"
                elif c_idx == 5 and isinstance(val, (int, float)):
                    cell.number_format = "0.0000"
                elif c_idx in (6, 8) and isinstance(val, (int, float)):
                    cell.number_format = "0.00"
            cur_row += 1

    # 底部附表二：各单位手动填报额外嘉奖明细
    extra_rows: List[Tuple[str, str, float, str]] = []
    for unit_code in STANDARD_UNIT_ORDER:
        unit_obj = next((u for u in units_data if str(u.get("code") or "") == unit_code), None)
        if not unit_obj:
            continue
        u_name = str(unit_obj.get("name") or unit_code)
        _, items = _get_unit_extra_rewards(unit_obj)
        for item in items:
            extra_rows.append((u_name, item["title"], item["amount"], item["remark"]))

    if extra_rows:
        cur_row += 1
        ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=8)
        ws.cell(row=cur_row, column=1, value="附表二：各单位额外嘉奖项目及金额明细（手动认定）")
        ws.cell(row=cur_row, column=1).font = _FONT_TH
        ws.cell(row=cur_row, column=1).alignment = _ALIGN_LEFT
        ws.row_dimensions[cur_row].height = 22
        cur_row += 1

        e_headers = ["序号", "参评单位", "嘉奖项目名称", "嘉奖金额(元)", "备注 / 认定依据"]
        ws.row_dimensions[cur_row].height = 22
        ws.merge_cells(start_row=cur_row, start_column=3, end_row=cur_row, end_column=4)
        ws.merge_cells(start_row=cur_row, start_column=6, end_row=cur_row, end_column=8)
        e_col_positions = [1, 2, 3, 5, 6]
        for h_idx, h in enumerate(e_headers):
            c_idx = e_col_positions[h_idx]
            cell = ws.cell(row=cur_row, column=c_idx, value=h)
            cell.font = _FONT_TH
            cell.fill = _FILL_HEADER
            cell.alignment = _ALIGN_CENTER
        _style_range(ws, 1, cur_row, 8, cur_row, font=_FONT_TH, fill=_FILL_HEADER, border=_BORDER_ALL, alignment=_ALIGN_CENTER)
        cur_row += 1

        extra_start_row = cur_row
        for idx_e, (u_name, title, amt, remark) in enumerate(extra_rows, start=1):
            ws.row_dimensions[cur_row].height = 20
            ws.merge_cells(start_row=cur_row, start_column=3, end_row=cur_row, end_column=4)
            ws.merge_cells(start_row=cur_row, start_column=6, end_row=cur_row, end_column=8)
            ws.cell(row=cur_row, column=1, value=idx_e)
            ws.cell(row=cur_row, column=2, value=u_name)
            ws.cell(row=cur_row, column=3, value=title)
            ws.cell(row=cur_row, column=5, value=_normalize_excel_money(amt))
            ws.cell(row=cur_row, column=6, value=remark or "-")
            _style_range(ws, 1, cur_row, 8, cur_row, font=_FONT_TD, border=_BORDER_ALL)
            ws.cell(row=cur_row, column=1).alignment = _ALIGN_CENTER
            ws.cell(row=cur_row, column=2).alignment = _ALIGN_CENTER
            ws.cell(row=cur_row, column=3).alignment = _ALIGN_LEFT
            ws.cell(row=cur_row, column=5).alignment = _ALIGN_RIGHT
            ws.cell(row=cur_row, column=5).font = _FONT_TD_BOLD
            ws.cell(row=cur_row, column=5).number_format = "#,##0" if amt == int(amt) else "#,##0.00"
            ws.cell(row=cur_row, column=6).alignment = _ALIGN_LEFT
            cur_row += 1

        extra_end_row = cur_row - 1
        ws.row_dimensions[cur_row].height = 22
        ws.merge_cells(start_row=cur_row, start_column=1, end_row=cur_row, end_column=4)
        ws.merge_cells(start_row=cur_row, start_column=6, end_row=cur_row, end_column=8)
        ws.cell(row=cur_row, column=1, value="额外嘉奖合计")
        ws.cell(row=cur_row, column=5, value=f"=SUM(E{extra_start_row}:E{extra_end_row})")
        ws.cell(row=cur_row, column=6, value=f"共 {len(extra_rows)} 项额外嘉奖")
        _style_range(ws, 1, cur_row, 8, cur_row, font=_FONT_TD_BOLD, fill=_FILL_SUBTOTAL, border=_BORDER_ALL)
        ws.cell(row=cur_row, column=1).alignment = _ALIGN_CENTER
        ws.cell(row=cur_row, column=5).alignment = _ALIGN_RIGHT
        ws.cell(row=cur_row, column=5).number_format = "#,##0"
        ws.cell(row=cur_row, column=6).alignment = _ALIGN_LEFT
        cur_row += 1

    col_widths = {1: 14, 2: 11, 3: 18, 4: 10, 5: 15, 6: 15, 7: 11, 8: 16, 9: 54, 10: 12, 11: 30}
    for col_idx, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    return indicator_coord_map, subtotal_coord_map


def _build_matrix_sheet(
    wb: openpyxl.Workbook,
    month_label: str,
    indicator_coord_map: Dict[Tuple[str, str], str],
) -> Dict[str, str]:
    """
    构建 Sheet 2《指标得分矩阵》，完全参照《考评意见报告》内嵌表格样式：
    - 灰底双行表头，7 家单位横向并列（项目 | 分值）；
    - 运营指标 6 行，供热公司第 1~2 行为主城区耗标煤总量+供暖热单耗，其余 6 家前 2 行纵向合并；
    - 管理指标 3 行（安全文明生产、安全环保事故、红黑榜奖惩）；
    - 合计行使用 =MAX(0, SUM(...)) 自动合计。
    返回 {unit_code: "C14"} 供 Sheet 1 引用。
    """
    ws = wb.create_sheet(title="指标得分矩阵", index=0)
    ws.views.sheetView[0].showGridLines = True

    ws.merge_cells("A1:O1")
    ws["A1"] = f"{month_label} 各单位指标得分分布表"
    ws["A1"].font = _FONT_TITLE
    ws["A1"].alignment = _ALIGN_CENTER
    ws.row_dimensions[1].height = 28

    unit_headers = [
        ("BeiHai", "北海热电厂"),
        ("XiangHai", "香海热电厂"),
        ("GongRe", "供热公司"),
        ("JinZhou", "金州热电"),
        ("BeiFang", "北方热电"),
        ("JinPu", "金普公司"),
        ("ZhuangHe", "庄河环海"),
    ]

    # 表头第 3~4 行
    ws.merge_cells("A3:A4")
    ws["A3"] = "类别"
    ws.row_dimensions[3].height = 22
    ws.row_dimensions[4].height = 20

    for idx, (_, u_name) in enumerate(unit_headers):
        p_col = 2 + idx * 2
        s_col = p_col + 1
        ws.merge_cells(start_row=3, start_column=p_col, end_row=3, end_column=s_col)
        ws.cell(row=3, column=p_col, value=u_name)
        ws.cell(row=4, column=p_col, value="项目")
        ws.cell(row=4, column=s_col, value="分值")

    _style_range(ws, 1, 3, 15, 4, font=_FONT_TH, fill=_FILL_HEADER, border=_BORDER_ALL, alignment=_ALIGN_CENTER)

    # 类别列纵向合并：运营指标 (5~10)、管理指标 (11~13)
    ws.merge_cells("A5:A10")
    ws["A5"] = "运\n营\n指\n标"
    ws.merge_cells("A11:A13")
    ws["A11"] = "管\n理\n指\n标"
    ws["A14"] = "合计"

    def _ref_formula(u_code: str, item_key: str) -> str:
        coord = indicator_coord_map.get((u_code, item_key))
        if not coord:
            return "-"
        return f"=IF('计算过程明细'!{coord}=\"\", \"-\", '计算过程明细'!{coord})"

    # 每行高度
    for r in range(5, 15):
        ws.row_dimensions[r].height = 23

    # 各单位在矩阵中的槽位定义
    # 行 5~6：供热公司两项拆分；其他 6 家纵向合并 5~6 行
    unit_slots: Dict[str, List[Tuple[int, int, str, str]]] = {
        "BeiHai": [
            (5, 6, "耗标煤总量", "coal"),
            (7, 7, "厂内水耗量", "plant_water"),
            (8, 8, "现货电价", "spot_price"),
            (9, 9, "全厂热效率", "heat_eff"),
            (10, 10, "非计划停炉停机", "shutdown"),
        ],
        "XiangHai": [
            (5, 6, "耗标煤总量", "coal"),
            (7, 7, "厂内水耗量", "plant_water"),
            (8, 8, "现货电价", "spot_price"),
            (9, 9, "全厂热效率", "heat_eff"),
            (10, 10, "非计划停炉停机", "shutdown"),
        ],
        "GongRe": [
            (5, 5, "主城区耗标煤总量", "coal"),
            (6, 6, "供暖热单耗", "heat_unit"),
            (7, 7, "供暖电单耗", "elec_unit"),
            (8, 8, "供暖水单耗", "water_unit"),
            (9, 9, "服务投诉率", "complaint"),
            (10, 10, "停供断管率", "pipe_cutoff"),
        ],
        "JinZhou": [
            (5, 6, "耗标煤总量", "coal"),
            (7, 7, "供暖电单耗", "elec_unit"),
            (8, 8, "供暖水单耗", "water_unit"),
            (9, 9, "服务投诉率", "complaint"),
            (10, 10, "停供断管率", "pipe_cutoff"),
        ],
        "BeiFang": [
            (5, 6, "耗标煤总量", "coal"),
            (7, 7, "供暖电单耗", "elec_unit"),
            (8, 8, "供暖水单耗", "water_unit"),
            (9, 9, "服务投诉率", "complaint"),
            (10, 10, "停供断管率", "pipe_cutoff"),
        ],
        "JinPu": [
            (5, 6, "耗标煤总量", "coal"),
            (7, 7, "供暖电单耗", "elec_unit"),
            (8, 8, "供暖水单耗", "water_unit"),
            (9, 9, "服务投诉率", "complaint"),
            (10, 10, "停供断管率", "pipe_cutoff"),
        ],
        "ZhuangHe": [
            (5, 6, "外购热量", "coal"),
            (7, 7, "供暖电单耗", "elec_unit"),
            (8, 8, "供暖水单耗", "water_unit"),
            (9, 9, "服务投诉率", "complaint"),
            (10, 10, "停供断管率", "pipe_cutoff"),
        ],
    }

    matrix_total_coord: Dict[str, str] = {}
    for idx, (u_code, _) in enumerate(unit_headers):
        p_col = 2 + idx * 2
        s_col = p_col + 1
        s_letter = get_column_letter(s_col)

        slots = list(unit_slots[u_code]) + [
            (11, 11, "安全文明生产", "civic"),
            (12, 12, "安全环保事故", "accident"),
            (13, 13, "红黑榜奖惩", "redblack"),
        ]

        for r_start, r_end, label, item_key in slots:
            if r_end > r_start:
                ws.merge_cells(start_row=r_start, start_column=p_col, end_row=r_end, end_column=p_col)
                ws.merge_cells(start_row=r_start, start_column=s_col, end_row=r_end, end_column=s_col)
            ws.cell(row=r_start, column=p_col, value=label)
            score_cell = ws.cell(row=r_start, column=s_col, value=_ref_formula(u_code, item_key))
            score_cell.number_format = "0.00"

        # 合计行
        total_cell = ws.cell(row=14, column=s_col, value=f"=MAX(0, SUM({s_letter}5:{s_letter}13))")
        total_cell.number_format = "0.00"
        matrix_total_coord[u_code] = f"{s_letter}14"

    _style_range(ws, 1, 5, 15, 14, font=_FONT_TD, border=_BORDER_ALL, alignment=_ALIGN_CENTER)
    ws["A5"].font = _FONT_TH
    ws["A11"].font = _FONT_TH
    _style_range(ws, 1, 14, 15, 14, font=_FONT_TD_BOLD, fill=_FILL_SUBTOTAL, border=_BORDER_ALL, alignment=_ALIGN_CENTER)

    # 列宽
    ws.column_dimensions["A"].width = 7
    for idx in range(7):
        ws.column_dimensions[get_column_letter(2 + idx * 2)].width = 13.5
        ws.column_dimensions[get_column_letter(3 + idx * 2)].width = 8.5

    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    return matrix_total_coord


def _build_summary_sheet(
    wb: openpyxl.Workbook,
    month_label: str,
    status_note: str,
    units_data: List[Dict[str, Any]],
    matrix_total_coord: Dict[str, str],
    now_str: str,
) -> None:
    """
    构建 Sheet 1《考评兑现汇总》，完全参照《考评意见报告》正文兑现表样式：
    名次 | 单位 | 基数 | 指标结果 | 竞赛指标奖励金额 | 其他嘉奖 | 奖励合计 | 资格状态(内部核查)
    """
    ws = wb.create_sheet(title="考评兑现汇总", index=0)
    ws.views.sheetView[0].showGridLines = True

    ws.merge_cells("A1:H1")
    ws["A1"] = f"{month_label} 指标竞赛活动考评兑现汇总表"
    ws["A1"].font = _FONT_TITLE
    ws["A1"].alignment = _ALIGN_CENTER
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:H2")
    ws["A2"] = f"状态：{status_note or '在线测算'}   |   绩效发放规则：基数×指标结果%，按5元倍数取整   |   导出：{now_str}"
    ws["A2"].font = _FONT_SUBTITLE
    ws["A2"].alignment = _ALIGN_CENTER
    ws.row_dimensions[2].height = 20

    headers = ["名次", "单位", "基数", "指标结果", "竞赛指标奖励金额", "其他嘉奖", "奖励合计", "资格状态（核查参考）"]
    ws.row_dimensions[4].height = 24
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = _FONT_TH
        cell.fill = _FILL_HEADER if col_idx <= 7 else _FILL_SUBHEADER
        cell.border = _BORDER_ALL
        cell.alignment = _ALIGN_CENTER

    # 按当前综合得分降序排列
    sorted_units = sorted(units_data, key=lambda u: float(u.get("score") or 0.0), reverse=True)
    disq_count = 0
    extra_summary_notes: List[str] = []
    for idx, unit in enumerate(sorted_units, start=1):
        row_num = 4 + idx
        u_code = str(unit.get("code") or "")
        u_name = str(unit.get("name") or u_code)
        base_amt = int(unit.get("baseAmount") or 0)
        pending_cnt = int(unit.get("pendingCount") or 0)
        eligible = bool(unit.get("eligible", True))
        disq_reason = str(unit.get("disqualifyReason") or "取消资格")
        extra_total, extra_items = _get_unit_extra_rewards(unit)
        if extra_items:
            desc_parts = [f"{it['title']} ¥{it['amount']:,.0f}" if it['amount'] == int(it['amount']) else f"{it['title']} ¥{it['amount']:,.2f}" for it in extra_items]
            extra_summary_notes.append(f"{u_name}（{'、'.join(desc_parts)}）")
        elif extra_total != 0:
            extra_summary_notes.append(f"{u_name}（¥{extra_total:,.0f}）")

        if not eligible:
            disq_count += 1
            status_text = disq_reason
        elif pending_cnt > 0:
            status_text = f"阶段测算（尚有{pending_cnt}项待月报）"
        else:
            status_text = "正常兑现"

        m_coord = matrix_total_coord.get(u_code)
        score_formula = f"='指标得分矩阵'!{m_coord}" if m_coord else float(unit.get("score") or 0.0)
        # 仅当资格状态含“取消/否决/淘汰”时归零；其余按基数×指标结果%并按5元倍数取整
        reward_formula = (
            f'=IF(ISNUMBER(SEARCH("取消",H{row_num}))+ISNUMBER(SEARCH("否决",H{row_num}))+ISNUMBER(SEARCH("淘汰",H{row_num}))>0,'
            f' 0, ROUND((C{row_num}*D{row_num}/100)/5, 0)*5)'
        )
        total_formula = f"=E{row_num}+F{row_num}"
        extra_cell_val = _normalize_excel_money(extra_total) if extra_total != 0 else 0

        vals = [idx, u_name, base_amt, score_formula, reward_formula, extra_cell_val, total_formula, status_text]
        ws.row_dimensions[row_num].height = 23
        for c_idx, val in enumerate(vals, start=1):
            cell = ws.cell(row=row_num, column=c_idx, value=val)
            cell.border = _BORDER_ALL
            cell.font = _FONT_TD_RED if (not eligible and c_idx in (5, 7, 8)) else (_FONT_TD_BOLD if c_idx in (4, 7) else _FONT_TD)
            if not eligible:
                cell.fill = _FILL_DISQUALIFIED
            cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 8) else _ALIGN_RIGHT
            if c_idx in (3, 5, 6, 7):
                cell.number_format = "#,##0.00" if (c_idx == 6 and isinstance(val, float)) else "#,##0"
            elif c_idx == 4:
                cell.number_format = "0.00"

    # 合计行
    sum_row = 5 + len(sorted_units)
    ws.row_dimensions[sum_row].height = 24
    sum_vals = [
        "",
        "合计",
        f"=SUM(C5:C{sum_row - 1})",
        "",
        f"=SUM(E5:E{sum_row - 1})",
        f"=SUM(F5:F{sum_row - 1})",
        f"=SUM(G5:G{sum_row - 1})",
        f"合格 {len(sorted_units) - disq_count} 家 / 否决 {disq_count} 家" if disq_count > 0 else "全员合格",
    ]
    for c_idx, val in enumerate(sum_vals, start=1):
        cell = ws.cell(row=sum_row, column=c_idx, value=val)
        cell.font = _FONT_TD_BOLD
        cell.fill = _FILL_SUBTOTAL
        cell.border = _BORDER_ALL
        cell.alignment = _ALIGN_CENTER if c_idx in (1, 2, 8) else _ALIGN_RIGHT
        if c_idx in (3, 5, 6, 7):
            cell.number_format = "#,##0"

    # 备注与汇报指引
    note_row = sum_row + 2
    ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=8)
    ws.cell(
        row=note_row,
        column=1,
        value="注：1. 复制 A4:G12 区域即可直接粘贴至《考评意见报告》正文；“指标得分矩阵”工作表可直接截图作为报告附图。",
    )
    ws.cell(row=note_row, column=1).font = _FONT_TD_MUTED
    ws.cell(row=note_row, column=1).alignment = _ALIGN_LEFT

    note_row2 = note_row + 1
    ws.merge_cells(start_row=note_row2, start_column=1, end_row=note_row2, end_column=8)
    ws.cell(
        row=note_row2,
        column=1,
        value="2. 竞赛指标奖励金额 = ROUND((基数 × 指标结果%)/5, 0) × 5；其余嘉奖已同步页面“额外嘉奖”填报值（也可在 F 列微调），奖励合计自动联动更新。",
    )
    ws.cell(row=note_row2, column=1).font = _FONT_TD_MUTED
    ws.cell(row=note_row2, column=1).alignment = _ALIGN_LEFT

    if extra_summary_notes:
        note_row3 = note_row2 + 1
        ws.merge_cells(start_row=note_row3, start_column=1, end_row=note_row3, end_column=8)
        ws.cell(
            row=note_row3,
            column=1,
            value=f"3. 本期额外嘉奖项目：{'；'.join(extra_summary_notes)}（详见《计算过程明细》附表二）。",
        )
        ws.cell(row=note_row3, column=1).font = _FONT_TD_MUTED
        ws.cell(row=note_row3, column=1).alignment = _ALIGN_LEFT

    col_widths = {1: 8, 2: 15, 3: 13, 4: 13, 5: 19, 6: 13, 7: 14, 8: 28}
    for col_idx, width in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1


def generate_competition_excel(payload: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    生成供暖期指标竞赛 3-Sheet Excel 工作簿字节流及建议文件名。
    """
    month = str(payload.get("month") or "").strip()
    month_label = str(payload.get("month_label") or month or "当期").strip()
    status_note = str(payload.get("status_note") or "").strip()
    units_data = payload.get("units_data") or []
    if not isinstance(units_data, list) or len(units_data) == 0:
        raise ValueError("缺少有效的参评单位测算数据，无法导出报表")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    wb = openpyxl.Workbook()
    # 移除默认的空白 Sheet，后面按序插入 3 张正式表
    wb.remove(wb.active)

    complaint_rows = _build_complaint_ranking(units_data)

    # 先构建第 3 张明细表拿到精确单元格坐标，再构建矩阵表（插到 index=0），最后构建兑现汇总表（插到 index=0）
    indicator_coord_map, _ = _build_detail_sheet(
        wb=wb,
        month_label=month_label,
        status_note=status_note,
        units_data=units_data,
        complaint_rows=complaint_rows,
        now_str=now_str,
    )
    matrix_total_coord = _build_matrix_sheet(
        wb=wb,
        month_label=month_label,
        indicator_coord_map=indicator_coord_map,
    )
    _build_summary_sheet(
        wb=wb,
        month_label=month_label,
        status_note=status_note,
        units_data=units_data,
        matrix_total_coord=matrix_total_coord,
        now_str=now_str,
    )

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_month = month.replace("/", "-") if month else datetime.now().strftime("%Y-%m")
    filename = f"供暖期指标竞赛考评表_{safe_month}.xlsx"
    return buf.getvalue(), filename
