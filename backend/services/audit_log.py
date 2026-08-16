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


_table_ensured = False

def ensure_audit_log_table() -> None:
    """
    自动自愈/创建 logs.system_audit_logs 数据表与全部列、索引。
    防止生产环境中因表结构缺失某些字段而产生 UndefinedColumn 错误。
    """
    global _table_ensured
    session = SessionLocal()
    try:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS logs;"))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS logs.system_audit_logs (
                id BIGSERIAL PRIMARY KEY,
                ts TIMESTAMPTZ NOT NULL,
                ts_east8 VARCHAR(32),
                project_key VARCHAR(64) DEFAULT 'global',
                category VARCHAR(64) NOT NULL DEFAULT 'default',
                action VARCHAR(64) NOT NULL DEFAULT 'action',
                status VARCHAR(32) DEFAULT 'success',
                duration_ms INTEGER,
                error_msg TEXT,
                resource_type VARCHAR(64),
                resource_id VARCHAR(128),
                page TEXT,
                target TEXT,
                request_id VARCHAR(64),
                username VARCHAR(64),
                user_group VARCHAR(64),
                unit VARCHAR(128),
                client_ip VARCHAR(64),
                user_agent TEXT,
                detail JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """))
        columns_to_add = [
            ("project_key", "VARCHAR(64) DEFAULT 'global'"),
            ("ts_east8", "VARCHAR(32)"),
            ("status", "VARCHAR(32) DEFAULT 'success'"),
            ("duration_ms", "INTEGER"),
            ("error_msg", "TEXT"),
            ("resource_type", "VARCHAR(64)"),
            ("resource_id", "VARCHAR(128)"),
            ("page", "TEXT"),
            ("target", "TEXT"),
            ("request_id", "VARCHAR(64)"),
            ("username", "VARCHAR(64)"),
            ("user_group", "VARCHAR(64)"),
            ("unit", "VARCHAR(128)"),
            ("client_ip", "VARCHAR(64)"),
            ("user_agent", "TEXT"),
            ("detail", "JSONB"),
            ("created_at", "TIMESTAMPTZ DEFAULT NOW()"),
        ]
        for col_name, col_type in columns_to_add:
            try:
                session.execute(text(f"ALTER TABLE logs.system_audit_logs ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
            except Exception:
                pass
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_ts ON logs.system_audit_logs (ts DESC);"))
        session.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_project_key ON logs.system_audit_logs (project_key);"))
        session.commit()
        _table_ensured = True
    except Exception as e:
        session.rollback()
        logger.warning("ensure_audit_log_table exception: %s", e)
    finally:
        session.close()


def append_events(events: Iterable[Dict[str, Any]]) -> int:
    """
    将操作审计日志批量写入 PostgreSQL logs.system_audit_logs 数据表。
    具备 Fail-Safe 安全保护：写日志异常绝不阻塞主业务流程，并自动执行表自愈。
    """
    global _table_ensured
    if not _table_ensured:
        ensure_audit_log_table()

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
            "error_msg": _normalize_text(item.get("error_msg")) or None,
            "resource_type": _normalize_text(item.get("resource_type")) or None,
            "resource_id": _normalize_text(item.get("resource_id")) or None,
            "page": page_str or None,
            "target": target_str or None,
            "request_id": _normalize_text(item.get("request_id")) or None,
            "username": _normalize_text(item.get("username")) or None,
            "user_group": user_grp or None,
            "unit": _normalize_text(item.get("unit")) or None,
            "client_ip": _normalize_text(item.get("client_ip") or item.get("ip")) or None,
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
    try:
        session.execute(insert_sql, batch_params)
        session.commit()
        return len(batch_params)
    except Exception as e:
        session.rollback()
        # 若因表结构缺失列，执行一次自愈重试
        err_str = str(e).lower()
        if "undefinedcolumn" in err_str or "does not exist" in err_str:
            ensure_audit_log_table()
            try:
                session.execute(insert_sql, batch_params)
                session.commit()
                return len(batch_params)
            except Exception as retry_err:
                session.rollback()
                logger.warning("Retry append_events failed: %s", retry_err)
        logger.warning("Failed to write audit logs to PostgreSQL logs.system_audit_logs: %s", e)
        return 0
    finally:
        session.close()


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
    global _table_ensured
    if not _table_ensured:
        ensure_audit_log_table()

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
    global _table_ensured
    if not _table_ensured:
        ensure_audit_log_table()

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


def inspect_ndjson_files(data_dir: Optional[Any] = None) -> Dict[str, Any]:
    """
    预检服务器磁盘上的所有历史 audit-*.ndjson 文件清单与元数据。
    毫秒级返回，不执行任何写库操作。
    """
    from pathlib import Path
    from backend.config import DATA_DIRECTORY
    root_dir = Path(data_dir) if data_dir else DATA_DIRECTORY

    if not root_dir.exists():
        return {
            "ok": False,
            "error": f"数据目录不存在: {root_dir}",
            "files_count": 0,
            "total_estimated_lines": 0,
            "files": [],
            "db_current_count": 0,
        }

    ndjson_files = sorted(list(root_dir.rglob("audit-*.ndjson")))
    files_detail = []
    total_lines_est = 0

    for file_path in ndjson_files:
        try:
            size_kb = round(file_path.stat().st_size / 1024, 1)
            rel_path = str(file_path.relative_to(root_dir)).replace("\\", "/")
            # 快速计算行数
            lines_cnt = 0
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip():
                        lines_cnt += 1
            total_lines_est += lines_cnt
            files_detail.append({
                "file_name": file_path.name,
                "rel_path": rel_path,
                "size_kb": size_kb,
                "lines_count": lines_cnt,
                "mtime": datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc).astimezone(EAST_8).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "pending",
            })
        except Exception as e:
            files_detail.append({
                "file_name": file_path.name,
                "rel_path": str(file_path),
                "size_kb": 0,
                "lines_count": 0,
                "mtime": "-",
                "status": f"error: {e}",
            })

    # 查询当前数据库现有日志条数
    db_count = 0
    try:
        session = SessionLocal()
        try:
            r = session.execute(text("SELECT COUNT(*) FROM logs.system_audit_logs")).scalar()
            db_count = int(r or 0)
        finally:
            session.close()
    except Exception as db_err:
        logger.warning("Failed to query db current count: %s", db_err)

    return {
        "ok": True,
        "files_count": len(files_detail),
        "total_estimated_lines": total_lines_est,
        "files": files_detail,
        "db_current_count": db_count,
    }


def migrate_ndjson_files_to_db(data_dir: Optional[Any] = None) -> Dict[str, Any]:
    """
    扫描服务器磁盘上的所有历史 audit-*.ndjson 文件，将其解析并全量导入 PostgreSQL logs.system_audit_logs 表。
    支持生产环境一键迁移与分批入库，并返回每个文件的详细执行明细。
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
            "files": [],
        }

    ndjson_files = sorted(list(root_dir.rglob("audit-*.ndjson")))
    if not ndjson_files:
        return {
            "ok": True,
            "message": "未在服务器数据目录中发现任何历史 audit-*.ndjson 文件",
            "files_count": 0,
            "total_lines": 0,
            "inserted_count": 0,
            "files": [],
        }

    session = SessionLocal()
    total_lines = 0
    inserted_count = 0
    file_results: List[Dict[str, Any]] = []
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
            file_inserted = 0
            file_lines = 0
            file_error = ""
            rel_path = str(file_path.relative_to(root_dir)).replace("\\", "/")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_idx, line in enumerate(f, 1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        try:
                            item = json.loads(line_str)
                            file_lines += 1
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
                                file_inserted += len(batch_records)
                                batch_records.clear()
                        except Exception as parse_err:
                            errors.append(f"{file_path.name}:{line_idx} 解析失败: {parse_err}")
                
                # 提交当前文件剩余未写记录
                if batch_records:
                    session.execute(insert_sql, batch_records)
                    session.commit()
                    inserted_count += len(batch_records)
                    file_inserted += len(batch_records)
                    batch_records.clear()

                file_results.append({
                    "file_name": file_path.name,
                    "rel_path": rel_path,
                    "lines_count": file_lines,
                    "inserted_count": file_inserted,
                    "status": "success",
                })
            except Exception as file_err:
                file_error = str(file_err)
                errors.append(f"读取文件 {file_path.name} 失败: {file_err}")
                file_results.append({
                    "file_name": file_path.name,
                    "rel_path": rel_path,
                    "lines_count": file_lines,
                    "inserted_count": file_inserted,
                    "status": "error",
                    "error": file_error,
                })

    except Exception as e:
        session.rollback()
        logger.error("Migration failed: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "files_count": len(ndjson_files),
            "total_lines": total_lines,
            "inserted_count": inserted_count,
            "files": file_results,
            "errors": errors[:10],
        }
    finally:
        session.close()

    # 查询迁移后数据库最新总量
    db_final_count = inserted_count
    try:
        session_chk = SessionLocal()
        try:
            r = session_chk.execute(text("SELECT COUNT(*) FROM logs.system_audit_logs")).scalar()
            db_final_count = int(r or 0)
        finally:
            session_chk.close()
    except Exception:
        pass

    return {
        "ok": True,
        "files_count": len(ndjson_files),
        "total_lines": total_lines,
        "inserted_count": inserted_count,
        "db_final_count": db_final_count,
        "files": file_results,
        "errors_count": len(errors),
        "message": f"成功扫描 {len(ndjson_files)} 个历史文件，共导入 {inserted_count} 条操作审计日志！",
    }



