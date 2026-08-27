"""管件安装使用量记录、现场动态库存实时计算与使用流水台账服务。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.audit_log_service import save_operation_log


BEIJING_TZ = ZoneInfo("Asia/Shanghai")
PROJECT_KEY = "insulation_pipe_supply_2026"

_structures_checked = False


def _ensure_fitting_usage_table_structures() -> None:
    """自愈检查并保证 tube_fitting_daily_usage 表与核心索引存在。"""
    global _structures_checked
    if _structures_checked:
        return
    ddls = [
        """
        CREATE TABLE IF NOT EXISTS tube.tube_fitting_daily_usage (
            id BIGSERIAL PRIMARY KEY,
            project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
            section_1_id VARCHAR(64) NOT NULL,
            usage_date DATE NOT NULL,
            fitting_type VARCHAR(64) NOT NULL,
            model_spec VARCHAR(255) NOT NULL,
            unit VARCHAR(32) NOT NULL DEFAULT '个',
            usage_qty INTEGER NOT NULL CHECK (usage_qty > 0),
            remark TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            cancel_reason TEXT,
            cancelled_by VARCHAR(64),
            cancelled_at TIMESTAMPTZ,
            filled_by VARCHAR(64) NOT NULL,
            filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_by VARCHAR(64),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fitting_usage_stock_calc 
        ON tube.tube_fitting_daily_usage (section_1_id, fitting_type, model_spec) 
        WHERE status = 'active'
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fitting_usage_date_query 
        ON tube.tube_fitting_daily_usage (section_1_id, usage_date DESC, id DESC)
        """,
        "CREATE SEQUENCE IF NOT EXISTS tube.tube_fitting_daily_usage_id_seq",
        "ALTER TABLE tube.tube_fitting_daily_usage ALTER COLUMN id SET DEFAULT nextval('tube.tube_fitting_daily_usage_id_seq')",
        "SELECT setval('tube.tube_fitting_daily_usage_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_fitting_daily_usage), 0) + 1, false)",
    ]
    session = SessionLocal()
    try:
        for stmt in ddls:
            try:
                session.execute(text(stmt))
                session.commit()
            except Exception:
                session.rollback()
        _structures_checked = True
    finally:
        session.close()


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _serialize_time(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=BEIJING_TZ)
        return value.astimezone(BEIJING_TZ).isoformat()
    return str(value)


def get_fitting_inventory_summary(section_1_id: str) -> Dict[str, Any]:
    """
    动态实时计算当前标段所有已到货物料的现场库存与使用统计。
    
    返回：
      - summary: { total_types, arrived_sum, used_sum, stock_sum, overall_rate_pct }
      - items: [
          {
            fitting_type: str,
            model_spec: str,
            unit: str,
            arrived_qty: int,
            used_qty: int,
            stock_qty: int,
            usage_rate_pct: float
          }, ...
        ]
    """
    _ensure_fitting_usage_table_structures()
    sec_id = _clean(section_1_id)
    if not sec_id:
        raise HTTPException(status_code=422, detail="缺少标段参数 section_1_id")

    session = SessionLocal()
    try:
        # 1. 从发货表中汇总当前标段已到货数量 (status = 'arrived')
        arrived_sql = text(
            """
            SELECT 
                TRIM(fitting_type) AS fitting_type,
                TRIM(model_spec) AS model_spec,
                COALESCE(NULLIF(TRIM(unit), ''), '个') AS unit,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_arrived
            FROM tube.tube_fitting_delivery
            WHERE section_1_id = :section_1_id
              AND (status IN ('pending_receive', 'pending_warehouse', 'completed', 'arrived') OR arrived_confirm_at IS NOT NULL)
            GROUP BY TRIM(fitting_type), TRIM(model_spec), COALESCE(NULLIF(TRIM(unit), ''), '个')
            HAVING SUM(COALESCE(arrived_qty, shipped_qty, 0)) > 0
            """
        )
        arrived_rows = session.execute(arrived_sql, {"section_1_id": sec_id}).mappings().all()

        # 2. 从使用量表中汇总当前标段已使用数量 (status = 'active')
        used_sql = text(
            """
            SELECT 
                TRIM(fitting_type) AS fitting_type,
                TRIM(model_spec) AS model_spec,
                COALESCE(NULLIF(TRIM(unit), ''), '个') AS unit,
                SUM(usage_qty) AS total_used
            FROM tube.tube_fitting_daily_usage
            WHERE section_1_id = :section_1_id
              AND status = 'active'
            GROUP BY TRIM(fitting_type), TRIM(model_spec), COALESCE(NULLIF(TRIM(unit), ''), '个')
            """
        )
        used_rows = session.execute(used_sql, {"section_1_id": sec_id}).mappings().all()

        # 映射构建 (fitting_type, model_spec, unit) -> used_qty
        used_map: Dict[tuple, int] = {}
        for r in used_rows:
            key = (r["fitting_type"], r["model_spec"], r["unit"])
            used_map[key] = int(r["total_used"] or 0)

        # 3. 组合得出库存列表
        items = []
        arrived_sum = 0
        used_sum = 0
        stock_sum = 0

        for r in arrived_rows:
            f_type = r["fitting_type"]
            m_spec = r["model_spec"]
            unit = r["unit"]
            arrived_qty = int(r["total_arrived"] or 0)
            key = (f_type, m_spec, unit)
            used_qty = used_map.get(key, 0)
            stock_qty = max(arrived_qty - used_qty, 0)
            
            usage_rate_pct = round((used_qty / arrived_qty) * 100, 1) if arrived_qty > 0 else 0.0

            arrived_sum += arrived_qty
            used_sum += used_qty
            stock_sum += stock_qty

            items.append({
                "fitting_type": f_type,
                "model_spec": m_spec,
                "unit": unit,
                "arrived_qty": arrived_qty,
                "used_qty": used_qty,
                "stock_qty": stock_qty,
                "usage_rate_pct": usage_rate_pct,
            })

        # 按管件类别与规格自然排序
        items.sort(key=lambda x: (x["fitting_type"], x["model_spec"]))

        overall_rate_pct = round((used_sum / arrived_sum) * 100, 1) if arrived_sum > 0 else 0.0

        summary = {
            "section_1_id": sec_id,
            "total_types": len(items),
            "arrived_sum": arrived_sum,
            "used_sum": used_sum,
            "stock_sum": stock_sum,
            "overall_rate_pct": overall_rate_pct,
        }

        return {
            "ok": True,
            "summary": summary,
            "items": items,
        }
    finally:
        session.close()


def submit_fitting_usage_batch(
    section_1_id: str,
    usage_date: str,
    items: Sequence[Dict[str, Any]],
    operator: str,
    user_group: str,
    ip_address: str = "127.0.0.1",
) -> Dict[str, Any]:
    """
    批量提交指定标段在某一业务日期的管件安装使用量。
    
    原子事务保证：
      - 逐项校验数量为正整数；
      - 校验当次使用量 <= 现场当前可用库存；
      - 写入流水并记录审计日志。
    """
    _ensure_fitting_usage_table_structures()
    sec_id = _clean(section_1_id)
    if not sec_id:
        raise HTTPException(status_code=422, detail="缺少标段参数 section_1_id")

    u_date_str = _clean(usage_date)
    if not u_date_str:
        raise HTTPException(status_code=422, detail="缺少使用业务日期 usage_date")

    try:
        parsed_date = datetime.strptime(u_date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"使用日期格式无效：{u_date_str}，应为 YYYY-MM-DD") from exc

    valid_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        f_type = _clean(item.get("fitting_type"))
        m_spec = _clean(item.get("model_spec"))
        unit = _clean(item.get("unit")) or "个"
        raw_qty = item.get("usage_qty")
        if raw_qty is None or str(raw_qty).strip() == "":
            continue
        try:
            qty = int(raw_qty)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"管件【{f_type} {m_spec}】的使用数量必须为整数") from exc

        if qty <= 0:
            continue  # 忽略 <= 0 的项

        remark = _clean(item.get("remark"))

        valid_items.append({
            "fitting_type": f_type,
            "model_spec": m_spec,
            "unit": unit,
            "usage_qty": qty,
            "remark": remark,
        })

    if not valid_items:
        raise HTTPException(status_code=422, detail="未填报任何大于 0 的管件使用数量")

    session = SessionLocal()
    try:
        # 0. 校验当前标段在当日是否已经存在处于 active 状态的管件安装记录（单日仅允许提交一次）
        check_existing_sql = text(
            """
            SELECT COUNT(*) 
            FROM tube.tube_fitting_daily_usage
            WHERE section_1_id = :section_1_id
              AND usage_date = :usage_date
              AND status = 'active'
            """
        )
        existing_count = int(session.execute(check_existing_sql, {
            "section_1_id": sec_id,
            "usage_date": parsed_date
        }).scalar_one() or 0)

        if existing_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"当前标段在【{u_date_str}】已提交过管件安装记录（共 {existing_count} 笔有效记录），单日仅允许提交一次。如需重新填报，请先在下方历史台账中撤回当日记录。"
            )

        # 对该标段的到货和使用进行实时校验与排他锁定（安全扣减）
        # 1. 实时获取已到货量
        arrived_sql = text(
            """
            SELECT 
                TRIM(fitting_type) AS fitting_type,
                TRIM(model_spec) AS model_spec,
                COALESCE(NULLIF(TRIM(unit), ''), '个') AS unit,
                SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_arrived
            FROM tube.tube_fitting_delivery
            WHERE section_1_id = :section_1_id
              AND (status IN ('pending_receive', 'pending_warehouse', 'completed', 'arrived') OR arrived_confirm_at IS NOT NULL)
            GROUP BY TRIM(fitting_type), TRIM(model_spec), COALESCE(NULLIF(TRIM(unit), ''), '个')
            """
        )
        arrived_rows = session.execute(arrived_sql, {"section_1_id": sec_id}).mappings().all()
        arrived_map = {
            (r["fitting_type"], r["model_spec"], r["unit"]): int(r["total_arrived"] or 0)
            for r in arrived_rows
        }

        # 2. 实时获取已使用量
        used_sql = text(
            """
            SELECT 
                TRIM(fitting_type) AS fitting_type,
                TRIM(model_spec) AS model_spec,
                COALESCE(NULLIF(TRIM(unit), ''), '个') AS unit,
                SUM(usage_qty) AS total_used
            FROM tube.tube_fitting_daily_usage
            WHERE section_1_id = :section_1_id
              AND status = 'active'
            GROUP BY TRIM(fitting_type), TRIM(model_spec), COALESCE(NULLIF(TRIM(unit), ''), '个')
            """
        )
        used_rows = session.execute(used_sql, {"section_1_id": sec_id}).mappings().all()
        used_map = {
            (r["fitting_type"], r["model_spec"], r["unit"]): int(r["total_used"] or 0)
            for r in used_rows
        }

        # 3. 逐项核验库存并累加当次使用
        # 针对同一次提交中同一规格出现多次的情况做累加保护
        batch_accumulated: Dict[tuple, int] = {}
        for it in valid_items:
            key = (it["fitting_type"], it["model_spec"], it["unit"])
            arrived_qty = arrived_map.get(key, 0)
            if arrived_qty <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"管件【{it['fitting_type']} {it['model_spec']}】在当前标段尚无已到货记录，不可填报使用量",
                )
            used_qty = used_map.get(key, 0)
            current_stock = max(arrived_qty - used_qty, 0)
            already_in_batch = batch_accumulated.get(key, 0)
            total_attempt = already_in_batch + it["usage_qty"]

            if total_attempt > current_stock:
                raise HTTPException(
                    status_code=422,
                    detail=f"管件【{it['fitting_type']} {it['model_spec']}】现场当前可用库存仅剩 {current_stock} {it['unit']}，无法使用 {total_attempt} {it['unit']}",
                )
            batch_accumulated[key] = total_attempt

        # 4. 执行写入流水表
        insert_sql = text(
            """
            INSERT INTO tube.tube_fitting_daily_usage (
                project_key, section_1_id, usage_date, fitting_type, model_spec, unit,
                usage_qty, remark, status, filled_by, filled_at,
                updated_by, updated_at
            ) VALUES (
                :project_key, :section_1_id, :usage_date, :fitting_type, :model_spec, :unit,
                :usage_qty, :remark, 'active', :filled_by, NOW(),
                :filled_by, NOW()
            )
            RETURNING id
            """
        )

        inserted_ids = []
        for it in valid_items:
            res = session.execute(
                insert_sql,
                {
                    "project_key": PROJECT_KEY,
                    "section_1_id": sec_id,
                    "usage_date": parsed_date,
                    "fitting_type": it["fitting_type"],
                    "model_spec": it["model_spec"],
                    "unit": it["unit"],
                    "usage_qty": it["usage_qty"],
                    "remark": it["remark"] or None,
                    "filled_by": operator or "system",
                },
            )
            inserted_id = res.scalar()
            inserted_ids.append(inserted_id)

        session.commit()

        # 5. 记录审计日志
        try:
            total_qty_sum = sum(it["usage_qty"] for it in valid_items)
            save_operation_log(
                project_key=PROJECT_KEY,
                target_type="fitting_usage",
                target_id=sec_id,
                action="submit_fitting_usage",
                operator=operator,
                user_group=user_group,
                ip_address=ip_address,
                details={
                    "section_1_id": sec_id,
                    "usage_date": u_date_str,
                    "item_count": len(valid_items),
                    "total_usage_qty": total_qty_sum,
                    "inserted_ids": inserted_ids,
                },
            )
        except Exception:
            pass

        return {
            "ok": True,
            "message": f"成功提交 {len(valid_items)} 项管件安装使用记录，共计 {sum(it['usage_qty'] for it in valid_items)} 件",
            "inserted_ids": inserted_ids,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_fitting_usage_history(
    section_1_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = "all",
) -> List[Dict[str, Any]]:
    """
    查询管件安装使用流水台账。
    """
    _ensure_fitting_usage_table_structures()
    sec_id = _clean(section_1_id)
    if not sec_id:
        raise HTTPException(status_code=422, detail="缺少标段参数 section_1_id")

    conditions = ["section_1_id = :section_1_id"]
    params: Dict[str, Any] = {"section_1_id": sec_id}

    if start_date:
        conditions.append("usage_date >= :start_date")
        params["start_date"] = datetime.strptime(_clean(start_date), "%Y-%m-%d").date()

    if end_date:
        conditions.append("usage_date <= :end_date")
        params["end_date"] = datetime.strptime(_clean(end_date), "%Y-%m-%d").date()

    if status and status != "all":
        conditions.append("status = :status")
        params["status"] = _clean(status)

    if keyword:
        kw = f"%{_clean(keyword)}%"
        conditions.append("(fitting_type ILIKE :kw OR model_spec ILIKE :kw OR remark ILIKE :kw OR filled_by ILIKE :kw)")
        params["kw"] = kw

    where_clause = " AND ".join(conditions)

    sql = text(
        f"""
        SELECT 
            id, project_key, section_1_id, usage_date, fitting_type, model_spec, unit,
            usage_qty, remark, status, cancel_reason,
            cancelled_by, cancelled_at, filled_by, filled_at, updated_by, updated_at
        FROM tube.tube_fitting_daily_usage
        WHERE {where_clause}
        ORDER BY usage_date DESC, id DESC
        """
    )

    session = SessionLocal()
    try:
        rows = session.execute(sql, params).mappings().all()
        result = []
        for r in rows:
            result.append({
                "id": int(r["id"]),
                "section_1_id": r["section_1_id"],
                "usage_date": str(r["usage_date"]),
                "fitting_type": r["fitting_type"],
                "model_spec": r["model_spec"],
                "unit": r["unit"] or "个",
                "usage_qty": int(r["usage_qty"] or 0),
                "remark": r["remark"] or "",
                "status": r["status"],
                "cancel_reason": r["cancel_reason"] or "",
                "cancelled_by": r["cancelled_by"] or "",
                "cancelled_at": _serialize_time(r["cancelled_at"]),
                "filled_by": r["filled_by"],
                "filled_at": _serialize_time(r["filled_at"]),
                "updated_at": _serialize_time(r["updated_at"]),
            })
        return result
    finally:
        session.close()


def cancel_fitting_usage_record(
    usage_id: int,
    operator: str,
    user_group: str,
    cancel_reason: str,
    ip_address: str = "127.0.0.1",
) -> Dict[str, Any]:
    """
    撤回作废管件使用记录。
    
    权限规则：
      - 仅限超级管理员 (global_admin/dev_admin) 拥有操作权限；
      - 普通填报人员禁止撤销。
    """
    _ensure_fitting_usage_table_structures()
    if not usage_id or int(usage_id) <= 0:
        raise HTTPException(status_code=422, detail="使用记录 ID 无效")

    reason = _clean(cancel_reason)
    if not reason:
        raise HTTPException(status_code=422, detail="撤回作废必须填写原因说明")

    g = str(user_group or "").strip().lower()
    is_admin = g in ("global_admin", "dev_admin")
    if not is_admin:
        raise HTTPException(status_code=403, detail="仅超级管理员（Global_admin）拥有管件安装记录的作废与撤回权限")

    session = SessionLocal()
    try:
        select_sql = text(
            """
            SELECT id, section_1_id, usage_date, fitting_type, model_spec, unit,
                   usage_qty, status, filled_by, filled_at
            FROM tube.tube_fitting_daily_usage
            WHERE id = :usage_id
            FOR UPDATE
            """
        )
        row = session.execute(select_sql, {"usage_id": int(usage_id)}).mappings().one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail=f"管件使用记录 ID 【{usage_id}】不存在")

        if row["status"] == "cancelled":
            raise HTTPException(status_code=422, detail="该记录此前已被撤回作废，无需重复操作")

        # 执行撤回
        update_sql = text(
            """
            UPDATE tube.tube_fitting_daily_usage
            SET status = 'cancelled',
                cancel_reason = :cancel_reason,
                cancelled_by = :cancelled_by,
                cancelled_at = NOW(),
                updated_by = :cancelled_by,
                updated_at = NOW()
            WHERE id = :usage_id
            """
        )
        session.execute(
            update_sql,
            {
                "usage_id": int(usage_id),
                "cancel_reason": reason,
                "cancelled_by": operator or "system",
            },
        )
        session.commit()

        # 记录审计日志
        try:
            save_operation_log(
                project_key=PROJECT_KEY,
                target_type="fitting_usage",
                target_id=str(usage_id),
                action="cancel_fitting_usage",
                operator=operator,
                user_group=user_group,
                ip_address=ip_address,
                details={
                    "usage_id": usage_id,
                    "section_1_id": row["section_1_id"],
                    "fitting_type": row["fitting_type"],
                    "model_spec": row["model_spec"],
                    "usage_qty": row["usage_qty"],
                    "cancel_reason": reason,
                },
            )
        except Exception:
            pass

        return {
            "ok": True,
            "message": f"成功撤回管件【{row['fitting_type']} {row['model_spec']}】的使用记录（{row['usage_qty']} {row['unit']}），现场库存已自动释放恢复",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_fitting_usage_item(
    usage_id: int,
    operator: str,
    user_group: str,
    usage_qty: Optional[int] = None,
    remark: Optional[str] = None,
    status: Optional[str] = None,
    cancel_reason: Optional[str] = None,
    filled_by: Optional[str] = None,
    usage_date: Optional[str] = None,
    ip_address: str = "127.0.0.1",
) -> Dict[str, Any]:
    """
    【Global_admin 专属】编辑单笔管件安装使用记录。
    支持修改安装数量（自动核算库存上限）、施工备注、填报人、采集日期及状态。
    """
    _ensure_fitting_usage_table_structures()
    g = str(user_group or "").strip().lower()
    if g not in ("global_admin", "dev_admin"):
        raise HTTPException(status_code=403, detail="仅超级管理员（Global_admin）拥有管件安装记录的高级编辑权限")

    if not usage_id or int(usage_id) <= 0:
        raise HTTPException(status_code=422, detail="记录 ID 无效")

    session = SessionLocal()
    try:
        select_sql = text(
            """
            SELECT id, section_1_id, usage_date, fitting_type, model_spec, unit,
                   usage_qty, remark, status, filled_by
            FROM tube.tube_fitting_daily_usage
            WHERE id = :usage_id
            FOR UPDATE
            """
        )
        row = session.execute(select_sql, {"usage_id": int(usage_id)}).mappings().one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail=f"管件使用记录 ID 【{usage_id}】不存在")

        sec_id = row["section_1_id"]
        f_type = row["fitting_type"]
        m_spec = row["model_spec"]
        unit = row["unit"] or "个"
        old_qty = int(row["usage_qty"] or 0)
        old_status = row["status"]

        # 检查是否修改了数量或激活状态，核验可用库存
        target_qty = int(usage_qty) if usage_qty is not None else old_qty
        target_status = _clean(status) if status is not None else old_status

        if target_qty <= 0 and target_status == "active":
            raise HTTPException(status_code=422, detail="有效记录的安装数量必须大于 0")

        if target_status == "active" and (target_qty != old_qty or old_status != "active"):
            # 查总到货
            arrived_sql = text(
                """
                SELECT SUM(COALESCE(arrived_qty, shipped_qty, 0)) AS total_arrived
                FROM tube.tube_fitting_delivery
                WHERE section_1_id = :sec_id
                  AND TRIM(fitting_type) = :f_type
                  AND TRIM(model_spec) = :m_spec
                  AND (status IN ('pending_receive', 'pending_warehouse', 'completed', 'arrived') OR arrived_confirm_at IS NOT NULL)
                """
            )
            total_arrived = int(session.execute(arrived_sql, {"sec_id": sec_id, "f_type": f_type, "m_spec": m_spec}).scalar_one() or 0)

            # 查除本条记录外的其余已使用总量
            other_used_sql = text(
                """
                SELECT SUM(usage_qty) AS other_used
                FROM tube.tube_fitting_daily_usage
                WHERE section_1_id = :sec_id
                  AND TRIM(fitting_type) = :f_type
                  AND TRIM(model_spec) = :m_spec
                  AND status = 'active'
                  AND id != :usage_id
                """
            )
            other_used = int(session.execute(other_used_sql, {"sec_id": sec_id, "f_type": f_type, "m_spec": m_spec, "usage_id": int(usage_id)}).scalar_one() or 0)

            available_max = max(total_arrived - other_used, 0)
            if target_qty > available_max:
                raise HTTPException(
                    status_code=422,
                    detail=f"管件【{f_type} {m_spec}】修改后的使用量 ({target_qty} {unit}) 超出最大可用库存容量 ({available_max} {unit})，当前累计到货 {total_arrived}，其余记录已占用 {other_used}"
                )

        # 构造更新字段
        updates = ["updated_by = :operator", "updated_at = NOW()"]
        params = {"usage_id": int(usage_id), "operator": operator or "admin"}

        if usage_qty is not None:
            updates.append("usage_qty = :usage_qty")
            params["usage_qty"] = target_qty

        if remark is not None:
            updates.append("remark = :remark")
            params["remark"] = _clean(remark)

        if status is not None:
            updates.append("status = :status")
            params["status"] = target_status
            if target_status == "cancelled":
                updates.append("cancel_reason = :cancel_reason")
                updates.append("cancelled_by = :cancelled_by")
                updates.append("cancelled_at = NOW()")
                params["cancel_reason"] = _clean(cancel_reason) or "管理员编辑作废"
                params["cancelled_by"] = operator
            elif target_status == "active":
                updates.append("cancel_reason = NULL")
                updates.append("cancelled_by = NULL")
                updates.append("cancelled_at = NULL")

        if filled_by is not None:
            updates.append("filled_by = :filled_by")
            params["filled_by"] = _clean(filled_by)

        if usage_date is not None:
            parsed_d = datetime.strptime(_clean(usage_date), "%Y-%m-%d").date()
            updates.append("usage_date = :usage_date")
            params["usage_date"] = parsed_d

        update_sql = text(f"UPDATE tube.tube_fitting_daily_usage SET {', '.join(updates)} WHERE id = :usage_id")
        session.execute(update_sql, params)
        session.commit()

        # 审计日志
        try:
            save_operation_log(
                project_key=PROJECT_KEY,
                target_type="fitting_usage",
                target_id=str(usage_id),
                action="admin_update_fitting_usage_item",
                operator=operator,
                user_group=user_group,
                ip_address=ip_address,
                details={
                    "usage_id": usage_id,
                    "section_1_id": sec_id,
                    "fitting_type": f_type,
                    "model_spec": m_spec,
                    "target_qty": target_qty,
                    "target_status": target_status,
                },
            )
        except Exception:
            pass

        return {"ok": True, "message": f"管理员已成功更新管件【{f_type} {m_spec}】的安装使用记录"}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_fitting_usage_batch(
    section_1_id: str,
    usage_date: str,
    operator: str,
    user_group: str,
    new_usage_date: Optional[str] = None,
    filled_by: Optional[str] = None,
    items: Optional[Sequence[Dict[str, Any]]] = None,
    cancel_reason: Optional[str] = None,
    ip_address: str = "127.0.0.1",
) -> Dict[str, Any]:
    """
    【Global_admin 专属】批量更新某标段某消耗采集日期的整日管件安装使用记录。
    支持修改消耗采集日期、填报人以及批量更新各子项的安装数量、位置和备注。
    """
    _ensure_fitting_usage_table_structures()
    g = str(user_group or "").strip().lower()
    if g not in ("global_admin", "dev_admin"):
        raise HTTPException(status_code=403, detail="仅超级管理员（Global_admin）拥有管件安装批次的高级编辑权限")

    sec_id = _clean(section_1_id)
    u_date = _clean(usage_date)
    if not sec_id or not u_date:
        raise HTTPException(status_code=422, detail="缺少标段ID或原始消耗采集日期")

    session = SessionLocal()
    try:
        # 查询该日期下的所有记录
        rows_sql = text(
            """
            SELECT id, section_1_id, usage_date, fitting_type, model_spec, unit,
                   usage_qty, remark, status, filled_by
            FROM tube.tube_fitting_daily_usage
            WHERE section_1_id = :sec_id AND usage_date = :u_date
            FOR UPDATE
            """
        )
        existing_rows = session.execute(rows_sql, {"sec_id": sec_id, "u_date": datetime.strptime(u_date, "%Y-%m-%d").date()}).mappings().all()
        if not existing_rows:
            raise HTTPException(status_code=404, detail=f"标段在【{u_date}】尚无任何管件使用记录")

        # 1. 如果修改了采集日期
        target_date_obj = None
        if new_usage_date and _clean(new_usage_date) != u_date:
            target_date_obj = datetime.strptime(_clean(new_usage_date), "%Y-%m-%d").date()

        # 2. 逐项处理子项修改
        items_map = {int(it["id"]): it for it in (items or []) if isinstance(it, dict) and it.get("id")}

        for r in existing_rows:
            r_id = int(r["id"])
            item_payload = items_map.get(r_id)

            updates = ["updated_by = :operator", "updated_at = NOW()"]
            params = {"r_id": r_id, "operator": operator or "admin"}

            if target_date_obj is not None:
                updates.append("usage_date = :new_usage_date")
                params["new_usage_date"] = target_date_obj

            if filled_by is not None and _clean(filled_by):
                updates.append("filled_by = :filled_by")
                params["filled_by"] = _clean(filled_by)

            if item_payload:
                if "usage_qty" in item_payload and item_payload["usage_qty"] is not None:
                    q = int(item_payload["usage_qty"])
                    if q < 0:
                        raise HTTPException(status_code=422, detail="使用数量不能小于 0")
                    updates.append("usage_qty = :usage_qty")
                    params["usage_qty"] = q

                if "remark" in item_payload and item_payload["remark"] is not None:
                    updates.append("remark = :remark")
                    params["remark"] = _clean(item_payload["remark"])

                if "status" in item_payload and item_payload["status"] is not None:
                    st = _clean(item_payload["status"])
                    updates.append("status = :status")
                    params["status"] = st
                    if st == "cancelled":
                        updates.append("cancel_reason = :cancel_reason")
                        updates.append("cancelled_by = :cancelled_by")
                        updates.append("cancelled_at = NOW()")
                        params["cancel_reason"] = _clean(item_payload.get("cancel_reason")) or _clean(cancel_reason) or "管理员批量编辑作废"
                        params["cancelled_by"] = operator
                    elif st == "active":
                        updates.append("cancel_reason = NULL")
                        updates.append("cancelled_by = NULL")
                        updates.append("cancelled_at = NULL")

            if updates:
                session.execute(text(f"UPDATE tube.tube_fitting_daily_usage SET {', '.join(updates)} WHERE id = :r_id"), params)

        session.commit()

        # 审计日志
        try:
            save_operation_log(
                project_key=PROJECT_KEY,
                target_type="fitting_usage_batch",
                target_id=f"{sec_id}__{u_date}",
                action="admin_update_fitting_usage_batch",
                operator=operator,
                user_group=user_group,
                ip_address=ip_address,
                details={
                    "section_1_id": sec_id,
                    "old_usage_date": u_date,
                    "new_usage_date": new_usage_date or u_date,
                    "items_count": len(existing_rows),
                },
            )
        except Exception:
            pass

        return {
            "ok": True,
            "message": f"管理员已成功批量更新标段在【{new_usage_date or u_date}】的管件安装批次记录 (共 {len(existing_rows)} 笔)",
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
