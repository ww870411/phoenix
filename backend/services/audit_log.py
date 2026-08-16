# -*- coding: utf-8 -*-
"""
全局系统操作审计日志服务：基于 PostgreSQL (logs.system_audit_logs) 表的事件写入、SQL多维查询与极速分类统计。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal

logger = logging.getLogger(__name__)

EAST_8 = timezone(timedelta(hours=8))


def _normalize_text(value: object, default: str = "") -> str:
    text_val = str(value or "").strip()
    return text_val or default


def _parse_time(value: object) -> datetime:
    raw = _normalize_text(value)
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def infer_project_key(page: str, target: str, detail: Any) -> str:
    page_lower = (page or "").lower()
    if "/projects/insulation_pipe_supply_2026" in page_lower or "insulation_pipe" in page_lower:
        return "insulation_pipe_supply_2026"
    if "/projects/daily_report_25_26" in page_lower or "daily_report_25_26" in page_lower:
        return "daily_report_25_26"
    if "/projects/daily_report_spring_festval_2026" in page_lower:
        return "daily_report_spring_festval_2026"
    if "/projects/monthly_data_show" in page_lower:
        return "monthly_data_show"
    if "/projects/monthly_data_pull" in page_lower:
        return "monthly_data_pull"
    if "/admin-console" in page_lower:
        return "admin_console"
    if page_lower.startswith("/login"):
        return "global"
    if page_lower.startswith("/projects"):
        return "global"
    return "global"


def append_events(events: Iterable[Dict[str, Any]]) -> int:
    """
    将操作审计日志批量写入 PostgreSQL logs.system_audit_logs 数据表。
    具备 Fail-Safe 安全保护：写日志异常绝不阻塞主业务流程。
    """
    event_list = list(events)
    if not event_list:
        return 0

    batch_params: List[Dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)

    for item in event_list:
        ts_dt = _parse_time(item.get("ts"))
        ts_east8_str = item.get("ts_east8") or ts_dt.astimezone(EAST_8).isoformat()
        page_str = _normalize_text(item.get("page"))
        target_str = _normalize_text(item.get("target"))
        detail_val = item.get("detail")

        # 规范化 detail 为合法 JSON 字符串
        if detail_val is not None and not isinstance(detail_val, (dict, list)):
            try:
                detail_val = json.loads(str(detail_val))
            except Exception:
                detail_val = {"raw": str(detail_val)}

        detail_json = json.dumps(detail_val, ensure_ascii=False) if detail_val is not None else None
        cat_str = _normalize_text(item.get("category"), "default")
        act_str = _normalize_text(item.get("action"), "action")
        proj_key = _normalize_text(item.get("project_key")) or infer_project_key(page_str, target_str, detail_val)
        user_grp = _normalize_text(item.get("group") or item.get("user_group"))
        status_val = _normalize_text(item.get("status")) or ("failed" if (cat_str == "error" or act_str == "error") else "success")

        record = {
            "ts": ts_dt,
            "ts_east8": ts_east8_str,
            "project_key": proj_key,
            "category": cat_str,
            "action": act_str,
            "status": status_val,
            "duration_ms": item.get("duration_ms"),
            "error_msg": item.get("error_msg"),
            "resource_type": item.get("resource_type"),
            "resource_id": item.get("resource_id"),
            "page": page_str or None,
            "target": target_str or None,
            "request_id": item.get("request_id"),
            "username": _normalize_text(item.get("username")) or None,
            "user_group": user_grp or None,
            "unit": _normalize_text(item.get("unit")) or None,
            "client_ip": _normalize_text(item.get("client_ip")) or None,
            "user_agent": _normalize_text(item.get("user_agent")) or None,
            "detail": detail_json,
            "created_at": now_utc,
        }
        batch_params.append(record)

    insert_sql = text("""
        INSERT INTO logs.system_audit_logs (
            ts, ts_east8, project_key, category, action, status, 
            duration_ms, error_msg, resource_type, resource_id, 
            page, target, request_id, username, user_group, 
            unit, client_ip, user_agent, detail, created_at
        ) VALUES (
            :ts, :ts_east8, :project_key, :category, :action, :status,
            :duration_ms, :error_msg, :resource_type, :resource_id,
            :page, :target, :request_id, :username, :user_group,
            :unit, :client_ip, :user_agent, :detail, :created_at
        )
    """)

    session = SessionLocal()
    written = 0
    try:
        session.execute(insert_sql, batch_params)
        session.commit()
        written = len(batch_params)
    except Exception as e:
        session.rollback()
        logger.warning("Failed to write audit logs to PostgreSQL logs.system_audit_logs: %s", e)
    finally:
        session.close()

    return written


def query_events(
    *,
    days: int = 7,
    username: str = "",
    category: str = "",
    action: str = "",
    keyword: str = "",
    limit: int = 200,
    project_key: str = "",
    status: str = "",
) -> List[Dict[str, Any]]:
    """
    基于 PostgreSQL 索引进行高性能多维审计日志检索。
    """
    safe_limit = max(1, min(int(limit), 1000))
    safe_days = max(1, min(int(days), 90))

    where_clauses = ["ts >= NOW() - (:days || ' days')::INTERVAL"]
    params: Dict[str, Any] = {"days": safe_days, "limit": safe_limit}

    wanted_user = _normalize_text(username).lower()
    if wanted_user:
        where_clauses.append("LOWER(username) = :username")
        params["username"] = wanted_user

    wanted_category = _normalize_text(category).lower()
    if wanted_category:
        where_clauses.append("LOWER(category) = :category")
        params["category"] = wanted_category

    wanted_action = _normalize_text(action).lower()
    if wanted_action:
        where_clauses.append("LOWER(action) = :action")
        params["action"] = wanted_action

    wanted_proj = _normalize_text(project_key)
    if wanted_proj:
        where_clauses.append("project_key = :project_key")
        params["project_key"] = wanted_proj

    wanted_status = _normalize_text(status).lower()
    if wanted_status:
        where_clauses.append("LOWER(status) = :status")
        params["status"] = wanted_status

    wanted_keyword = _normalize_text(keyword)
    if wanted_keyword:
        where_clauses.append("(page ILIKE :kw OR target ILIKE :kw OR username ILIKE :kw OR detail::text ILIKE :kw)")
        params["kw"] = f"%{wanted_keyword}%"

    sql_query = f"""
        SELECT 
            id, ts, ts_east8, project_key, category, action, status,
            duration_ms, error_msg, resource_type, resource_id,
            page, target, request_id, username, user_group,
            unit, client_ip, user_agent, detail, created_at
        FROM logs.system_audit_logs
        WHERE {' AND '.join(where_clauses)}
        ORDER BY ts DESC
        LIMIT :limit
    """

    session = SessionLocal()
    rows: List[Dict[str, Any]] = []
    try:
        cursor = session.execute(text(sql_query), params)
        for row in cursor.mappings():
            item = dict(row)
            # 格式化兼容前端既有数据契约
            ts_val = item.get("ts")
            if isinstance(ts_val, datetime):
                item["ts"] = ts_val.isoformat()
            item["group"] = item.get("user_group") or ""
            # 如果 detail 在数据库为 dict/list 直接保持
            detail_val = item.get("detail")
            if isinstance(detail_val, str):
                try:
                    item["detail"] = json.loads(detail_val)
                except Exception:
                    pass
            rows.append(item)
    except Exception as e:
        logger.error("Failed to query audit logs from PostgreSQL: %s", e)
    finally:
        session.close()

    return rows


def build_stats(*, days: int = 7, project_key: str = "") -> Dict[str, Any]:
    """
    基于 PostgreSQL 进行极速实时 SQL 聚合统计。
    """
    safe_days = max(1, min(int(days), 90))
    where_base = "ts >= NOW() - (:days || ' days')::INTERVAL"
    params: Dict[str, Any] = {"days": safe_days}

    if project_key:
        where_base += " AND project_key = :project_key"
        params["project_key"] = project_key

    session = SessionLocal()
    total_count = 0
    by_category: Dict[str, int] = {}
    by_action: Dict[str, int] = {}
    by_user: Dict[str, int] = {}
    by_page: Dict[str, int] = {}

    try:
        # 1. 日志总量
        count_res = session.execute(text(f"SELECT COUNT(*) AS total FROM logs.system_audit_logs WHERE {where_base}"), params).scalar()
        total_count = int(count_res or 0)

        # 2. 分类 TOP
        cat_rows = session.execute(text(f"""
            SELECT category, COUNT(*) AS cnt 
            FROM logs.system_audit_logs 
            WHERE {where_base} 
            GROUP BY category 
            ORDER BY cnt DESC
        """), params).fetchall()
        for r in cat_rows:
            by_category[r[0] or "unknown"] = int(r[1])

        # 3. 动作 TOP
        act_rows = session.execute(text(f"""
            SELECT action, COUNT(*) AS cnt 
            FROM logs.system_audit_logs 
            WHERE {where_base} 
            GROUP BY action 
            ORDER BY cnt DESC 
            LIMIT 30
        """), params).fetchall()
        for r in act_rows:
            by_action[r[0] or "unknown"] = int(r[1])

        # 4. 用户 TOP
        user_rows = session.execute(text(f"""
            SELECT COALESCE(username, 'unknown') AS uname, COUNT(*) AS cnt 
            FROM logs.system_audit_logs 
            WHERE {where_base} 
            GROUP BY username 
            ORDER BY cnt DESC 
            LIMIT 30
        """), params).fetchall()
        for r in user_rows:
            by_user[r[0]] = int(r[1])

        # 5. 页面 TOP
        page_rows = session.execute(text(f"""
            SELECT COALESCE(page, 'unknown') AS pname, COUNT(*) AS cnt 
            FROM logs.system_audit_logs 
            WHERE {where_base} 
            GROUP BY page 
            ORDER BY cnt DESC 
            LIMIT 30
        """), params).fetchall()
        for r in page_rows:
            by_page[r[0]] = int(r[1])

    except Exception as e:
        logger.error("Failed to build audit stats from PostgreSQL: %s", e)
    finally:
        session.close()

    return {
        "total": total_count,
        "by_category": by_category,
        "by_action": by_action,
        "by_user": by_user,
        "by_page": by_page,
    }


def migrate_ndjson_files_to_db(data_dir: Optional[Any] = None) -> Dict[str, Any]:
    """
    扫描服务器磁盘上的所有历史 audit-*.ndjson 文件，将其解析并全量导入 PostgreSQL logs.system_audit_logs 表。
    支持生产环境一键迁移与分批入库。
    """
    from pathlib import Path
    from backend.config import DATA_DIRECTORY
    root_dir = Path(data_dir) if data_dir else DATA_DIRECTORY

    if not root_dir.exists():
        return {
            "ok": False,
            "error": f"数据目录不存在: {root_dir}",
            "files_count": 0,
            "total_lines": 0,
            "inserted_count": 0,
        }

    ndjson_files = sorted(list(root_dir.rglob("audit-*.ndjson")))
    if not ndjson_files:
        return {
            "ok": True,
            "message": "未在服务器数据目录中发现任何历史 audit-*.ndjson 文件",
            "files_count": 0,
            "total_lines": 0,
            "inserted_count": 0,
        }

    session = SessionLocal()
    total_lines = 0
    inserted_count = 0
    errors: List[str] = []

    insert_sql = text("""
        INSERT INTO logs.system_audit_logs (
            ts, ts_east8, project_key, category, action, status, 
            duration_ms, error_msg, resource_type, resource_id, 
            page, target, request_id, username, user_group, 
            unit, client_ip, user_agent, detail, created_at
        ) VALUES (
            :ts, :ts_east8, :project_key, :category, :action, :status,
            :duration_ms, :error_msg, :resource_type, :resource_id,
            :page, :target, :request_id, :username, :user_group,
            :unit, :client_ip, :user_agent, :detail, :created_at
        )
    """)

    batch_records: List[Dict[str, Any]] = []
    BATCH_SIZE = 500

    try:
        for file_path in ndjson_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f, 1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            item = json.loads(line_str)
                            total_lines += 1

                            ts_dt = _parse_time(item.get("ts"))
                            ts_east8_str = item.get("ts_east8") or ts_dt.astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S")

                            page_str = _normalize_text(item.get("page"))
                            target_str = _normalize_text(item.get("target"))
                            detail_obj = item.get("detail")

                            proj_key = _normalize_text(item.get("project_key")) or infer_project_key(page_str, target_str, detail_obj)
                            category_str = _normalize_text(item.get("category"), "default")
                            action_str = _normalize_text(item.get("action"), "action")
                            status_str = _normalize_text(item.get("status"), "success")
                            user_grp = _normalize_text(item.get("user_group") or item.get("group"))

                            detail_json = None
                            if detail_obj is not None:
                                detail_json = json.dumps(detail_obj, ensure_ascii=False)

                            batch_records.append({
                                "ts": ts_dt,
                                "ts_east8": ts_east8_str,
                                "project_key": proj_key,
                                "category": category_str,
                                "action": action_str,
                                "status": status_str,
                                "duration_ms": item.get("duration_ms"),
                                "error_msg": item.get("error_msg"),
                                "resource_type": item.get("resource_type"),
                                "resource_id": item.get("resource_id"),
                                "page": page_str or None,
                                "target": target_str or None,
                                "request_id": item.get("request_id"),
                                "username": _normalize_text(item.get("username")) or None,
                                "user_group": user_grp or None,
                                "unit": _normalize_text(item.get("unit")) or None,
                                "client_ip": _normalize_text(item.get("client_ip") or item.get("ip")) or None,
                                "user_agent": _normalize_text(item.get("user_agent")) or None,
                                "detail": detail_json,
                                "created_at": datetime.now(timezone.utc),
                            })

                            if len(batch_records) >= BATCH_SIZE:
                                session.execute(insert_sql, batch_records)
                                session.commit()
                                inserted_count += len(batch_records)
                                batch_records.clear()
                        except Exception as parse_err:
                            errors.append(f"{file_path.name}:{line_idx} 解析失败: {parse_err}")
            except Exception as file_err:
                errors.append(f"读取文件 {file_path.name} 失败: {file_err}")

        if batch_records:
            session.execute(insert_sql, batch_records)
            session.commit()
            inserted_count += len(batch_records)
            batch_records.clear()

    except Exception as e:
        session.rollback()
        logger.error("Migration failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "files_count": len(ndjson_files),
            "total_lines": total_lines,
            "inserted_count": inserted_count,
            "errors": errors[:10],
        }
    finally:
        session.close()

    return {
        "ok": True,
        "files_count": len(ndjson_files),
        "total_lines": total_lines,
        "inserted_count": inserted_count,
        "errors_count": len(errors),
        "message": f"成功扫描 {len(ndjson_files)} 个历史文件，共导入 {inserted_count} 条操作审计日志！",
    }


