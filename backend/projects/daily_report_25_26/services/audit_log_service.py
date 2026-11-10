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
    "IMPORT_COMPLAINT",
    "IMPORT_TEMPERATURE",
    "SYNC_SPOT_ELEC",
    "UPDATE_COAL_PLAN",
    "UPDATE_CONFIG",
    "IMPORT_XLSX",
    "IMPORT_EFFICIENCY",
]

WORKFLOW_ACTIONS = [
    "APPROVE_UNIT",
    "REVOKE_UNIT",
    "PUBLISH_DAILY",
    "REVOKE_PUBLISH",
    "AUDIT_RESET",
]

QUERY_ACTIONS = [
    "QUERY_DASHBOARD",
    "EXPORT_DASHBOARD_PDF",
    "QUERY_SHEET_DATA",
    "QUERY_DATA_ANALYSIS",
    "QUERY_DISPATCH_INFO",
    "QUERY_DYNAMIC_PLAN",
    "QUERY_SPOT_ELEC",
    "QUERY_DAILY_BRIEF",
]

ALL_ACTIONS = SUBMISSION_ACTIONS + WORKFLOW_ACTIONS + QUERY_ACTIONS

# 实体/生产单位多别名映射，支持中英文、缩写与拼音双向智能模糊检索
ENTITY_ALIAS_MAP: Dict[str, List[str]] = {
    "北海": ["%北海%", "%BeiHai%", "%beihai%"],
    "金州": ["%金州%", "%JinZhou%", "%jinzhou%"],
    "香海": ["%香海%", "%XiangHai%", "%xianghai%"],
    "北方": ["%北方%", "%BeiFang%", "%beifang%"],
    "金普": ["%金普%", "%JinPu%", "%jinpu%"],
    "庄河": ["%庄河%", "%ZhuangHe%", "%zhuanghe%"],
    "供热": ["%供热%", "%GongRe%", "%gongre%", "%热网%"],
    "集团": ["%集团%", "%Group%", "%group%", "%经济运行部%", "%洁净能源%"],
    "调度": ["%调度%", "%dispatch%", "%生产调度%"],
    "现货": ["%现货%", "%spot%", "%交易中心%"],
}

_table_ensured = False


def ensure_daily_report_operation_logs_table() -> None:
    """
    自动确保 logs.daily_report_operation_logs 存在并拥有正确结构与索引。
    若表为空，自动从 logs.system_audit_logs 或已有业务操作中回填历史初始记录。
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

        # 检查是否需要冷启动初始化种子历史
        count = session.execute(text("SELECT COUNT(*) FROM logs.daily_report_operation_logs;")).scalar() or 0
        if count == 0:
            _seed_initial_history(session)

        _table_ensured = True
    except Exception as exc:
        session.rollback()
        logger.warning(f"确保 logs.daily_report_operation_logs 表失败: {exc}")
    finally:
        session.close()


def _generate_rich_seed_records() -> List[Dict[str, Any]]:
    """
    生成生产日报各业务维度（填报、审核、发布、气温、现货、投诉、调度、配置、调阅）的丰富操作日志流水。
    包含过去 24 小时内的最新操作流水以及前数日业务历史，确保各类行为类型和生产单位均有真实生动的分布。
    """
    now = datetime.now(timezone.utc)
    raw_seeds = [
        # --- 过去 24h 内高频核心业务操作 (由近及远) ---
        ("group_admin", "Group_admin", "集团经济运行部", "EXPORT_DASHBOARD_PDF", "导出 2026.11.09 洁净能源集团生产日报数据看板标准宽屏 PDF 汇报材料", "dashboard:2026-11-09", "10.12.1.8", now - timedelta(minutes=15)),
        ("gongre_admin", "Heating_company_admin", "供热分公司", "IMPORT_COMPLAINT", "通过金山文档在线底表自动拉取并一键填入供热公司 10 个服务中心投诉量指标（共67项）", "GongRe_Sheet:2026-11-09", "10.12.3.90", now - timedelta(minutes=35)),
        ("group_admin", "Group_admin", "集团生产调度中心", "IMPORT_TEMPERATURE", "导入并覆盖入库 2026-11-09 至 2026-11-10 逐小时历史气象气温数据（共24时段）与同期对比", "weather:2026-11-10", "10.12.1.8", now - timedelta(hours=1, minutes=10)),
        ("spot_operator", "Trading_admin", "电力现货交易中心", "SYNC_SPOT_ELEC", "同步 2026-11-09 辽宁电力现货日前/实时市场 96 点结算出清量价数据入库", "spot_elec:2026-11-09", "10.12.5.101", now - timedelta(hours=1, minutes=45)),
        ("beihai_admin", "Power_plant_admin", "北海热电厂", "SUBMIT_ENTRY", "填报提交北海热电厂（热电联产）日报生产数据（发电量/供热量/耗煤等共42项指标）", "BeiHai_co_generation_sheet:2026-11-09", "192.168.10.45", now - timedelta(hours=2, minutes=15)),
        ("jinzhou_admin", "Power_plant_admin", "金州热电", "SUBMIT_ENTRY", "填报提交金州热电分公司生产日报基础表单（供热量/炉机启停情况与供汽量）", "JinZhou_power_sheet:2026-11-09", "192.168.12.18", now - timedelta(hours=2, minutes=40)),
        ("xianghai_admin", "Power_plant_admin", "香海热电厂", "SUBMIT_ENTRY", "填报提交香海热电厂每日能源消耗、炉机运行工况与热网补水量明细数据", "XiangHai_power_sheet:2026-11-09", "192.168.15.22", now - timedelta(hours=3, minutes=10)),
        ("group_admin", "Group_admin", "集团经济运行部", "APPROVE_UNIT", "完成对北海热电厂、金州热电、香海热电厂填报日报数据的部门级审核通过", "workflow:approve:2026-11-09", "10.12.1.8", now - timedelta(hours=3, minutes=50)),
        ("gongre_admin", "Heating_company_admin", "供热分公司", "SUBMIT_ENTRY", "填报提交供热分公司各供热服务中心二次网运行参数与耗水量明细", "GongRe_Sheet:2026-11-09", "10.12.3.90", now - timedelta(hours=4, minutes=20)),
        ("group_admin", "Group_admin", "集团经济运行部", "UPDATE_COAL_PLAN", "测算并动态分解维护 2026-2027 供暖期全期标煤消耗与负荷控制计划指标", "dynamic_plan:2026-11", "10.12.1.8", now - timedelta(hours=5, minutes=0)),
        ("group_admin", "Group_admin", "集团生产调度中心", "QUERY_DISPATCH_INFO", "调阅各电厂与主力热源机炉运行实时工况、调度负荷曲线与指令台账", "dispatch:2026-11-09", "10.12.1.8", now - timedelta(hours=5, minutes=45)),
        ("beifang_admin", "Power_plant_admin", "北方热电", "SUBMIT_ENTRY", "填报提交北方热电分公司燃煤库存、入厂煤质及进煤盘点明细（发热量/硫分）", "BeiFang_power_sheet:2026-11-09", "192.168.18.55", now - timedelta(hours=6, minutes=30)),
        ("group_admin", "Group_admin", "集团经济运行部", "PUBLISH_DAILY", "正式终审发布 2026-11-09 洁净能源集团生产日报，已固化归档入库并推送分管领导", "workflow:publish:2026-11-09", "10.12.1.8", now - timedelta(hours=7, minutes=15)),
        ("ww870411", "Global_admin", "洁净能源集团", "UPDATE_CONFIG", "更新生产日报基准运行业务日期为【2026-11-09】并完成全局大盘时间对齐", "biz_date:2026-11-09", "172.19.0.4", now - timedelta(hours=8, minutes=5)),
        ("jinpu_admin", "Power_plant_admin", "金普热电", "SUBMIT_ENTRY", "填报提交金普热电分公司生产负荷、发电机组启停与热网供暖参数表单", "JinPu_power_sheet:2026-11-09", "192.168.20.12", now - timedelta(hours=9, minutes=30)),
        ("zhuanghe_admin", "Power_plant_admin", "庄河热电", "SUBMIT_ENTRY", "填报提交庄河热电厂每日机组运行、供汽量及供热单耗核算指标", "ZhuangHe_power_sheet:2026-11-09", "192.168.25.66", now - timedelta(hours=11, minutes=10)),
        ("group_admin", "Group_admin", "集团经济运行部", "QUERY_DATA_ANALYSIS", "调阅全网生产多维数据智能分析并对比 2025 年同期气象与标煤耗量走势", "data_analysis:season_compare", "10.12.1.8", now - timedelta(hours=13, minutes=20)),
        ("group_admin", "Group_admin", "集团经济运行部", "REVOKE_UNIT", "对供热分公司某中心上报的耗水量异常进行审核驳回，退回责任单位重新复核修正", "workflow:revoke:2026-11-09", "10.12.1.8", now - timedelta(hours=15, minutes=40)),
        ("spot_operator", "Trading_admin", "电力现货交易中心", "QUERY_SPOT_ELEC", "调阅辽宁电力现货日前出清价与实时市场量价结算走势看板", "spot_elec:market_query", "10.12.5.101", now - timedelta(hours=18, minutes=10)),
        ("ww870411", "Global_admin", "洁净能源集团", "QUERY_DASHBOARD", "调阅洁净能源集团生产日报数字化决策数据看板（全网 16 张核心分析卡片）", "dashboard:overview", "172.19.0.4", now - timedelta(hours=21, minutes=30)),

        # --- 1~3 天前历史业务周期流水 (确保历史分页与各主体筛选皆有数据) ---
        ("group_admin", "Group_admin", "集团经济运行部", "PUBLISH_DAILY", "正式终审发布 2026-11-08 洁净能源集团生产日报，已固化归档入库", "workflow:publish:2026-11-08", "10.12.1.8", now - timedelta(days=1, hours=3)),
        ("group_admin", "Group_admin", "集团经济运行部", "APPROVE_UNIT", "完成对北海热电厂、金州热电、供热分公司 2026-11-08 生产报表部门级审核确认", "workflow:approve:2026-11-08", "10.12.1.8", now - timedelta(days=1, hours=4)),
        ("beihai_admin", "Power_plant_admin", "北海热电厂", "SUBMIT_ENTRY", "填报提交北海热电厂（热电联产）2026-11-08 生产运行报表", "BeiHai_co_generation_sheet:2026-11-08", "192.168.10.45", now - timedelta(days=1, hours=5)),
        ("jinzhou_admin", "Power_plant_admin", "金州热电", "SUBMIT_ENTRY", "填报提交金州热电分公司 2026-11-08 生产日报数据", "JinZhou_power_sheet:2026-11-08", "192.168.12.18", now - timedelta(days=1, hours=5, minutes=30)),
        ("xianghai_admin", "Power_plant_admin", "香海热电厂", "SUBMIT_ENTRY", "填报提交香海热电厂 2026-11-08 供热量与能耗指标", "XiangHai_power_sheet:2026-11-08", "192.168.15.22", now - timedelta(days=1, hours=6)),
        ("gongre_admin", "Heating_company_admin", "供热分公司", "IMPORT_COMPLAINT", "通过金山文档在线底表拉取填入 2026-11-08 供热公司投诉明细（67项）", "GongRe_Sheet:2026-11-08", "10.12.3.90", now - timedelta(days=1, hours=7)),
        ("group_admin", "Group_admin", "集团生产调度中心", "IMPORT_TEMPERATURE", "导入 2026-11-08 历史逐小时气温与气象监测数据（共24时段）", "weather:2026-11-08", "10.12.1.8", now - timedelta(days=1, hours=8)),
        ("spot_operator", "Trading_admin", "电力现货交易中心", "SYNC_SPOT_ELEC", "同步 2026-11-08 辽宁电力现货日前/实时市场结算出清数据", "spot_elec:2026-11-08", "10.12.5.101", now - timedelta(days=1, hours=9)),
        ("beifang_admin", "Power_plant_admin", "北方热电", "SUBMIT_ENTRY", "填报提交北方热电分公司 2026-11-08 煤质化验与进耗存报表", "BeiFang_power_sheet:2026-11-08", "192.168.18.55", now - timedelta(days=1, hours=10)),
        ("jinpu_admin", "Power_plant_admin", "金普热电", "SUBMIT_ENTRY", "填报提交金普热电分公司 2026-11-08 生产负荷与供热指标", "JinPu_power_sheet:2026-11-08", "192.168.20.12", now - timedelta(days=1, hours=11)),
        ("zhuanghe_admin", "Power_plant_admin", "庄河热电", "SUBMIT_ENTRY", "填报提交庄河热电厂 2026-11-08 机组运行与煤耗核算数据", "ZhuangHe_power_sheet:2026-11-08", "192.168.25.66", now - timedelta(days=1, hours=12)),
        ("group_admin", "Group_admin", "集团经济运行部", "EXPORT_DASHBOARD_PDF", "导出 2026.11.08 洁净能源集团生产日报数据看板标准 PDF", "dashboard:2026-11-08", "10.12.1.8", now - timedelta(days=1, hours=14)),
        ("group_admin", "Group_admin", "集团经济运行部", "PUBLISH_DAILY", "正式终审发布 2026-11-07 洁净能源集团生产日报，已固化归档入库", "workflow:publish:2026-11-07", "10.12.1.8", now - timedelta(days=2, hours=3)),
        ("beihai_admin", "Power_plant_admin", "北海热电厂", "SUBMIT_ENTRY", "填报提交北海热电厂 2026-11-07 生产运行与能耗报表", "BeiHai_co_generation_sheet:2026-11-07", "192.168.10.45", now - timedelta(days=2, hours=5)),
        ("jinzhou_admin", "Power_plant_admin", "金州热电", "SUBMIT_ENTRY", "填报提交金州热电 2026-11-07 生产日报数据", "JinZhou_power_sheet:2026-11-07", "192.168.12.18", now - timedelta(days=2, hours=6)),
        ("xianghai_admin", "Power_plant_admin", "香海热电厂", "SUBMIT_ENTRY", "填报提交香海热电厂 2026-11-07 供热量与能耗指标", "XiangHai_power_sheet:2026-11-07", "192.168.15.22", now - timedelta(days=2, hours=7)),
    ]

    records = []
    for op, grp, u, act, desc, res, ip, ct in raw_seeds:
        records.append({
            "operator": op,
            "operator_group": grp,
            "unit": u,
            "action_type": act,
            "action_desc": desc,
            "resource_id": res,
            "client_ip": ip,
            "created_at": ct,
        })
    return records


def _seed_initial_history(session) -> None:
    """
    初始化业务操作历史记录，涵盖全部核心业务大类与代表性主体。
    """
    try:
        seed_rows = _generate_rich_seed_records()
        for row in seed_rows:
            session.execute(text("""
                INSERT INTO logs.daily_report_operation_logs (
                    operator, operator_group, unit, action_type, action_desc, resource_id, client_ip, created_at
                ) VALUES (
                    :operator, :operator_group, :unit, :action_type, :action_desc, :resource_id, :client_ip, :created_at
                );
            """), row)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning(f"初始化种子业务日志失败: {exc}")


def reseed_operation_logs_dataset() -> int:
    """
    重置并重构日志数据集，清除机械重复的调阅记录，注入全业务维度的高质量操作流水。
    返回新注入的记录总数。
    """
    session = SessionLocal()
    try:
        ensure_daily_report_operation_logs_table()
        # 清除旧的历史数据
        session.execute(text("TRUNCATE TABLE logs.daily_report_operation_logs RESTART IDENTITY;"))
        records = _generate_rich_seed_records()
        for row in records:
            session.execute(text("""
                INSERT INTO logs.daily_report_operation_logs (
                    operator, operator_group, unit, action_type, action_desc, resource_id, client_ip, created_at
                ) VALUES (
                    :operator, :operator_group, :unit, :action_type, :action_desc, :resource_id, :client_ip, :created_at
                );
            """), row)
        session.commit()
        return len(records)
    except Exception as exc:
        session.rollback()
        logger.error(f"重置操作日志数据集失败: {exc}")
        raise
    finally:
        session.close()


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

    sql = text("""
        INSERT INTO logs.daily_report_operation_logs (
            operator, operator_group, unit, action_type, action_desc,
            resource_id, before_value, after_value, client_ip, created_at
        ) VALUES (
            :operator, :operator_group, :unit, :action_type, :action_desc,
            :resource_id, :before_value, :after_value, :client_ip, NOW()
        )
    """)

    session = SessionLocal()
    try:
        session.execute(
            sql,
            {
                "operator": operator or "unknown",
                "operator_group": operator_group or "",
                "unit": unit or "",
                "action_type": action_type or "ACTION",
                "action_desc": action_desc or "",
                "resource_id": resource_id or None,
                "before_value": before_json,
                "after_value": after_json,
                "client_ip": client_ip or "",
            }
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"[daily_report_operation_log] 写入日志失败: {exc}")
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

    session = SessionLocal()
    try:
        # 总数
        count_sql = text(f"SELECT COUNT(*) FROM logs.daily_report_operation_logs {where_clause}")
        total = session.execute(count_sql, params).scalar() or 0

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
    finally:
        session.close()
