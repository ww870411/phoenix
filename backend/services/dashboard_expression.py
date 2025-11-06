# -*- coding: utf-8 -*-
"""
数据看板渲染引擎（初版）

职责：
- 读取数据看板配置（backend_data/数据结构_数据看板.json）
- 解析 show_date / push_date，处理默认日期回退逻辑
- 为 /dashboard API 提供统一的数据载体，后续可扩展数据库查询与指标计算

当前实现仍返回静态配置，未来会在 evaluate_dashboard 中补充数据库取数与表达式求值。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import re

from fastapi import HTTPException

from backend.config import DATA_DIRECTORY
from backend.db.database_daily_report_25_26 import (
    SessionLocal,
    TemperatureData,
    CoalInventoryData,
)
from backend.services.runtime_expression import _fetch_metrics_from_view, _to_decimal
from sqlalchemy import select, text

DATA_ROOT = Path(DATA_DIRECTORY)
DASHBOARD_CONFIG_PATH = DATA_ROOT / "数据结构_数据看板.json"
DATE_CONFIG_PATH = DATA_ROOT / "date.json"
EAST_8 = timezone(timedelta(hours=8))
SECTION_PREFIX_PATTERN = re.compile(r"^(\d+)\.")
HEATING_SEASON_START = date(2025, 11, 1)


@dataclass
class DashboardResult:
    """标准化后的数据看板响应。"""

    project_key: str
    show_date: str
    push_date: str
    generated_at: str
    source: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_key": self.project_key,
            "show_date": self.show_date,
            "push_date": self.push_date,
            "generated_at": self.generated_at,
            "source": self.source,
            "data": self.data,
        }


def _read_json(path: Path) -> Any:
    """尝试使用常见编码读取 JSON 文件。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
        try:
            with path.open("r", encoding=enc) as fh:
                import json  # 局部导入，避免模块顶部不必要依赖

                return json.load(fh)
        except Exception:
            continue
    raise FileNotFoundError(f"无法读取 JSON：{path}")


def normalize_show_date(value: Optional[str]) -> str:
    """将 show_date 正规化为 YYYY-MM-DD 或空字符串。"""
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    try:
        from datetime import datetime as _dt

        parsed = _dt.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="show_date 需为 YYYY-MM-DD 格式") from exc
    return parsed.isoformat()


def load_default_push_date() -> str:
    """从 date.json 中读取默认 push_date。"""
    if not DATE_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail="日期配置文件不存在")
    try:
        payload = _read_json(DATE_CONFIG_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"读取日期配置失败: {exc}") from exc

    value = payload.get("set_biz_date")
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=500, detail="日期配置缺少 set_biz_date 或格式不正确")
    normalized = value.strip()
    try:
        from datetime import datetime as _dt

        parsed = _dt.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="日期配置 set_biz_date 需为 YYYY-MM-DD 格式") from exc
    return parsed.isoformat()


def load_dashboard_config() -> Dict[str, Any]:
    """读取数据看板配置。"""
    if not DASHBOARD_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="数据看板配置文件不存在")
    try:
        payload = _read_json(DASHBOARD_CONFIG_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"读取数据看板配置失败: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="数据看板配置需为对象类型")
    return payload


def _generate_label_variants(label: str) -> List[str]:
    """生成多种同义写法，便于匹配“其中：暖收入”等标签。"""
    variants = set()
    text = str(label or "").strip()
    if not text:
        return []
    variants.add(text)

    # 去除常见前缀
    for prefix in ("其中：", "其中:", "其中", "当日", "当期", "本期", "同期"):
        if text.startswith(prefix):
            variants.add(text[len(prefix):].strip())

    # 替换全角括号
    normalized = text.replace("（", "(").replace("）", ")")
    variants.add(normalized)

    # 去除括号及其内容
    no_paren = re.sub(r"[（(].*?[）)]", "", normalized).strip()
    if no_paren:
        variants.add(no_paren)

    return [v for v in variants if v]


def _reverse_mapping(mapping: Dict[str, str]) -> Dict[str, str]:
    """构造 value -> key 的反向映射，包含常见同义写法。"""
    reversed_map: Dict[str, str] = {}
    for key, value in mapping.items():
        if not value:
            continue
        code = str(key).strip()
        for variant in _generate_label_variants(value):
            reversed_map.setdefault(variant, code)
    return reversed_map


def _decimal_to_float(number) -> float:
    """辅助：将 Decimal/字符串 转换为 float，避免 JSON 序列化问题。"""
    if number is None:
        return 0.0
    try:
        return float(number)
    except (TypeError, ValueError):
        return 0.0


def _fetch_temperature_series(
    session,
    start: datetime,
    end: datetime,
) -> List[Optional[float]]:
    """查询指定时间区间内的逐小时气温。"""
    if start.tzinfo is None:
        start = start.replace(tzinfo=EAST_8)
    else:
        start = start.astimezone(EAST_8)
    if end.tzinfo is None:
        end = end.replace(tzinfo=EAST_8)
    else:
        end = end.astimezone(EAST_8)
    stmt = (
        select(TemperatureData.date_time, TemperatureData.value)
        .where(TemperatureData.date_time >= start, TemperatureData.date_time < end)
        .order_by(TemperatureData.date_time.asc())
    )
    rows = session.execute(stmt).all()

    # 24 小时数组，缺失保持为 None 以便前端区分
    values: List[Optional[float]] = [None] * 24
    for row in rows:
        dt = row[0]
        value = row[1]
        try:
            if dt.tzinfo is not None:
                local_dt = dt.astimezone(EAST_8)
            else:
                local_dt = dt
            hour_index = local_dt.hour
            if value is None or hour_index < 0 or hour_index > 23:
                continue
            values[hour_index] = _decimal_to_float(value)
        except Exception:
            continue
    return values


def _fill_temperature_block(
    session,
    bucket: Dict[str, Any],
    dates: List[date],
) -> None:
    """按照指定日期列表填充逐小时气温数据。"""
    for dt in dates:
        key = dt.isoformat()
        start_dt = datetime.combine(dt, time.min)
        end_dt = start_dt + timedelta(days=1)
        bucket[key] = _fetch_temperature_series(session, start_dt.replace(tzinfo=EAST_8), end_dt.replace(tzinfo=EAST_8))


def _resolve_company_codes(
    source_config: Dict[str, Iterable[str]],
    company_cn_to_code: Dict[str, str],
) -> Dict[str, List[str]]:
    """解析数据来源中的公司列表，映射为英文编码。"""
    resolved: Dict[str, List[str]] = {}
    for table_name, companies in source_config.items():
        codes: List[str] = []
        for company_cn in companies:
            code = company_cn_to_code.get(str(company_cn).strip())
            if code:
                codes.append(code)
        resolved[table_name] = codes
    return resolved


def _build_section_index_map(payload: Dict[str, Any]) -> Dict[str, str]:
    """根据配置键的序号前缀构建映射，支持名称调整。"""
    index_map: Dict[str, str] = {}
    if not isinstance(payload, dict):
        return index_map
    for key in payload.keys():
        if not isinstance(key, str):
            continue
        match = SECTION_PREFIX_PATTERN.match(key)
        if match:
            index = match.group(1)
            index_map.setdefault(index, key)
    return index_map


def _evaluate_expression(
    metrics: Dict[str, Any],
    item_expression: str,
    item_cn_to_code: Dict[str, str],
    frame_key: str,
) -> float:
    """支持简单的加号表达式，将中文指标组合求和。"""
    if not item_expression:
        return 0.0
    total = _to_decimal(0)
    parts = [part.strip() for part in item_expression.split("+")]
    for part in parts:
        if not part:
            continue
        item_code = item_cn_to_code.get(part, part)
        bucket = metrics.get(item_code, {})
        total += _to_decimal(bucket.get(frame_key))
    return _decimal_to_float(total)


def _fill_metric_panel(
    session,
    section: Dict[str, Any],
    project_key: str,
    push_date: str,
    phase_key: str,
    company_cn_to_code: Dict[str, str],
    company_code_to_cn: Dict[str, str],
    item_cn_to_code: Dict[str, str],
    frame_key: str,
) -> None:
    """通用填充逻辑：处理按单位/指标展开的面板（边际利润、单耗等）。"""
    source_config = section.get("数据来源")
    data_bucket = section.get(phase_key)
    if not isinstance(source_config, dict) or not isinstance(data_bucket, dict):
        return

    resolved_sources = _resolve_company_codes(source_config, company_cn_to_code)
    for table_name, company_codes in resolved_sources.items():
        for company_code in company_codes:
            metrics = _fetch_metrics_from_view(session, table_name, company_code, push_date)
            company_cn = company_code_to_cn.get(company_code, company_code)
            company_bucket = data_bucket.get(company_cn)
            if not isinstance(company_bucket, dict):
                continue
            for label, expr in list(company_bucket.items()):
                value = _evaluate_expression(metrics, expr or label, item_cn_to_code, frame_key)
                company_bucket[label] = value


def _fill_simple_metric(
    session,
    section: Dict[str, Any],
    phase_key: str,
    company_cn_to_code: Dict[str, str],
    company_code_to_cn: Dict[str, str],
    item_cn_to_code: Dict[str, str],
    frame_key: str,
    push_date: str,
) -> None:
    """填充只有单个根指标的面板（标煤耗量、投诉量等）。"""
    root_item_cn = section.get("根指标")
    if not root_item_cn:
        return
    item_code = item_cn_to_code.get(root_item_cn, root_item_cn)

    source_config = section.get("数据来源")
    data_bucket = section.get(phase_key)
    if not isinstance(source_config, dict) or not isinstance(data_bucket, dict):
        return

    # “研究院”不参与标煤耗量统计，确保配置与响应保持一致
    if root_item_cn == "标煤耗量" and "研究院" in data_bucket:
        data_bucket.pop("研究院", None)

    resolved_sources = _resolve_company_codes(source_config, company_cn_to_code)
    for table_name, company_codes in resolved_sources.items():
        for company_code in company_codes:
            metrics = _fetch_metrics_from_view(session, table_name, company_code, push_date)
            company_cn = company_code_to_cn.get(company_code, company_code)
            if root_item_cn == "标煤耗量" and company_cn == "研究院":
                continue
            if company_cn not in data_bucket:
                continue
            bucket = metrics.get(item_code, {})
            data_bucket[company_cn] = _decimal_to_float(bucket.get(frame_key))


def _fill_complaint_section(
    session,
    section: Dict[str, Any],
    company_cn_to_code: Dict[str, str],
    company_code_to_cn: Dict[str, str],
    item_cn_to_code: Dict[str, str],
    push_date: str,
) -> None:
    """填充投诉量板块，支持多个指标并区分本期/同期。"""

    if not isinstance(section, dict):
        return

    source_config = section.get("数据来源")
    if not isinstance(source_config, dict):
        return

    resolved_sources = _resolve_company_codes(source_config, company_cn_to_code)
    metric_keys = [
        key
        for key in section.keys()
        if key not in {"数据来源", "查询结构", "计量单位"}
    ]

    for metric_name in metric_keys:
        metric_bucket = section.get(metric_name)
        if not isinstance(metric_bucket, dict):
            continue

        item_code = item_cn_to_code.get(metric_name, metric_name)
        for phase_key, frame_key in (("本期", "value_biz_date"), ("同期", "value_peer_date")):
            company_bucket = metric_bucket.get(phase_key)
            if not isinstance(company_bucket, dict):
                continue

            for table_name, company_codes in resolved_sources.items():
                for company_code in company_codes:
                    metrics = _fetch_metrics_from_view(session, table_name, company_code, push_date)
                    company_cn = company_code_to_cn.get(company_code, company_code)
                    if company_cn not in company_bucket:
                        continue
                    bucket = metrics.get(item_code, {})
                    company_bucket[company_cn] = _decimal_to_float(bucket.get(frame_key))


def evaluate_dashboard(project_key: str, show_date: str = "") -> DashboardResult:
    """核心入口：组装数据看板结果。目前直接返回配置，后续可在此进行数据库查询。"""
    normalized_show_date = normalize_show_date(show_date)
    push_date = normalized_show_date or load_default_push_date()
    payload = load_dashboard_config()

    data = dict(payload)
    data["push_date"] = push_date
    data["展示日期"] = push_date

    project_items = data.get("项目字典", {})
    project_units = data.get("单位字典", {})
    item_cn_to_code = _reverse_mapping(project_items)
    company_cn_to_code = _reverse_mapping(project_units)
    company_code_to_cn = {code: cn for cn, code in company_cn_to_code.items()}

    section_index_map = _build_section_index_map(data)

    def get_section_by_index(index: str, *aliases: str) -> Optional[Dict[str, Any]]:
        key = section_index_map.get(index)
        if key:
            section = data.get(key)
            if isinstance(section, dict):
                return section
        for alias in aliases:
            section = data.get(alias)
            if isinstance(section, dict):
                return section
        return None

    with SessionLocal() as session:
        # 1. 逐小时气温
        temp_section = get_section_by_index("1", "1.逐小时气温")
        if isinstance(temp_section, dict):
            forecast_days = max(int(temp_section.get("预测天数", 0)), 0)
            main_bucket = temp_section.get("本期")
            peer_bucket = temp_section.get("同期")
            if isinstance(main_bucket, dict) and isinstance(peer_bucket, dict):
                try:
                    push_dt = date.fromisoformat(push_date)
                except ValueError:
                    push_dt = date.today()
                try:
                    start_main = min(date.fromisoformat(k) for k in main_bucket.keys())
                except ValueError:
                    start_main = push_dt
                    main_bucket[start_main.isoformat()] = []
                if start_main > push_dt:
                    start_main = push_dt
                total_days = (push_dt - start_main).days + forecast_days + 1
                if total_days < 1:
                    total_days = 1
                main_dates = [start_main + timedelta(days=i) for i in range(total_days)]
                for dt in main_dates:
                    main_bucket.setdefault(dt.isoformat(), [])
                peer_dates = [dt - timedelta(days=365) for dt in main_dates]
                for dt in peer_dates:
                    peer_bucket.setdefault(dt.isoformat(), [])
                _fill_temperature_block(session, main_bucket, main_dates)
                _fill_temperature_block(session, peer_bucket, peer_dates)

        # 2. 边际利润
        margin_section = get_section_by_index("2", "2.边际利润")
        if isinstance(margin_section, dict):
            _fill_metric_panel(
                session,
                margin_section,
                project_key,
                push_date,
                "本期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_biz_date",
            )
            _fill_metric_panel(
                session,
                margin_section,
                project_key,
                push_date,
                "同期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_peer_date",
            )

        # 3. 集团汇总收入明细
        income_section = get_section_by_index("3", "3.集团汇总收入明细", "3.集团全口径收入明细")
        if isinstance(income_section, dict):
            income_items = list(income_section.get("本期", {}).keys())
            metrics = _fetch_metrics_from_view(session, "groups", "Group", push_date)
            for label in income_items:
                item_code = item_cn_to_code.get(label, label)
                bucket = metrics.get(item_code, {})
                income_section["本期"][label] = _decimal_to_float(bucket.get("value_biz_date"))
                income_section["同期"][label] = _decimal_to_float(bucket.get("value_peer_date"))

        # 4. 供暖单耗
        heating_section = get_section_by_index("4", "4.供暖单耗")
        if isinstance(heating_section, dict):
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "本期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_biz_date",
            )
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "同期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_peer_date",
            )

        # 5. 标煤耗量
        coal_section = get_section_by_index("5", "5.标煤耗量")
        if isinstance(coal_section, dict):
            _fill_simple_metric(
                session,
                coal_section,
                "本期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_biz_date",
                push_date,
            )
            _fill_simple_metric(
                session,
                coal_section,
                "同期",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "value_peer_date",
                push_date,
            )

        # 6. 省市平台投诉量
        complaint_section = get_section_by_index("6", "6.当日省市平台服务投诉量")
        if isinstance(complaint_section, dict):
            _fill_complaint_section(
                session,
                complaint_section,
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                push_date,
            )

        # 7. 煤炭库存明细
        coal_detail_section = get_section_by_index("7", "7.煤炭库存明细")
        if isinstance(coal_detail_section, dict):
            try:
                inventory_date = date.fromisoformat(push_date)
            except ValueError:
                inventory_date = date.today()
            _fill_coal_inventory(session, coal_detail_section, inventory_date)

        # 8. 供热分中心单耗明细（仅需本期）
        branch_consumption_section = get_section_by_index("8", "8.供热分中心单耗明细")
        if isinstance(branch_consumption_section, dict):
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )

        # 9. 累计卡片
        cumulative_section = get_section_by_index("9", "9.累计卡片")
        if isinstance(cumulative_section, dict):
            _fill_cumulative_cards(session, cumulative_section, push_date)

    generated_at = datetime.now(EAST_8).isoformat()
    source = (
        str(DASHBOARD_CONFIG_PATH.relative_to(DATA_ROOT))
        if DASHBOARD_CONFIG_PATH.exists()
        else str(DASHBOARD_CONFIG_PATH)
    )

    return DashboardResult(
        project_key=project_key,
        show_date=normalized_show_date,
        push_date=push_date,
        generated_at=generated_at,
        source=source,
        data=data,
    )

def _fill_coal_inventory(
    session,
    section: Dict[str, Any],
    target_date: date,
) -> None:
    """填充煤炭库存明细模块."""
    if not isinstance(section, dict):
        return

    source = str(section.get("数据来源") or "").strip()
    if source != "coal_inventory_data":
        return

    root_label = section.get("根指标", "")
    if root_label != "煤炭库存明细":
        return

    stmt = select(
        CoalInventoryData.company_cn,
        CoalInventoryData.storage_type_cn,
        CoalInventoryData.value,
    ).where(CoalInventoryData.date == target_date)
    rows = session.execute(stmt).all()

    inventory: Dict[str, Dict[str, float]] = {}
    for company_cn, storage_type_cn, value in rows:
        company_key = str(company_cn or "").strip()
        storage_key = str(storage_type_cn or "").strip()
        if not company_key or not storage_key or value is None:
            continue
        value_float = _decimal_to_float(value)
        storage_map = inventory.setdefault(company_key, {})
        storage_map[storage_key] = storage_map.get(storage_key, 0.0) + value_float

    def resolve_value(company_cn: str, storage_type: str) -> float:
        return inventory.get(company_cn, {}).get(storage_type, 0.0)

    for company_cn, storage_map in section.items():
        if not isinstance(storage_map, dict):
            continue
        if company_cn in {"数据来源", "查询结构", "根指标", "计量单位"}:
            continue

        for storage_type, expr in list(storage_map.items()):
            expression = str(expr or "").strip()
            if not expression:
                storage_map[storage_type] = resolve_value(company_cn, storage_type)
                continue

            total = 0.0
            for part in expression.split("+"):
                company_name = part.strip()
                if not company_name:
                    continue
                total += resolve_value(company_name, storage_type)
            storage_map[storage_type] = total


def _fill_heating_branch_consumption(
    session,
    section: Dict[str, Any],
    push_date: str,
    company_cn_to_code: Dict[str, str],
    item_cn_to_code: Dict[str, str],
) -> None:
    """填充供热分中心单耗明细，按中心直接取 sum_basic_data 的本期数。"""
    if not isinstance(section, dict):
        return

    source_table = str(section.get("数据来源") or "").strip()
    if not source_table:
        return

    for center_name, metrics_map in section.items():
        if center_name in {"数据来源", "查询结构", "计量单位"}:
            continue
        if not isinstance(metrics_map, dict):
            continue
        company_code = company_cn_to_code.get(str(center_name).strip(), str(center_name).strip())
        if not company_code:
            continue
        metrics = _fetch_metrics_from_view(session, source_table, company_code, push_date)
        for label, expr in list(metrics_map.items()):
            expression = str(expr).strip() if isinstance(expr, str) else ""
            target = expression or label
            value = _evaluate_expression(metrics, target, item_cn_to_code, "value_biz_date")
            metrics_map[label] = value


def _add_years(origin: date, years: int) -> date:
    """安全地为日期加减年份，处理闰年场景。"""
    try:
        return origin.replace(year=origin.year + years)
    except ValueError:
        # 对于闰年 2 月 29 日，退回至当年最后一天
        interim = origin.replace(day=1, month=3, year=origin.year + years)
        return interim - timedelta(days=1)


def _fetch_daily_average_temperature_map(
    session,
    start_date: date,
    end_date: date,
) -> Dict[date, Optional[float]]:
    """按东八区日期聚合 temperature_data，缺失日期以 None 填充。"""
    if start_date > end_date:
        return {}

    start_local = datetime.combine(start_date, time.min, tzinfo=EAST_8)
    end_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=EAST_8)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    stmt = text(
        """
        SELECT (date_time AT TIME ZONE 'Asia/Shanghai')::date AS local_date,
               AVG(value) AS avg_temp
        FROM temperature_data
        WHERE date_time >= :start_utc AND date_time < :end_utc
        GROUP BY local_date
        ORDER BY local_date
        """,
    )
    rows = session.execute(
        stmt,
        {"start_utc": start_utc, "end_utc": end_utc},
    ).all()

    daily_map: Dict[date, Optional[float]] = {}
    for row_date, avg_temp in rows:
        if row_date is None:
            continue
        if isinstance(row_date, datetime):
            cast_date = row_date.date()
        elif isinstance(row_date, date):
            cast_date = row_date
        else:
            try:
                cast_date = date.fromisoformat(str(row_date))
            except ValueError:
                continue

        if avg_temp is None:
            daily_map[cast_date] = None
            continue
        try:
            daily_map[cast_date] = float(avg_temp)
        except (TypeError, ValueError):
            daily_map[cast_date] = None

    total_days = (end_date - start_date).days + 1
    if total_days <= 0:
        return {}

    ordered: Dict[date, Optional[float]] = {}
    for idx in range(total_days):
        current = start_date + timedelta(days=idx)
        ordered[current] = daily_map.get(current)

    return ordered


def _fetch_average_temperature_between(
    session,
    start_date: date,
    end_date: date,
) -> Optional[float]:
    """从 calc_temperature_data 视图求指定日期区间的平均气温。"""
    daily_map = _fetch_daily_average_temperature_map(session, start_date, end_date)
    if not daily_map:
        return None

    values = [value for value in daily_map.values() if value is not None]
    if not values:
        return None

    return sum(values) / len(values)


def _fill_cumulative_cards(
    session,
    section: Dict[str, Any],
    push_date: str,
) -> None:
    """填充“累计卡片”板块（平均气温 + 供暖期累计指标）。"""
    if not isinstance(section, dict):
        return

    try:
        push_dt = date.fromisoformat(push_date)
    except ValueError:
        push_dt = HEATING_SEASON_START

    # 计算供暖期平均气温（本期/同期），返回逐日列表
    temp_bucket = section.get("供暖期平均气温")
    if isinstance(temp_bucket, dict):
        season_start = HEATING_SEASON_START if HEATING_SEASON_START <= push_dt else push_dt
        main_series = _fetch_daily_average_temperature_map(session, season_start, push_dt)

        peer_start = _add_years(season_start, -1)
        peer_end = _add_years(push_dt, -1)
        peer_series = _fetch_daily_average_temperature_map(session, peer_start, peer_end)

        temp_bucket["本期"] = [
            {
                "date": day.isoformat(),
                "value": None if value is None else round(value, 2),
            }
            for day, value in main_series.items()
        ]
        temp_bucket["同期"] = [
            {
                "date": day.isoformat(),
                "value": None if value is None else round(value, 2),
            }
            for day, value in peer_series.items()
        ]

    # 其余累计指标直接读取 groups 视图的 sum_ytd_* 字段
    metrics = _fetch_metrics_from_view(session, "groups", "Group", push_date)
    mapping = {
        "集团汇总供暖期标煤耗量": "consumption_std_coal",
        "集团汇总供暖期可比煤价边际利润": "eco_comparable_marginal_profit",
        "集团汇总供暖期省市平台投诉量": "amount_daily_service_complaints",
    }

    for label, item_code in mapping.items():
        bucket = section.get(label)
        if not isinstance(bucket, dict):
            continue
        metric_payload = metrics.get(item_code, {})
        bucket["本期"] = _decimal_to_float(metric_payload.get("sum_ytd_biz"))
        bucket["同期"] = _decimal_to_float(metric_payload.get("sum_ytd_peer"))
