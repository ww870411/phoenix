# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 八大主体标准台账中心与缺失项补录 API
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import engine
from backend.services.auth_manager import AuthSession, get_current_session

router = APIRouter(prefix="/dicts", tags=["smart_heating_platform_dicts"])


def _require_admin(session: AuthSession) -> None:
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="标准台账维护仅限 Global_admin 访问")


class StationAreaPatch(BaseModel):
    covered_area: Optional[float] = Field(None, ge=0, description="在网供热面积（㎡）")
    rdfz: Optional[str] = Field(None, description="热源大网")


class MerchantTagsPatch(BaseModel):
    rdfz: Optional[str] = None
    rdry: Optional[str] = None
    rdss: Optional[str] = None
    rdjg: Optional[str] = None
    rdgz: Optional[str] = None


@router.get("/overview", summary="获取八大主体规模与待补录统计")
def api_dict_overview(session: AuthSession = Depends(get_current_session)):
    _require_admin(session)
    with engine.connect() as conn:
        counts = {
            "centers": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_service_center")).scalar_one(),
            "main_networks": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_main_network")).scalar_one(),
            "branch_networks": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_branch_network")).scalar_one(),
            "stations": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_heating_station")).scalar_one(),
            "zones": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_secondary_zone")).scalar_one(),
            "temp_devices": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_temp_device")).scalar_one(),
            "merchants": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_merchant")).scalar_one(),
            "upstream_points": conn.execute(text("SELECT COUNT(*) FROM smart_heating_platform.dict_upstream_point")).scalar_one(),
            "missing_area_stations": conn.execute(
                text("SELECT COUNT(*) FROM smart_heating_platform.dict_heating_station WHERE covered_area IS NULL")
            ).scalar_one(),
            "offline_zones": conn.execute(
                text("SELECT COUNT(*) FROM smart_heating_platform.dict_secondary_zone WHERE is_online IS FALSE")
            ).scalar_one(),
            "missing_tag_merchants": conn.execute(
                text(
                    "SELECT COUNT(*) FROM smart_heating_platform.dict_merchant "
                    "WHERE rdfz IS NULL OR rdry IS NULL OR rdss IS NULL OR rdjg IS NULL OR rdgz IS NULL"
                )
            ).scalar_one(),
            "alias_groups": conn.execute(
                text("SELECT COUNT(*) FROM smart_heating_platform.v_temp_station_alias_map")
            ).scalar_one(),
            "total_covered_area_m2": float(
                conn.execute(
                    text("SELECT COALESCE(SUM(covered_area), 0) FROM smart_heating_platform.dict_heating_station")
                ).scalar_one()
            ),
            "unregistered_temp_devices": conn.execute(
                text(
                    "SELECT COUNT(DISTINCT temp_device_id) FROM smart_heating_platform.fact_temp_hourly "
                    "WHERE is_registered IS FALSE"
                )
            ).scalar_one(),
        }
    return {"ok": True, "data": {k: (v if k == "total_covered_area_m2" else int(v)) for k, v in counts.items()}}


@router.get("/items/{entity}", summary="查询指定台账主体列表")
def api_dict_items(
    entity: str,
    only_missing: bool = Query(False),
    keyword: Optional[str] = Query(None),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    kw = f"%{keyword.strip()}%" if keyword and keyword.strip() else None

    with engine.connect() as conn:
        if entity == "centers":
            rows = conn.execute(
                text(
                    "SELECT sc.center_id, sc.name, sc.name_raw, "
                    "COUNT(DISTINCT hs.station_id) AS station_count "
                    "FROM smart_heating_platform.dict_service_center sc "
                    "LEFT JOIN smart_heating_platform.dict_heating_station hs ON sc.center_id = hs.center_id "
                    "GROUP BY sc.center_id, sc.name, sc.name_raw ORDER BY sc.center_id"
                )
            ).fetchall()
        elif entity == "main_networks":
            rows = conn.execute(
                text(
                    "SELECT mn.main_network_id, mn.name, mn.name_raw, COUNT(bn.branch_network_id) AS branch_count "
                    "FROM smart_heating_platform.dict_main_network mn "
                    "LEFT JOIN smart_heating_platform.dict_branch_network bn ON mn.main_network_id = bn.main_network_id "
                    "GROUP BY mn.main_network_id, mn.name, mn.name_raw ORDER BY mn.main_network_id"
                )
            ).fetchall()
        elif entity == "branch_networks":
            rows = conn.execute(
                text(
                    "SELECT bn.branch_network_id, bn.name, bn.main_network_id, mn.name AS main_name "
                    "FROM smart_heating_platform.dict_branch_network bn "
                    "JOIN smart_heating_platform.dict_main_network mn ON bn.main_network_id = mn.main_network_id "
                    "ORDER BY bn.branch_network_id"
                )
            ).fetchall()
        elif entity == "stations":
            conds = []
            params: Dict[str, Any] = {}
            if only_missing:
                conds.append("hs.covered_area IS NULL")
            if kw:
                conds.append("(hs.name ILIKE :kw OR hs.rd_code ILIKE :kw OR sc.name ILIKE :kw)")
                params["kw"] = kw
            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                text(
                    f"SELECT hs.station_id, hs.name, hs.rd_code, sc.name AS center_name, bn.name AS branch_name, "
                    f"hs.covered_area, hs.rdfz, hs.rdry, hs.rdss, hs.first_run_time "
                    f"FROM smart_heating_platform.dict_heating_station hs "
                    f"JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id "
                    f"JOIN smart_heating_platform.dict_branch_network bn ON hs.branch_network_id = bn.branch_network_id "
                    f"{where} ORDER BY hs.covered_area IS NULL DESC, hs.center_id, hs.name"
                ),
                params,
            ).fetchall()
        elif entity == "zones":
            conds = []
            params = {}
            if only_missing:
                conds.append("dz.is_online IS FALSE")
            if kw:
                conds.append("(hs.name ILIKE :kw OR dz.zone_name ILIKE :kw OR dz.secondary_zone_id ILIKE :kw)")
                params["kw"] = kw
            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                text(
                    f"SELECT dz.secondary_zone_id, dz.zone_name, dz.is_online, dz.online_status_raw, "
                    f"hs.station_id, hs.name AS station_name, sc.name AS center_name "
                    f"FROM smart_heating_platform.dict_secondary_zone dz "
                    f"JOIN smart_heating_platform.dict_heating_station hs ON dz.station_id = hs.station_id "
                    f"JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id "
                    f"{where} ORDER BY dz.is_online ASC, dz.secondary_zone_id"
                ),
                params,
            ).fetchall()
        elif entity == "temp_devices":
            conds = []
            params = {}
            if only_missing:
                conds.append("td.station_name <> td.station_name_raw")
            if kw:
                conds.append("(td.name ILIKE :kw OR td.temp_device_id ILIKE :kw OR td.station_name ILIKE :kw)")
                params["kw"] = kw
            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                text(
                    f"SELECT td.temp_device_id, td.name, td.terminal_model, td.install_batch, "
                    f"td.station_name, td.station_name_raw, td.remark "
                    f"FROM smart_heating_platform.dict_temp_device td {where} "
                    f"ORDER BY td.station_name, td.name LIMIT 500"
                ),
                params,
            ).fetchall()
        elif entity == "merchants":
            conds = []
            params = {}
            if only_missing:
                conds.append("(m.rdfz IS NULL OR m.rdry IS NULL OR m.rdss IS NULL OR m.rdjg IS NULL OR m.rdgz IS NULL)")
            if kw:
                conds.append("(m.name ILIKE :kw OR m.table_name ILIKE :kw)")
                params["kw"] = kw
            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                text(
                    f"SELECT m.merchant_id, m.name, m.table_name, bn.name AS branch_name, "
                    f"m.rdfz, m.rdry, m.rdss, m.rdjg, m.rdgz "
                    f"FROM smart_heating_platform.dict_merchant m "
                    f"JOIN smart_heating_platform.dict_branch_network bn ON m.branch_network_id = bn.branch_network_id "
                    f"{where} ORDER BY m.name"
                ),
                params,
            ).fetchall()
        elif entity == "upstream_points":
            conds = []
            params = {}
            if kw:
                conds.append("(name ILIKE :kw OR source_name ILIKE :kw OR category ILIKE :kw)")
                params["kw"] = kw
            where = f"WHERE {' AND '.join(conds)}" if conds else ""
            rows = conn.execute(
                text(
                    f"SELECT point_id, source_page, category, sub_category, data_zone, name, name_raw, source_name "
                    f"FROM smart_heating_platform.dict_upstream_point {where} ORDER BY point_id"
                ),
                params,
            ).fetchall()
        elif entity == "unregistered_temp_devices":
            rows = conn.execute(
                text(
                    "SELECT DISTINCT ON (temp_device_id) temp_device_id, village_name, station_name_raw, "
                    "zdxh, temp_raw, upload_time, remark_snapshot "
                    "FROM smart_heating_platform.fact_temp_hourly "
                    "WHERE is_registered IS FALSE ORDER BY temp_device_id, biz_hour DESC"
                )
            ).fetchall()
        else:
            raise HTTPException(status_code=404, detail=f"未知主体类型: {entity}")

    result = []
    for r in rows:
        item = dict(r._mapping)
        for k, v in list(item.items()):
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            elif type(v).__name__ == "Decimal":
                item[k] = float(v)
        result.append(item)
    return {"ok": True, "data": result}


@router.patch("/stations/{station_id}", summary="在线补录换热站供热面积或热源大网")
def api_patch_station(
    station_id: str,
    payload: StationAreaPatch = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "UPDATE smart_heating_platform.dict_heating_station "
                "SET covered_area = COALESCE(:area, covered_area), "
                "rdfz = COALESCE(:rdfz, rdfz), updated_at = NOW() "
                "WHERE station_id = :sid RETURNING station_id, name, covered_area, rdfz"
            ),
            {"area": payload.covered_area, "rdfz": payload.rdfz, "sid": station_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="换热站不存在")
    return {"ok": True, "message": "换热站台账已更新", "data": {**dict(row), "covered_area": float(row["covered_area"]) if row["covered_area"] is not None else None}}


@router.patch("/merchants/{merchant_id}", summary="在线补录商业用户五维标签")
def api_patch_merchant(
    merchant_id: str,
    payload: MerchantTagsPatch = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    _require_admin(session)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "UPDATE smart_heating_platform.dict_merchant "
                "SET rdfz = COALESCE(:rdfz, rdfz), rdry = COALESCE(:rdry, rdry), "
                "rdss = COALESCE(:rdss, rdss), rdjg = COALESCE(:rdjg, rdjg), "
                "rdgz = COALESCE(:rdgz, rdgz), updated_at = NOW() "
                "WHERE merchant_id = :mid RETURNING merchant_id, name, rdfz, rdry, rdss, rdjg, rdgz"
            ),
            {
                "rdfz": payload.rdfz,
                "rdry": payload.rdry,
                "rdss": payload.rdss,
                "rdjg": payload.rdjg,
                "rdgz": payload.rdgz,
                "mid": merchant_id,
            },
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="商户不存在")
    return {"ok": True, "message": "商户台账已更新", "data": dict(row)}
