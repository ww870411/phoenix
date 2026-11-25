# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 阴面异常巡检与权责督办中心 API
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.projects.smart_heating_platform.services.cleaning_engine import EAST_8
from backend.projects.smart_heating_platform.services.report_query_service import get_collection_coverage_diagnostics
from backend.services.auth_manager import AuthSession, get_current_session

router = APIRouter(prefix="/faults", tags=["smart_heating_platform_faults"])

FAULT_CODE_LABELS = {
    "SENSOR_OUT_OF_RANGE": "1.传感器断路/越限",
    "COMM_OFFLINE": "2.通讯中断与僵尸死数",
    "HEAT_IMBALANCE": "3.一二网热平衡失真",
    "TEMP_INVERSION": "4.供回水物理倒挂",
    "METER_JUMP": "5.累计表底跳变/清零",
    "SOFTWARE_DEFECT": "6.上位机接口与台账缺陷",
    "HEAT_METER_ZERO": "7.在线站零耗热/热表挂零",
}

OWNER_LABELS = {
    "RESEARCH_INSTITUTE": "下位机/传感器故障",
    "UNIVERSITY_SOFTWARE": "上位机/台账缺陷",
    "SHARED": "现场与平台协同排查",
}


def _require_admin(session: AuthSession) -> None:
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="阴面督办中心仅限 Global_admin 访问")


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., description="OPEN | ACKNOWLEDGED | RESOLVED")
    handler_note: Optional[str] = Field(None, description="督办处理备注")


def _resolve_range(days: int, target_date: Optional[str]) -> Tuple[datetime, datetime]:
    now_e8 = datetime.now(EAST_8)
    if target_date:
        d = date.fromisoformat(target_date)
        end_dt = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=EAST_8) + timedelta(days=1)
        start_dt = end_dt - timedelta(days=max(1, days))
        return start_dt, end_dt
    end_dt = now_e8 + timedelta(hours=1)
    start_dt = datetime(now_e8.year, now_e8.month, now_e8.day, 0, 0, 0, tzinfo=EAST_8) - timedelta(days=max(0, days - 1))
    return start_dt, end_dt


@router.get("/coverage", summary="获取各主体当日取数完整度、降级补救与源头缺损诊断")
def api_fault_coverage(
    date: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    return {"ok": True, "data": get_collection_coverage_diagnostics(date)}


@router.get("/summary", summary="获取阴面异常分类与三方权责汇总")
def api_fault_summary(
    days: int = Query(1, ge=1, le=30),
    date: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    start_dt, end_dt = _resolve_range(days, date)

    with engine.connect() as conn:
        by_code = conn.execute(
            text(
                "SELECT fault_code, COUNT(*) AS cnt, "
                "COUNT(*) FILTER (WHERE status = 'OPEN') AS open_cnt "
                "FROM smart_heating_platform.fact_fault_ticket "
                "WHERE biz_hour >= :st AND biz_hour < :et "
                "GROUP BY fault_code ORDER BY cnt DESC"
            ),
            {"st": start_dt, "et": end_dt},
        ).fetchall()

        by_owner = conn.execute(
            text(
                "SELECT owner_party, COUNT(*) AS cnt, "
                "COUNT(*) FILTER (WHERE status = 'OPEN') AS open_cnt "
                "FROM smart_heating_platform.fact_fault_ticket "
                "WHERE biz_hour >= :st AND biz_hour < :et "
                "GROUP BY owner_party ORDER BY cnt DESC"
            ),
            {"st": start_dt, "et": end_dt},
        ).fetchall()

        missing_area_cnt = conn.execute(
            text("SELECT COUNT(*) FROM smart_heating_platform.dict_heating_station WHERE covered_area IS NULL")
        ).scalar_one()
        missing_merchant_cnt = conn.execute(
            text(
                "SELECT COUNT(*) FROM smart_heating_platform.dict_merchant "
                "WHERE rdfz IS NULL OR rdry IS NULL OR rdss IS NULL OR rdjg IS NULL OR rdgz IS NULL"
            )
        ).scalar_one()

    total_tickets = sum(int(r.cnt) for r in by_code)
    return {
        "ok": True,
        "data": {
            "total_tickets": total_tickets,
            "missing_area_stations": int(missing_area_cnt),
            "missing_tag_merchants": int(missing_merchant_cnt),
            "by_fault_code": [
                {
                    "fault_code": r.fault_code,
                    "label": FAULT_CODE_LABELS.get(r.fault_code, r.fault_code),
                    "count": int(r.cnt),
                    "open_count": int(r.open_cnt),
                }
                for r in by_code
            ],
            "by_owner": [
                {
                    "owner_party": r.owner_party,
                    "label": OWNER_LABELS.get(r.owner_party, r.owner_party),
                    "count": int(r.cnt),
                    "open_count": int(r.open_cnt),
                }
                for r in by_owner
            ],
        },
    }


@router.get("/tickets", summary="分页查询阴面异常督办单明细")
def api_fault_tickets(
    days: int = Query(1, ge=1, le=30),
    date: Optional[str] = Query(None),
    owner_party: Optional[str] = Query(None),
    fault_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    start_dt, end_dt = _resolve_range(days, date)

    conds = ["biz_hour >= :st", "biz_hour < :et"]
    params: Dict[str, Any] = {"st": start_dt, "et": end_dt, "lim": limit}
    if owner_party:
        conds.append("owner_party = :op")
        params["op"] = owner_party
    if fault_code:
        conds.append("fault_code = :fc")
        params["fc"] = fault_code
    if status:
        conds.append("status = :status")
        params["status"] = status
    if keyword and keyword.strip():
        conds.append("(entity_name ILIKE :kw OR raw_value_text ILIKE :kw)")
        params["kw"] = f"%{keyword.strip()}%"

    sql = (
        "SELECT ticket_id, biz_hour, entity_type, entity_id, entity_name, fault_code, "
        "owner_party, raw_value_text, clean_strategy, rule_desc, status, handler_note, updated_at "
        f"FROM smart_heating_platform.fact_fault_ticket WHERE {' AND '.join(conds)} "
        "ORDER BY biz_hour DESC, ticket_id DESC LIMIT :lim"
    )
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()

    return {
        "ok": True,
        "data": [
            {
                "ticket_id": r.ticket_id,
                "biz_hour": r.biz_hour.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M"),
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "entity_name": r.entity_name,
                "fault_code": r.fault_code,
                "fault_label": FAULT_CODE_LABELS.get(r.fault_code, r.fault_code),
                "owner_party": r.owner_party,
                "owner_label": OWNER_LABELS.get(r.owner_party, r.owner_party),
                "raw_value_text": r.raw_value_text,
                "clean_strategy": r.clean_strategy,
                "rule_desc": r.rule_desc,
                "status": r.status,
                "handler_note": r.handler_note,
            }
            for r in rows
        ],
    }


@router.patch("/tickets/{ticket_id}", summary="更新异常督办单流转状态")
def api_update_ticket(
    ticket_id: int,
    payload: TicketStatusUpdate = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    st = str(payload.status or "").upper()
    if st not in ("OPEN", "ACKNOWLEDGED", "RESOLVED"):
        raise HTTPException(status_code=400, detail="状态仅支持 OPEN / ACKNOWLEDGED / RESOLVED")
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "UPDATE smart_heating_platform.fact_fault_ticket "
                "SET status = :st, handler_note = COALESCE(:note, handler_note), updated_at = NOW() "
                "WHERE ticket_id = :tid RETURNING ticket_id"
            ),
            {"st": st, "note": payload.handler_note, "tid": ticket_id},
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail="督办单不存在")
    return {"ok": True, "message": "督办单状态已更新"}


@router.get("/export", summary="一键导出异常监测清单 Excel")
def api_export_faults(
    owner_party: Optional[str] = Query(None, description="RESEARCH_INSTITUTE | UNIVERSITY_SOFTWARE | SHARED"),
    days: int = Query(1, ge=1, le=30),
    date: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    start_dt, end_dt = _resolve_range(days, date)

    conds = ["biz_hour >= :st", "biz_hour < :et"]
    params: Dict[str, Any] = {"st": start_dt, "et": end_dt}
    if owner_party:
        conds.append("owner_party = :op")
        params["op"] = owner_party

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT biz_hour, entity_type, entity_name, fault_code, owner_party, "
                "raw_value_text, rule_desc, clean_strategy, status "
                f"FROM smart_heating_platform.fact_fault_ticket WHERE {' AND '.join(conds)} "
                "ORDER BY biz_hour DESC, fault_code, entity_name"
            ),
            params,
        ).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "异常数据监测清单"
    fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    font = Font(color="FFFFFF", bold=True)
    headers = ["发生小时", "主体类别", "站点/测点名称", "故障类型", "问题类别", "原始异常快照", "拦截规则", "数据处置策略", "状态"]
    ws.append(headers)
    for c in ws[1]:
        c.fill = fill
        c.font = font
        c.alignment = Alignment(horizontal="center", vertical="center")
    for r in rows:
        ws.append([
            r.biz_hour.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M"),
            r.entity_type,
            r.entity_name,
            FAULT_CODE_LABELS.get(r.fault_code, r.fault_code),
            OWNER_LABELS.get(r.owner_party, r.owner_party),
            r.raw_value_text,
            r.rule_desc,
            r.clean_strategy,
            r.status,
        ])
    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 4, 14), 45)

    buf = BytesIO()
    wb.save(buf)
    tag = "下位机传感器" if owner_party == "RESEARCH_INSTITUTE" else ("上位机台账" if owner_party == "UNIVERSITY_SOFTWARE" else "全量")
    filename = f"智慧供热异常监测清单_{tag}.xlsx"
    encoded = quote(filename)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
