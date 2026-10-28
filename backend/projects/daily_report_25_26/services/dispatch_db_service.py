# -*- coding: utf-8 -*-
r"""
调度生产日报数据库持久化与查询服务 (100+ 物理展开列工业大宽表版)
支持 PostgreSQL 本机 (5434) 与 Docker 容器 (5432) 端口自适应容错
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import re

logger = logging.getLogger(__name__)

def safe_date_str(val: Any) -> Optional[str]:
    """安全校验与格式化日期字符串，钳位容错处理如平年2月29日手误"""
    if not val:
        return None
    s = str(val).strip()
    m = re.match(r"^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            if mo == 2 and d >= 29:
                return f"{y:04d}-02-28"
            elif d > 30 and mo in [4, 6, 9, 11]:
                return f"{y:04d}-{mo:02d}-30"
            elif d > 31:
                return f"{y:04d}-{mo:02d}-31"
    return None

# 完整 100+ 物理列字段清单定义
PHYSICAL_COLUMNS = [
    # 1. 基础发令
    "project_key", "biz_date", "issue_date", "publish_date", "duty_staff", "file_name",
    # 2. 气象全要素
    "wth_date", "wth_weekday", "wth_condition", "wth_temp_min", "wth_temp_max",
    "wth_hum_min", "wth_hum_max", "wth_wind_dir", "wth_wind_scale", "wth_raw_text",
    # 3. 水网首站 36项
    "bh_s1_pumps", "bh_s1_flow", "bh_s1_press_sup", "bh_s1_press_ret", "bh_s1_temp_sup", "bh_s1_temp_ret",
    "bh_s2_pumps", "bh_s2_flow", "bh_s2_press_sup", "bh_s2_press_ret", "bh_s2_temp_sup", "bh_s2_temp_ret",
    "bh_wl_pumps", "bh_wl_flow", "bh_wl_press_sup", "bh_wl_press_ret", "bh_wl_temp_sup", "bh_wl_temp_ret",
    "xh_lv1_pumps", "xh_lv1_flow", "xh_lv1_press_sup", "xh_lv1_press_ret", "xh_lv1_temp_sup", "xh_lv1_temp_ret",
    "xh_lv3_pumps", "xh_lv3_flow", "xh_lv3_press_sup", "xh_lv3_press_ret", "xh_lv3_temp_sup", "xh_lv3_temp_ret",
    "xh_main_pumps", "xh_main_flow", "xh_main_press_sup", "xh_main_press_ret", "xh_main_temp_sup", "xh_main_temp_ret",
    # 4. 蒸汽网口 12项
    "bh_south_status", "bh_south_press", "bh_south_flow",
    "xb_link_status", "xb_link_press", "xb_link_flow",
    "xh_east_status", "xh_east_press", "xh_east_flow",
    "xh_west_status", "xh_west_press", "xh_west_flow",
    # 5. 燃煤收耗存 25项
    "coal_remark",
    "coal_bh_in", "coal_bh_use", "coal_bh_stock",
    "coal_xh_in", "coal_xh_use", "coal_xh_stock",
    "coal_main_sum_in", "coal_main_sum_use", "coal_main_sum_stock",
    "coal_jz_in", "coal_jz_use", "coal_jz_stock",
    "coal_bf_in", "coal_bf_use", "coal_bf_stock",
    "coal_zh_in", "coal_zh_use", "coal_zh_stock",
    "coal_dlg_in", "coal_dlg_use", "coal_dlg_stock",
    "coal_total_in", "coal_total_use", "coal_total_stock",
    # 6. 当日产量与计划 20项
    "prod_bh_steam_coal_plan", "prod_bh_steam_coal_act",
    "prod_bh_water_coal_plan", "prod_bh_water_coal_act",
    "prod_bh_power_plan", "prod_bh_power_act",
    "prod_bh_heat_plan", "prod_bh_heat_act",
    "prod_xh_steam_coal_plan", "prod_xh_steam_coal_act",
    "prod_xh_power_plan", "prod_xh_power_act",
    "prod_xh_heat_plan", "prod_xh_heat_act",
    "prod_main_coal_plan", "prod_main_coal_act",
    "prod_main_power_plan", "prod_main_power_act",
    "prod_main_heat_plan", "prod_main_heat_act",
    # 7. 网口热量 6项
    "gw_high_temp_water", "gw_lv1_heat", "gw_lv3_heat",
    "gw_bh_south_steam", "gw_xh_ew_steam", "gw_xb_link_steam",
    # 8. 初期补水量 6项
    "water_sup_bh_s1", "water_sup_bh_s2", "water_sup_period_last_year",
    "water_sup_accum", "water_sup_accum_last", "substations_filled",
    # 9. 宏观四大总量
    "total_coal_consumed", "total_power_generated", "total_heat_supplied", "total_water_replenished",
    # 10. 高度动态结构化存根 (JSONB)
    "eqp_status_json", "boiler_turbine_status", "log_items_json", "operations_and_tickets"
]


def get_db_connection():
    """
    获取数据库连接，具备端口自适应容错机制 (优先尝试 5434 本机服务，回退 5432 容器)
    """
    db_urls_to_try = []

    env_url = os.getenv("DATABASE_URL")
    if env_url:
        db_urls_to_try.append(env_url)

    db_urls_to_try.extend([
        "postgresql://postgres:postgres@localhost:5434/phoenix",
        "postgresql://postgres:postgres@127.0.0.1:5434/phoenix",
        "postgresql://postgres:postgres@localhost:5432/phoenix",
        "postgresql://postgres:postgres@127.0.0.1:5432/phoenix",
    ])

    last_err = None
    for url in db_urls_to_try:
        try:
            conn = psycopg2.connect(url, connect_timeout=3)
            return conn
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Unable to connect to PostgreSQL database. Last error: {last_err}")


def ensure_dispatch_table_exists():
    """确保 public.dispatch_daily_reports 表存在，若现有列数少于 50 则自动执行无损重构升级"""
    sql_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sql", "dispatch_daily_reports.sql")
    if os.path.exists(sql_path):
        with open(sql_path, "r", encoding="utf-8") as f:
            full_ddl = f.read()
    else:
        full_ddl = ""

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 检查现有表字段数量
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'dispatch_daily_reports';
            """)
            col_count = cur.fetchone()[0]

            # 若表不存在或列数少于 50 列，则使用完整 DDL 执行全量建表
            if col_count < 50 and full_ddl:
                logger.info("Upgrading dispatch_daily_reports table to 100+ physical columns wide schema...")
                cur.execute(full_ddl)
                conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Failed to ensure dispatch table exists: %s", e)
    finally:
        conn.close()


def check_existing_dates(biz_dates: List[str], project_key: str = "daily_report_25_26") -> List[str]:
    """检查给定的业务日期中，哪些已经在数据库中存在"""
    if not biz_dates:
        return []

    ensure_dispatch_table_exists()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT biz_date::text 
                FROM public.dispatch_daily_reports 
                WHERE project_key = %s AND biz_date = ANY(%s::date[])
                ORDER BY biz_date ASC;
                """,
                (project_key, biz_dates)
            )
            rows = cur.fetchall()
            return [r[0] for r in rows]
    finally:
        conn.close()


def save_dispatch_reports(
    reports: List[Dict[str, Any]], 
    overwrite: bool = False,
    project_key: str = "daily_report_25_26"
) -> Dict[str, Any]:
    """
    保存/入库调度日报全要素大宽表数据 (100+ 物理列)
    """
    ensure_dispatch_table_exists()
    if not reports:
        return {"ok": True, "inserted": 0, "updated": 0, "message": "无待保存数据"}

    valid_reports = [r for r in reports if r.get("biz_date")]
    if not valid_reports:
        return {"ok": False, "message": "待保存数据中未包含有效业务日期 (biz_date)"}

    biz_dates = [r["biz_date"] for r in valid_reports]
    existing_dates = check_existing_dates(biz_dates, project_key)

    if existing_dates and not overwrite:
        return {
            "ok": False,
            "has_conflict": True,
            "conflict_dates": existing_dates,
            "message": f"检测到 {len(existing_dates)} 个日期的日报已存在于数据库中，请确认是否覆盖更新。"
        }

    conn = get_db_connection()
    inserted_count = 0
    updated_count = 0

    # 动态构建 100+ 物理列的 INSERT ... ON CONFLICT DO UPDATE 语句
    cols_str = ", ".join(PHYSICAL_COLUMNS)
    placeholders = ", ".join(["%s"] * len(PHYSICAL_COLUMNS))

    # 更新字段列表 (排除 project_key 与 biz_date)
    update_cols = [c for c in PHYSICAL_COLUMNS if c not in ["project_key", "biz_date"]]
    update_set_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])

    upsert_sql = f"""
    INSERT INTO public.dispatch_daily_reports ({cols_str}, updated_at)
    VALUES ({placeholders}, NOW())
    ON CONFLICT (project_key, biz_date) DO UPDATE SET
        {update_set_str},
        updated_at = NOW()
    RETURNING (xmax = 0) AS is_insert;
    """

    existing_set = set(existing_dates)
    try:
        with conn.cursor() as cur:
            for item in valid_reports:
                b_date = item.get("biz_date")

                # 按 PHYSICAL_COLUMNS 顺序提取对应值
                values = []
                for col in PHYSICAL_COLUMNS:
                    val = item.get(col)
                    # JSONB 字段特殊包装
                    if col in ["eqp_status_json", "boiler_turbine_status", "log_items_json", "operations_and_tickets"]:
                        values.append(Json(val or [] if "list" in col or "status" in col or "operations" in col else val or {}))
                    elif col in ["biz_date", "issue_date", "wth_date"]:
                        values.append(safe_date_str(val))
                    elif col == "project_key":
                        values.append(project_key)
                    elif col == "duty_staff":
                        values.append(val or item.get("duty_officers"))
                    else:
                        values.append(val)

                cur.execute(upsert_sql, values)
                row = cur.fetchone()
                is_insert = row[0] if row else (b_date not in existing_set)
                if is_insert:
                    inserted_count += 1
                else:
                    updated_count += 1

        conn.commit()
        return {
            "ok": True,
            "has_conflict": False,
            "total_saved": len(valid_reports),
            "inserted": inserted_count,
            "updated": updated_count,
            "message": f"成功保存 {len(valid_reports)} 条调度全要素宽表记录（新增 {inserted_count} 条，覆盖更新 {updated_count} 条）。"
        }
    except Exception as e:
        conn.rollback()
        logger.error("Save dispatch reports failed: %s", e)
        raise e
    finally:
        conn.close()


def query_dispatch_reports(
    project_key: str = "daily_report_25_26",
    biz_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    根据日期、区间或关键词检索已入库的调度日报 (返回全要素大宽表及对齐前端的嵌套结构)
    """
    ensure_dispatch_table_exists()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conditions = ["project_key = %s"]
            params: List[Any] = [project_key]

            if biz_date:
                conditions.append("biz_date = %s")
                params.append(biz_date)
            else:
                if start_date:
                    conditions.append("biz_date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("biz_date <= %s")
                    params.append(end_date)

            if keyword and keyword.strip():
                kw = f"%{keyword.strip()}%"
                conditions.append(
                    "(file_name ILIKE %s OR duty_staff ILIKE %s OR log_items_json::text ILIKE %s OR wth_raw_text ILIKE %s)"
                )
                params.extend([kw, kw, kw, kw])

            where_clause = " WHERE " + " AND ".join(conditions)

            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM public.dispatch_daily_reports {where_clause};"
            cur.execute(count_sql, params)
            total = cur.fetchone()["count"]

            # 全量物理字段查询
            query_sql = f"""
                SELECT *
                FROM public.dispatch_daily_reports 
                {where_clause}
                ORDER BY biz_date DESC
                LIMIT %s OFFSET %s;
            """
            cur.execute(query_sql, params + [limit, offset])
            rows = cur.fetchall()

            # 转换为对齐前端组件的响应格式
            formatted_items = []
            for r in rows:
                item = dict(r)
                # 日期与数值类型格式化
                for k, v in item.items():
                    if isinstance(v, (datetime, date)):
                        item[k] = v.isoformat()
                    elif hasattr(v, "__float__"):
                        try:
                            item[k] = float(v)
                        except Exception:
                            pass

                # 兼容旧前端读取的结构体字段包装
                item["duty_officers"] = item.get("duty_staff")
                item["weather"] = {
                    "raw_text": item.get("wth_raw_text"),
                    "weather_desc": item.get("wth_condition"),
                    "temp_min": item.get("wth_temp_min"),
                    "temp_max": item.get("wth_temp_max"),
                    "humidity": f"{item.get('wth_hum_min')}%~{item.get('wth_hum_max')}%" if item.get("wth_hum_min") is not None else "",
                    "wind": f"{item.get('wth_wind_dir') or ''}{item.get('wth_wind_scale') or ''}".strip(),
                    "forecast_date": item.get("wth_date"),
                    "weekday": item.get("wth_weekday")
                }

                # 组装首站列表供前端表格渲染
                first_stations = [
                    {
                        "plant": "北海电厂", "station_name": "#1首站",
                        "pump_count": item.get("bh_s1_pumps"), "flow_rate_th": item.get("bh_s1_flow"),
                        "supply_pressure_mpa": item.get("bh_s1_press_sup"), "return_pressure_mpa": item.get("bh_s1_press_ret"),
                        "pressure_diff_mpa": round(item["bh_s1_press_sup"] - item["bh_s1_press_ret"], 3) if item.get("bh_s1_press_sup") is not None and item.get("bh_s1_press_ret") is not None else None,
                        "supply_temp_c": item.get("bh_s1_temp_sup"), "return_temp_c": item.get("bh_s1_temp_ret"),
                        "temp_diff_c": round(item["bh_s1_temp_sup"] - item["bh_s1_temp_ret"], 2) if item.get("bh_s1_temp_sup") is not None and item.get("bh_s1_temp_ret") is not None else None
                    },
                    {
                        "plant": "北海电厂", "station_name": "#2首站",
                        "pump_count": item.get("bh_s2_pumps"), "flow_rate_th": item.get("bh_s2_flow"),
                        "supply_pressure_mpa": item.get("bh_s2_press_sup"), "return_pressure_mpa": item.get("bh_s2_press_ret"),
                        "pressure_diff_mpa": round(item["bh_s2_press_sup"] - item["bh_s2_press_ret"], 3) if item.get("bh_s2_press_sup") is not None and item.get("bh_s2_press_ret") is not None else None,
                        "supply_temp_c": item.get("bh_s2_temp_sup"), "return_temp_c": item.get("bh_s2_temp_ret"),
                        "temp_diff_c": round(item["bh_s2_temp_sup"] - item["bh_s2_temp_ret"], 2) if item.get("bh_s2_temp_sup") is not None and item.get("bh_s2_temp_ret") is not None else None
                    },
                    {
                        "plant": "北海电厂", "station_name": "水炉",
                        "pump_count": item.get("bh_wl_pumps"), "flow_rate_th": item.get("bh_wl_flow"),
                        "supply_pressure_mpa": item.get("bh_wl_press_sup"), "return_pressure_mpa": item.get("bh_wl_press_ret"),
                        "pressure_diff_mpa": round(item["bh_wl_press_sup"] - item["bh_wl_press_ret"], 3) if item.get("bh_wl_press_sup") is not None and item.get("bh_wl_press_ret") is not None else None,
                        "supply_temp_c": item.get("bh_wl_temp_sup"), "return_temp_c": item.get("bh_wl_temp_ret"),
                        "temp_diff_c": round(item["bh_wl_temp_sup"] - item["bh_wl_temp_ret"], 2) if item.get("bh_wl_temp_sup") is not None and item.get("bh_wl_temp_ret") is not None else None
                    },
                    {
                        "plant": "香海电厂", "station_name": "#1低真空",
                        "pump_count": item.get("xh_lv1_pumps"), "flow_rate_th": item.get("xh_lv1_flow"),
                        "supply_pressure_mpa": item.get("xh_lv1_press_sup"), "return_pressure_mpa": item.get("xh_lv1_press_ret"),
                        "pressure_diff_mpa": round(item["xh_lv1_press_sup"] - item["xh_lv1_press_ret"], 3) if item.get("xh_lv1_press_sup") is not None and item.get("xh_lv1_press_ret") is not None else None,
                        "supply_temp_c": item.get("xh_lv1_temp_sup"), "return_temp_c": item.get("xh_lv1_temp_ret"),
                        "temp_diff_c": round(item["xh_lv1_temp_sup"] - item["xh_lv1_temp_ret"], 2) if item.get("xh_lv1_temp_sup") is not None and item.get("xh_lv1_temp_ret") is not None else None
                    },
                    {
                        "plant": "香海电厂", "station_name": "#3低真空",
                        "pump_count": item.get("xh_lv3_pumps"), "flow_rate_th": item.get("xh_lv3_flow"),
                        "supply_pressure_mpa": item.get("xh_lv3_press_sup"), "return_pressure_mpa": item.get("xh_lv3_press_ret"),
                        "pressure_diff_mpa": round(item["xh_lv3_press_sup"] - item["xh_lv3_press_ret"], 3) if item.get("xh_lv3_press_sup") is not None and item.get("xh_lv3_press_ret") is not None else None,
                        "supply_temp_c": item.get("xh_lv3_temp_sup"), "return_temp_c": item.get("xh_lv3_temp_ret"),
                        "temp_diff_c": round(item["xh_lv3_temp_sup"] - item["xh_lv3_temp_ret"], 2) if item.get("xh_lv3_temp_sup") is not None and item.get("xh_lv3_temp_ret") is not None else None
                    },
                    {
                        "plant": "香海电厂", "station_name": "首站",
                        "pump_count": item.get("xh_main_pumps"), "flow_rate_th": item.get("xh_main_flow"),
                        "supply_pressure_mpa": item.get("xh_main_press_sup"), "return_pressure_mpa": item.get("xh_main_press_ret"),
                        "pressure_diff_mpa": round(item["xh_main_press_sup"] - item["xh_main_press_ret"], 3) if item.get("xh_main_press_sup") is not None and item.get("xh_main_press_ret") is not None else None,
                        "supply_temp_c": item.get("xh_main_temp_sup"), "return_temp_c": item.get("xh_main_temp_ret"),
                        "temp_diff_c": round(item["xh_main_temp_sup"] - item["xh_main_temp_ret"], 2) if item.get("xh_main_temp_sup") is not None and item.get("xh_main_temp_ret") is not None else None
                    }
                ]
                item["first_stations"] = [s for s in first_stations if s["flow_rate_th"] is not None or s["supply_temp_c"] is not None]

                # 组装蒸汽网口
                steam_networks = [
                    {"network_name": "北海南网", "status": item.get("bh_south_status") or "投运", "pressure_mpa": item.get("bh_south_press"), "flow_th": item.get("bh_south_flow")},
                    {"network_name": "香北联络", "status": item.get("xb_link_status") or "投运", "pressure_mpa": item.get("xb_link_press"), "flow_th": item.get("xb_link_flow")},
                    {"network_name": "香海东网", "status": item.get("xh_east_status") or "投运", "pressure_mpa": item.get("xh_east_press"), "flow_th": item.get("xh_east_flow")},
                    {"network_name": "香海西网", "status": item.get("xh_west_status") or "投运", "pressure_mpa": item.get("xh_west_press"), "flow_th": item.get("xh_west_flow")}
                ]
                item["steam_networks"] = [s for s in steam_networks if s["pressure_mpa"] is not None or s["flow_th"] is not None]

                # 组装燃煤列表
                coal_stats = [
                    {"category": "北海", "standard_org": "北海电厂", "in_coal_tons": item.get("coal_bh_in"), "consumed_coal_tons": item.get("coal_bh_use"), "storage_coal_tons": item.get("coal_bh_stock")},
                    {"category": "香海", "standard_org": "香海电厂", "in_coal_tons": item.get("coal_xh_in"), "consumed_coal_tons": item.get("coal_xh_use"), "storage_coal_tons": item.get("coal_xh_stock")},
                    {"category": "主城区合计", "standard_org": "主城区合计", "in_coal_tons": item.get("coal_main_sum_in"), "consumed_coal_tons": item.get("coal_main_sum_use"), "storage_coal_tons": item.get("coal_main_sum_stock")},
                    {"category": "金州", "standard_org": "金州热电", "in_coal_tons": item.get("coal_jz_in"), "consumed_coal_tons": item.get("coal_jz_use"), "storage_coal_tons": item.get("coal_jz_stock")},
                    {"category": "北方", "standard_org": "北方热电", "in_coal_tons": item.get("coal_bf_in"), "consumed_coal_tons": item.get("coal_bf_use"), "storage_coal_tons": item.get("coal_bf_stock")},
                    {"category": "庄河", "standard_org": "庄河环海", "in_coal_tons": item.get("coal_zh_in"), "consumed_coal_tons": item.get("coal_zh_use"), "storage_coal_tons": item.get("coal_zh_stock")},
                    {"category": "大连港", "standard_org": "大连港", "in_coal_tons": item.get("coal_dlg_in"), "consumed_coal_tons": item.get("coal_dlg_use"), "storage_coal_tons": item.get("coal_dlg_stock")},
                    {"category": "合计", "standard_org": "全网合计", "in_coal_tons": item.get("coal_total_in"), "consumed_coal_tons": item.get("coal_total_use"), "storage_coal_tons": item.get("coal_total_stock")},
                ]
                item["coal_stats"] = [c for c in coal_stats if c["consumed_coal_tons"] is not None or c["storage_coal_tons"] is not None]

                # 组装产量
                item["production_stats"] = {
                    "beihai_plan_coal": (item.get("prod_bh_steam_coal_plan") or 0) + (item.get("prod_bh_water_coal_plan") or 0) if item.get("prod_bh_steam_coal_plan") is not None or item.get("prod_bh_water_coal_plan") is not None else None,
                    "beihai_actual_coal": (item.get("prod_bh_steam_coal_act") or 0) + (item.get("prod_bh_water_coal_act") or 0) if item.get("prod_bh_steam_coal_act") is not None or item.get("prod_bh_water_coal_act") is not None else None,
                    "beihai_plan_power": item.get("prod_bh_power_plan"),
                    "beihai_actual_power": item.get("prod_bh_power_act"),
                    "beihai_plan_heat": item.get("prod_bh_heat_plan"),
                    "beihai_actual_heat": item.get("prod_bh_heat_act"),
                    "xianghai_plan_coal": item.get("prod_xh_steam_coal_plan"),
                    "xianghai_actual_coal": item.get("prod_xh_steam_coal_act"),
                    "xianghai_plan_power": item.get("prod_xh_power_plan"),
                    "xianghai_actual_power": item.get("prod_xh_power_act"),
                    "xianghai_plan_heat": item.get("prod_xh_heat_plan"),
                    "xianghai_actual_heat": item.get("prod_xh_heat_act"),
                    "urban_total_plan_coal": item.get("prod_main_coal_plan"),
                    "urban_total_actual_coal": item.get("prod_main_coal_act"),
                    "urban_total_plan_power": item.get("prod_main_power_plan"),
                    "urban_total_actual_power": item.get("prod_main_power_act"),
                    "urban_total_plan_heat": item.get("prod_main_heat_plan"),
                    "urban_total_actual_heat": item.get("prod_main_heat_act")
                }

                # 组装补水量
                item["water_replenishment"] = {
                    "first_station_1_water_tons": item.get("water_sup_bh_s1"),
                    "first_station_2_water_tons": item.get("water_sup_bh_s2"),
                    "period_last_year_water_tons": item.get("water_sup_period_last_year"),
                    "accumulated_water_tons": item.get("water_sup_accum"),
                    "accumulated_last_year_water_tons": item.get("water_sup_accum_last"),
                    "substations_filled": item.get("substations_filled")
                }

                formatted_items.append(item)

            return {
                "ok": True,
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": formatted_items
            }
    finally:
        conn.close()


def get_available_dispatch_dates(project_key: str = "daily_report_25_26") -> List[str]:
    """获取数据库中已有记录的所有业务日期列表（倒序）"""
    ensure_dispatch_table_exists()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT biz_date::text 
                FROM public.dispatch_daily_reports 
                WHERE project_key = %s
                ORDER BY biz_date DESC;
                """,
                (project_key,)
            )
            rows = cur.fetchall()
            return [r[0] for r in rows]
    finally:
        conn.close()
