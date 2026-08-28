# -*- coding: utf-8 -*-
"""
保温管与管件综合历史数据查询与统计分析服务 (Comprehensive History Service)。
支持每日全流程流转台账、设计采购基准量对比、责任主体与人员管辖速查等业务聚合。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    get_config_list,
    load_tube_config,
)
from backend.services.project_data_paths import resolve_accounts_path

BEIJING_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_KEY = "insulation_pipe_supply_2026"


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "null") else s


def _clean_num(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        num = float(val)
        return num if num >= 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


# -----------------------------------------------------------------------------
def _get_section_options(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return get_config_list(cfg, "demand_entities") or get_config_list(cfg, "section_1")


def _get_pipe_models(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return get_config_list(cfg, "pipe_models") or get_config_list(cfg, "pipe_model")


def _get_supplier_map(cfg: Dict[str, Any]) -> Dict[str, str]:
    sup_map = {
        "KAIYUAN": "大连开元热力管道股份有限公司",
        "SA": "大连开元热力管道股份有限公司",
        "XINRUIDE": "河北鑫瑞得管道设备有限公司",
        "SB": "河北鑫瑞得管道设备有限公司",
        "TIANDILONG": "天津天地龙管业股份有限公司",
        "SG": "天津天地龙管业股份有限公司",
        "WOSHENG": "江苏沃圣阀业有限公司",
        "SD": "江苏沃圣阀业有限公司",
        "KAERSI": "天津卡尔斯阀门股份有限公司",
        "SE": "天津卡尔斯阀门股份有限公司",
        "ZEYUE": "河北泽悦节能设备科技有限公司",
        "SF": "河北泽悦节能设备科技有限公司",
        "吴近": "能源集团保温管厂",
        "SC": "能源集团保温管厂",
    }
    for item in (get_config_list(cfg, "supply_entities") or get_config_list(cfg, "suppliers") or []):
        sid = str(item.get("entity_id") or item.get("supplier_id") or "").upper()
        code = str(item.get("code") or "").upper()
        sname = str(item.get("entity_name") or item.get("supplier_name") or item.get("name") or sid)
        if sid:
            sup_map[sid] = sname
        if code:
            sup_map[code] = sname
    return sup_map


def _get_pipe_section_dynamic_suppliers(session, cfg: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    纯数据驱动解析保温管直管供给方与标段的映射：
    1. 优先从 tube.tube_delivery 真实发货表中动态统计各标段实际供货最多的主体；
    2. 其次从配置 tube_config.json 的 supply_entities 中查找管辖标段的主体；
    3. 绝不基于标段名称前缀硬编码，完全按发货事实与配置动态自适应。
    """
    sup_name_map = _get_supplier_map(cfg)
    sec_to_sup: Dict[str, Dict[str, str]] = {}

    # 1. 优先从数据库实际直管发货记录动态提取真实主供货商
    try:
        rows = session.execute(text("""
            SELECT DISTINCT ON (section_1_id)
                section_1_id,
                LOWER(TRIM(supply_entity_id)) AS supply_entity_id,
                COUNT(*) as cnt
            FROM tube.tube_delivery
            WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, LOWER(TRIM(supply_entity_id))
            ORDER BY section_1_id, COUNT(*) DESC
        """)).mappings().all()
        for r in rows:
            sid = str(r["section_1_id"] or "").strip()
            sup_code = str(r["supply_entity_id"] or "").strip()
            if sid and sup_code:
                sup_name = sup_name_map.get(sup_code.upper()) or sup_name_map.get(sup_code) or sup_code
                sec_to_sup[sid] = {"supplier_id": sup_code, "supplier_name": sup_name}
    except Exception:
        pass

    # 2. 结合配置 supply_entities 补充尚未有实际发货记录的标段
    for ent in (get_config_list(cfg, "supply_entities") or []):
        ent_id = str(ent.get("entity_id") or ent.get("supplier_id") or "").strip()
        ent_name = str(ent.get("entity_name") or ent.get("supplier_name") or ent.get("name") or ent_id)
        for sid in (ent.get("section_1_ids") or []):
            s_str = str(sid).strip()
            if s_str and s_str not in sec_to_sup:
                sec_to_sup[s_str] = {"supplier_id": ent_id, "supplier_name": ent_name}

    return sec_to_sup


def _get_fitting_dynamic_supplier_map(session, cfg: Dict[str, Any]):
    """
    纯数据驱动解析管件各标段与品类的供给方解析器：
    1. 优先从 tube.tube_fitting_delivery 实际发运表中动态提取 (标段, 管件类型) 的真实供货主体；
    2. 其次提取该标段整体在管件发货表中的供货主体；
    3. 再次从配置 supply_entities 中查找管辖该标段的供货主体；
    4. 彻底消除按“阀”、“补偿”等字符串硬编码判定的逻辑。
    """
    sup_name_map = _get_supplier_map(cfg)
    type_map: Dict[Tuple[str, str], Dict[str, str]] = {}
    sec_map: Dict[str, Dict[str, str]] = {}

    try:
        # 1. 细粒度：(标段, 管件类型) -> 实际发货最多主体
        rows_type = session.execute(text("""
            SELECT DISTINCT ON (section_1_id, fitting_type)
                section_1_id,
                fitting_type,
                LOWER(TRIM(supply_entity_id)) AS supply_entity_id,
                COUNT(*) as cnt
            FROM tube.tube_fitting_delivery
            WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, fitting_type, LOWER(TRIM(supply_entity_id))
            ORDER BY section_1_id, fitting_type, COUNT(*) DESC
        """)).mappings().all()
        for r in rows_type:
            sid = str(r["section_1_id"] or "").strip()
            ft = str(r["fitting_type"] or "").strip()
            sup_code = str(r["supply_entity_id"] or "").strip()
            if sid and ft and sup_code:
                sup_name = sup_name_map.get(sup_code.upper()) or sup_name_map.get(sup_code) or sup_code
                type_map[(sid, ft)] = {"supplier_id": sup_code, "supplier_name": sup_name}

        # 2. 标段粒度：标段 -> 实际发货最多主体
        rows_sec = session.execute(text("""
            SELECT DISTINCT ON (section_1_id)
                section_1_id,
                LOWER(TRIM(supply_entity_id)) AS supply_entity_id,
                COUNT(*) as cnt
            FROM tube.tube_fitting_delivery
            WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, LOWER(TRIM(supply_entity_id))
            ORDER BY section_1_id, COUNT(*) DESC
        """)).mappings().all()
        for r in rows_sec:
            sid = str(r["section_1_id"] or "").strip()
            sup_code = str(r["supply_entity_id"] or "").strip()
            if sid and sup_code:
                sup_name = sup_name_map.get(sup_code.upper()) or sup_name_map.get(sup_code) or sup_code
                sec_map[sid] = {"supplier_id": sup_code, "supplier_name": sup_name}
    except Exception:
        pass

    # 3. 配置标段兜底映射
    cfg_sec_map: Dict[str, Dict[str, str]] = {}
    for ent in (get_config_list(cfg, "supply_entities") or []):
        ent_id = str(ent.get("entity_id") or ent.get("supplier_id") or "").strip()
        ent_name = str(ent.get("entity_name") or ent.get("supplier_name") or ent.get("name") or ent_id)
        for sid in (ent.get("section_1_ids") or []):
            s_str = str(sid).strip()
            if s_str and s_str not in cfg_sec_map:
                cfg_sec_map[s_str] = {"supplier_id": ent_id, "supplier_name": ent_name}

    def resolve_supplier(sec_id: str, fitting_type: str = "") -> Dict[str, str]:
        s_str = str(sec_id or "").strip()
        f_str = str(fitting_type or "").strip()
        # 1. 命中具体管件品类的真实发货主体
        if f_str and (s_str, f_str) in type_map:
            return type_map[(s_str, f_str)]
        # 2. 命中该标段整体管件发货主体
        if s_str in sec_map:
            return sec_map[s_str]
        # 3. 命中配置中分配给该标段的主体
        if s_str in cfg_sec_map:
            return cfg_sec_map[s_str]
        # 4. 兜底
        return {"supplier_id": "", "supplier_name": "待分配供货方"}

    return resolve_supplier


# -----------------------------------------------------------------------------
# 1. 📅 每日流转综合台账聚合 (Daily Flow History)
# -----------------------------------------------------------------------------

def query_daily_flow_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    section_1_ids: Optional[List[str]] = None,
    pipe_model_ids: Optional[List[str]] = None,
    material_type: str = "pipe",
) -> Dict[str, Any]:
    """
    查询每日全流程综合流转历史数据。
    保温管包含 6 大节点：计划量、发货量、确认到货量、施工接收量、现场使用量、库管确认量。
    管件包含 5 大节点：发货件数、确认到货件数、施工接收件数、现场安装件数、库管确认件数。
    """
    cfg = load_tube_config() or {}
    sec_options = _get_section_options(cfg)
    sec_name_map = {str(item.get("section_1_id")): str(item.get("section_1_name") or item.get("section_1_id")) for item in sec_options}
    
    pipe_models = _get_pipe_models(cfg)
    model_name_map = {str(item.get("pipe_model_id")): str(item.get("pipe_model_name") or item.get("pipe_model_id")) for item in pipe_models}

    sec_filter_set = set(section_1_ids) if section_1_ids else None
    model_filter_set = set(pipe_model_ids) if pipe_model_ids else None

    # 默认项目启动日 2026-07-28
    if not end_date:
        end_date = datetime.now(BEIJING_TZ).date()
    if not start_date:
        start_date = date(2026, 7, 28)

    session = SessionLocal()
    try:
        if material_type == "fitting":
            return _query_fitting_daily_flow(
                session=session,
                start_date=start_date,
                end_date=end_date,
                sec_filter_set=sec_filter_set,
                sec_name_map=sec_name_map,
            )
        else:
            return _query_pipe_daily_flow(
                session=session,
                start_date=start_date,
                end_date=end_date,
                sec_filter_set=sec_filter_set,
                model_filter_set=model_filter_set,
                sec_name_map=sec_name_map,
                model_name_map=model_name_map,
            )
    finally:
        session.close()


def _query_pipe_daily_flow(
    session,
    start_date: date,
    end_date: date,
    sec_filter_set: Optional[Set[str]],
    model_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
    model_name_map: Dict[str, str],
) -> Dict[str, Any]:
    """保温管 6 节点每日综合流转查询（数据驱动：动态识别各标段发运与供货单位）。"""
    cfg = load_tube_config() or {}
    supplier_map = _get_supplier_map(cfg)
    sec_to_sup = _get_pipe_section_dynamic_suppliers(session, cfg)

    sql = text("""
        WITH actual_sup AS (
            SELECT DISTINCT ON (section_1_id)
                section_1_id,
                LOWER(TRIM(supply_entity_id)) AS supply_entity_id
            FROM tube.tube_delivery
            WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, LOWER(TRIM(supply_entity_id))
            ORDER BY section_1_id, COUNT(*) DESC
        ), p AS (
            SELECT
                p_raw.section_1_id,
                p_raw.plan_date AS biz_date,
                p_raw.pipe_model_id,
                COALESCE(act.supply_entity_id, '') AS supply_entity_id,
                SUM(COALESCE(p_raw.plan_qty, 0)) AS total_plan_qty
            FROM tube.tube_daily_plan p_raw
            LEFT JOIN actual_sup act ON act.section_1_id = p_raw.section_1_id
            WHERE p_raw.plan_date >= :start_date AND p_raw.plan_date <= :end_date
              AND p_raw.plan_qty IS NOT NULL AND p_raw.plan_qty > 0
            GROUP BY p_raw.section_1_id, p_raw.plan_date, p_raw.pipe_model_id, act.supply_entity_id
        ), s AS (
            SELECT
                section_1_id,
                (shipped_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(shipped_qty, 0)) AS total_shipped_qty
            FROM tube.tube_delivery
            WHERE shipped_at IS NOT NULL
              AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date
              AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
              AND shipped_qty IS NOT NULL AND shipped_qty > 0
            GROUP BY section_1_id, (shipped_at AT TIME ZONE 'Asia/Shanghai')::date, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), arr AS (
            SELECT
                section_1_id,
                (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(arrived_qty, 0)) AS total_arrived_qty,
                SUM(EXTRACT(EPOCH FROM (arrived_confirm_at - shipped_at))) AS total_transit_seconds,
                COUNT(id) AS arrived_batch_count
            FROM tube.tube_delivery
            WHERE arrived_confirm_at IS NOT NULL
              AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
              AND arrived_qty IS NOT NULL AND arrived_qty > 0
            GROUP BY section_1_id, (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), rec AS (
            SELECT
                section_1_id,
                (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(received_qty, arrived_qty, shipped_qty, 0)) AS total_received_qty
            FROM tube.tube_delivery
            WHERE received_confirm_at IS NOT NULL
              AND (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
            GROUP BY section_1_id, (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), u AS (
            SELECT
                u_raw.section_1_id,
                u_raw.usage_date AS biz_date,
                u_raw.pipe_model_id,
                COALESCE(act.supply_entity_id, '') AS supply_entity_id,
                SUM(COALESCE(u_raw.usage_qty, 0)) AS total_usage_qty,
                SUM(COALESCE(u_raw.loss_qty, 0)) AS total_loss_qty
            FROM tube.tube_daily_usage u_raw
            LEFT JOIN actual_sup act ON act.section_1_id = u_raw.section_1_id
            WHERE u_raw.usage_date >= :start_date AND u_raw.usage_date <= :end_date
              AND (
                (u_raw.usage_qty IS NOT NULL AND u_raw.usage_qty > 0)
                OR (u_raw.loss_qty IS NOT NULL AND u_raw.loss_qty > 0)
              )
            GROUP BY u_raw.section_1_id, u_raw.usage_date, u_raw.pipe_model_id, act.supply_entity_id
        ), wh AS (
            SELECT
                section_1_id,
                (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(received_qty, arrived_qty, shipped_qty, 0)) AS total_warehouse_qty
            FROM tube.tube_delivery
            WHERE warehouse_confirm_at IS NOT NULL
              AND (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status = 'completed'
            GROUP BY section_1_id, (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), all_keys AS (
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM s
            UNION
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM arr
            UNION
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM rec
            UNION
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM wh
            UNION
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM p
            UNION
            SELECT section_1_id, biz_date, pipe_model_id, supply_entity_id FROM u
        )
        SELECT
            k.section_1_id,
            k.biz_date,
            k.pipe_model_id,
            k.supply_entity_id,
            COALESCE(p.total_plan_qty, 0) AS plan_qty,
            COALESCE(s.total_shipped_qty, 0) AS shipped_qty,
            COALESCE(arr.total_arrived_qty, 0) AS arrived_qty,
            COALESCE(rec.total_received_qty, 0) AS received_qty,
            COALESCE(u.total_usage_qty, 0) AS usage_qty,
            COALESCE(u.total_loss_qty, 0) AS loss_qty,
            COALESCE(wh.total_warehouse_qty, 0) AS warehouse_qty,
            COALESCE(arr.total_transit_seconds, 0) AS total_transit_seconds,
            COALESCE(arr.arrived_batch_count, 0) AS arrived_batch_count
        FROM all_keys k
        LEFT JOIN p ON p.section_1_id = k.section_1_id AND p.biz_date = k.biz_date AND p.pipe_model_id = k.pipe_model_id AND p.supply_entity_id = k.supply_entity_id
        LEFT JOIN s ON s.section_1_id = k.section_1_id AND s.biz_date = k.biz_date AND s.pipe_model_id = k.pipe_model_id AND s.supply_entity_id = k.supply_entity_id
        LEFT JOIN arr ON arr.section_1_id = k.section_1_id AND arr.biz_date = k.biz_date AND arr.pipe_model_id = k.pipe_model_id AND arr.supply_entity_id = k.supply_entity_id
        LEFT JOIN rec ON rec.section_1_id = k.section_1_id AND rec.biz_date = k.biz_date AND rec.pipe_model_id = k.pipe_model_id AND rec.supply_entity_id = k.supply_entity_id
        LEFT JOIN wh ON wh.section_1_id = k.section_1_id AND wh.biz_date = k.biz_date AND wh.pipe_model_id = k.pipe_model_id AND wh.supply_entity_id = k.supply_entity_id
        LEFT JOIN u ON u.section_1_id = k.section_1_id AND u.biz_date = k.biz_date AND u.pipe_model_id = k.pipe_model_id AND u.supply_entity_id = k.supply_entity_id
        ORDER BY k.biz_date DESC, k.section_1_id ASC, k.pipe_model_id ASC
    """)

    params = {"start_date": start_date, "end_date": end_date}
    rows = session.execute(sql, params).mappings().all()

    items = []
    summary = {
        "total_plan_qty": 0.0,
        "total_shipped_qty": 0.0,
        "total_arrived_qty": 0.0,
        "total_received_qty": 0.0,
        "total_usage_qty": 0.0,
        "total_loss_qty": 0.0,
        "total_warehouse_qty": 0.0,
        "record_count": 0,
        "transit_seconds_sum": 0.0,
        "transit_batches_count": 0,
    }

    for row in rows:
        sec_id = str(row["section_1_id"] or "")
        model_id = str(row["pipe_model_id"] or "")

        if sec_filter_set and sec_id not in sec_filter_set:
            continue
        if model_filter_set and model_id not in model_filter_set:
            continue

        plan_q = float(row["plan_qty"] or 0)
        ship_q = float(row["shipped_qty"] or 0)
        arr_q = float(row["arrived_qty"] or 0)
        rec_q = float(row["received_qty"] or 0)
        use_q = float(row["usage_qty"] or 0)
        loss_q = float(row["loss_qty"] or 0)
        wh_q = float(row["warehouse_qty"] or 0)
        transit_sec = float(row["total_transit_seconds"] or 0)
        arr_cnt = int(row["arrived_batch_count"] or 0)

        # 闭环率计算
        fulfillment_rate = (arr_q / plan_q * 100) if plan_q > 0 else 0.0
        conversion_rate = (use_q / arr_q * 100) if arr_q > 0 else 0.0
        avg_transit_str = "—"
        if arr_cnt > 0 and transit_sec > 0:
            avg_sec = transit_sec / arr_cnt
            hours = int(avg_sec // 3600)
            mins = int((avg_sec % 3600) // 60)
            avg_transit_str = f"{hours}小时{mins}分" if hours > 0 else f"{mins}分钟"

        raw_sup_id = str(row["supply_entity_id"] or "").strip()
        if raw_sup_id:
            sup_id = raw_sup_id
            sup_name = supplier_map.get(sup_id.upper()) or supplier_map.get(sup_id) or sup_id
        else:
            sup_info = sec_to_sup.get(sec_id, {})
            sup_id = sup_info.get("supplier_id") or ""
            sup_name = sup_info.get("supplier_name") or "全网直供"

        items.append({
            "biz_date": row["biz_date"].isoformat() if row["biz_date"] else "",
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "supplier_id": sup_id,
            "supplier_name": sup_name,
            "pipe_model_id": model_id,
            "pipe_model_name": model_name_map.get(model_id, model_id),
            "unit": "米",
            "plan_qty": plan_q,
            "shipped_qty": ship_q,
            "arrived_qty": arr_q,
            "received_qty": rec_q,
            "usage_qty": use_q,
            "loss_qty": loss_q,
            "warehouse_qty": wh_q,
            "fulfillment_rate": round(fulfillment_rate, 1),
            "conversion_rate": round(conversion_rate, 1),
            "avg_transit_display": avg_transit_str,
            "arrived_batch_count": arr_cnt,
        })

        summary["total_plan_qty"] += plan_q
        summary["total_shipped_qty"] += ship_q
        summary["total_arrived_qty"] += arr_q
        summary["total_received_qty"] += rec_q
        summary["total_usage_qty"] += use_q
        summary["total_loss_qty"] += loss_q
        summary["total_warehouse_qty"] += wh_q
        summary["transit_seconds_sum"] += transit_sec
        summary["transit_batches_count"] += arr_cnt
        summary["record_count"] += 1

    overall_avg_transit = "—"
    if summary["transit_batches_count"] > 0 and summary["transit_seconds_sum"] > 0:
        sec = summary["transit_seconds_sum"] / summary["transit_batches_count"]
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        overall_avg_transit = f"{h}小时{m}分" if h > 0 else f"{m}分钟"

    summary["overall_avg_transit"] = overall_avg_transit
    summary["overall_fulfillment_rate"] = round(summary["total_arrived_qty"] / summary["total_plan_qty"] * 100, 1) if summary["total_plan_qty"] > 0 else 0.0
    summary["overall_conversion_rate"] = round(summary["total_usage_qty"] / summary["total_arrived_qty"] * 100, 1) if summary["total_arrived_qty"] > 0 else 0.0

    return {
        "ok": True,
        "material_type": "pipe",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "items": items,
    }


def _query_fitting_daily_flow(
    session,
    start_date: date,
    end_date: date,
    sec_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
) -> Dict[str, Any]:
    """管件 5 节点每日综合流转查询。"""
    cfg = load_tube_config() or {}
    supplier_map = _get_supplier_map(cfg)

    sql = text("""
        WITH s AS (
            SELECT
                section_1_id,
                (shipped_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                fitting_type,
                model_spec,
                supply_entity_id,
                unit,
                SUM(COALESCE(shipped_qty, 0)) AS total_shipped_qty
            FROM tube.tube_fitting_delivery
            WHERE shipped_at IS NOT NULL
              AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date
              AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
              AND shipped_qty IS NOT NULL AND shipped_qty > 0
            GROUP BY section_1_id, (shipped_at AT TIME ZONE 'Asia/Shanghai')::date, fitting_type, model_spec, supply_entity_id, unit
        ), arr AS (
            SELECT
                section_1_id,
                (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                fitting_type,
                model_spec,
                supply_entity_id,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_arrived_qty
            FROM tube.tube_fitting_delivery
            WHERE arrived_confirm_at IS NOT NULL
              AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
            GROUP BY section_1_id, (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, fitting_type, model_spec, supply_entity_id
        ), rec AS (
            SELECT
                section_1_id,
                (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                fitting_type,
                model_spec,
                supply_entity_id,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_received_qty
            FROM tube.tube_fitting_delivery
            WHERE received_confirm_at IS NOT NULL
              AND (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status <> 'cancelled'
            GROUP BY section_1_id, (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, fitting_type, model_spec, supply_entity_id
        ), u AS (
            SELECT
                section_1_id,
                usage_date AS biz_date,
                fitting_type,
                model_spec,
                SUM(COALESCE(usage_qty, 0)) AS total_usage_qty
            FROM tube.tube_fitting_daily_usage
            WHERE usage_date >= :start_date AND usage_date <= :end_date
              AND status = 'active'
              AND usage_qty IS NOT NULL AND usage_qty > 0
            GROUP BY section_1_id, usage_date, fitting_type, model_spec
        ), wh AS (
            SELECT
                section_1_id,
                (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS biz_date,
                fitting_type,
                model_spec,
                supply_entity_id,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_warehouse_qty
            FROM tube.tube_fitting_delivery
            WHERE warehouse_confirm_at IS NOT NULL
              AND (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date 
              AND (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date
              AND status = 'completed'
            GROUP BY section_1_id, (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date, fitting_type, model_spec, supply_entity_id
        ), all_keys AS (
            SELECT section_1_id, biz_date, fitting_type, model_spec FROM s
            UNION
            SELECT section_1_id, biz_date, fitting_type, model_spec FROM arr
            UNION
            SELECT section_1_id, biz_date, fitting_type, model_spec FROM rec
            UNION
            SELECT section_1_id, biz_date, fitting_type, model_spec FROM u
            UNION
            SELECT section_1_id, biz_date, fitting_type, model_spec FROM wh
        )
        SELECT
            k.section_1_id,
            k.biz_date,
            k.fitting_type,
            k.model_spec,
            COALESCE(s.supply_entity_id, arr.supply_entity_id, rec.supply_entity_id, wh.supply_entity_id, '') AS supply_entity_id,
            COALESCE(s.unit, '个') AS unit,
            COALESCE(s.total_shipped_qty, 0) AS shipped_qty,
            COALESCE(arr.total_arrived_qty, 0) AS arrived_qty,
            COALESCE(rec.total_received_qty, 0) AS received_qty,
            COALESCE(u.total_usage_qty, 0) AS usage_qty,
            COALESCE(wh.total_warehouse_qty, 0) AS warehouse_qty
        FROM all_keys k
        LEFT JOIN s ON s.section_1_id = k.section_1_id AND s.biz_date = k.biz_date AND s.fitting_type = k.fitting_type AND s.model_spec = k.model_spec
        LEFT JOIN arr ON arr.section_1_id = k.section_1_id AND arr.biz_date = k.biz_date AND arr.fitting_type = k.fitting_type AND arr.model_spec = k.model_spec
        LEFT JOIN rec ON rec.section_1_id = k.section_1_id AND rec.biz_date = k.biz_date AND rec.fitting_type = k.fitting_type AND rec.model_spec = k.model_spec
        LEFT JOIN u ON u.section_1_id = k.section_1_id AND u.biz_date = k.biz_date AND u.fitting_type = k.fitting_type AND u.model_spec = k.model_spec
        LEFT JOIN wh ON wh.section_1_id = k.section_1_id AND wh.biz_date = k.biz_date AND wh.fitting_type = k.fitting_type AND wh.model_spec = k.model_spec
        ORDER BY k.biz_date DESC, k.section_1_id ASC, k.fitting_type ASC, k.model_spec ASC
    """)

    resolve_fitting_supplier = _get_fitting_dynamic_supplier_map(session, cfg)
    params = {"start_date": start_date, "end_date": end_date}
    rows = session.execute(sql, params).mappings().all()

    items = []
    summary = {
        "total_shipped_qty": 0,
        "total_arrived_qty": 0,
        "total_received_qty": 0,
        "total_usage_qty": 0,
        "total_warehouse_qty": 0,
        "record_count": 0,
    }

    for row in rows:
        sec_id = str(row["section_1_id"] or "")
        if sec_filter_set and sec_id not in sec_filter_set:
            continue

        ship_q = int(row["shipped_qty"] or 0)
        arr_q = int(row["arrived_qty"] or 0)
        rec_q = int(row["received_qty"] or 0)
        use_q = int(row["usage_qty"] or 0)
        wh_q = int(row["warehouse_qty"] or 0)
        
        raw_sup = str(row["supply_entity_id"] or "").strip()
        if raw_sup:
            sup_code = raw_sup.lower()
            sup_name = supplier_map.get(raw_sup.upper()) or supplier_map.get(raw_sup) or raw_sup
        else:
            sup_info = resolve_fitting_supplier(sec_id, str(row["fitting_type"] or ""))
            sup_code = (sup_info.get("supplier_id") or "").lower()
            sup_name = sup_info.get("supplier_name") or "—"

        items.append({
            "biz_date": row["biz_date"].isoformat() if row["biz_date"] else "",
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "supplier_id": sup_code,
            "supplier_name": sup_name,
            "fitting_type": row["fitting_type"] or "管件",
            "model_spec": row["model_spec"] or "—",
            "unit": row["unit"] or "个",
            "shipped_qty": ship_q,
            "arrived_qty": arr_q,
            "received_qty": rec_q,
            "usage_qty": use_q,
            "warehouse_qty": wh_q,
        })

        summary["total_shipped_qty"] += ship_q
        summary["total_arrived_qty"] += arr_q
        summary["total_received_qty"] += rec_q
        summary["total_usage_qty"] += use_q
        summary["total_warehouse_qty"] += wh_q
        summary["record_count"] += 1

    summary["site_stock_pcs"] = max(0, summary["total_arrived_qty"] - summary["total_usage_qty"])

    return {
        "ok": True,
        "material_type": "fitting",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "items": items,
    }


# -----------------------------------------------------------------------------
# 2. 📐 设计采购与基准量进度对照 (Baseline & Progress History)
# -----------------------------------------------------------------------------

def query_baseline_progress_history(
    section_1_ids: Optional[List[str]] = None,
    pipe_model_ids: Optional[List[str]] = None,
    material_type: str = "pipe",
) -> Dict[str, Any]:
    """
    查询设计使用量与计划采购量基准对照台账。
    实时对比设计使用量、计划采购量、累计发货量、累计到货量、累计安装量、现场库存及完成率。
    """
    cfg = load_tube_config() or {}
    sec_options = _get_section_options(cfg)
    sec_name_map = {str(item.get("section_1_id")): str(item.get("section_1_name") or item.get("section_1_id")) for item in sec_options}
    
    pipe_models = _get_pipe_models(cfg)
    model_name_map = {str(item.get("pipe_model_id")): str(item.get("pipe_model_name") or item.get("pipe_model_id")) for item in pipe_models}

    sec_filter_set = set(section_1_ids) if section_1_ids else None
    model_filter_set = set(pipe_model_ids) if pipe_model_ids else None

    session = SessionLocal()
    try:
        if material_type == "fitting":
            return _query_fitting_baseline_progress(
                session=session,
                sec_filter_set=sec_filter_set,
                sec_name_map=sec_name_map,
            )
        else:
            return _query_pipe_baseline_progress(
                session=session,
                sec_filter_set=sec_filter_set,
                model_filter_set=model_filter_set,
                sec_name_map=sec_name_map,
                model_name_map=model_name_map,
            )
    finally:
        session.close()


def _query_pipe_baseline_progress(
    session,
    sec_filter_set: Optional[Set[str]],
    model_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
    model_name_map: Dict[str, str],
) -> Dict[str, Any]:
    """保温管设计使用量与计划采购量对照（数据驱动：动态识别发运与供货主体）。"""
    cfg = load_tube_config() or {}
    supplier_map = _get_supplier_map(cfg)
    sec_to_sup = _get_pipe_section_dynamic_suppliers(session, cfg)

    sql = text("""
        WITH actual_sup AS (
            SELECT DISTINCT ON (section_1_id)
                section_1_id,
                LOWER(TRIM(supply_entity_id)) AS supply_entity_id
            FROM tube.tube_delivery
            WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, LOWER(TRIM(supply_entity_id))
            ORDER BY section_1_id, COUNT(*) DESC
        ), b AS (
            SELECT
                b_raw.section_1_id,
                b_raw.pipe_model_id,
                COALESCE(act.supply_entity_id, '') AS supply_entity_id,
                MAX(COALESCE(b_raw.unit, '米')) AS unit,
                SUM(COALESCE(b_raw.design_qty, 0)) AS design_qty,
                SUM(COALESCE(b_raw.purchase_plan_qty, 0)) AS purchase_plan_qty
            FROM tube.tube_pipe_baseline b_raw
            LEFT JOIN actual_sup act ON act.section_1_id = b_raw.section_1_id
            GROUP BY b_raw.section_1_id, b_raw.pipe_model_id, act.supply_entity_id
        ), s AS (
            SELECT
                section_1_id,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(shipped_qty, 0)) AS total_shipped_qty
            FROM tube.tube_delivery
            WHERE shipped_at IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), arr AS (
            SELECT
                section_1_id,
                pipe_model_id,
                LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
                SUM(COALESCE(arrived_qty, 0)) AS total_arrived_qty
            FROM tube.tube_delivery
            WHERE arrived_confirm_at IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, pipe_model_id, LOWER(TRIM(COALESCE(supply_entity_id, '')))
        ), u AS (
            SELECT
                u_raw.section_1_id,
                u_raw.pipe_model_id,
                COALESCE(act.supply_entity_id, '') AS supply_entity_id,
                SUM(COALESCE(u_raw.usage_qty, 0)) AS total_usage_qty,
                SUM(COALESCE(u_raw.loss_qty, 0)) AS total_loss_qty
            FROM tube.tube_daily_usage u_raw
            LEFT JOIN actual_sup act ON act.section_1_id = u_raw.section_1_id
            GROUP BY u_raw.section_1_id, u_raw.pipe_model_id, act.supply_entity_id
        ), keys AS (
            SELECT section_1_id, pipe_model_id, supply_entity_id FROM s
            UNION
            SELECT section_1_id, pipe_model_id, supply_entity_id FROM arr
            UNION
            SELECT section_1_id, pipe_model_id, supply_entity_id FROM b
            UNION
            SELECT section_1_id, pipe_model_id, supply_entity_id FROM u
        )
        SELECT
            k.section_1_id,
            k.pipe_model_id,
            k.supply_entity_id,
            COALESCE(b.unit, '米') AS unit,
            COALESCE(b.design_qty, 0) AS design_qty,
            COALESCE(b.purchase_plan_qty, 0) AS purchase_plan_qty,
            COALESCE(s.total_shipped_qty, 0) AS total_shipped_qty,
            COALESCE(arr.total_arrived_qty, 0) AS total_arrived_qty,
            COALESCE(u.total_usage_qty, 0) AS total_usage_qty,
            COALESCE(u.total_loss_qty, 0) AS total_loss_qty
        FROM keys k
        LEFT JOIN b ON b.section_1_id = k.section_1_id AND b.pipe_model_id = k.pipe_model_id AND b.supply_entity_id = k.supply_entity_id
        LEFT JOIN s ON s.section_1_id = k.section_1_id AND s.pipe_model_id = k.pipe_model_id AND s.supply_entity_id = k.supply_entity_id
        LEFT JOIN arr ON arr.section_1_id = k.section_1_id AND arr.pipe_model_id = k.pipe_model_id AND arr.supply_entity_id = k.supply_entity_id
        LEFT JOIN u ON u.section_1_id = k.section_1_id AND u.pipe_model_id = k.pipe_model_id AND u.supply_entity_id = k.supply_entity_id
        ORDER BY k.section_1_id ASC, k.pipe_model_id ASC
    """)

    rows = session.execute(sql).mappings().all()

    items = []
    summary = {
        "total_design_qty": 0.0,
        "total_purchase_plan_qty": 0.0,
        "total_shipped_qty": 0.0,
        "total_arrived_qty": 0.0,
        "total_usage_qty": 0.0,
        "total_loss_qty": 0.0,
        "total_stock_qty": 0.0,
        "record_count": 0,
    }

    for row in rows:
        sec_id = str(row["section_1_id"] or "")
        model_id = str(row["pipe_model_id"] or "")

        if sec_filter_set and sec_id not in sec_filter_set:
            continue
        if model_filter_set and model_id not in model_filter_set:
            continue

        des_q = float(row["design_qty"] or 0)
        pur_q = float(row["purchase_plan_qty"] or 0)
        ship_q = float(row["total_shipped_qty"] or 0)
        arr_q = float(row["total_arrived_qty"] or 0)
        use_q = float(row["total_usage_qty"] or 0)
        loss_q = float(row["total_loss_qty"] or 0)
        stock_q = max(0.0, arr_q - use_q - loss_q)

        purchase_rate = (arr_q / pur_q * 100) if pur_q > 0 else 0.0
        install_rate = (use_q / des_q * 100) if des_q > 0 else 0.0
        balance_qty = pur_q - arr_q

        raw_sup_id = str(row["supply_entity_id"] or "").strip()
        if raw_sup_id:
            sup_id = raw_sup_id
            sup_name = supplier_map.get(sup_id.upper()) or supplier_map.get(sup_id) or sup_id
        else:
            sup_info = sec_to_sup.get(sec_id, {})
            sup_id = sup_info.get("supplier_id") or ""
            sup_name = sup_info.get("supplier_name") or "全网直供"

        items.append({
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "supplier_id": sup_id,
            "supplier_name": sup_name,
            "pipe_model_id": model_id,
            "pipe_model_name": model_name_map.get(model_id, model_id),
            "unit": "米",
            "design_qty": des_q,
            "purchase_plan_qty": pur_q,
            "total_shipped_qty": ship_q,
            "total_arrived_qty": arr_q,
            "total_usage_qty": use_q,
            "total_loss_qty": loss_q,
            "stock_qty": round(stock_q, 2),
            "balance_qty": round(balance_qty, 2),
            "purchase_rate": round(purchase_rate, 1),
            "install_rate": round(install_rate, 1),
        })

        summary["total_design_qty"] += des_q
        summary["total_purchase_plan_qty"] += pur_q
        summary["total_shipped_qty"] += ship_q
        summary["total_arrived_qty"] += arr_q
        summary["total_usage_qty"] += use_q
        summary["total_loss_qty"] += loss_q
        summary["total_stock_qty"] += stock_q
        summary["record_count"] += 1

    summary["total_design_qty"] = round(summary["total_design_qty"], 2)
    summary["total_purchase_plan_qty"] = round(summary["total_purchase_plan_qty"], 2)
    summary["total_shipped_qty"] = round(summary["total_shipped_qty"], 2)
    summary["total_arrived_qty"] = round(summary["total_arrived_qty"], 2)
    summary["total_usage_qty"] = round(summary["total_usage_qty"], 2)
    summary["total_loss_qty"] = round(summary["total_loss_qty"], 2)
    summary["total_stock_qty"] = round(summary["total_stock_qty"], 2)

    total_pur = summary["total_purchase_plan_qty"]
    total_des = summary["total_design_qty"]
    summary["overall_purchase_rate"] = round(summary["total_arrived_qty"] / total_pur * 100, 1) if total_pur > 0 else 0.0
    summary["overall_install_rate"] = round(summary["total_usage_qty"] / total_des * 100, 1) if total_des > 0 else 0.0

    return {
        "items": items,
        "summary": summary,
    }


def _query_fitting_baseline_progress(
    session,
    sec_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
) -> Dict[str, Any]:
    """管件设计使用量与计划采购量对照（含累计发货、累计到货、累计使用与现场库存）。"""
    cfg = load_tube_config() or {}
    supplier_map = _get_supplier_map(cfg)

    # 1. 查询管件设计与计划采购基准数据 (严格来自 tube.tube_fitting_baseline)
    sql_base = text("""
        SELECT
            section_1_id,
            COALESCE(NULLIF(standard_name, ''), category, '管件') AS fitting_type,
            category,
            standard_name,
            model_spec,
            sub_model_spec,
            COALESCE(unit, '件') AS unit,
            SUM(CASE WHEN TRIM(COALESCE(unit, '')) = '米' OR LOWER(TRIM(COALESCE(unit, ''))) = 'm' THEN 0 ELSE COALESCE(design_qty, 0) END) AS design_qty,
            SUM(CASE WHEN TRIM(COALESCE(unit, '')) = '米' OR LOWER(TRIM(COALESCE(unit, ''))) = 'm' THEN 0 ELSE COALESCE(purchase_plan_qty, 0) END) AS purchase_plan_qty
        FROM tube.tube_fitting_baseline
        GROUP BY section_1_id, COALESCE(NULLIF(standard_name, ''), category, '管件'), category, standard_name, model_spec, sub_model_spec, unit
        ORDER BY section_1_id ASC, category ASC, model_spec ASC
    """)
    rows_base = session.execute(sql_base).mappings().all()

    baseline_items = []
    total_design_qty = 0
    total_purchase_plan_qty = 0

    resolve_fitting_supplier = _get_fitting_dynamic_supplier_map(session, cfg)

    for row in rows_base:
        sec_id = str(row["section_1_id"] or "")
        if sec_filter_set and sec_id not in sec_filter_set:
            continue

        des_q = int(row["design_qty"] or 0)
        pur_q = int(row["purchase_plan_qty"] or 0)
        raw_unit = str(row["unit"] or "").strip() or "个"

        sup_info = resolve_fitting_supplier(sec_id, str(row["fitting_type"] or row["category"] or row["standard_name"] or ""))
        sup_id = sup_info.get("supplier_id") or ""
        sup_name = sup_info.get("supplier_name") or "—"

        baseline_items.append({
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "supplier_id": sup_id,
            "supplier_name": sup_name,
            "category": row["category"] or "管件",
            "standard_name": row["standard_name"] or "",
            "fitting_type": row["fitting_type"] or "管件",
            "model_spec": row["model_spec"] or "—",
            "sub_model_spec": row["sub_model_spec"] or "",
            "unit": raw_unit,
            "design_qty": des_q,
            "purchase_plan_qty": pur_q,
        })
        total_design_qty += des_q
        total_purchase_plan_qty += pur_q

    # 2. 查询管件全周期累计流转与现场库存数据 (来自 delivery 与 daily_usage)
    sql_flow = text("""
        WITH s AS (
            SELECT
                section_1_id,
                fitting_type,
                model_spec,
                supply_entity_id,
                SUM(COALESCE(shipped_qty, 0)) AS total_shipped_qty
            FROM tube.tube_fitting_delivery
            WHERE shipped_at IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, fitting_type, model_spec, supply_entity_id
        ), arr AS (
            SELECT
                section_1_id,
                fitting_type,
                model_spec,
                supply_entity_id,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_arrived_qty
            FROM tube.tube_fitting_delivery
            WHERE arrived_confirm_at IS NOT NULL AND status <> 'cancelled'
            GROUP BY section_1_id, fitting_type, model_spec, supply_entity_id
        ), u AS (
            SELECT
                section_1_id,
                fitting_type,
                model_spec,
                SUM(COALESCE(usage_qty, 0)) AS total_usage_qty
            FROM tube.tube_fitting_daily_usage
            WHERE status = 'active'
            GROUP BY section_1_id, fitting_type, model_spec
        ), flow_keys AS (
            SELECT section_1_id, fitting_type, model_spec FROM s
            UNION
            SELECT section_1_id, fitting_type, model_spec FROM arr
            UNION
            SELECT section_1_id, fitting_type, model_spec FROM u
        )
        SELECT
            k.section_1_id,
            k.fitting_type,
            k.model_spec,
            COALESCE(s.supply_entity_id, arr.supply_entity_id, '') AS supply_entity_id,
            COALESCE(s.total_shipped_qty, 0) AS total_shipped_qty,
            COALESCE(arr.total_arrived_qty, 0) AS total_arrived_qty,
            COALESCE(u.total_usage_qty, 0) AS total_usage_qty
        FROM flow_keys k
        LEFT JOIN s ON s.section_1_id = k.section_1_id AND s.fitting_type = k.fitting_type AND s.model_spec = k.model_spec
        LEFT JOIN arr ON arr.section_1_id = k.section_1_id AND arr.fitting_type = k.fitting_type AND arr.model_spec = k.model_spec
        LEFT JOIN u ON u.section_1_id = k.section_1_id AND u.fitting_type = k.fitting_type AND u.model_spec = k.model_spec
        ORDER BY k.section_1_id ASC, k.fitting_type ASC, k.model_spec ASC
    """)
    rows_flow = session.execute(sql_flow).mappings().all()

    flow_items = []
    total_shipped_qty = 0
    total_arrived_qty = 0
    total_usage_qty = 0
    total_stock_qty = 0

    for row in rows_flow:
        sec_id = str(row["section_1_id"] or "")
        if sec_filter_set and sec_id not in sec_filter_set:
            continue

        ship_q = int(row["total_shipped_qty"] or 0)
        arr_q = int(row["total_arrived_qty"] or 0)
        use_q = int(row["total_usage_qty"] or 0)
        stock_q = max(0, arr_q - use_q)
        raw_sup = str(row["supply_entity_id"] or "").strip()
        if raw_sup:
            sup_code = raw_sup.lower()
            sup_name = supplier_map.get(raw_sup.upper()) or supplier_map.get(raw_sup) or raw_sup
        else:
            fallback_sup = resolve_fitting_supplier(sec_id, str(row["fitting_type"] or ""))
            sup_code = (fallback_sup.get("supplier_id") or "").lower()
            sup_name = fallback_sup.get("supplier_name") or "—"

        flow_items.append({
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "supplier_id": sup_code,
            "supplier_name": sup_name,
            "fitting_type": row["fitting_type"] or "管件",
            "model_spec": row["model_spec"] or "—",
            "unit": "件",
            "total_shipped_qty": ship_q,
            "total_arrived_qty": arr_q,
            "total_usage_qty": use_q,
            "stock_qty": stock_q,
        })
        total_shipped_qty += ship_q
        total_arrived_qty += arr_q
        total_usage_qty += use_q
        total_stock_qty += stock_q

    summary = {
        "total_design_qty": total_design_qty,
        "total_purchase_plan_qty": total_purchase_plan_qty,
        "total_shipped_qty": total_shipped_qty,
        "total_arrived_qty": total_arrived_qty,
        "total_usage_qty": total_usage_qty,
        "total_stock_qty": total_stock_qty,
        "record_count": len(baseline_items),
        "overall_purchase_rate": round(total_arrived_qty / total_purchase_plan_qty * 100, 1) if total_purchase_plan_qty > 0 else 0.0,
        "overall_install_rate": round(total_usage_qty / total_design_qty * 100, 1) if total_design_qty > 0 else 0.0,
    }

    return {
        "ok": True,
        "material_type": "fitting",
        "summary": summary,
        "items": baseline_items, # 兼容已有接口
        "baseline_items": baseline_items,
        "flow_items": flow_items,
    }


# -----------------------------------------------------------------------------
# 3. 🏢 责任主体与人员管辖速查矩阵 (Entities & Accounts Directory)
# -----------------------------------------------------------------------------

def query_entity_directory(project_key: str = PROJECT_KEY) -> Dict[str, Any]:
    """
    读取供给主体、施工需求主体、库管仓储主体及全局人员的账号、联系方式与管辖标段。
    """
    cfg = load_tube_config() or {}
    sec_options = _get_section_options(cfg)
    sec_name_map = {str(item.get("section_1_id")): str(item.get("section_1_name") or item.get("section_1_id")) for item in sec_options}
    
    supplier_map = _get_supplier_map(cfg)
    supply_options = get_config_list(cfg, "supply_entities")
    construct_options = get_config_list(cfg, "construction_units")
    manager_assignments = get_config_list(cfg, "manager_assignments")

    # 读取账户信息.json
    acc_path = resolve_accounts_path()
    accounts_data = {}
    if acc_path.exists():
        try:
            with open(acc_path, "r", encoding="utf-8") as f:
                accounts_data = json.load(f)
        except Exception:
            pass

    users_map = accounts_data.get("users", {})

    # 1. 动态扫描数据库中实际发货的主体与标段关联
    db_ent_sec_map: Dict[str, Set[str]] = {}
    try:
        session_dir = SessionLocal()
        try:
            p_rows = session_dir.execute(text("""
                SELECT DISTINCT LOWER(TRIM(supply_entity_id)) as sup_id, section_1_id
                FROM tube.tube_delivery
                WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            """)).mappings().all()
            for r in p_rows:
                s_code = str(r["sup_id"] or "").strip()
                sec = str(r["section_1_id"] or "").strip()
                if s_code and sec:
                    db_ent_sec_map.setdefault(s_code, set()).add(sec)

            f_rows = session_dir.execute(text("""
                SELECT DISTINCT LOWER(TRIM(supply_entity_id)) as sup_id, section_1_id
                FROM tube.tube_fitting_delivery
                WHERE supply_entity_id IS NOT NULL AND status <> 'cancelled'
            """)).mappings().all()
            for r in f_rows:
                s_code = str(r["sup_id"] or "").strip()
                sec = str(r["section_1_id"] or "").strip()
                if s_code and sec:
                    db_ent_sec_map.setdefault(s_code, set()).add(sec)
        finally:
            session_dir.close()
    except Exception:
        pass

    # 2. 供给主体列表 (配置主体 + 数据库动态主体融合)
    suppliers = []
    seen_ent_ids = set()
    supplier_users = users_map.get("tube_supplier_admin", []) + users_map.get("tube_supplier", [])
    
    for ent in supply_options:
        ent_id = str(ent.get("entity_id") or ent.get("supplier_id") or "").strip()
        seen_ent_ids.add(ent_id.lower())
        ent_name = str(ent.get("entity_name") or ent.get("supplier_name") or ent.get("name") or ent_id)
        
        # 寻找匹配账号
        matched_users = [u.get("username") for u in supplier_users if ent_id in str(u.get("unit", "")) or ent_name in str(u.get("unit", ""))]
        
        # 融合配置标段与实际发货标段
        cfg_sec_ids = set(ent.get("section_1_ids") or [])
        real_sec_ids = db_ent_sec_map.get(ent_id.lower(), set())
        merged_sec_ids = list(cfg_sec_ids | real_sec_ids)
        sec_names = [sec_name_map.get(sid, sid) for sid in merged_sec_ids]
        has_assigned_sections = len(merged_sec_ids) > 0
        scope_str = "、".join(sec_names) if sec_names else "暂未分配供应标段"

        suppliers.append({
            "category": "供货厂家",
            "entity_id": ent_id,
            "entity_name": ent_name,
            "contact_name": ent.get("contact_name") or "调度负责人",
            "contact_phone": ent.get("contact_phone") or "—",
            "scope_desc": scope_str,
            "has_assigned_sections": has_assigned_sections,
            "managed_sections": sec_names,
            "managed_section_ids": merged_sec_ids,
            "accounts": matched_users if matched_users else ["tube_supplier_1"],
        })

    # 对数据库中实际发货但配置中未列出的新增供货主体进行动态追加
    for sup_code, sec_ids_set in db_ent_sec_map.items():
        if sup_code not in seen_ent_ids:
            seen_ent_ids.add(sup_code)
            ent_name = supplier_map.get(sup_code.upper()) or supplier_map.get(sup_code) or sup_code
            sec_list = list(sec_ids_set)
            sec_names = [sec_name_map.get(sid, sid) for sid in sec_list]
            suppliers.append({
                "category": "供货厂家",
                "entity_id": sup_code,
                "entity_name": ent_name,
                "contact_name": "调度负责人",
                "contact_phone": "—",
                "scope_desc": "、".join(sec_names) if sec_names else "实际发运供货",
                "has_assigned_sections": len(sec_list) > 0,
                "managed_sections": sec_names,
                "managed_section_ids": sec_list,
                "accounts": ["tube_supplier_1"],
            })

    # 2. 施工需求主体列表 (仅列出已明确配置施工单位的企业与标段，空缺不列出)
    demand_sections = []
    construct_users = users_map.get("tube_site_manager", []) + users_map.get("tube_construction_unit", [])
    
    for c in construct_options:
        unit_name = str(c.get("unit_name") or c.get("unit_id") or "").strip()
        if not unit_name or unit_name in ("标段施工单位", "施工单位"):
            continue
        
        c_secs = c.get("section_1_ids") or c.get("section_ids") or []
        if isinstance(c_secs, str):
            c_secs = [s.strip() for s in c_secs.split(",")]
        
        sec_names = [sec_name_map.get(sid, sid) for sid in c_secs if sid]
        contact_name = c.get("contact_name") or c.get("unit_id") or "现场负责人"
        contact_phone = c.get("contact_phone") or "—"

        # 匹配人员账号
        matched_users = [
            u.get("username") 
            for u in construct_users 
            if any(sid in str(u.get("unit", "")) for sid in c_secs) or unit_name in str(u.get("unit", ""))
        ]
        
        demand_sections.append({
            "category": "施工单位",
            "section_1_id": c_secs[0] if c_secs else "",
            "managed_section_ids": c_secs,
            "section_1_name": "、".join(sec_names) if sec_names else "标段施工",
            "managed_sections": sec_names,
            "construction_unit_name": unit_name,
            "contact_name": contact_name,
            "contact_phone": contact_phone,
            "scope_desc": f"负责 {'、'.join(sec_names)} 现场施工与使用量填报",
            "accounts": matched_users if matched_users else c_secs,
        })

    # 3. 现场负责人列表 (Site Managers)
    site_managers = []
    for m in manager_assignments:
        m_id = m.get("manager_id") or m.get("manager_name")
        m_name = m.get("manager_name") or m_id
        m_phone = m.get("contact_phone") or "—"
        sec_ids = m.get("section_1_ids") or []
        if isinstance(sec_ids, str):
            sec_ids = [s.strip() for s in sec_ids.split(",")]
        sec_names = [sec_name_map.get(sid, sid) for sid in sec_ids]
        is_global = len(sec_ids) >= len(sec_options)
        scope_str = "全标段总协调" if is_global else "、".join(sec_names)

        site_managers.append({
            "category": "现场负责人",
            "person_name": m_name,
            "contact_name": m_name,
            "contact_phone": m_phone,
            "managed_sections": sec_names,
            "managed_section_ids": sec_ids,
            "scope_desc": scope_str,
            "is_global": is_global,
        })

    # 4. 库管仓储核验主体 (Warehouse Keepers 融合真实电话与管辖)
    warehouse_keepers = []
    wh_cfg_map = {str(w.get("keeper_id") or w.get("keeper_name")): w for w in get_config_list(cfg, "warehouse_keepers")}
    wh_users = users_map.get("tube_warehouse_keeper", [])
    
    for u in wh_users:
        u_name = u.get("username")
        unit_scope = str(u.get("unit") or "")
        
        # 优先从配置提取电话，若无则从账号提取
        cfg_match = wh_cfg_map.get(u_name, {})
        phone = cfg_match.get("contact_phone") or u.get("phone") or "—"

        # 解析管辖标段
        managed_sec_ids = []
        managed_sec_names = []
        for s_code in unit_scope.split(","):
            s_code = s_code.strip()
            if s_code:
                managed_sec_ids.append(s_code)
                managed_sec_names.append(sec_name_map.get(s_code, s_code))
        
        is_global = len(managed_sec_ids) >= len(sec_options) or unit_scope == "物资仓库"
        scope_str = "全项目物资仓库" if is_global else "、".join(managed_sec_names)

        warehouse_keepers.append({
            "category": "物资库管员",
            "username": u_name,
            "person_name": u_name,
            "contact_name": u_name,
            "contact_phone": phone,
            "managed_sections": managed_sec_names,
            "managed_section_ids": managed_sec_ids,
            "scope_desc": f"负责 {scope_str} 到货核验与库管确认",
            "is_global": is_global,
        })

    # 5. 全局管理与观察员
    global_members = []
    g_admins = users_map.get("Global_admin", [])
    g_viewers = users_map.get("tube_global_viewer", [])
    for u in g_admins:
        global_members.append({
            "category": "系统管理员",
            "username": u.get("username"),
            "person_name": u.get("username"),
            "contact_name": "系统超级管理员",
            "contact_phone": "内部专线",
            "role_name": "系统超级管理员",
            "scope_desc": "全网数字指挥大屏、数据审批、配置大厅与综合监管",
        })
    for u in g_viewers:
        global_members.append({
            "category": "全局观察员",
            "username": u.get("username"),
            "person_name": u.get("username"),
            "contact_name": "项目全局观察员",
            "contact_phone": "—",
            "role_name": "项目全局只读观察员",
            "scope_desc": "全网数字大屏与多维综合台账只读审阅",
        })

    return {
        "ok": True,
        "suppliers": suppliers,
        "demand_sections": demand_sections,
        "site_managers": site_managers,
        "warehouse_keepers": warehouse_keepers,
        "global_members": global_members,
    }


# -----------------------------------------------------------------------------
# 4. 🏭 供给方发货流转台账 (Supplier Delivery Ledger)
# -----------------------------------------------------------------------------

def query_supplier_ledger_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    supplier_ids: Optional[List[str]] = None,
    section_1_ids: Optional[List[str]] = None,
    pipe_model_ids: Optional[List[str]] = None,
    material_type: str = "pipe",
) -> Dict[str, Any]:
    """
    专门针对供给方视角的发货订单全生命周期流转台账。
    直接来源于发货订单表 tube.tube_delivery / tube.tube_fitting_delivery。
    包含发货量、确认到货量、施工接收量、库管确认量、在途时间、车次批次等。
    """
    cfg = load_tube_config() or {}
    sec_options = _get_section_options(cfg)
    sec_name_map = {str(item.get("section_1_id")): str(item.get("section_1_name") or item.get("section_1_id")) for item in sec_options}
    
    pipe_models = _get_pipe_models(cfg)
    model_name_map = {str(item.get("pipe_model_id")): str(item.get("pipe_model_name") or item.get("pipe_model_id")) for item in pipe_models}
    supplier_map = _get_supplier_map(cfg)

    # 默认项目启动日 2026-07-28
    if not end_date:
        end_date = datetime.now(BEIJING_TZ).date()
    if not start_date:
        start_date = date(2026, 7, 28)

    sup_filter_set = {s.lower() for s in supplier_ids} if supplier_ids else None
    sec_filter_set = set(section_1_ids) if section_1_ids else None
    model_filter_set = set(pipe_model_ids) if pipe_model_ids else None

    session = SessionLocal()
    try:
        if material_type == "fitting":
            return _query_fitting_supplier_ledger(
                session=session,
                start_date=start_date,
                end_date=end_date,
                sup_filter_set=sup_filter_set,
                sec_filter_set=sec_filter_set,
                sec_name_map=sec_name_map,
                supplier_map=supplier_map,
                cfg=cfg,
            )
        else:
            return _query_pipe_supplier_ledger(
                session=session,
                start_date=start_date,
                end_date=end_date,
                sup_filter_set=sup_filter_set,
                sec_filter_set=sec_filter_set,
                model_filter_set=model_filter_set,
                sec_name_map=sec_name_map,
                model_name_map=model_name_map,
                supplier_map=supplier_map,
                cfg=cfg,
            )
    finally:
        session.close()


def _query_pipe_supplier_ledger(
    session,
    start_date: date,
    end_date: date,
    sup_filter_set: Optional[Set[str]],
    sec_filter_set: Optional[Set[str]],
    model_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
    model_name_map: Dict[str, str],
    supplier_map: Dict[str, str],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """保温管直管供给方发运台账。"""
    sql = text("""
        SELECT
            id,
            COALESCE(shipment_no, order_no, '') AS batch_no,
            COALESCE(vehicle_plate_no, '') AS vehicle_no,
            COALESCE(ship_contact_name, '') AS driver_name,
            COALESCE(ship_contact_phone, '') AS driver_phone,
            section_1_id,
            pipe_model_id,
            LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
            (shipped_at AT TIME ZONE 'Asia/Shanghai')::date AS shipped_date,
            (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS arrived_date,
            (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS received_date,
            (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS warehouse_date,
            COALESCE(shipped_qty, 0) AS shipped_qty,
            COALESCE(arrived_qty, 0) AS arrived_qty,
            (CASE 
                WHEN received_confirm_at IS NOT NULL OR status IN ('received', 'completed') 
                THEN COALESCE(received_qty, arrived_qty, shipped_qty, 0) 
                ELSE 0 
            END) AS received_qty,
            (CASE 
                WHEN warehouse_confirm_at IS NOT NULL OR status = 'completed' 
                THEN COALESCE(received_qty, arrived_qty, shipped_qty, 0) 
                ELSE 0 
            END) AS warehouse_qty,
            status,
            EXTRACT(EPOCH FROM (arrived_confirm_at - shipped_at)) AS transit_seconds
        FROM tube.tube_delivery
        WHERE status <> 'cancelled'
          AND (
            ((shipped_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date)
            OR ((arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date)
          )
        ORDER BY shipped_at DESC, id DESC
    """)

    params = {"start_date": start_date, "end_date": end_date}
    rows = session.execute(sql, params).mappings().all()

    sec_to_sup = _get_pipe_section_dynamic_suppliers(session, cfg)
    items = []
    summary = {
        "total_shipped_qty": 0.0,
        "total_arrived_qty": 0.0,
        "total_received_qty": 0.0,
        "total_warehouse_qty": 0.0,
        "total_orders_count": 0,
        "transit_seconds_sum": 0.0,
        "transit_count": 0,
    }

    for row in rows:
        sec_id = str(row["section_1_id"] or "")
        model_id = str(row["pipe_model_id"] or "")
        raw_sup = str(row["supply_entity_id"] or "").strip().lower()

        if not raw_sup:
            sup_info = sec_to_sup.get(sec_id, {})
            raw_sup = (sup_info.get("supplier_id") or "").lower()

        if sup_filter_set and raw_sup not in sup_filter_set:
            continue
        if sec_filter_set and sec_id not in sec_filter_set:
            continue
        if model_filter_set and model_id not in model_filter_set:
            continue

        ship_q = float(row["shipped_qty"] or 0)
        arr_q = float(row["arrived_qty"] or 0)
        rec_q = float(row["received_qty"] or 0)
        wh_q = float(row["warehouse_qty"] or 0)
        t_sec = float(row["transit_seconds"] or 0)

        sup_name = supplier_map.get(raw_sup.upper()) or supplier_map.get(raw_sup) or raw_sup or "待分配供货方"
        shipped_d = row["shipped_date"].isoformat() if row["shipped_date"] else ""
        arrived_d = row["arrived_date"].isoformat() if row["arrived_date"] else ""

        transit_str = "在途中" if not arrived_d else "—"
        if t_sec > 0:
            h = int(t_sec // 3600)
            m = int((t_sec % 3600) // 60)
            transit_str = f"{h}小时{m}分" if h > 0 else (f"{m}分钟" if m > 0 else "<1分钟")
            summary["transit_seconds_sum"] += t_sec
            summary["transit_count"] += 1

        items.append({
            "id": row["id"],
            "batch_no": row["batch_no"] or f"TUBE-{row['id']}",
            "vehicle_no": row["vehicle_no"] or "—",
            "driver_name": row["driver_name"] or "—",
            "driver_phone": row["driver_phone"] or "—",
            "biz_date": shipped_d or arrived_d,
            "shipped_date": shipped_d,
            "arrived_date": arrived_d,
            "supplier_id": raw_sup,
            "supplier_name": sup_name,
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "pipe_model_id": model_id,
            "pipe_model_name": model_name_map.get(model_id, model_id),
            "unit": "米",
            "shipped_qty": ship_q,
            "arrived_qty": arr_q,
            "received_qty": rec_q,
            "warehouse_qty": wh_q,
            "status": row["status"] or "shipped",
            "transit_seconds": t_sec,
            "transit_display": transit_str,
            "fulfillment_rate": round(min(100.0, arr_q / ship_q * 100), 1) if ship_q > 0 else 0.0,
            "receipt_rate": round(min(100.0, rec_q / arr_q * 100), 1) if arr_q > 0 else 0.0,
            "warehouse_rate": round(min(100.0, wh_q / arr_q * 100), 1) if arr_q > 0 else (round(min(100.0, wh_q / ship_q * 100), 1) if ship_q > 0 else 0.0),
        })

        summary["total_shipped_qty"] += ship_q
        summary["total_arrived_qty"] += arr_q
        summary["total_received_qty"] += rec_q
        summary["total_warehouse_qty"] += wh_q
        summary["total_orders_count"] += 1

    summary["total_shipped_qty"] = round(summary["total_shipped_qty"], 2)
    summary["total_arrived_qty"] = round(summary["total_arrived_qty"], 2)
    summary["total_received_qty"] = round(summary["total_received_qty"], 2)
    summary["total_warehouse_qty"] = round(summary["total_warehouse_qty"], 2)
    
    avg_transit_str = "在途中" if summary["total_orders_count"] > 0 and summary["transit_count"] == 0 else "—"
    if summary["transit_count"] > 0:
        avg_sec = summary["transit_seconds_sum"] / summary["transit_count"]
        h = int(avg_sec // 3600)
        m = int((avg_sec % 3600) // 60)
        avg_transit_str = f"{h}小时{m}分" if h > 0 else (f"{m}分钟" if m > 0 else "<1分钟")
    summary["avg_transit_display"] = avg_transit_str
    summary["overall_fulfillment_rate"] = round(min(100.0, summary["total_arrived_qty"] / summary["total_shipped_qty"] * 100), 1) if summary["total_shipped_qty"] > 0 else 0.0
    summary["overall_receipt_rate"] = round(min(100.0, summary["total_received_qty"] / summary["total_arrived_qty"] * 100), 1) if summary["total_arrived_qty"] > 0 else 0.0
    summary["overall_warehouse_rate"] = round(min(100.0, summary["total_warehouse_qty"] / summary["total_arrived_qty"] * 100), 1) if summary["total_arrived_qty"] > 0 else 0.0

    return {
        "ok": True,
        "material_type": "pipe",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "items": items,
    }


def _query_fitting_supplier_ledger(
    session,
    start_date: date,
    end_date: date,
    sup_filter_set: Optional[Set[str]],
    sec_filter_set: Optional[Set[str]],
    sec_name_map: Dict[str, str],
    supplier_map: Dict[str, str],
    cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """管件与阀门供给方发运台账。"""
    sql = text("""
        SELECT
            id,
            COALESCE(shipment_no, order_no, '') AS batch_no,
            COALESCE(vehicle_plate_no, '') AS vehicle_no,
            COALESCE(ship_contact_name, '') AS driver_name,
            COALESCE(ship_contact_phone, '') AS driver_phone,
            section_1_id,
            fitting_type,
            model_spec,
            LOWER(TRIM(COALESCE(supply_entity_id, ''))) AS supply_entity_id,
            (shipped_at AT TIME ZONE 'Asia/Shanghai')::date AS shipped_date,
            (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS arrived_date,
            (received_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS received_date,
            (warehouse_confirm_at AT TIME ZONE 'Asia/Shanghai')::date AS warehouse_date,
            COALESCE(shipped_qty, 0) AS shipped_qty,
            COALESCE(arrived_qty, 0) AS arrived_qty,
            (CASE WHEN received_confirm_at IS NOT NULL THEN COALESCE(arrived_qty, shipped_qty, 0) ELSE 0 END) AS received_qty,
            (CASE WHEN status = 'completed' OR warehouse_confirm_at IS NOT NULL THEN COALESCE(arrived_qty, shipped_qty, 0) ELSE 0 END) AS warehouse_qty,
            status,
            EXTRACT(EPOCH FROM (arrived_confirm_at - shipped_at)) AS transit_seconds
        FROM tube.tube_fitting_delivery
        WHERE status <> 'cancelled'
          AND (
            ((shipped_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date AND (shipped_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date)
            OR ((arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date >= :start_date AND (arrived_confirm_at AT TIME ZONE 'Asia/Shanghai')::date <= :end_date)
          )
        ORDER BY shipped_at DESC, id DESC
    """)

    params = {"start_date": start_date, "end_date": end_date}
    rows = session.execute(sql, params).mappings().all()

    fitting_sup_map = _get_fitting_dynamic_supplier_map(session, cfg)
    items = []
    summary = {
        "total_shipped_qty": 0,
        "total_arrived_qty": 0,
        "total_received_qty": 0,
        "total_warehouse_qty": 0,
        "total_orders_count": 0,
        "transit_seconds_sum": 0.0,
        "transit_count": 0,
    }

    for row in rows:
        sec_id = str(row["section_1_id"] or "")
        f_type = str(row["fitting_type"] or "管件")
        m_spec = str(row["model_spec"] or "—")
        raw_sup = str(row["supply_entity_id"] or "").strip().lower()

        if not raw_sup:
            sup_info = _resolve_fitting_supplier(fitting_sup_map, sec_id, f_type)
            raw_sup = (sup_info.get("supplier_id") or "").lower()

        if sup_filter_set and raw_sup not in sup_filter_set:
            continue
        if sec_filter_set and sec_id not in sec_filter_set:
            continue

        ship_q = int(row["shipped_qty"] or 0)
        arr_q = int(row["arrived_qty"] or 0)
        rec_q = int(row["received_qty"] or 0)
        wh_q = int(row["warehouse_qty"] or 0)
        t_sec = float(row["transit_seconds"] or 0)

        sup_name = supplier_map.get(raw_sup.upper()) or supplier_map.get(raw_sup) or raw_sup or "待分配供货方"
        shipped_d = row["shipped_date"].isoformat() if row["shipped_date"] else ""
        arrived_d = row["arrived_date"].isoformat() if row["arrived_date"] else ""

        transit_str = "在途中" if not arrived_d else "—"
        if t_sec > 0:
            h = int(t_sec // 3600)
            m = int((t_sec % 3600) // 60)
            transit_str = f"{h}小时{m}分" if h > 0 else (f"{m}分钟" if m > 0 else "<1分钟")
            summary["transit_seconds_sum"] += t_sec
            summary["transit_count"] += 1

        items.append({
            "id": row["id"],
            "batch_no": row["batch_no"] or f"FIT-{row['id']}",
            "vehicle_no": row["vehicle_no"] or "—",
            "driver_name": row["driver_name"] or "—",
            "driver_phone": row["driver_phone"] or "—",
            "biz_date": shipped_d or arrived_d,
            "shipped_date": shipped_d,
            "arrived_date": arrived_d,
            "supplier_id": raw_sup,
            "supplier_name": sup_name,
            "section_1_id": sec_id,
            "section_1_name": sec_name_map.get(sec_id, sec_id),
            "fitting_type": f_type,
            "model_spec": m_spec,
            "pipe_model_id": m_spec,
            "pipe_model_name": f"{f_type} {m_spec}",
            "unit": "件",
            "shipped_qty": ship_q,
            "arrived_qty": arr_q,
            "received_qty": rec_q,
            "warehouse_qty": wh_q,
            "status": row["status"] or "shipped",
            "transit_seconds": t_sec,
            "transit_display": transit_str,
            "fulfillment_rate": round(min(100.0, arr_q / ship_q * 100), 1) if ship_q > 0 else 0.0,
            "receipt_rate": round(min(100.0, rec_q / arr_q * 100), 1) if arr_q > 0 else 0.0,
            "warehouse_rate": round(min(100.0, wh_q / arr_q * 100), 1) if arr_q > 0 else (round(min(100.0, wh_q / ship_q * 100), 1) if ship_q > 0 else 0.0),
        })

        summary["total_shipped_qty"] += ship_q
        summary["total_arrived_qty"] += arr_q
        summary["total_received_qty"] += rec_q
        summary["total_warehouse_qty"] += wh_q
        summary["total_orders_count"] += 1

    avg_transit_str = "在途中" if summary["total_orders_count"] > 0 and summary["transit_count"] == 0 else "—"
    if summary["transit_count"] > 0:
        avg_sec = summary["transit_seconds_sum"] / summary["transit_count"]
        h = int(avg_sec // 3600)
        m = int((avg_sec % 3600) // 60)
        avg_transit_str = f"{h}小时{m}分" if h > 0 else (f"{m}分钟" if m > 0 else "<1分钟")
    summary["avg_transit_display"] = avg_transit_str
    summary["overall_fulfillment_rate"] = round(min(100.0, summary["total_arrived_qty"] / summary["total_shipped_qty"] * 100), 1) if summary["total_shipped_qty"] > 0 else 0.0
    summary["overall_receipt_rate"] = round(min(100.0, summary["total_received_qty"] / summary["total_arrived_qty"] * 100), 1) if summary["total_arrived_qty"] > 0 else 0.0
    summary["overall_warehouse_rate"] = round(min(100.0, summary["total_warehouse_qty"] / summary["total_arrived_qty"] * 100), 1) if summary["total_arrived_qty"] > 0 else 0.0

    return {
        "ok": True,
        "material_type": "fitting",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": summary,
        "items": items,
    }
