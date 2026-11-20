#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对照 `configs/20261106年度采暖供热站面积报表2026年(1).xlsx` 同步修正
`configs/成果_智慧供热平台基础台账.xlsx` 与 PostgreSQL `smart_heating_platform.dict_heating_station`。

规则（经人工确认）：
1. 230 座可直接匹配或经门牌/分区核验的站点按 20261106 表更新面积；
2. `第六干休所` 取 20261106 表中 股份(38,433.35) + 集团(23,978.19) = 62,411.54 ㎡；
3. 人工指定对应：
   - `大连港西区` -> 161,390.60（来源：中海天誉站）
   - `海涵庄园` -> 21,226.24（来源：保利天禧F01-05地块）
   - `达沃斯广场` -> 67,366.62（来源：碧桂园站）
   - `东关街站` -> 61,373.01（来源：万科泓胤）
   - `新农行` (`Data0508`) -> `name` 改为 `农行`（保留 `name_raw='新农行'`，原面积不变）
4. `卓锦滨海道 (29,673.88)` 为新建站，平台暂未接入，仅记入修正日志表；其余未匹配站保持原值不变。
5. 原修改前数值全部写入 `4_换热站(物理主体，242座)` 的 `面积与名称修正备注` 列及新建 `20261120面积修正记录` 工作表留痕。
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.scripts.init_smart_heating_platform_dicts import run_init  # noqa: E402

LATEST_AREA_FILE = PROJECT_ROOT / "configs" / "20261106年度采暖供热站面积报表2026年(1).xlsx"
BASELINE_EXCEL = PROJECT_ROOT / "configs" / "成果_智慧供热平台基础台账.xlsx"
STATION_SHEET = "4_换热站(物理主体，242座)"
AUDIT_SHEET = "20261120面积修正记录"
REMARK_COL_HEADER = "面积与名称修正备注"

# 经门牌/分区核验及人工确认的 20261106 表站名 -> 台账标准站名映射
EXCEL_TO_BASELINE_NAME: Dict[str, str] = {
    # 东港服务中心
    "万科誉澜道": "万科御澜道",
    "东方威尼斯水城一站": "东方威尼斯",
    "东方威尼斯水城二站": "东方威尼斯二期",
    "东港E09中海东港": "中海东港(E09)",
    "东港保利天禧站": "保利天禧",
    "保利天禧I01地块站": "保利天禧I01",
    "保利天禧I04地块": "保利天禧I04",
    "东港禧岸站": "保利禧岸",
    "瑞府": "华润瑞府",
    "东港月桂台站": "国合月桂台",
    "东港国滨苑站": "国宾苑",
    "东港天鹅湾站": "天鹅湾",
    "迦南公馆站": "恒大四季K03",
    "东港四季上东站": "恒大四季上东",
    "招商臻园": "招商臻园(I09)",
    "星光耀1期站": "星光耀",
    "星光耀2期站": "星光耀2期(东港区E11)",
    "碧桂园望海中心": "望海中心",
    "东港E20桂语朝阳": "桂语朝阳E20",
    "东港龙湖水晶郦湾站": "水晶丽湾",
    "东港海韵华府站": "海韵华府",
    "东港紫御东方站": "紫御东方",
    "东港维多利亚公馆站": "维多利亚公馆",
    "东港维多利亚广场站": "维多利亚广场",
    "海韵晓风": "绿城海韵晓风",
    "保利天禧F01-05地块": "海涵庄园",
    "碧桂园站": "达沃斯广场",
    # 中山服务中心
    "大都会站": "万科大都会",
    "16中站": "十六中",
    "外语学院站": "外国语学院",
    "大外站": "大外(控股)",
    "宏爱巷锅炉房站": "宏爱巷",
    "悦泰城里站": "悦泰诚里",
    "新生街站": "新生街回迁",
    "杏林街站": "杏林苑",
    "红旗小区锅炉房站": "红旗锅炉房",
    "经典生活A站": "经典A",
    "经典生活B站": "经典B",
    # 兴工服务中心
    "五一广场站": "五一站",
    "国合·锦里站": "国合锦里",
    "诚品城站": "城品城",
    "天河公寓站": "天河大厦",
    "春风巷站": "春芳巷",
    "兴工街北站": "机车厂兴工北",
    "西山站": "机车西山村区",
    "技校生活区电锅炉": "机车锅炉房",
    "绿城沁园": "沁园(大柴东北路)",
    # 北岗服务中心
    "万达新开路站": "万达",
    "华府站": "万达华府",
    "华城御园站": "华城",
    "大胜街站": "大胜",
    "星海融汇A区": "星海A",
    "星海融汇B区": "星海B",
    "星海融汇F区": "星海F",
    "龙湖唐宁苑": "胜利路(唐宁)",
    "白云站": "莲花白云",
    "银寰站": "银环",
    "香都站": "香都花园",
    "万科泓胤": "东关街站",
    # 华乐服务中心
    "五五路站": "五五",
    "解放站": "老解放",
    "良运四季汇站": "良运四季",
    "金广东海岸站": "金广",
    # 双兴服务中心
    "兴业站": "兴业街",
    "双兴北站": "双兴锅炉房",
    "良久国际站": "良玖",
    "铁路2#站": "铁路保障房2#",
    "黑咀子": "黑嘴子(融创)",
    # 大纺服务中心
    "金盛家园站": "金盛",
    "顺达小区站": "顺达",
    # 春海服务中心
    "东港佳兆业站": "东港区佳兆业中心",
    "中海峰汇城站": "中海峰汇城(港西区C01-2地块)",
    "丹东街52#站": "丹东52号",
    "丹东街75#站": "丹东75号",
    "中海十里潮颂": "十里潮颂",
    "嘉洲阳光站": "嘉州阳光",
    "东港星天悦站": "星天悦",
    "中海星时代": "星时代",
    "东港朗庭站": "朗庭公寓",
    "港湾壹号站": "港湾一号",
    "东港磐海站": "磐海",
    "东港绿地站": "绿地中心",
    "金合苑站": "金和苑",
    "东港首开铂郡站": "首开铂郡",
    "中海天誉站": "大连港西区",
    # 香炉礁服务中心
    "铁路1#站": "铁路保障房1#",
}


def _norm_station_name(name: str) -> str:
    text = name.strip()
    if text.endswith("换热站"):
        return text[:-3]
    if text.endswith("站"):
        return text[:-1]
    return text


def _load_latest_area_rows() -> List[Dict[str, Any]]:
    wb = openpyxl.load_workbook(LATEST_AREA_FILE, data_only=True)
    ws = wb["年度采暖供热站面积报表"]
    rows: List[Dict[str, Any]] = []
    for idx, r in enumerate(ws.iter_rows(values_only=True)):
        if idx < 4:
            continue
        seq = str(r[1] or "").strip()
        if not seq.isdigit():
            continue
        area_text = str(r[7] or "").replace(",", "").strip()
        rows.append({
            "seq": int(seq),
            "prop": str(r[3] or "").strip(),
            "owner": str(r[4] or "").strip(),
            "center": str(r[5] or "").strip(),
            "st_name": str(r[6] or "").strip(),
            "area": Decimal(area_text) if area_text else Decimal("0"),
        })
    return rows


def sync_excel_and_db() -> Dict[str, Any]:
    latest_rows = _load_latest_area_rows()

    wb = openpyxl.load_workbook(BASELINE_EXCEL)
    ws = wb[STATION_SHEET]
    headers = [c.value for c in ws[1]]
    col_idx = {str(h).strip(): idx + 1 for idx, h in enumerate(headers) if h is not None}

    if REMARK_COL_HEADER not in col_idx:
        remark_col = len(headers) + 1
        ws.cell(row=1, column=remark_col, value=REMARK_COL_HEADER)
    else:
        remark_col = col_idx[REMARK_COL_HEADER]

    name_col = col_idx["name"]
    name_raw_col = col_idx["name_raw"]
    area_col = col_idx["covered_area"]
    id_col = col_idx["station_id"]
    rd_col = col_idx["rd_code"]

    # 建立现有台账行索引（保留行号与原名）
    baseline_rows: List[Dict[str, Any]] = []
    by_exact: Dict[str, Dict[str, Any]] = {}
    by_norm: Dict[str, List[Dict[str, Any]]] = {}
    for row_num in range(2, ws.max_row + 1):
        st_id = ws.cell(row=row_num, column=id_col).value
        if not st_id:
            continue
        cur_name = str(ws.cell(row=row_num, column=name_col).value or "").strip()
        cur_raw = str(ws.cell(row=row_num, column=name_raw_col).value or "").strip()
        cur_rd = str(ws.cell(row=row_num, column=rd_col).value or "").strip()
        raw_area = ws.cell(row=row_num, column=area_col).value
        cur_area = Decimal(str(raw_area).strip()) if raw_area not in (None, "") else None
        item = {
            "row_num": row_num,
            "station_id": str(st_id).strip(),
            "rd_code": cur_rd,
            "orig_name": cur_name,
            "orig_name_raw": cur_raw,
            "orig_area": cur_area,
        }
        baseline_rows.append(item)
        by_exact[cur_name] = item
        by_norm.setdefault(_norm_station_name(cur_name), []).append(item)

    # 聚合 20261106 表到台账目标站（支持 第六干休所 集团+股份合并，白兰忽略 0.00 重复行）
    updates_by_station_id: Dict[str, Dict[str, Any]] = {}
    unassigned_excel: List[Dict[str, Any]] = []

    for ex in latest_rows:
        st_name = ex["st_name"]
        mapped = EXCEL_TO_BASELINE_NAME.get(st_name)
        hit: Optional[Dict[str, Any]] = None
        if mapped:
            hit = by_exact.get(mapped)
        else:
            hit = by_exact.get(st_name) or by_exact.get(_norm_station_name(st_name))
            if not hit:
                cands = by_norm.get(_norm_station_name(st_name), [])
                if len(cands) == 1:
                    hit = cands[0]

        if not hit:
            unassigned_excel.append(ex)
            continue

        sid = hit["station_id"]
        if sid not in updates_by_station_id:
            updates_by_station_id[sid] = {
                "item": hit,
                "new_area": ex["area"],
                "sources": [f"{ex['st_name']}({ex['owner']}:{ex['area']:,.2f})"],
                "center": ex["center"],
            }
        else:
            # 第六干休所合并集团+股份；白兰站第二行 0.00 仅作来源补充
            if hit["orig_name"] == "第六干休所":
                updates_by_station_id[sid]["new_area"] += ex["area"]
            elif ex["area"] > 0 and updates_by_station_id[sid]["new_area"] == 0:
                updates_by_station_id[sid]["new_area"] = ex["area"]
            updates_by_station_id[sid]["sources"].append(f"{ex['st_name']}({ex['owner']}:{ex['area']:,.2f})")

    changelog_rows: List[Tuple[Any, ...]] = []
    area_updated_cnt = 0
    null_filled_cnt = 0
    renamed_cnt = 0

    for item in baseline_rows:
        sid = item["station_id"]
        old_name = item["orig_name"]
        old_area = item["orig_area"]

        # 特殊处理：新农行站名改为农行（保留 name_raw='新农行'，原面积暂不变）
        if old_name == "新农行":
            ws.cell(row=item["row_num"], column=name_col, value="农行")
            remark = (
                f"2026-11-20按确认修正：原name=新农行 -> 农行（保留name_raw={item['orig_name_raw']}）；"
                f"原covered_area={old_area if old_area is not None else '空'} 暂保持不变"
            )
            ws.cell(row=item["row_num"], column=remark_col, value=remark)
            changelog_rows.append((
                sid, item["rd_code"], "北岗服务中心", old_name, "农行",
                float(old_area) if old_area is not None else None,
                float(old_area) if old_area is not None else None,
                0.0, "人工确认：新农行改名农行", remark,
            ))
            renamed_cnt += 1
            continue

        upd = updates_by_station_id.get(sid)
        if not upd:
            continue

        new_area = upd["new_area"].quantize(Decimal("0.01"))
        src_text = " + ".join(upd["sources"])
        if old_area is None:
            null_filled_cnt += 1
            diff_val = float(new_area)
            remark = f"2026-11-20补录面积：原covered_area=空 -> {new_area:.2f} ㎡（来源：{src_text}）"
        elif abs(old_area - new_area) > Decimal("0.005"):
            area_updated_cnt += 1
            diff_val = float((new_area - old_area).quantize(Decimal("0.01")))
            remark = f"2026-11-20修正面积：原covered_area={old_area:.2f} -> {new_area:.2f} ㎡（来源：{src_text}）"
        else:
            diff_val = 0.0
            remark = f"2026-11-20核对一致：covered_area={new_area:.2f} ㎡（来源：{src_text}）"

        ws.cell(row=item["row_num"], column=area_col, value=float(new_area))
        ws.cell(row=item["row_num"], column=remark_col, value=remark)
        changelog_rows.append((
            sid, item["rd_code"], upd["center"], old_name, old_name,
            float(old_area) if old_area is not None else None,
            float(new_area),
            diff_val if old_area is not None else float(new_area),
            src_text, remark,
        ))

    # 写入/刷新 20261120面积修正记录 审计表
    if AUDIT_SHEET in wb.sheetnames:
        del wb[AUDIT_SHEET]
    ws_audit = wb.create_sheet(AUDIT_SHEET)
    ws_audit.append([
        "station_id", "rd_code", "服务中心", "原站名", "新站名",
        "原面积(㎡)", "新面积(㎡)", "差值(㎡)", "20261106表来源", "修正备注",
    ])
    for row in changelog_rows:
        ws_audit.append(list(row))

    ws_audit.append([])
    ws_audit.append(["--- 未入库/暂未修改记录 ---"])
    for ex in unassigned_excel:
        note = (
            "新建站，平台台账暂未接入，不写入"
            if ex["st_name"] == "卓锦滨海道"
            else ("归并项/虚站，未单独写入" if ex["area"] == 0 else "暂未匹配确认，本次保持台账原状不改")
        )
        ws_audit.append([
            "-", "-", ex["center"], "-", ex["st_name"],
            None, float(ex["area"]), None, f"{ex['st_name']}({ex['owner']})", note,
        ])

    tmp_excel = BASELINE_EXCEL.with_suffix(".tmp.xlsx")
    wb.save(tmp_excel)
    saved_excel = BASELINE_EXCEL
    excel_locked = False
    try:
        os.replace(tmp_excel, BASELINE_EXCEL)
    except PermissionError:
        excel_locked = True
        saved_excel = BASELINE_EXCEL.with_name("成果_智慧供热平台基础台账_20261120已更新.xlsx")
        os.replace(tmp_excel, saved_excel)

    db_summary = run_init(excel_path=saved_excel)
    return {
        "saved_excel": str(saved_excel),
        "excel_locked": excel_locked,
        "null_filled": null_filled_cnt,
        "area_updated": area_updated_cnt,
        "renamed": renamed_cnt,
        "changelog_count": len(changelog_rows),
        "unassigned_excel_count": len(unassigned_excel),
        "db_summary": db_summary,
    }


if __name__ == "__main__":
    res = sync_excel_and_db()
    print("=== 面积台账与数据库同步完成 ===")
    for k, v in res.items():
        print(f"  {k}: {v}")
