# -*- coding: utf-8 -*-
"""
tube 项目操作审计日志服务。
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal

def save_operation_log(
    operator: str,
    action_type: str,
    action_desc: str,
    operator_group: Optional[str] = None,
    resource_id: Optional[str] = None,
    before_value: Optional[Dict[str, Any]] = None,
    after_value: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
) -> None:
    """
    保存操作日志。包装在 try...except 中，确保不阻断主业务流程。
    """
    sql = text(
        """
        INSERT INTO logs.tube_operation_logs (
            operator, operator_group, action_type, action_desc, 
            resource_id, before_value, after_value, client_ip
        ) VALUES (
            :operator, :operator_group, :action_type, :action_desc, 
            :resource_id, :before_value, :after_value, :client_ip
        )
        """
    )
    
    # 序列化为 JSON 字符串以存入 JSONB 字段
    before_json = json.dumps(before_value) if before_value is not None else None
    after_json = json.dumps(after_value) if after_value is not None else None
    
    session = SessionLocal()
    try:
        session.execute(
            sql,
            {
                "operator": operator,
                "operator_group": operator_group,
                "action_type": action_type,
                "action_desc": action_desc,
                "resource_id": resource_id,
                "before_value": before_json,
                "after_value": after_json,
                "client_ip": client_ip,
            }
        )
        session.commit()
    except Exception as e:
        session.rollback()
        # 仅打印异常，确保不阻断主流程
        print(f"[Operation Log Error] Failed to save operation log: {e}")
    finally:
        session.close()


def query_operation_logs(
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    查询并过滤操作审计日志，返回列表及总数。
    """
    conditions = []
    params = {}
    
    if action_type:
        conditions.append("action_type = :action_type")
        params["action_type"] = action_type
        
    if operator:
        conditions.append("operator ILIKE :operator")
        params["operator"] = f"%{operator}%"
        
    if start_date:
        conditions.append("created_at >= :start_date")
        params["start_date"] = f"{start_date} 00:00:00+08"
        
    if end_date:
        conditions.append("created_at <= :end_date")
        params["end_date"] = f"{end_date} 23:59:59+08"
        
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
        
    count_sql = text(f"SELECT COUNT(*) FROM logs.tube_operation_logs {where_clause}")
    
    list_sql = text(
        f"""
        SELECT id, operator, operator_group, action_type, action_desc, 
               resource_id, before_value, after_value, client_ip, created_at
        FROM logs.tube_operation_logs 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
    )
    
    params["limit"] = limit
    params["offset"] = offset
    
    session = SessionLocal()
    try:
        total = session.execute(count_sql, params).scalar() or 0
        rows = session.execute(list_sql, params).mappings().all()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row["id"],
                "operator": row["operator"],
                "operator_group": row["operator_group"],
                "action_type": row["action_type"],
                "action_desc": row["action_desc"],
                "resource_id": row["resource_id"],
                "before_value": row["before_value"],
                "after_value": row["after_value"],
                "client_ip": row["client_ip"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })
            
        return {"total": total, "logs": logs}
    finally:
        session.close()


DEMAND_SUBMISSION_ACTIONS = [
    "SAVE_PLAN", "SUBMIT_USAGE", "SUBMIT_STATUS",
    "CONFIRM_ARRIVAL", "CONFIRM_CONSTRUCTION", "DIFF_APPROVE"
]
SUPPLY_SUBMISSION_ACTIONS = [
    "CREATE_DELIVERY", "CREATE_DELIVERY_BATCH", "CANCEL_DELIVERY", "CREATE_CUSTOM_ENTITY"
]
WAREHOUSE_SUBMISSION_ACTIONS = [
    "CONFIRM_WAREHOUSE"
]
ALL_SUBMISSION_ACTIONS = DEMAND_SUBMISSION_ACTIONS + SUPPLY_SUBMISSION_ACTIONS + WAREHOUSE_SUBMISSION_ACTIONS


def query_submission_logs(
    entity_type: Optional[str] = None,
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    专门查询主体数据提交（需求侧/供给侧/库管）的操作行为记录，
    并计算全网最新数据提交物理时间戳与 24h 内的提交计数。
    """
    conditions = []
    params: Dict[str, Any] = {}

    # 按主体分类约束 action_type
    if entity_type == "demand":
        conditions.append("action_type = ANY(:allowed_actions)")
        params["allowed_actions"] = DEMAND_SUBMISSION_ACTIONS
    elif entity_type == "supply":
        conditions.append("action_type = ANY(:allowed_actions)")
        params["allowed_actions"] = SUPPLY_SUBMISSION_ACTIONS
    elif entity_type == "warehouse":
        conditions.append("action_type = ANY(:allowed_actions)")
        params["allowed_actions"] = WAREHOUSE_SUBMISSION_ACTIONS
    else:
        conditions.append("action_type = ANY(:allowed_actions)")
        params["allowed_actions"] = ALL_SUBMISSION_ACTIONS

    # 具体的 action_type 过滤
    if action_type:
        conditions.append("action_type = :specific_action_type")
        params["specific_action_type"] = action_type

    if operator:
        conditions.append("operator ILIKE :operator")
        params["operator"] = f"%{operator}%"

    if start_date:
        conditions.append("created_at >= :start_date")
        params["start_date"] = f"{start_date} 00:00:00+08"

    if end_date:
        conditions.append("created_at <= :end_date")
        params["end_date"] = f"{end_date} 23:59:59+08"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_sql = text(f"SELECT COUNT(*) FROM logs.tube_operation_logs {where_clause}")
    list_sql = text(
        f"""
        SELECT id, operator, operator_group, action_type, action_desc, 
               resource_id, before_value, after_value, client_ip, created_at
        FROM logs.tube_operation_logs 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
    )

    latest_submitted_sql = text(
        """
        SELECT MAX(created_at) 
        FROM logs.tube_operation_logs 
        WHERE action_type = ANY(:all_submission_actions)
        """
    )
    recent_24h_sql = text(
        """
        SELECT COUNT(*) 
        FROM logs.tube_operation_logs 
        WHERE action_type = ANY(:all_submission_actions) 
          AND created_at >= NOW() - INTERVAL '24 HOURS'
        """
    )
    demand_24h_sql = text(
        """
        SELECT COUNT(*) 
        FROM logs.tube_operation_logs 
        WHERE action_type = ANY(:demand_submission_actions) 
          AND created_at >= NOW() - INTERVAL '24 HOURS'
        """
    )
    supply_24h_sql = text(
        """
        SELECT COUNT(*) 
        FROM logs.tube_operation_logs 
        WHERE action_type = ANY(:supply_submission_actions) 
          AND created_at >= NOW() - INTERVAL '24 HOURS'
        """
    )

    query_params = dict(params)
    query_params["limit"] = limit
    query_params["offset"] = offset

    session = SessionLocal()
    try:
        total = session.execute(count_sql, query_params).scalar() or 0
        rows = session.execute(list_sql, query_params).mappings().all()

        latest_submitted_at = session.execute(
            latest_submitted_sql, {"all_submission_actions": ALL_SUBMISSION_ACTIONS}
        ).scalar()
        recent_24h_count = session.execute(
            recent_24h_sql, {"all_submission_actions": ALL_SUBMISSION_ACTIONS}
        ).scalar() or 0
        demand_24h_count = session.execute(
            demand_24h_sql, {"demand_submission_actions": DEMAND_SUBMISSION_ACTIONS}
        ).scalar() or 0
        supply_24h_count = session.execute(
            supply_24h_sql, {"supply_submission_actions": SUPPLY_SUBMISSION_ACTIONS}
        ).scalar() or 0

        logs = []
        for row in rows:
            logs.append({
                "id": row["id"],
                "operator": row["operator"],
                "operator_group": row["operator_group"],
                "action_type": row["action_type"],
                "action_desc": row["action_desc"],
                "resource_id": row["resource_id"],
                "before_value": row["before_value"],
                "after_value": row["after_value"],
                "client_ip": row["client_ip"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None
            })

        return {
            "total": total,
            "logs": logs,
            "latest_submitted_at": latest_submitted_at.isoformat() if latest_submitted_at else None,
            "recent_24h_count": recent_24h_count,
            "demand_24h_count": demand_24h_count,
            "supply_24h_count": supply_24h_count,
        }
    finally:
        session.close()

