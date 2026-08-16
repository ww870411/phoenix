# -*- coding: utf-8 -*-
"""
保温直管与管件设计量与计划采购量基准服务 (Baseline Service)。
支持数据库表自愈、查询、批量保存以及从旧版 JSON 配置平滑迁移入库。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal


_baseline_tables_checked = False


def ensure_baseline_tables() -> None:
    """自愈检查并创建 tube_pipe_baseline 与 tube_fitting_baseline 表及索引。"""
    global _baseline_tables_checked
    if _baseline_tables_checked:
        return

    ddls = [
        """
        CREATE TABLE IF NOT EXISTS tube.tube_pipe_baseline (
            id BIGSERIAL PRIMARY KEY,
            section_1_id VARCHAR(64) NOT NULL,
            pipe_model_id VARCHAR(128) NOT NULL,
            unit VARCHAR(32) NOT NULL DEFAULT '米',
            design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
            purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
            remark TEXT,
            created_by VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(128),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_tube_pipe_baseline_qty_nonnegative 
                CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_pipe_baseline_sec_model 
            ON tube.tube_pipe_baseline (section_1_id, pipe_model_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_pipe_baseline_sec 
            ON tube.tube_pipe_baseline (section_1_id);
        """,
        """
        CREATE TABLE IF NOT EXISTS tube.tube_fitting_baseline (
            id BIGSERIAL PRIMARY KEY,
            section_1_id VARCHAR(64) NOT NULL,
            fitting_type VARCHAR(64) NOT NULL,
            model_spec VARCHAR(128) NOT NULL,
            sub_model_spec VARCHAR(128) NOT NULL DEFAULT '',
            unit VARCHAR(32) NOT NULL DEFAULT '个',
            design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
            purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
            remark TEXT,
            created_by VARCHAR(128),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(128),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_tube_fitting_baseline_qty_nonnegative 
                CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
        );
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_baseline_sec_type_spec_sub 
            ON tube.tube_fitting_baseline (section_1_id, fitting_type, model_spec, sub_model_spec);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_sec 
            ON tube.tube_fitting_baseline (section_1_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_type 
            ON tube.tube_fitting_baseline (fitting_type);
        """,
    ]

    session = SessionLocal()
    try:
        for stmt in ddls:
            try:
                session.execute(text(stmt))
                session.commit()
            except Exception:
                session.rollback()
        _baseline_tables_checked = True
    finally:
        session.close()


def _clean_str(val: Any) -> str:
    return str(val or "").strip()


def _clean_num(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        num = float(val)
        return num if num >= 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


# -----------------------------------------------------------------------------
# 直管基准量 (Pipe Baseline) 核心操作
# -----------------------------------------------------------------------------

def list_pipe_baselines(section_1_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """查询直管基准列表。"""
    ensure_baseline_tables()
    session = SessionLocal()
    try:
        sql = """
            SELECT id, section_1_id, pipe_model_id, unit, design_qty, purchase_plan_qty,
                   remark, created_by, created_at, updated_by, updated_at
            FROM tube.tube_pipe_baseline
        """
        params = {}
        if section_1_id:
            sql += " WHERE section_1_id = :section_1_id"
            params["section_1_id"] = section_1_id
        sql += " ORDER BY section_1_id ASC, id ASC"

        rows = session.execute(text(sql), params).mappings().all()
        return [
            {
                "id": row["id"],
                "section_1_id": row["section_1_id"],
                "pipe_model_id": row["pipe_model_id"],
                "unit": row["unit"] or "米",
                "design_qty": float(row["design_qty"] or 0),
                "purchase_plan_qty": float(row["purchase_plan_qty"] or 0),
                "remark": row["remark"] or "",
                "created_by": row["created_by"] or "",
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_by": row["updated_by"] or "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def save_pipe_baselines(
    items: List[Dict[str, Any]], 
    operator_name: str = "",
    replace_all_for_sections: Optional[List[str]] = None
) -> int:
    """
    保存或更新直管基准记录。
    如果指定了 replace_all_for_sections，则会先清空这些标段的旧记录，然后重新插入。
    """
    ensure_baseline_tables()
    session = SessionLocal()
    try:
        if replace_all_for_sections:
            session.execute(
                text("DELETE FROM tube.tube_pipe_baseline WHERE section_1_id = ANY(:sec_list)"),
                {"sec_list": list(set(replace_all_for_sections))}
            )

        upsert_sql = """
            INSERT INTO tube.tube_pipe_baseline (
                section_1_id, pipe_model_id, unit, design_qty, purchase_plan_qty,
                remark, created_by, updated_by, updated_at
            ) VALUES (
                :section_1_id, :pipe_model_id, :unit, :design_qty, :purchase_plan_qty,
                :remark, :operator_name, :operator_name, NOW()
            )
            ON CONFLICT (section_1_id, pipe_model_id) DO UPDATE SET
                unit = EXCLUDED.unit,
                design_qty = EXCLUDED.design_qty,
                purchase_plan_qty = EXCLUDED.purchase_plan_qty,
                remark = EXCLUDED.remark,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
        """
        saved_count = 0
        for it in items:
            sec_id = _clean_str(it.get("section_1_id"))
            model_id = _clean_str(it.get("pipe_model_id"))
            if not sec_id or not model_id:
                continue

            session.execute(
                text(upsert_sql),
                {
                    "section_1_id": sec_id,
                    "pipe_model_id": model_id,
                    "unit": _clean_str(it.get("unit")) or "米",
                    "design_qty": _clean_num(it.get("design_qty")),
                    "purchase_plan_qty": _clean_num(it.get("purchase_plan_qty")),
                    "remark": _clean_str(it.get("remark")),
                    "operator_name": _clean_str(operator_name) or "system",
                }
            )
            saved_count += 1

        session.commit()
        return saved_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def migrate_pipe_baselines_from_json(operator_name: str = "json_migration") -> Dict[str, Any]:
    """
    从 tube_config.json 配置文件中读取 baseline_presets 并全量迁移/同步至 tube.tube_pipe_baseline 表。
    返回导入统计结果字典。
    """
    from backend.projects.insulation_pipe_supply_2026.services.config_service import load_tube_config

    cfg = load_tube_config()
    raw_presets = cfg.get("baseline_presets") or []

    saved_count = save_pipe_baselines(raw_presets, operator_name=operator_name)
    total_in_db = len(list_pipe_baselines())

    return {
        "ok": True,
        "json_source_count": len(raw_presets),
        "imported_count": saved_count,
        "total_db_count": total_in_db,
    }


# -----------------------------------------------------------------------------
# 管件基准量 (Fitting Baseline) 核心操作
# -----------------------------------------------------------------------------

def list_fitting_baselines(section_1_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """查询管件基准列表。"""
    ensure_baseline_tables()
    session = SessionLocal()
    try:
        sql = """
            SELECT id, section_1_id, fitting_type, model_spec, sub_model_spec, unit,
                   design_qty, purchase_plan_qty, remark, created_by, created_at, updated_by, updated_at
            FROM tube.tube_fitting_baseline
        """
        params = {}
        if section_1_id:
            sql += " WHERE section_1_id = :section_1_id"
            params["section_1_id"] = section_1_id
        sql += " ORDER BY section_1_id ASC, fitting_type ASC, model_spec ASC, sub_model_spec ASC, id ASC"

        rows = session.execute(text(sql), params).mappings().all()
        return [
            {
                "id": row["id"],
                "section_1_id": row["section_1_id"],
                "fitting_type": row["fitting_type"],
                "model_spec": row["model_spec"],
                "sub_model_spec": row["sub_model_spec"] or "",
                "unit": row["unit"] or "个",
                "design_qty": float(row["design_qty"] or 0),
                "purchase_plan_qty": float(row["purchase_plan_qty"] or 0),
                "remark": row["remark"] or "",
                "created_by": row["created_by"] or "",
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_by": row["updated_by"] or "",
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]
    finally:
        session.close()


def save_fitting_baselines(
    items: List[Dict[str, Any]], 
    operator_name: str = "",
    replace_all_for_sections: Optional[List[str]] = None
) -> int:
    """保存或更新管件基准记录。"""
    ensure_baseline_tables()
    session = SessionLocal()
    try:
        if replace_all_for_sections:
            session.execute(
                text("DELETE FROM tube.tube_fitting_baseline WHERE section_1_id = ANY(:sec_list)"),
                {"sec_list": list(set(replace_all_for_sections))}
            )

        upsert_sql = """
            INSERT INTO tube.tube_fitting_baseline (
                section_1_id, fitting_type, model_spec, sub_model_spec, unit,
                design_qty, purchase_plan_qty, remark, created_by, updated_by, updated_at
            ) VALUES (
                :section_1_id, :fitting_type, :model_spec, :sub_model_spec, :unit,
                :design_qty, :purchase_plan_qty, :remark, :operator_name, :operator_name, NOW()
            )
            ON CONFLICT (section_1_id, fitting_type, model_spec, sub_model_spec) DO UPDATE SET
                unit = EXCLUDED.unit,
                design_qty = EXCLUDED.design_qty,
                purchase_plan_qty = EXCLUDED.purchase_plan_qty,
                remark = EXCLUDED.remark,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
        """
        saved_count = 0
        for it in items:
            sec_id = _clean_str(it.get("section_1_id"))
            f_type = _clean_str(it.get("fitting_type"))
            m_spec = _clean_str(it.get("model_spec"))
            sub_spec = _clean_str(it.get("sub_model_spec"))
            if not sec_id or not f_type or not m_spec:
                continue

            session.execute(
                text(upsert_sql),
                {
                    "section_1_id": sec_id,
                    "fitting_type": f_type,
                    "model_spec": m_spec,
                    "sub_model_spec": sub_spec,
                    "unit": _clean_str(it.get("unit")) or "个",
                    "design_qty": _clean_num(it.get("design_qty")),
                    "purchase_plan_qty": _clean_num(it.get("purchase_plan_qty")),
                    "remark": _clean_str(it.get("remark")),
                    "operator_name": _clean_str(operator_name) or "system",
                }
            )
            saved_count += 1

        session.commit()
        return saved_count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
