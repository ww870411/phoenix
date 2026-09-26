# -*- coding: utf-8 -*-
"""
供给主体（管件制造厂家）厂区成品管件库存盘点服务。
业务模式:
- 数据源: 以 tube.tube_material_price（物料价格/中标清单表）为基础，动态按厂家提取全量管件（非保温管类）类型与规格清单；
- 去重机制: 针对同一厂家在不同标段的中标单价记录，通过 (category, material_name, model_spec, unit) 进行聚合去重，避免规格重复列出；
- 模式A: 通用现货池（不绑定发货标段，section_1_id 默认为空字符串）；
- 盘点模式: 按次实盘（通过 batch_no 隔离每次盘点快照，支持同日多次盘点互不覆盖，支持一键沿用上次与置零）；
- 临时主体隔离: 临时/自定义供给主体（is_custom=True）无需盘点库存，直接放行或友好阻断。
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal

BEIJING_TZ = timezone(timedelta(hours=8))
_fitting_supplier_inventory_table_checked = False


def ensure_fitting_supplier_inventory_table() -> None:
    """自愈检查并创建 tube.tube_fitting_supplier_inventory 表及包含 material_name 的唯一索引。"""
    global _fitting_supplier_inventory_table_checked
    if _fitting_supplier_inventory_table_checked:
        return

    session = SessionLocal()
    try:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS tube;"))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS tube.tube_fitting_supplier_inventory (
                id BIGSERIAL PRIMARY KEY,
                batch_no VARCHAR(64) NOT NULL,
                report_date DATE NOT NULL,
                supply_entity_id VARCHAR(64) NOT NULL,
                section_1_id VARCHAR(64) NOT NULL DEFAULT '',
                fitting_type VARCHAR(64) NOT NULL,
                material_name VARCHAR(128) NOT NULL DEFAULT '',
                model_spec VARCHAR(128) NOT NULL,
                unit VARCHAR(32) NOT NULL DEFAULT '个',
                stock_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
                remark TEXT,
                reported_by VARCHAR(128),
                reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_by VARCHAR(128),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_fitting_supplier_inventory_qty_nonnegative 
                    CHECK (stock_qty >= 0)
            );
        """))

        # 确保 material_name 列存在
        try:
            session.execute(text("ALTER TABLE tube.tube_fitting_supplier_inventory ADD COLUMN IF NOT EXISTS material_name VARCHAR(128) NOT NULL DEFAULT '';"))
        except Exception:
            pass

        # 重构联合唯一索引 (包含 material_name)
        session.execute(text("DROP INDEX IF EXISTS tube.uq_tube_fitting_supplier_inv_batch_item;"))
        session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_supplier_inv_batch_item
                ON tube.tube_fitting_supplier_inventory (batch_no, supply_entity_id, section_1_id, fitting_type, material_name, model_spec, unit);
        """))

        # 查询索引
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_entity_time
                ON tube.tube_fitting_supplier_inventory (supply_entity_id, reported_at DESC);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_batch
                ON tube.tube_fitting_supplier_inventory (batch_no);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_entity_date
                ON tube.tube_fitting_supplier_inventory (supply_entity_id, report_date);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_date
                ON tube.tube_fitting_supplier_inventory (report_date);
        """))
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_type_spec
                ON tube.tube_fitting_supplier_inventory (fitting_type, model_spec);
        """))

        session.commit()
        _fitting_supplier_inventory_table_checked = True
    except Exception as exc:
        session.rollback()
        print(f"⚠️ 自愈检查 tube.tube_fitting_supplier_inventory 表结构异常: {exc}")
    finally:
        session.close()


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


FITTING_CATEGORY_ORDER = {
    "弯头": 1,
    "三通": 2,
    "变径管": 3,
    "大小头": 3,
    "弯管": 4,
    "直缝弯管": 4,
    "封头": 5,
    "固定支架": 6,
    "固定节": 6,
    "补偿器": 7,
    "波纹补偿器": 7,
    "球阀": 8,
    "密封节": 9,
    "物联网平衡阀": 10,
}


def _extract_spec_dn_tuple(spec_str: str) -> tuple:
    """提取规格中的管径数值用于科学排序，如 173° DN250 -> (250, 0), DN800/DN600 -> (800, 600)"""
    s = str(spec_str or "").strip()
    dn_matches = [float(n) for n in re.findall(r"(?:DN|Φ|φ)\s*(\d+(?:\.\d+)?)", s, re.IGNORECASE)]
    if dn_matches:
        main_dn = dn_matches[0]
        sub_dn = dn_matches[1] if len(dn_matches) > 1 else 0.0
    else:
        all_nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", s)]
        main_dn = all_nums[0] if len(all_nums) > 0 else 0.0
        sub_dn = all_nums[1] if len(all_nums) > 1 else 0.0
    return (-main_dn, -sub_dn, s)


def _fitting_inventory_sort_key(item: Dict[str, Any]) -> tuple:
    """
    按三层层次严格排序:
    1. 管件大类 (fitting_type / category)
    2. 材料名称 (material_name)
    3. 规格型号 (model_spec，主口径降序、次口径降序、文本自然序)
    """
    f_type = str(item.get("fitting_type") or item.get("category") or "").strip()
    m_name = str(item.get("material_name") or "").strip()
    m_spec = str(item.get("model_spec") or "").strip()
    cat_rank = FITTING_CATEGORY_ORDER.get(f_type, 99)
    spec_dim = _extract_spec_dn_tuple(m_spec)
    return (cat_rank, f_type, m_name, spec_dim)


def get_fitting_supplier_inventory_snapshot(supply_entity_id: str) -> Dict[str, Any]:
    """
    按次查询指定供给主体的管件库存盘点快照模板。
    - 临时主体保护: 若为 is_custom=True 的临时主体，返回提示且无需盘点；
    - 规格来源: 从 tube.tube_material_price 动态获取该厂家保供的管件物料，并通过 GROUP BY 对多标段单价去重；
    - 上次盘点: 从 tube.tube_fitting_supplier_inventory 提取该厂家最近一次成功提交的盘点批次；
    - 变动量与默认值: 默认实盘量置为 0，提供上次实盘数供前端一键沿用。
    """
    ensure_fitting_supplier_inventory_table()
    norm_entity_id = str(supply_entity_id or "").strip()
    if not norm_entity_id:
        return {
            "supply_entity_id": "",
            "is_custom": False,
            "has_previous_record": False,
            "has_record": False,
            "latest_previous_batch_no": None,
            "latest_previous_time": None,
            "latest_previous_date": None,
            "latest_previous_by": None,
            "total_previous_stock_qty": 0.0,
            "total_stock_qty": 0.0,
            "categories": [],
            "items": [],
        }

    # 1. 检查是否为临时/自定义供应商
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
            "categories": [],
            "items": [],
            "message": "当前供给主体为临时/自定义供应商，无需进行厂区成品库存盘点。",
        }

    session = SessionLocal()
    try:
        # 2. 查询该厂家最近一次成功提交的管件盘点批次
        latest_batch_row = session.execute(text("""
            SELECT batch_no, reported_at, reported_by
            FROM tube.tube_fitting_supplier_inventory
            WHERE supply_entity_id = :entity_id
            ORDER BY reported_at DESC, id DESC
            LIMIT 1;
        """), {"entity_id": norm_entity_id}).mappings().first()

        has_previous_record = latest_batch_row is not None
        latest_previous_batch_no = None
        latest_previous_time = None
        latest_previous_by = None
        previous_map: Dict[tuple, float] = {}
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

            # 读取该最近一次批次的所有管件明细 (包含 material_name)
            prev_rows = session.execute(text("""
                SELECT fitting_type, material_name, model_spec, unit, stock_qty 
                FROM tube.tube_fitting_supplier_inventory
                WHERE supply_entity_id = :entity_id
                  AND batch_no = :batch_no;
            """), {"entity_id": norm_entity_id, "batch_no": latest_previous_batch_no}).fetchall()

            for pr in prev_rows:
                f_type = str(pr[0] or "").strip()
                m_name = str(pr[1] or "").strip()
                m_spec = str(pr[2] or "").strip()
                u = str(pr[3] or "").strip()
                qty = float(pr[4] or 0)
                # 四元组唯一映射 (fitting_type, material_name, model_spec, unit)
                previous_map[(f_type, m_name, m_spec, u)] = qty
                # 回退兜底三元组映射 (若历史旧记录 material_name 为空)
                if not m_name:
                    previous_map[(f_type, "", m_spec, u)] = qty
                total_previous_stock += qty

        # 3. 从 tube.tube_material_price 查询该厂家的所有管件类型与型号清单
        # 关键: 使用 GROUP BY 进行多标段重复规格去重！彻底杜绝同一种管件出现多条！
        price_rows = session.execute(text("""
            SELECT category, material_name, model_spec, unit, MAX(unit_price) as unit_price
            FROM tube.tube_material_price
            WHERE (supply_entity_id = :entity_id OR supplier_name = :entity_id)
              AND category != '保温管'
            GROUP BY category, material_name, model_spec, unit
            ORDER BY category, model_spec;
        """), {"entity_id": norm_entity_id}).mappings().fetchall()

        items = []
        categories_set = set()
        total_stock = 0.0

        for r in price_rows:
            f_type = str(r["category"] or "").strip()
            mat_name = str(r["material_name"] or "").strip()
            m_spec = str(r["model_spec"] or "").strip()
            u = str(r["unit"] or "个").strip() or "个"
            u_price = float(r["unit_price"] or 0)
            
            categories_set.add(f_type)
            key = (f_type, mat_name, m_spec, u)
            prev_stock = previous_map.get(key)
            if prev_stock is None:
                # 尝试三元组回退匹配
                prev_stock = previous_map.get((f_type, "", m_spec, u), 0.0)

            cur_stock = 0.0  # 默认置 0，用户可一键沿用上次
            total_stock += cur_stock

            items.append({
                "fitting_type": f_type,
                "material_name": mat_name,
                "model_spec": m_spec,
                "unit": u,
                "unit_price": u_price,
                "section_1_id": "",
                "previous_stock_qty": prev_stock,
                "stock_qty": cur_stock,
                "change_qty": cur_stock - prev_stock,
                "remark": "",
            })

        # 按照用户业务要求严格按层次排序:
        # 层次1: 管件大类 (FITTING_CATEGORY_ORDER: 弯头 -> 三通 -> 变径管 -> 弯管 -> 封头 -> 固定支架 -> 补偿器 -> 球阀...)
        # 层次2: 材料名称 (material_name 自然聚合)
        # 层次3: 规格型号 (model_spec: 主口径降序、次口径降序、文本自然序)
        items.sort(key=_fitting_inventory_sort_key)

        sorted_categories = sorted(
            list(categories_set),
            key=lambda c: (FITTING_CATEGORY_ORDER.get(c, 99), c)
        )

        return {
            "supply_entity_id": norm_entity_id,
            "is_custom": False,
            "has_previous_record": has_previous_record,
            "has_record": has_previous_record,
            "latest_previous_batch_no": latest_previous_batch_no,
            "latest_previous_time": latest_previous_time,
            "latest_previous_date": latest_previous_time,
            "latest_previous_by": latest_previous_by,
            "total_previous_stock_qty": round(total_previous_stock, 2),
            "total_stock_qty": round(total_stock, 2),
            "categories": sorted_categories,
            "items": items,
        }
    finally:
        session.close()


def save_fitting_supplier_inventory(
    supply_entity_id: str,
    report_date: Optional[str] = None,
    items: List[Dict[str, Any]] = None,
    operator_name: str = "system",
) -> Dict[str, Any]:
    """
    提交指定供给主体的本次管件库存盘点数据（按次生成全新快照批次，不覆盖历史）。
    具备内存去重保护与 ON CONFLICT 幂等兜底，彻底杜绝主键与唯一键冲突。
    """
    ensure_fitting_supplier_inventory_table()
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
    safe_entity_tag = re.sub(r'[^a-zA-Z0-9]', '', norm_entity_id)[:8] or "SUP"
    batch_no = f"FIT_INV_{now.strftime('%Y%m%d_%H%M%S_%f')}_{safe_entity_tag}"

    # 包含 material_name 并支持 ON CONFLICT 幂等更新
    insert_sql = text("""
        INSERT INTO tube.tube_fitting_supplier_inventory (
            batch_no, report_date, supply_entity_id, section_1_id, fitting_type,
            material_name, model_spec, unit, stock_qty, remark, reported_by, reported_at, updated_by, updated_at
        ) VALUES (
            :batch_no, CAST(:report_date AS DATE), :supply_entity_id, :section_1_id, :fitting_type,
            :material_name, :model_spec, :unit, :stock_qty, :remark, :operator, :now, :operator, :now
        )
        ON CONFLICT (batch_no, supply_entity_id, section_1_id, fitting_type, material_name, model_spec, unit)
        DO UPDATE SET
            stock_qty = EXCLUDED.stock_qty,
            remark = EXCLUDED.remark,
            updated_by = EXCLUDED.updated_by,
            updated_at = EXCLUDED.updated_at;
    """)

    session = SessionLocal()
    try:
        # 内存级去重聚合保护 (防止前端由于视图重叠传入重复行)
        dedup_items: Dict[tuple, Dict[str, Any]] = {}
        for it in (items or []):
            f_type = str(it.get("fitting_type") or "").strip()
            m_name = str(it.get("material_name") or "").strip()
            m_spec = str(it.get("model_spec") or "").strip()
            unit_val = str(it.get("unit") or "个").strip() or "个"
            sec_id = str(it.get("section_1_id") or "").strip()
            if not f_type or not m_spec:
                continue

            dedup_key = (f_type, m_name, m_spec, unit_val, sec_id)
            stock_qty = max(0.0, float(it.get("stock_qty") or 0))
            remark = str(it.get("remark") or "").strip()

            dedup_items[dedup_key] = {
                "fitting_type": f_type,
                "material_name": m_name,
                "model_spec": m_spec,
                "unit": unit_val,
                "section_1_id": sec_id,
                "stock_qty": stock_qty,
                "remark": remark,
            }

        saved_count = 0
        total_stock = 0.0

        for it_data in dedup_items.values():
            session.execute(insert_sql, {
                "batch_no": batch_no,
                "report_date": norm_date_str,
                "supply_entity_id": norm_entity_id,
                "section_1_id": it_data["section_1_id"],
                "fitting_type": it_data["fitting_type"],
                "material_name": it_data["material_name"],
                "model_spec": it_data["model_spec"],
                "unit": it_data["unit"],
                "stock_qty": it_data["stock_qty"],
                "remark": it_data["remark"],
                "operator": operator,
                "now": now,
            })
            saved_count += 1
            total_stock += it_data["stock_qty"]

        # 记录操作日志
        try:
            from backend.projects.insulation_pipe_supply_2026.services.tube_audit_service import record_tube_operation_log
            record_tube_operation_log(
                session=session,
                operator=operator,
                action_type="SAVE_FITTING_SUPPLIER_INVENTORY",
                action_desc=f"提交厂家[{norm_entity_id}]管件成品库存盘点批次({batch_no})，共 {saved_count} 项，总在库 {round(total_stock, 2)} 件",
                resource_id=batch_no,
                before_value={},
                after_value={
                    "batch_no": batch_no,
                    "supply_entity_id": norm_entity_id,
                    "report_date": norm_date_str,
                    "saved_count": saved_count,
                    "total_stock_qty": round(total_stock, 2),
                }
            )
        except Exception:
            pass

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


def get_latest_all_fitting_suppliers_inventory() -> List[Dict[str, Any]]:
    """
    获取所有供给主体最新一次盘点批次的厂区成品待发管件库存汇总（供大屏或调度端使用）。
    """
    ensure_fitting_supplier_inventory_table()
    session = SessionLocal()
    try:
        sql = text("""
            WITH latest_batches AS (
                SELECT DISTINCT ON (supply_entity_id)
                    supply_entity_id, batch_no, reported_at
                FROM tube.tube_fitting_supplier_inventory
                ORDER BY supply_entity_id, reported_at DESC, id DESC
            )
            SELECT i.id, i.batch_no, i.report_date, i.supply_entity_id, i.fitting_type,
                   i.material_name, i.model_spec, i.unit, i.stock_qty, i.remark, 
                   i.reported_by, i.reported_at, i.updated_at
            FROM tube.tube_fitting_supplier_inventory i
            JOIN latest_batches lb 
              ON i.supply_entity_id = lb.supply_entity_id 
             AND (
                 (lb.batch_no IS NOT NULL AND i.batch_no = lb.batch_no)
                 OR (lb.batch_no IS NULL AND i.reported_at = lb.reported_at)
             )
            ORDER BY i.supply_entity_id ASC, i.fitting_type ASC, i.model_spec ASC;
        """)
        rows = session.execute(sql).mappings().all()
        return [
            {
                "id": r["id"],
                "batch_no": r["batch_no"] or "",
                "report_date": r["report_date"].isoformat() if r["report_date"] else "",
                "supply_entity_id": r["supply_entity_id"],
                "fitting_type": r["fitting_type"],
                "material_name": r["material_name"] or "",
                "model_spec": r["model_spec"],
                "unit": r["unit"] or "个",
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

