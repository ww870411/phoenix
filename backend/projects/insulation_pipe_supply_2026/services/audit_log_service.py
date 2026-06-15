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
        INSERT INTO tube.operation_logs (
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
        
    count_sql = text(f"SELECT COUNT(*) FROM tube.operation_logs {where_clause}")
    
    list_sql = text(
        f"""
        SELECT id, operator, operator_group, action_type, action_desc, 
               resource_id, before_value, after_value, client_ip, created_at
        FROM tube.operation_logs 
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
