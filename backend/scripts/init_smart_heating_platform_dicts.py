#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧供热管理平台 v2.0 旁路分析系统 —— 基础台账字典库初始化与核验脚本

功能：
1. 执行 `backend/sql/smart_heating_platform_dict_init.sql`，在 PostgreSQL 中创建
   `smart_heating_platform` schema、8 张 `dict_` 前缀标准字典表及别名映射视图；
2. 读取 `configs/成果_智慧供热平台基础台账.xlsx`，按各主体规范转换数据类型
   （剔除“主键/外键”表头前缀及 11 个全空冗余字段，`center_id` / `main_network_id` /
   `branch_network_id` 转为整型）；
3. 在单一数据库事务内按外键依赖顺序执行幂等 UPSERT（`ON CONFLICT ... DO UPDATE`）；
4. 校验全表行数、主键唯一性、外键联表完整性与缺失项基线统计。
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import openpyxl
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db.database_daily_report_25_26 import engine

SQL_FILE = PROJECT_ROOT / "backend" / "sql" / "smart_heating_platform_dict_init.sql"
EXCEL_FILE = PROJECT_ROOT / "configs" / "成果_智慧供热平台基础台账.xlsx"

SHEET_NAMES = {
    "service_center": "1_服务中心(逻辑主体，9个)",
    "main_network": "2_主干网(逻辑主体，15个)",
    "branch_network": "3_支线网(逻辑主体，41个)",
    "heating_station": "4_换热站(物理主体，242座)",
    "secondary_zone": "5_换热站二次网分区（物理主体,580个）",
    "temp_device": "6_测温用户（物理主体，2097个）",
    "merchant": "7_商户(物理主体，464户)",
    "upstream_point": "8_热源、首站、网口（物理主体，83个）",
}


def _clean_str(val: Any, allow_empty: bool = False) -> Optional[str]:
    """将单元格值规范化为去首尾空白的字符串；空值统一转为 None（可选保留空串）。"""
    if val is None:
        return None
    s = str(val).strip()
    if s == "" and not allow_empty:
        return None
    return s


def _to_int(val: Any) -> Optional[int]:
    """将数字或数字字符串安全转换为整数；空值返回 None。"""
    s = _clean_str(val)
    if s is None:
        return None
    return int(Decimal(s))


def _to_decimal(val: Any) -> Optional[Decimal]:
    """将数值或数值字符串安全转换为 Decimal；空值返回 None。"""
    s = _clean_str(val)
    if s is None:
        return None
    return Decimal(s)


def _load_sheet_dicts(wb: openpyxl.Workbook, sheet_name: str) -> List[Dict[str, Any]]:
    """读取指定工作表为字典列表（自动跳过全空尾行）。"""
    if sheet_name not in wb.sheetnames:
        raise KeyError(f"工作簿中缺少工作表: {sheet_name}")
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(col).strip() if col is not None else "" for col in rows[0]]
    result: List[Dict[str, Any]] = []
    for raw_row in rows[1:]:
        if not any(cell is not None and str(cell).strip() != "" for cell in raw_row):
            continue
        result.append(dict(zip(headers, raw_row)))
    return result


def _build_upsert_sql(
    table_name: str,
    columns: Sequence[str],
    conflict_columns: Sequence[str],
    update_columns: Sequence[str],
) -> str:
    """构造 PostgreSQL 幂等 UPSERT SQL 语句。"""
    col_list = ", ".join(columns)
    bind_list = ", ".join(f":{c}" for c in columns)
    conflict_list = ", ".join(conflict_columns)
    set_clauses = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
    if set_clauses:
        set_clauses += ", updated_at = NOW()"
    else:
        set_clauses = "updated_at = NOW()"
    return (
        f"INSERT INTO smart_heating_platform.{table_name} ({col_list}) "
        f"VALUES ({bind_list}) "
        f"ON CONFLICT ({conflict_list}) DO UPDATE SET {set_clauses}"
    )


def _transform_service_centers(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 1_服务中心 数据。"""
    return [
        {
            "center_id": _to_int(r["主键center_id"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
        }
        for r in raw_rows
    ]


def _transform_main_networks(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 2_主干网 数据。"""
    return [
        {
            "main_network_id": _to_int(r["主键main_network_id"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
        }
        for r in raw_rows
    ]


def _transform_branch_networks(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 3_支线网 数据。"""
    return [
        {
            "branch_network_id": _to_int(r["主键branch_network_id"]),
            "main_network_id": _to_int(r["外键main_network_id"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
        }
        for r in raw_rows
    ]


def _transform_heating_stations(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 4_换热站 数据（剔除 11 个全空冗余字段并保留标准主外键）。"""
    return [
        {
            "station_id": _clean_str(r["station_id"]),
            "center_id": _to_int(r["外键center_id"]),
            "branch_network_id": _to_int(r["外键branch_network_id"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
            "rd_code": _clean_str(r["rd_code"]),
            "covered_area": _to_decimal(r["covered_area"]),
            "rdfz": _clean_str(r["rdfz"]),
            "rdry": _clean_str(r["rdry"]),
            "rdss": _clean_str(r["rdss"]),
            "latitude": _to_decimal(r["latitude"]),
            "longitude": _to_decimal(r["longitude"]),
            "first_run_time": _clean_str(r["first_run_time"]),
            "heating_medium": _to_int(r["heating_medium"]),
            "heat_transfer_mode": _to_int(r["heat_transfer_mode"]),
            "power_supply_mode": _to_int(r["power_supply_mode"]),
            "run_mode": _to_int(r["run_mode"]),
            "jlzq": _to_int(r["jlzq"]),
            "sfzz": _to_int(r["sfzz"]),
        }
        for r in raw_rows
    ]


def _transform_secondary_zones(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 5_换热站二次网分区 数据。"""
    rows: List[Dict[str, Any]] = []
    for r in raw_rows:
        status_raw = _clean_str(r["当前是否在线"]) or "在线"
        rows.append(
            {
                "secondary_zone_id": _clean_str(r["主键secondary_zone_id"]),
                "station_id": _clean_str(r["外键station_id"]),
                "zone_name": _clean_str(r["二次网分区名称"]),
                "is_online": status_raw == "在线",
                "online_status_raw": status_raw,
            }
        )
    return rows


def _transform_temp_devices(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 6_测温用户 数据（保留设备硬件编号为主键）。"""
    return [
        {
            "temp_device_id": _clean_str(r["主键temp_device_id"]),
            "station_id": _clean_str(r["外键station_id"]),
            "name": _clean_str(r["name"]),
            "terminal_model": _clean_str(r["终端型号"]),
            "install_batch": _clean_str(r["安装批次与类型"]),
            "remark": _clean_str(r["备注"], allow_empty=True),
            "station_name": _clean_str(r["所属换热站名称"]),
            "station_name_raw": _clean_str(r["所属换热站原名称"]),
        }
        for r in raw_rows
    ]


def _transform_merchants(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 7_商户 数据（仅挂接支线网外键）。"""
    return [
        {
            "merchant_id": _clean_str(r["主键merchant_id"]),
            "branch_network_id": _to_int(r["外键branch_network_id"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
            "table_name": _clean_str(r["table_name"]),
            "merchant_type": _to_int(r["type"]),
            "rdfz": _clean_str(r["rdfz"]),
            "rdry": _clean_str(r["rdry"]),
            "rdss": _clean_str(r["rdss"]),
            "rdjg": _clean_str(r["rdjg"]),
            "rdgz": _clean_str(r["rdgz"]),
            "latitude": _to_decimal(r["latitude"]),
            "longitude": _to_decimal(r["longitude"]),
        }
        for r in raw_rows
    ]


def _transform_upstream_points(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """转换 8_热源、首站、网口 数据。"""
    return [
        {
            "source_page": _clean_str(r["来源页面"]),
            "category": _clean_str(r["类别"]),
            "sub_category": _clean_str(r["子类"]),
            "data_zone": _clean_str(r["数据区"]),
            "name": _clean_str(r["name"]),
            "name_raw": _clean_str(r["name_raw"]),
            "source_name": _clean_str(r["采集名称"]),
        }
        for r in raw_rows
    ]


def run_init(excel_path: Optional[Path] = None) -> Dict[str, Any]:
    """执行 DDL 建表、台账数据导入并返回核验汇总统计。"""
    target_excel = excel_path or EXCEL_FILE
    if not SQL_FILE.exists():
        raise FileNotFoundError(f"未找到建表 SQL 文件: {SQL_FILE}")
    if not target_excel.exists():
        raise FileNotFoundError(f"未找到台账 Excel 文件: {target_excel}")

    ddl_sql = SQL_FILE.read_text(encoding="utf-8")
    wb = openpyxl.load_workbook(target_excel, read_only=True, data_only=True)
    try:
        datasets = {
            "dict_service_center": _transform_service_centers(
                _load_sheet_dicts(wb, SHEET_NAMES["service_center"])
            ),
            "dict_main_network": _transform_main_networks(
                _load_sheet_dicts(wb, SHEET_NAMES["main_network"])
            ),
            "dict_branch_network": _transform_branch_networks(
                _load_sheet_dicts(wb, SHEET_NAMES["branch_network"])
            ),
            "dict_heating_station": _transform_heating_stations(
                _load_sheet_dicts(wb, SHEET_NAMES["heating_station"])
            ),
            "dict_secondary_zone": _transform_secondary_zones(
                _load_sheet_dicts(wb, SHEET_NAMES["secondary_zone"])
            ),
            "dict_temp_device": _transform_temp_devices(
                _load_sheet_dicts(wb, SHEET_NAMES["temp_device"])
            ),
            "dict_merchant": _transform_merchants(
                _load_sheet_dicts(wb, SHEET_NAMES["merchant"])
            ),
            "dict_upstream_point": _transform_upstream_points(
                _load_sheet_dicts(wb, SHEET_NAMES["upstream_point"])
            ),
        }
    finally:
        wb.close()

    table_specs = [
        (
            "dict_service_center",
            ["center_id", "name", "name_raw"],
            ["center_id"],
            ["name", "name_raw"],
        ),
        (
            "dict_main_network",
            ["main_network_id", "name", "name_raw"],
            ["main_network_id"],
            ["name", "name_raw"],
        ),
        (
            "dict_branch_network",
            ["branch_network_id", "main_network_id", "name", "name_raw"],
            ["branch_network_id"],
            ["main_network_id", "name", "name_raw"],
        ),
        (
            "dict_heating_station",
            [
                "station_id",
                "center_id",
                "branch_network_id",
                "name",
                "name_raw",
                "rd_code",
                "covered_area",
                "rdfz",
                "rdry",
                "rdss",
                "latitude",
                "longitude",
                "first_run_time",
                "heating_medium",
                "heat_transfer_mode",
                "power_supply_mode",
                "run_mode",
                "jlzq",
                "sfzz",
            ],
            ["station_id"],
            [
                "center_id",
                "branch_network_id",
                "name",
                "name_raw",
                "rd_code",
                "covered_area",
                "rdfz",
                "rdry",
                "rdss",
                "latitude",
                "longitude",
                "first_run_time",
                "heating_medium",
                "heat_transfer_mode",
                "power_supply_mode",
                "run_mode",
                "jlzq",
                "sfzz",
            ],
        ),
        (
            "dict_secondary_zone",
            ["secondary_zone_id", "station_id", "zone_name", "is_online", "online_status_raw"],
            ["secondary_zone_id"],
            ["station_id", "zone_name", "is_online", "online_status_raw"],
        ),
        (
            "dict_temp_device",
            [
                "temp_device_id",
                "station_id",
                "name",
                "terminal_model",
                "install_batch",
                "remark",
                "station_name",
                "station_name_raw",
            ],
            ["temp_device_id"],
            [
                "station_id",
                "name",
                "terminal_model",
                "install_batch",
                "remark",
                "station_name",
                "station_name_raw",
            ],
        ),
        (
            "dict_merchant",
            [
                "merchant_id",
                "branch_network_id",
                "name",
                "name_raw",
                "table_name",
                "merchant_type",
                "rdfz",
                "rdry",
                "rdss",
                "rdjg",
                "rdgz",
                "latitude",
                "longitude",
            ],
            ["merchant_id"],
            [
                "branch_network_id",
                "name",
                "name_raw",
                "table_name",
                "merchant_type",
                "rdfz",
                "rdry",
                "rdss",
                "rdjg",
                "rdgz",
                "latitude",
                "longitude",
            ],
        ),
        (
            "dict_upstream_point",
            ["source_page", "category", "sub_category", "data_zone", "name", "name_raw", "source_name"],
            ["data_zone", "source_name"],
            ["source_page", "category", "sub_category", "name", "name_raw"],
        ),
    ]

    # 1. 执行建 Schema 与建表 DDL（SQL 文件内已包含 BEGIN/COMMIT）
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute(ddl_sql)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()

    # 2. 按主外键依赖顺序执行幂等 UPSERT
    with engine.begin() as conn:
        for table_name, columns, conflict_cols, update_cols in table_specs:
            rows = datasets[table_name]
            upsert_sql = _build_upsert_sql(table_name, columns, conflict_cols, update_cols)
            conn.execute(text(upsert_sql), rows)

    # 3. 核验入库结果与主外键一致性
    summary: Dict[str, Any] = {"counts": {}, "checks": {}}
    with engine.connect() as conn:
        for table_name, _, _, _ in table_specs:
            cnt = conn.execute(
                text(f"SELECT COUNT(*) FROM smart_heating_platform.{table_name}")
            ).scalar_one()
            summary["counts"][table_name] = int(cnt)

        summary["checks"]["alias_group_count"] = int(
            conn.execute(
                text("SELECT COUNT(*) FROM smart_heating_platform.v_temp_station_alias_map")
            ).scalar_one()
        )
        summary["checks"]["stations_missing_area"] = int(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM smart_heating_platform.dict_heating_station "
                    "WHERE covered_area IS NULL"
                )
            ).scalar_one()
        )
        summary["checks"]["total_covered_area_m2"] = str(
            conn.execute(
                text(
                    "SELECT COALESCE(SUM(covered_area), 0) "
                    "FROM smart_heating_platform.dict_heating_station"
                )
            ).scalar_one()
        )
        summary["checks"]["offline_secondary_zones"] = int(
            conn.execute(
                text(
                    "SELECT COUNT(*) FROM smart_heating_platform.dict_secondary_zone "
                    "WHERE is_online IS FALSE"
                )
            ).scalar_one()
        )
        summary["checks"]["fk_join_valid_devices"] = int(
            conn.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM smart_heating_platform.dict_temp_device td "
                    "JOIN smart_heating_platform.dict_heating_station hs ON td.station_id = hs.station_id "
                    "JOIN smart_heating_platform.dict_service_center sc ON hs.center_id = sc.center_id "
                    "JOIN smart_heating_platform.dict_branch_network bn ON hs.branch_network_id = bn.branch_network_id "
                    "JOIN smart_heating_platform.dict_main_network mn ON bn.main_network_id = mn.main_network_id"
                )
            ).scalar_one()
        )

    return summary


if __name__ == "__main__":
    res = run_init()
    print("=== smart_heating_platform 字典库初始化完成 ===")
    for tbl, cnt in res["counts"].items():
        print(f"  {tbl}: {cnt} 条")
    print("=== 完整性与质量校验 ===")
    for k, v in res["checks"].items():
        print(f"  {k}: {v}")
