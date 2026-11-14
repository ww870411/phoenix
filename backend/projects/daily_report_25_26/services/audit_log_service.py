# -*- coding: utf-8 -*-
"""
daily_report_25_26 项目操作审计日志服务。
提供业务操作记录写入、全网物理时间戳与 24h 操作计数统计，以及多维筛选与分页检索。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal

logger = logging.getLogger(__name__)

PROJECT_KEY = "daily_report_25_26"
EAST_8 = timezone(timedelta(hours=8))

# 行为分类定义
SUBMISSION_ACTIONS = [
    "SUBMIT_ENTRY",
    "SUBMIT_SHEET",
    "SUBMIT_CORRECTION",
    "IMPORT_COMPLAINT",
    "IMPORT_TEMPERATURE",
    "SYNC_SPOT_ELEC",
    "IMPORT_DISPATCH",
    "IMPORT_EFFICIENCY",
    "IMPORT_XLSX",
    "UPDATE_COAL_PLAN",
    "UPDATE_CONFIG",
]

WORKFLOW_ACTIONS = [
    "APPROVE_UNIT",
    "REVOKE_UNIT",
    "PUBLISH_DAILY",
    "REVOKE_PUBLISH",
    "APPROVE_CORRECTION",
    "REJECT_CORRECTION",
    "AUDIT_RESET",
]

QUERY_ACTIONS = [
    "EXPORT_DASHBOARD_PDF",
    "EXPORT_DAILY_BRIEF_PDF",
    "EXPORT_SHEET_DATA",
    "QUERY_DASHBOARD",
    "QUERY_SHEET_DATA",
    "QUERY_DATA_ANALYSIS",
    "QUERY_DISPATCH_INFO",
    "QUERY_DYNAMIC_PLAN",
    "QUERY_SPOT_ELEC",
    "QUERY_DAILY_BRIEF",
]

ALL_ACTIONS = SUBMISSION_ACTIONS + WORKFLOW_ACTIONS + QUERY_ACTIONS

# 允许前端主动上报的纯客户端导出/交互动作白名单
CLIENT_REPORTABLE_ACTIONS = frozenset({
    "EXPORT_DASHBOARD_PDF",
    "EXPORT_DAILY_BRIEF_PDF",
    "EXPORT_SHEET_DATA",
})

# 单位代号/别名到标准中文显示名的映射
UNIT_LABEL_MAP: Dict[str, str] = {
    "BeiHai": "北海热电厂",
    "beihai": "北海热电厂",
    "JinZhou": "金州热电",
    "jinzhou": "金州热电",
    "XiangHai": "香海热电厂",
    "xianghai": "香海热电厂",
    "BeiFang": "北方热电",
    "beifang": "北方热电",
    "JinPu": "金普热电",
    "jinpu": "金普热电",
    "ZhuangHe": "庄河热电",
    "zhuanghe": "庄河热电",
    "GongRe": "供热分公司",
    "gongre": "供热分公司",
    "Group": "洁净能源集团",
    "group": "洁净能源集团",
    "ZhuChengQu": "主城区",
    "zhuchengqu": "主城区",
    "ShouDian": "售电公司",
    "shoudian": "售电公司",
    "YanJiuYuan": "研究院",
    "yanjiuyuan": "研究院",
    "系统管理员": "集团全局管理",
}

# 实体/生产单位多别名映射，支持中英文、缩写与拼音双向智能模糊检索
ENTITY_ALIAS_MAP: Dict[str, List[str]] = {
    "北海": ["%北海%", "%BeiHai%", "%beihai%"],
    "金州": ["%金州%", "%JinZhou%", "%jinzhou%"],
    "香海": ["%香海%", "%XiangHai%", "%xianghai%"],
    "北方": ["%北方%", "%BeiFang%", "%beifang%"],
    "金普": ["%金普%", "%JinPu%", "%jinpu%"],
    "庄河": ["%庄河%", "%ZhuangHe%", "%zhuanghe%"],
    "供热": ["%供热%", "%GongRe%", "%gongre%", "%热网%"],
    "集团": ["%集团%", "%Group%", "%group%", "%经济运行部%", "%洁净能源%", "%系统管理员%", "%全局%"],
    "调度": ["%调度%", "%dispatch%", "%生产调度%"],
    "现货": ["%现货%", "%spot%", "%交易中心%", "%售电%", "%ShouDian%"],
    "主城区": ["%主城%", "%ZhuChengQu%", "%zhuchengqu%"],
    "售电": ["%售电%", "%ShouDian%", "%shoudian%"],
    "研究院": ["%研究院%", "%YanJiuYuan%", "%yanjiuyuan%"],
}

_table_ensured = False


def normalize_unit_label(raw_unit: Optional[str]) -> str:
    """将单位代号统一转换为前端可读中文名称。"""
    text_val = str(raw_unit or "").strip()
    if not text_val:
        return ""
    return UNIT_LABEL_MAP.get(text_val, text_val)


def extract_client_ip(request: Any) -> str:
    """从 FastAPI Request 中解析真实客户端 IP（优先反向代理头）。"""
    if request is None:
        return ""
    try:
        headers = getattr(request, "headers", None)
        if headers:
            xff = str(headers.get("x-forwarded-for") or "").strip()
            if xff:
                first_ip = xff.split(",")[0].strip()
                if first_ip:
                    return first_ip[:64]
            xri = str(headers.get("x-real-ip") or "").strip()
            if xri:
                return xri[:64]
        client = getattr(request, "client", None)
        host = getattr(client, "host", "") if client else ""
        return str(host or "").strip()[:64]
    except Exception:
        return ""


def ensure_daily_report_operation_logs_table() -> None:
    """
    自动确保 logs.daily_report_operation_logs 存在并拥有正确结构与索引。
    不再在空表时自动灌入任何虚构演示种子数据。
    """
    global _table_ensured
    if _table_ensured:
        return

    session = SessionLocal()
    try:
        session.execute(text("CREATE SCHEMA IF NOT EXISTS logs;"))
        session.execute(text("""
            CREATE SEQUENCE IF NOT EXISTS logs.daily_report_operation_logs_id_seq;
            CREATE TABLE IF NOT EXISTS logs.daily_report_operation_logs (
                id BIGINT PRIMARY KEY DEFAULT nextval('logs.daily_report_operation_logs_id_seq'),
                operator VARCHAR(64) NOT NULL,
                operator_group VARCHAR(64),
                unit VARCHAR(128),
                action_type VARCHAR(64) NOT NULL,
                action_desc TEXT NOT NULL,
                resource_id VARCHAR(128),
                before_value JSONB,
                after_value JSONB,
                client_ip VARCHAR(64),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_dr_op_logs_created_at ON logs.daily_report_operation_logs (created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_dr_op_logs_action ON logs.daily_report_operation_logs (action_type);
            CREATE INDEX IF NOT EXISTS idx_dr_op_logs_operator ON logs.daily_report_operation_logs (operator);
            CREATE INDEX IF NOT EXISTS idx_dr_op_logs_unit ON logs.daily_report_operation_logs (unit);
        """))
        session.commit()
        _table_ensured = True
    except Exception as exc:
        session.rollback()
        logger.warning(f"确保 logs.daily_report_operation_logs 表失败: {exc}")
    finally:
        session.close()


def _is_missing_operation_logs_table(exc: Exception) -> bool:
    """判断异常是否因表在运行期被外部删除或还原覆盖而缺失。"""
    msg = str(exc).lower()
    return "daily_report_operation_logs" in msg and (
        "does not exist" in msg or "undefinedtable" in msg or "undefined table" in msg
    )


def _recover_missing_operation_logs_table() -> None:
    """重置内存建表缓存并重新确保表结构存在。"""
    global _table_ensured
    _table_ensured = False
    ensure_daily_report_operation_logs_table()


def save_operation_log(
    operator: str,
    action_type: str,
    action_desc: str,
    operator_group: Optional[str] = None,
    unit: Optional[str] = None,
    resource_id: Optional[str] = None,
    before_value: Optional[Dict[str, Any]] = None,
    after_value: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """
    保存单条业务操作日志。包装在 try...except 中，确保绝对不阻断主业务流程。
    """
    ensure_daily_report_operation_logs_table()

    def _serialize_default(obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj) if (obj % 1 > 0) else int(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    before_json = json.dumps(before_value, default=_serialize_default, ensure_ascii=False) if before_value is not None else None
    after_json = json.dumps(after_value, default=_serialize_default, ensure_ascii=False) if after_value is not None else None
    normalized_unit = normalize_unit_label(unit)

    sql = text("""
        INSERT INTO logs.daily_report_operation_logs (
            operator, operator_group, unit, action_type, action_desc,
            resource_id, before_value, after_value, client_ip, created_at
        ) VALUES (
            :operator, :operator_group, :unit, :action_type, :action_desc,
            :resource_id, :before_value, :after_value, :client_ip, COALESCE(:created_at, NOW())
        )
    """)

    insert_params = {
        "operator": operator or "unknown",
        "operator_group": operator_group or "",
        "unit": normalized_unit,
        "action_type": action_type or "ACTION",
        "action_desc": action_desc or "",
        "resource_id": resource_id or None,
        "before_value": before_json,
        "after_value": after_json,
        "client_ip": client_ip or "",
        "created_at": created_at,
    }

    for attempt in range(2):
        session = SessionLocal()
        try:
            session.execute(sql, insert_params)
            session.commit()
            return
        except Exception as exc:
            session.rollback()
            if attempt == 0 and _is_missing_operation_logs_table(exc):
                _recover_missing_operation_logs_table()
                continue
            logger.error(f"[daily_report_operation_log] 写入日志失败: {exc}")
            return
        finally:
            session.close()


def log_session_operation(
    session: Any,
    action_type: str,
    action_desc: str,
    *,
    request: Any = None,
    unit: Optional[str] = None,
    resource_id: Optional[str] = None,
    before_value: Optional[Dict[str, Any]] = None,
    after_value: Optional[Dict[str, Any]] = None,
    fallback_operator: str = "system",
) -> None:
    """
    统一从 AuthSession 与 FastAPI Request 提取操作人、角色组、单位和来源 IP，写入业务操作日志。
    失败仅告警，不影响主业务返回。
    """
    try:
        operator = str(getattr(session, "username", "") or "").strip() or fallback_operator
        operator_group = str(getattr(session, "group", "") or "").strip()
        raw_unit = unit if unit is not None else getattr(session, "unit", "")
        client_ip = extract_client_ip(request)
        save_operation_log(
            operator=operator,
            operator_group=operator_group,
            unit=raw_unit,
            action_type=action_type,
            action_desc=action_desc,
            resource_id=resource_id,
            before_value=before_value,
            after_value=after_value,
            client_ip=client_ip,
        )
    except Exception as exc:
        logger.warning(f"[daily_report_operation_log] 记录会话业务日志失败（已忽略）: {exc}")


SYNTHETIC_SEED_IPS = (
    "10.12.1.8",
    "10.12.3.90",
    "10.12.5.101",
    "192.168.10.45",
    "192.168.12.18",
    "192.168.15.22",
    "192.168.18.55",
    "192.168.20.12",
    "192.168.25.66",
)


def purge_synthetic_seed_logs() -> int:
    """
    清理历史版本自动生成的虚构种子日志（保留所有真实业务记录）。
    """
    ensure_daily_report_operation_logs_table()
    session = SessionLocal()
    try:
        result = session.execute(text("""
            DELETE FROM logs.daily_report_operation_logs
            WHERE after_value IS NULL
              AND before_value IS NULL
              AND (
                client_ip = ANY(:seed_ips)
                OR (
                    client_ip = '172.19.0.4'
                    AND operator = 'ww870411'
                    AND resource_id IN ('biz_date:2026-11-09', 'dashboard:overview')
                    AND action_desc IN (
                        '更新生产日报基准运行业务日期为【2026-11-09】并完成全局大盘时间对齐',
                        '调阅洁净能源集团生产日报数字化决策数据看板（全网 16 张核心分析卡片）'
                    )
                )
              )
        """), {"seed_ips": list(SYNTHETIC_SEED_IPS)})
        session.commit()
        return int(result.rowcount or 0)
    except Exception as exc:
        session.rollback()
        logger.error(f"清理虚构种子日志失败: {exc}")
        raise
    finally:
        session.close()


def _map_system_audit_click(row: Any) -> Optional[Dict[str, Any]]:
    """将 logs.system_audit_logs 中的真实前端交互记录映射为业务操作记录。"""
    target = str(row.target or "").strip()
    page = str(row.page or "").strip()
    unit_label = normalize_unit_label(row.unit)

    if target == "下载PDF":
        return {
            "action_type": "EXPORT_DASHBOARD_PDF",
            "action_desc": "导出洁净能源集团生产日报数据看板标准 PDF（历史埋点回填）",
            "resource_id": "dashboard:pdf",
        }
    if target == "导出 PDF":
        return {
            "action_type": "EXPORT_DAILY_BRIEF_PDF",
            "action_desc": "导出每日生产状况内参简报 PDF（历史埋点回填）",
            "resource_id": "daily_brief:pdf",
        }
    if target == "导出Excel":
        return {
            "action_type": "EXPORT_SHEET_DATA",
            "action_desc": "导出生产日报展示表 Excel 工作簿（历史埋点回填）",
            "resource_id": "data_show:excel",
        }
    if target == "📷 导出截图":
        return {
            "action_type": "EXPORT_SHEET_DATA",
            "action_desc": "导出生产日报展示表高清长截图（历史埋点回填）",
            "resource_id": "data_show:screenshot",
        }
    if target == "📥 导出数据 (Excel/CSV)":
        return {
            "action_type": "EXPORT_SHEET_DATA",
            "action_desc": "导出电力现货市场交易数据（历史埋点回填）",
            "resource_id": "spot_elec:export",
        }
    if target in ("提交", "仅提交当前表") or target.startswith("一并提交"):
        sheet_key = ""
        marker = "/data_entry/sheets/"
        if marker in page:
            sheet_key = page.split(marker, 1)[1].split("?", 1)[0].strip("/")
        suffix = f"（{sheet_key}）" if sheet_key else ""
        return {
            "action_type": "SUBMIT_ENTRY",
            "action_desc": f"填报提交{unit_label or '单位'}生产日报数据{suffix}（历史埋点回填）",
            "resource_id": f"sheet:{sheet_key}" if sheet_key else "sheet:submit",
        }
    if target == "批准":
        return {
            "action_type": "APPROVE_UNIT",
            "action_desc": f"批准通过{unit_label or '单位'}生产日报数据（历史埋点回填）",
            "resource_id": "workflow:approve",
        }
    if target == "确认覆盖入库" and "/dashboard" in page:
        return {
            "action_type": "IMPORT_TEMPERATURE",
            "action_desc": "在数据看板手动确认导入近端逐小时气温数据（历史埋点回填）",
            "resource_id": "weather:near",
        }
    if target == "⛅ 导入35天预报":
        return {
            "action_type": "IMPORT_TEMPERATURE",
            "action_desc": "手动导入 35 天集合气温预报数据（历史埋点回填）",
            "resource_id": "weather:far",
        }
    if target == "⚡ 自动拉取投诉量":
        return {
            "action_type": "IMPORT_COMPLAINT",
            "action_desc": "从金山文档拉取 12345 投诉统计明细（历史埋点回填）",
            "resource_id": "kdocs:complaint",
        }
    if target == "确认入库" and "/spot_electricity" in page:
        return {
            "action_type": "SYNC_SPOT_ELEC",
            "action_desc": "手动确认导入电力现货市场/结算数据（历史埋点回填）",
            "resource_id": "spot_elec:confirm",
        }
    if target == "💾 一键保存入库" and "/dispatch" in page:
        return {
            "action_type": "IMPORT_DISPATCH",
            "action_desc": "保存生产调度日报提取结果入库（历史埋点回填）",
            "resource_id": "dispatch:save",
        }
    if target == "📁 上传能效分析表":
        return {
            "action_type": "IMPORT_EFFICIENCY",
            "action_desc": f"上传解析{unit_label or '单位'}能效分析表 Excel（历史埋点回填）",
            "resource_id": "efficiency:upload",
        }
    if target == "生成分析结果":
        return {
            "action_type": "QUERY_DATA_ANALYSIS",
            "action_desc": "执行生产多维数据组合分析查询（历史埋点回填）",
            "resource_id": "data_analysis:query",
        }
    if target == "确认提交申请":
        return {
            "action_type": "SUBMIT_CORRECTION",
            "action_desc": f"提交{unit_label or '单位'}日报数据修正申请（历史埋点回填）",
            "resource_id": "correction:create",
        }
    if target in ("💾 保存自动获取设置", "💾 保存配置", "💾 保存持久化配置"):
        return {
            "action_type": "UPDATE_CONFIG",
            "action_desc": f"修改系统运行或自动导入配置（{target}，历史埋点回填）",
            "resource_id": "config:update",
        }
    return None


def backfill_from_system_audit_logs(days: int = 30) -> int:
    """
    从 logs.system_audit_logs 中提取近 N 天真实已发生的 daily_report_25_26 核心业务操作回填至本表。
    通过 after_value->>'source_audit_id' 实现幂等，重复调用不会产生重复记录。
    """
    ensure_daily_report_operation_logs_table()
    session = SessionLocal()
    inserted = 0
    try:
        existing_ids = {
            str(r[0])
            for r in session.execute(text("""
                SELECT after_value->>'source_audit_id'
                FROM logs.daily_report_operation_logs
                WHERE after_value ? 'source_audit_id'
            """)).fetchall()
            if r[0] is not None
        }

        rows = session.execute(text("""
            SELECT id, ts, username, user_group, unit, page, target, client_ip
            FROM logs.system_audit_logs
            WHERE project_key = 'daily_report_25_26'
              AND category = 'ui'
              AND action = 'click'
              AND ts >= NOW() - make_interval(days => :days)
            ORDER BY ts ASC
        """), {"days": int(max(1, days))}).fetchall()

        last_seen: Dict[tuple, datetime] = {}
        for row in rows:
            mapped = _map_system_audit_click(row)
            if not mapped:
                continue
            dedupe_key = (str(row.username or ""), mapped["action_type"], mapped["resource_id"])
            audit_id = str(row.id)
            if audit_id in existing_ids:
                last_seen[dedupe_key] = row.ts
                continue

            # 2 秒内同一人同页同动作仅保留一条，过滤误双击抖动
            prev_ts = last_seen.get(dedupe_key)
            if prev_ts is not None and abs((row.ts - prev_ts).total_seconds()) < 2:
                continue
            last_seen[dedupe_key] = row.ts

            after_payload = json.dumps(
                {
                    "source": "system_audit_logs_backfill",
                    "source_audit_id": audit_id,
                    "original_target": str(row.target or ""),
                },
                ensure_ascii=False,
            )
            session.execute(text("""
                INSERT INTO logs.daily_report_operation_logs (
                    operator, operator_group, unit, action_type, action_desc,
                    resource_id, before_value, after_value, client_ip, created_at
                ) VALUES (
                    :operator, :operator_group, :unit, :action_type, :action_desc,
                    :resource_id, NULL, :after_value, :client_ip, :created_at
                )
            """), {
                "operator": str(row.username or "unknown"),
                "operator_group": str(row.user_group or ""),
                "unit": normalize_unit_label(row.unit),
                "action_type": mapped["action_type"],
                "action_desc": mapped["action_desc"],
                "resource_id": mapped["resource_id"],
                "after_value": after_payload,
                "client_ip": str(row.client_ip or ""),
                "created_at": row.ts,
            })
            inserted += 1

        session.commit()
        return inserted
    except Exception as exc:
        session.rollback()
        logger.error(f"回填真实业务操作记录失败: {exc}")
        raise
    finally:
        session.close()


def query_submission_logs(
    category: Optional[str] = None,
    entity_type: Optional[str] = None,
    action_type: Optional[str] = None,
    operator: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    多维检索业务操作记录，并返回全网最新操作时间戳以及 24h 内统计指标。
    """
    ensure_daily_report_operation_logs_table()

    conditions: List[str] = []
    params: Dict[str, Any] = {}

    # 1. 大类约束 (category)
    if category == "submission":
        conditions.append("action_type = ANY(:cat_actions)")
        params["cat_actions"] = SUBMISSION_ACTIONS
    elif category == "workflow":
        conditions.append("action_type = ANY(:cat_actions)")
        params["cat_actions"] = WORKFLOW_ACTIONS
    elif category == "query":
        conditions.append("action_type = ANY(:cat_actions)")
        params["cat_actions"] = QUERY_ACTIONS

    # 2. 生产单位与主体约束 (entity_type)，结合别名映射表实现智能模糊多重检索
    if entity_type:
        clean_key = entity_type.strip()
        patterns = ENTITY_ALIAS_MAP.get(clean_key, [f"%{clean_key}%"])
        clauses = []
        for i, pat in enumerate(patterns):
            p_key = f"ent_pat_{i}"
            clauses.append(f"(unit ILIKE :{p_key} OR resource_id ILIKE :{p_key} OR action_desc ILIKE :{p_key})")
            params[p_key] = pat
        conditions.append(f"({' OR '.join(clauses)})")

    # 3. 具体 action_type
    if action_type:
        conditions.append("action_type = :specific_action_type")
        params["specific_action_type"] = action_type

    # 4. 操作人 / 账号
    if operator:
        conditions.append("operator ILIKE :operator_pattern")
        params["operator_pattern"] = f"%{operator}%"

    # 5. 时间范围
    if start_date:
        conditions.append("created_at >= :start_ts")
        params["start_ts"] = f"{start_date} 00:00:00+08"

    if end_date:
        conditions.append("created_at <= :end_ts")
        params["end_ts"] = f"{end_date} 23:59:59+08"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    for attempt in range(2):
        session = SessionLocal()
        try:
            # 总数（若表在运行期被外部删除或还原覆盖，自动重建并重试一次）
            count_sql = text(f"SELECT COUNT(*) FROM logs.daily_report_operation_logs {where_clause}")
            total = session.execute(count_sql, params).scalar() or 0
            if total == 0 and not conditions:
                session.rollback()
                try:
                    if backfill_from_system_audit_logs(days=30) > 0:
                        total = session.execute(count_sql, params).scalar() or 0
                except Exception as exc:
                    logger.warning(f"[daily_report_operation_log] 空表自动回填真实历史失败（已忽略）: {exc}")

            # 明细列表
            list_sql = text(f"""
                SELECT id, operator, operator_group, unit, action_type, action_desc,
                       resource_id, before_value, after_value, client_ip, created_at
                FROM logs.daily_report_operation_logs
                {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            list_params = {**params, "limit": limit, "offset": offset}
            rows = session.execute(list_sql, list_params).fetchall()

            logs: List[Dict[str, Any]] = []
            for r in rows:
                created_dt = r[10]
                if isinstance(created_dt, datetime):
                    created_iso = created_dt.isoformat()
                else:
                    created_iso = str(created_dt) if created_dt else None

                logs.append({
                    "id": r[0],
                    "operator": r[1],
                    "operator_group": r[2],
                    "unit": r[3],
                    "action_type": r[4],
                    "action_desc": r[5],
                    "resource_id": r[6],
                    "before_value": r[7],
                    "after_value": r[8],
                    "client_ip": r[9],
                    "created_at": created_iso,
                })

            # 最新操作物理时间
            latest_submitted_sql = text("SELECT MAX(created_at) FROM logs.daily_report_operation_logs;")
            latest_submitted_dt = session.execute(latest_submitted_sql).scalar()
            latest_submitted_at = latest_submitted_dt.isoformat() if latest_submitted_dt else None

            # 24h 操作计数看板
            recent_24h_sql = text("""
                SELECT COUNT(*) FROM logs.daily_report_operation_logs
                WHERE created_at >= NOW() - INTERVAL '24 HOURS';
            """)
            recent_24h_count = session.execute(recent_24h_sql).scalar() or 0

            submission_24h_sql = text("""
                SELECT COUNT(*) FROM logs.daily_report_operation_logs
                WHERE action_type = ANY(:sub_actions)
                  AND created_at >= NOW() - INTERVAL '24 HOURS';
            """)
            submission_24h_count = session.execute(submission_24h_sql, {"sub_actions": SUBMISSION_ACTIONS}).scalar() or 0

            workflow_24h_sql = text("""
                SELECT COUNT(*) FROM logs.daily_report_operation_logs
                WHERE action_type = ANY(:wf_actions)
                  AND created_at >= NOW() - INTERVAL '24 HOURS';
            """)
            workflow_24h_count = session.execute(workflow_24h_sql, {"wf_actions": WORKFLOW_ACTIONS}).scalar() or 0

            query_24h_sql = text("""
                SELECT COUNT(*) FROM logs.daily_report_operation_logs
                WHERE action_type = ANY(:q_actions)
                  AND created_at >= NOW() - INTERVAL '24 HOURS';
            """)
            query_24h_count = session.execute(query_24h_sql, {"q_actions": QUERY_ACTIONS}).scalar() or 0

            return {
                "total": total,
                "latest_submitted_at": latest_submitted_at,
                "recent_24h_count": recent_24h_count,
                "submission_24h_count": submission_24h_count,
                "workflow_24h_count": workflow_24h_count,
                "query_24h_count": query_24h_count,
                "logs": logs,
            }
        except Exception as exc:
            session.rollback()
            if attempt == 0 and _is_missing_operation_logs_table(exc):
                _recover_missing_operation_logs_table()
                continue
            raise
        finally:
            session.close()


def log_sheet_submission(
    session: Any,
    request: Any,
    sheet_key: str,
    payload: Dict[str, Any],
    *,
    unit_name: str = "",
    sheet_name: str = "",
    inserted_count: int = 0,
) -> None:
    """统一记录表单提交（日常指标、供热分中心明细、煤炭库存、常量表）。"""
    biz_date = str(payload.get("biz_date") or "").strip()
    status_val = str(payload.get("status") or "submit").strip() or "submit"
    resolved_unit = normalize_unit_label(
        unit_name or payload.get("unit_name") or payload.get("unit_id") or getattr(session, "unit", "")
    )
    resolved_sheet = str(sheet_name or payload.get("sheet_name") or sheet_key).strip()
    action_label = "暂存草稿" if status_val == "draft" else "填报提交"
    date_part = f" {biz_date}" if biz_date else ""
    log_session_operation(
        session,
        "SUBMIT_ENTRY",
        f"{action_label}【{resolved_unit or '单位'}】{resolved_sheet}{date_part}（写入 {inserted_count} 项）",
        request=request,
        unit=resolved_unit,
        resource_id=f"{sheet_key}:{biz_date or 'latest'}",
        after_value={
            "sheet_key": sheet_key,
            "sheet_name": resolved_sheet,
            "biz_date": biz_date,
            "status": status_val,
            "inserted": inserted_count,
        },
    )


def log_efficiency_import(
    session: Any,
    request: Any,
    *,
    unit_label: str,
    sheet_tag: str,
    filename: str,
    biz_date: str,
    res: Any,
) -> None:
    """统一记录能效分析表 Excel 上传解析操作（仅解析成功时写入）。"""
    if not isinstance(res, dict) or not res.get("ok"):
        return
    log_session_operation(
        session,
        "IMPORT_EFFICIENCY",
        f"上传解析【{unit_label}】{biz_date} 能效分析表（{filename or sheet_tag}）",
        request=request,
        unit=unit_label,
        resource_id=f"{sheet_tag}:{biz_date}",
        after_value={"filename": filename, "biz_date": biz_date},
    )


def log_data_analysis_query(
    session: Any,
    request: Any,
    *,
    unit_key: str,
    analysis_mode: str,
    start_date: str,
    end_date: Optional[str],
    metrics_count: int,
    request_ai_report: bool = False,
) -> None:
    """记录用户在数据分析页主动发起的多维数据查询操作。"""
    unit_label = normalize_unit_label(unit_key)
    span = f"{start_date} ~ {end_date}" if end_date and end_date != start_date else start_date
    ai_note = "（含 AI 智能解读）" if request_ai_report else ""
    log_session_operation(
        session,
        "QUERY_DATA_ANALYSIS",
        f"执行生产多维数据分析查询：口径【{unit_label or unit_key}】，模式 {analysis_mode}，日期 {span}，指标 {metrics_count} 项{ai_note}",
        request=request,
        unit=unit_label,
        resource_id=f"data_analysis:{unit_key}:{start_date}",
        after_value={
            "unit_key": unit_key,
            "analysis_mode": analysis_mode,
            "start_date": start_date,
            "end_date": end_date,
            "metrics_count": metrics_count,
            "request_ai_report": request_ai_report,
        },
    )
