# -*- coding: utf-8 -*-
"""
供给主体（保温管生产厂家）厂区成品库存盘点服务。
业务模式:
- 模式A: 通用现货池（不绑定发货标段，section_1_id 默认为空字符串）；
- 方案A: 每日实盘在库快照录入（支持历史回溯，当日未录入时智能回退拉取最近一次有效盘点量）。
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal

BEIJING_TZ = timezone(timedelta(hours=8))
_supplier_inventory_table_checked = False


def ensure_supplier_inventory_table() -> None:
    """自愈检查并创建 tube.tube_supplier_inventory 表及按次盘点索引。"""
    global _supplier_inventory_table_checked
    if _supplier_inventory_table_checked:
        return

    session = SessionLocal()
    try:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS tube;"))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS tube.tube_supplier_inventory (
                id BIGSERIAL PRIMARY KEY,
                batch_no VARCHAR(64) NOT NULL,
                report_date DATE NOT NULL,
                supply_entity_id VARCHAR(64) NOT NULL,
                pipe_model_id VARCHAR(64) NOT NULL,
                section_1_id VARCHAR(64) NOT NULL DEFAULT '',
                stock_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
                remark TEXT,
                reported_by VARCHAR(128),
                reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_by VARCHAR(128),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_supplier_inventory_qty_nonnegative 
                    CHECK (stock_qty >= 0)
            );
        """))

        # 自愈新增 batch_no 字段 (若旧表不存在) 并设置 NOT NULL
        try:
            session.execute(text("ALTER TABLE tube.tube_supplier_inventory ADD COLUMN IF NOT EXISTS batch_no VARCHAR(64);"))
            session.execute(text("""
                UPDATE tube.tube_supplier_inventory 
                SET batch_no = 'INV_' || TO_CHAR(reported_at AT TIME ZONE 'Asia/Shanghai', 'YYYYMMDD_HH24MISS') || '_000000_' || supply_entity_id 
                WHERE batch_no IS NULL;
            """))
            session.execute(text("ALTER TABLE tube.tube_supplier_inventory ALTER COLUMN batch_no SET NOT NULL;"))
        except Exception:
            pass

        # 自愈补齐非负数量约束
        try:
            session.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'chk_supplier_inventory_qty_nonnegative'
                    ) THEN
                        ALTER TABLE tube.tube_supplier_inventory 
                        ADD CONSTRAINT chk_supplier_inventory_qty_nonnegative CHECK (stock_qty >= 0);
                    END IF;
                END $$;
            """))
        except Exception:
            pass

        # 确保删除旧的 daily_produced_qty 字段 (自愈迁移)
        try:
            session.execute(text("ALTER TABLE tube.tube_supplier_inventory DROP COLUMN IF EXISTS daily_produced_qty;"))
        except Exception:
            pass

        # 移除旧的按日唯一索引 (允许一天内多次盘点且不互相覆盖)
        try:
            session.execute(text("DROP INDEX IF EXISTS tube.uq_tube_supplier_inventory_date_entity_model_sec;"))
        except Exception:
            pass

        # 新增按批次的联合唯一索引 (防止同一次批次内部型号重复)
        session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_supplier_inventory_batch_entity_model
                ON tube.tube_supplier_inventory (batch_no, supply_entity_id, pipe_model_id);
        """))

        # 高频查询索引 (按厂家及提交时间倒序)
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_entity_time
                ON tube.tube_supplier_inventory (supply_entity_id, reported_at DESC);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_batch
                ON tube.tube_supplier_inventory (batch_no);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_date
                ON tube.tube_supplier_inventory (report_date);
        """))

        # 自增序列保底
        try:
            session.execute(text("""
                CREATE SEQUENCE IF NOT EXISTS tube.tube_supplier_inventory_id_seq;
                ALTER TABLE tube.tube_supplier_inventory ALTER COLUMN id SET DEFAULT nextval('tube.tube_supplier_inventory_id_seq');
            """))
        except Exception:
            pass

        session.commit()
        _supplier_inventory_table_checked = True
    except Exception as exc:
        session.rollback()
        print(f"⚠️ 自愈检查 tube.tube_supplier_inventory 表结构异常: {exc}")
    finally:
        session.close()


def _extract_dn_number(model_id: str) -> float:
    """提取型号中的管径数值用于科学排序，如 Φ1120×13/Φ1260×16 -> 1120.0"""
    m = re.search(r"(\d+)", model_id or "")
    if m:
        try:
            return float(m.group(1))
        except (ValueError, TypeError):
            pass
    return 0.0

def _is_custom_supplier(supply_entity_id: str) -> bool:
    """判断供给主体是否为临时/自定义供应商。"""
    from backend.projects.insulation_pipe_supply_2026.services.config_service import (
        load_tube_config,
        get_config_list,
    )
    try:
        cfg = load_tube_config()
        supply_entities = get_config_list(cfg, "supply_entities")
        norm_id = str(supply_entity_id or "").strip().lower()
        for se in supply_entities:
            eid = str(se.get("entity_id") or "").strip().lower()
            ename = str(se.get("entity_name") or "").strip().lower()
            if eid == norm_id or ename == norm_id:
                return bool(se.get("is_custom"))
    except Exception:
        pass
    return False


def list_models_for_supply_entity(supply_entity_id: str) -> List[str]:
    """
    根据供给主体所负责的标段动态过滤保温管型号并集:
    - 若供应高温水标段，则显示高温水标段所涉及型号的并集；
    - 若负责低温水标段，则显示低温水标段所涉及型号的并集；
    - 若高温水、低温水全都涉及（或未限制标段），则显示全部需求型号并集；
    - 默认按管径数值降序排列（大口径在先）。
    """
    ensure_supplier_inventory_table()
    norm_entity_id = str(supply_entity_id or "").strip()

    # 1. 解析该供给主体所分配的标段
    from backend.projects.insulation_pipe_supply_2026.services.config_service import (
        load_tube_config,
        get_config_list,
    )

    assigned_section_ids: Set[str] = set()
    try:
        cfg = load_tube_config()
        supply_entities = get_config_list(cfg, "supply_entities")
        for se in supply_entities:
            eid = str(se.get("entity_id") or "").strip()
            if eid.lower() == norm_entity_id.lower() or str(se.get("entity_name") or "").strip() == norm_entity_id:
                sids = se.get("section_1_ids") or []
                assigned_section_ids = {str(s).strip() for s in sids if str(s).strip()}
                break
    except Exception as e:
        print(f"⚠️ 解析供给主体[{norm_entity_id}]管辖标段失败，降级为全量型号: {e}")
        assigned_section_ids = set()

    # 2. 判断属于高温水还是低温水标段
    if not assigned_section_ids:
        # 未限制标段或为空，视为全部涉及
        scope = "all"
    else:
        has_high = any(sid.lower().startswith("high") or "high" in sid.lower() for sid in assigned_section_ids)
        has_low = any(sid.lower().startswith("low") or "low" in sid.lower() for sid in assigned_section_ids)
        if has_high and has_low:
            scope = "all"
        elif has_high and not has_low:
            scope = "high"
        elif has_low and not has_high:
            scope = "low"
        else:
            scope = "all"

    # 3. 从 tube.tube_pipe_baseline 查询对应水质标段涉及的型号并集
    session = SessionLocal()
    try:
        if scope == "high":
            sql = text("""
                SELECT DISTINCT pipe_model_id 
                FROM tube.tube_pipe_baseline 
                WHERE section_1_id LIKE 'high%' AND pipe_model_id IS NOT NULL AND TRIM(pipe_model_id) <> ''
                ORDER BY pipe_model_id;
            """)
        elif scope == "low":
            sql = text("""
                SELECT DISTINCT pipe_model_id 
                FROM tube.tube_pipe_baseline 
                WHERE section_1_id LIKE 'low%' AND pipe_model_id IS NOT NULL AND TRIM(pipe_model_id) <> ''
                ORDER BY pipe_model_id;
            """)
        else:
            sql = text("""
                SELECT DISTINCT pipe_model_id 
                FROM tube.tube_pipe_baseline 
                WHERE pipe_model_id IS NOT NULL AND TRIM(pipe_model_id) <> ''
                ORDER BY pipe_model_id;
            """)

        rows = session.execute(sql).fetchall()
        models = [str(r[0]).strip() for r in rows if r[0]]
        # 按照口径数值降序排序，大口径优先
        models.sort(key=lambda x: (_extract_dn_number(x), x), reverse=True)
        return models
    finally:
        session.close()


def list_standard_pipe_models() -> List[str]:
    """获取系统中所有直管的标准型号列表，按口径从大到小排列。"""
    return list_models_for_supply_entity("")



def get_supplier_inventory_for_date(
    supply_entity_id: str,
    report_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    按次查询指定供给主体的库存盘点快照。
    - 业务逻辑：不限盘点时间点，只有“这次”和“上次”；
    - “上次”：获取该供给主体最近一次成功提交的盘点批次数据；
    - “这次”：以管辖标段涉及型号并集为准，默认将上次实盘量作为建议初值，支持随时多次提交且互不覆盖。
    """
    ensure_supplier_inventory_table()
    norm_entity_id = str(supply_entity_id or "").strip()

    if _is_custom_supplier(norm_entity_id):
        return {
            "supply_entity_id": norm_entity_id,
            "is_custom": True,
            "has_previous_record": False,
            "has_record": False,
            "latest_previous_batch_no": None,
            "latest_previous_time": None,
            "latest_previous_date": None,
            "latest_previous_by": None,
            "total_previous_stock_qty": 0.0,
            "total_stock_qty": 0.0,
            "items": [],
            "message": "当前供给主体为临时/自定义供应商，无需进行厂区成品库存盘点。",
        }

    session = SessionLocal()
    try:
        # 1. 查询该厂家最近一次成功提交的盘点批次
        latest_batch_row = session.execute(text("""
            SELECT batch_no, reported_at, reported_by
            FROM tube.tube_supplier_inventory
            WHERE supply_entity_id = :entity_id
            ORDER BY reported_at DESC, id DESC
            LIMIT 1;
        """), {"entity_id": norm_entity_id}).mappings().first()

        has_previous_record = latest_batch_row is not None
        latest_previous_batch_no = None
        latest_previous_time = None
        latest_previous_by = None
        previous_map: Dict[str, float] = {}
        total_previous_stock = 0.0

        if latest_batch_row:
            latest_previous_batch_no = latest_batch_row["batch_no"]
            rep_at = latest_batch_row["reported_at"]
            if rep_at:
                if rep_at.tzinfo is None:
                    latest_previous_time = rep_at.strftime("%Y/%m/%d %H:%M:%S")
                else:
                    latest_previous_time = rep_at.astimezone(BEIJING_TZ).strftime("%Y/%m/%d %H:%M:%S")
            latest_previous_by = latest_batch_row["reported_by"] or ""

            # 读取该最近一次批次的所有型号数据
            if latest_previous_batch_no:
                prev_rows = session.execute(text("""
                    SELECT pipe_model_id, stock_qty 
                    FROM tube.tube_supplier_inventory
                    WHERE supply_entity_id = :entity_id
                      AND batch_no = :batch_no;
                """), {"entity_id": norm_entity_id, "batch_no": latest_previous_batch_no}).fetchall()
            else:
                prev_rows = session.execute(text("""
                    SELECT pipe_model_id, stock_qty 
                    FROM tube.tube_supplier_inventory
                    WHERE supply_entity_id = :entity_id
                      AND reported_at = :rep_at;
                """), {"entity_id": norm_entity_id, "rep_at": rep_at}).fetchall()

            for pr in prev_rows:
                pm = str(pr[0]).strip()
                qty = float(pr[1] or 0)
                previous_map[pm] = qty
                total_previous_stock += qty

        # 2. 对齐该供给主体的标段管型并集 (按口径数值降序排列)
        all_models = list_models_for_supply_entity(norm_entity_id)
        # 若历史已有记录中包含特殊型号，做保底合并
        if has_previous_record:
            for em in previous_map.keys():
                if em not in all_models:
                    all_models.append(em)
            all_models.sort(key=lambda x: (_extract_dn_number(x), x), reverse=True)

        items = []
        total_stock = 0.0

        for pm in all_models:
            prev_stock = previous_map.get(pm, 0.0)
            # 方案 B：本次实盘在库量默认置 0，厂家需主动盘点录入或点击“沿用上次盘点”一键填充
            cur_stock = 0.0
            total_stock += cur_stock

            items.append({
                "pipe_model_id": pm,
                "pipe_model_name": pm,
                "previous_stock_qty": prev_stock,
                "stock_qty": cur_stock,
                "change_qty": cur_stock - prev_stock,
                "remark": "",
            })

        return {
            "supply_entity_id": norm_entity_id,
            "has_previous_record": has_previous_record,
            "has_record": has_previous_record,  # 兼容前端字段
            "latest_previous_batch_no": latest_previous_batch_no,
            "latest_previous_time": latest_previous_time,
            "latest_previous_date": latest_previous_time,  # 兼容前端字段
            "latest_previous_by": latest_previous_by,
            "total_previous_stock_qty": round(total_previous_stock, 2),
            "total_stock_qty": round(total_stock, 2),
            "items": items,
        }
    finally:
        session.close()


def save_supplier_inventory(
    supply_entity_id: str,
    report_date: Optional[str] = None,
    items: List[Dict[str, Any]] = None,
    operator_name: str = "system",
) -> Dict[str, Any]:
    """
    提交指定供给主体的本次库存盘点数据（按次生成全新快照批次，不覆盖历史）。
    """
    ensure_supplier_inventory_table()
    norm_entity_id = str(supply_entity_id or "").strip()
    if not norm_entity_id:
        raise ValueError("供给主体标识 (supply_entity_id) 不能为空")

    if _is_custom_supplier(norm_entity_id):
        raise ValueError("临时/自定义供给主体无需填报厂区成品库存")

    now = datetime.now(BEIJING_TZ)
    norm_date_str = str(report_date or "").strip()
    if not norm_date_str:
        norm_date_str = now.strftime("%Y-%m-%d")

    operator = str(operator_name or "system").strip()
    # 生成全局唯一的盘点批次号: INV_YYYYMMDD_HHMMSS_ffffff_ENTITY
    safe_entity_tag = re.sub(r'[^a-zA-Z0-9]', '', norm_entity_id)[:8] or "SUP"
    batch_no = f"INV_{now.strftime('%Y%m%d_%H%M%S_%f')}_{safe_entity_tag}"

    insert_sql = text("""
        INSERT INTO tube.tube_supplier_inventory (
            batch_no, report_date, supply_entity_id, pipe_model_id, section_1_id,
            stock_qty, remark, reported_by, reported_at, updated_by, updated_at
        ) VALUES (
            :batch_no, CAST(:report_date AS DATE), :supply_entity_id, :pipe_model_id, '',
            :stock_qty, :remark, :operator, :now, :operator, :now
        );
    """)

    session = SessionLocal()
    try:
        saved_count = 0
        total_stock = 0.0

        for it in (items or []):
            pm = str(it.get("pipe_model_id") or "").strip()
            if not pm:
                continue
            stock_qty = max(0.0, float(it.get("stock_qty") or 0))
            remark = str(it.get("remark") or "").strip()

            session.execute(insert_sql, {
                "batch_no": batch_no,
                "report_date": norm_date_str,
                "supply_entity_id": norm_entity_id,
                "pipe_model_id": pm,
                "stock_qty": stock_qty,
                "remark": remark,
                "operator": operator,
                "now": now,
            })
            saved_count += 1
            total_stock += stock_qty

        session.commit()
        return {
            "ok": True,
            "supply_entity_id": norm_entity_id,
            "batch_no": batch_no,
            "report_date": norm_date_str,
            "reported_at": now.strftime("%Y/%m/%d %H:%M:%S"),
            "saved_count": saved_count,
            "total_stock_qty": round(total_stock, 2),
        }
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


def get_latest_all_suppliers_inventory() -> List[Dict[str, Any]]:
    """
    获取所有供给主体最新一次盘点批次的厂区成品待发库存汇总（供调度端或大屏使用）。
    """
    ensure_supplier_inventory_table()
    session = SessionLocal()
    try:
        # 取每个 supply_entity_id 最新一次提交的批次号与时间
        sql = text("""
            WITH latest_batches AS (
                SELECT DISTINCT ON (supply_entity_id)
                    supply_entity_id, batch_no, reported_at
                FROM tube.tube_supplier_inventory
                ORDER BY supply_entity_id, reported_at DESC, id DESC
            )
            SELECT i.id, i.batch_no, i.report_date, i.supply_entity_id, i.pipe_model_id,
                   i.stock_qty, i.remark, i.reported_by, i.reported_at, i.updated_at
            FROM tube.tube_supplier_inventory i
            JOIN latest_batches lb 
              ON i.supply_entity_id = lb.supply_entity_id 
             AND (
                 (lb.batch_no IS NOT NULL AND i.batch_no = lb.batch_no)
                 OR (lb.batch_no IS NULL AND i.reported_at = lb.reported_at)
             )
            ORDER BY i.supply_entity_id ASC, i.pipe_model_id ASC;
        """)
        rows = session.execute(sql).mappings().all()
        return [
            {
                "id": r["id"],
                "batch_no": r["batch_no"] or "",
                "report_date": r["report_date"].isoformat() if r["report_date"] else "",
                "supply_entity_id": r["supply_entity_id"],
                "pipe_model_id": r["pipe_model_id"],
                "stock_qty": float(r["stock_qty"] or 0),
                "remark": r["remark"] or "",
                "reported_by": r["reported_by"] or "",
                "reported_at": r["reported_at"].isoformat() if r["reported_at"] else "",
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else "",
            }
            for r in rows
        ]
    finally:
        session.close()

