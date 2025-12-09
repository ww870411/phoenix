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
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
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


from typing import Tuple
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


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:  # NaN
        return None
    return numeric


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
            raw_expr = data_bucket[company_cn]
            expression = raw_expr.strip() if isinstance(raw_expr, str) else ""
            if expression:
                data_bucket[company_cn] = _evaluate_expression(
                    metrics,
                    expression,
                    item_cn_to_code,
                    frame_key,
                )
            else:
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


def _fill_device_status_section(
    session,
    section: Dict[str, Any],
    push_date: str,
    company_cn_to_code: Dict[str, str],
    item_cn_to_code: Dict[str, str],
) -> None:
    """填充“各单位运行设备数量明细表”板块。"""
    if not isinstance(section, dict):
        return

    companies = section.get("单位")
    if not isinstance(companies, list):
        return
    
    # 从配置中获取本期和同期的指标列表
    current_metrics_list = section.get("本期")
    peer_metrics_list = section.get("同期")

    if not isinstance(current_metrics_list, list) and not isinstance(peer_metrics_list, list):
        return

    table_name = "sum_basic_data"
    source_config = section.get("数据来源") or {}
    if isinstance(source_config, dict):
        for t, _ in source_config.items():
            table_name = t
            break

    # 初始化本期和同期的数据桶
    current_bucket = section.setdefault("本期数据", {}) # 避免与配置的 "本期" 列表冲突，改名为 "本期数据"
    peer_bucket = section.setdefault("同期数据", {})   # 新增同期数据桶

    for company_cn in companies:
        company_cn_str = str(company_cn).strip()
        if not company_cn_str:
            continue
        
        company_code = company_cn_to_code.get(company_cn_str, company_cn_str)
        metrics_data = _fetch_metrics_from_view(session, table_name, company_code, push_date)
        
        # 填充本期数据
        if isinstance(current_metrics_list, list):
            current_company_bucket = current_bucket.setdefault(company_cn_str, {})
            for item_cn in current_metrics_list:
                item_cn_str = str(item_cn).strip()
                if not item_cn_str:
                    continue
                item_code = item_cn_to_code.get(item_cn_str, item_cn_str)
                item_payload = metrics_data.get(item_code, {})
                val = _decimal_to_float(item_payload.get("value_biz_date"))
                current_company_bucket[item_cn_str] = val
        
        # 填充同期数据
        if isinstance(peer_metrics_list, list):
            peer_company_bucket = peer_bucket.setdefault(company_cn_str, {})
            for item_cn in peer_metrics_list:
                item_cn_str = str(item_cn).strip()
                if not item_cn_str:
                    continue
                item_code = item_cn_to_code.get(item_cn_str, item_cn_str)
                item_payload = metrics_data.get(item_code, {})
                val = _decimal_to_float(item_payload.get("value_peer_date")) # 同期数据取 value_peer_date
                peer_company_bucket[item_cn_str] = val


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
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "本月累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_month_biz",
            )
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "同期月累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_month_peer",
            )
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "本供暖期累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_ytd_biz",
            )
            _fill_metric_panel(
                session,
                heating_section,
                project_key,
                push_date,
                "同供暖期累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_ytd_peer",
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
            _fill_simple_metric(
                session,
                coal_section,
                "本月累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_month_biz",
                push_date,
            )
            _fill_simple_metric(
                session,
                coal_section,
                "同期月累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_month_peer",
                push_date,
            )
            _fill_simple_metric(
                session,
                coal_section,
                "本供暖期累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_ytd_biz",
                push_date,
            )
            _fill_simple_metric(
                session,
                coal_section,
                "同供暖期累计",
                company_cn_to_code,
                company_code_to_cn,
                item_cn_to_code,
                "sum_ytd_peer",
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

        # 8. 供热分中心单耗明细
        branch_consumption_section = get_section_by_index("8", "8.供热分中心单耗明细")
        if isinstance(branch_consumption_section, dict):
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "本期",
                "value_biz_date",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "同期",
                "value_peer_date",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "本月累计",
                "sum_month_biz",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "同期月累计",
                "sum_month_peer",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "本供暖期累计",
                "sum_ytd_biz",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )
            _fill_heating_branch_consumption(
                session,
                branch_consumption_section,
                "同供暖期累计",
                "sum_ytd_peer",
                push_date,
                company_cn_to_code,
                item_cn_to_code,
            )

        # 0.5 折叠卡片
        summary_fold_section = get_section_by_index("0.5", "0.5卡片详细信数据表（折叠）")
        if isinstance(summary_fold_section, dict):
            _fill_summary_fold_section(session, summary_fold_section, push_date, item_cn_to_code)

        # 9. 累计卡片
        cumulative_section = get_section_by_index("9", "9.累计卡片")
        if isinstance(cumulative_section, dict):
            _fill_cumulative_cards(session, cumulative_section, push_date)

        # 10. 每日对比趋势
        daily_trend_section = get_section_by_index("10", "10.每日对比趋势")
        if isinstance(daily_trend_section, dict):
            _fill_daily_trend_section(session, daily_trend_section, push_date, item_cn_to_code)

        # 11. 各单位运行设备数量明细表
        device_status_section = get_section_by_index("11", "11.各单位运行设备数量明细表")
        if isinstance(device_status_section, dict):
            _fill_device_status_section(session, device_status_section, push_date, company_cn_to_code, item_cn_to_code)

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
    phase_key: str,
    frame_key: str,
    push_date: str,
    company_cn_to_code: Dict[str, str],
    item_cn_to_code: Dict[str, str],
) -> None:
    """填充供热分中心单耗明细，支持多阶段框架。"""
    if not isinstance(section, dict):
        return

    source_table = str(section.get("数据来源") or "").strip()
    if not source_table:
        return

    data_bucket = section.get(phase_key)
    if not isinstance(data_bucket, dict):
        return

    for center_name, metrics_map in data_bucket.items():
        if not isinstance(metrics_map, dict):
            continue
        company_code = company_cn_to_code.get(str(center_name).strip(), str(center_name).strip())
        if not company_code:
            continue
        metrics = _fetch_metrics_from_view(session, source_table, company_code, push_date)
        for label, expr in list(metrics_map.items()):
            expression = str(expr).strip() if isinstance(expr, str) else ""
            target = expression or label
            value = _evaluate_expression(metrics, target, item_cn_to_code, frame_key)
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
    """按日从 calc_temperature_data 视图聚合平均气温，缺失日期以 None 填充。"""
    if start_date > end_date:
        return {}

    stmt = text(
        """
        SELECT date, aver_temp
          FROM calc_temperature_data
         WHERE date BETWEEN :start_date AND :end_date
         ORDER BY date
        """,
    )
    rows = session.execute(
        stmt,
        {"start_date": start_date, "end_date": end_date},
    ).all()

    daily_map: Dict[date, Optional[float]] = {}
    for row_date, avg_temp in rows:
        if row_date is None:
            continue
        try:
            cast_date = row_date if isinstance(row_date, date) else date.fromisoformat(str(row_date))
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


def _normalize_metric_entries(raw_config: Any) -> List[Dict[str, Any]]:
    """将配置指标列表标准化为 {key, axis} 结构。"""
    entries: List[Dict[str, Any]] = []
    if isinstance(raw_config, list):
        iterable = raw_config
    elif raw_config:
        iterable = [raw_config]
    else:
        iterable = []
    for item in iterable:
        if isinstance(item, str):
            key = item.strip()
            axis = None
        elif isinstance(item, dict):
            key = str(item.get("指标") or item.get("key") or item.get("label") or "").strip()
            axis = str(item.get("轴") or item.get("axis") or "").strip().lower() or None
        else:
            continue
        if key:
            entries.append({"key": key, "axis": axis})
    return entries


def _is_temperature_metric(metric_key: str) -> bool:
    return "温" in metric_key


def _resolve_metric_axis(metric_key: str, preferred: Optional[str]) -> str:
    axis = (preferred or "").lower()
    if axis in {"left", "right"}:
        return axis
    return "right" if _is_temperature_metric(metric_key) else "left"


def _build_group_metric_cache(
    session,
    dates: Sequence[date],
) -> Dict[str, Dict[str, Any]]:
    cache: Dict[str, Dict[str, Any]] = {}
    for dt in dates:
        iso_key = dt.isoformat()
        if iso_key in cache:
            continue
        cache[iso_key] = _fetch_metrics_from_view(session, "groups", "Group", iso_key)
    return cache


def _extract_group_metric_series(
    cache: Dict[str, Dict[str, Any]],
    iso_dates: Sequence[str],
    item_code: str,
) -> List[Optional[float]]:
    series: List[Optional[float]] = []
    for iso_key in iso_dates:
        metrics = cache.get(iso_key)
        bucket = metrics.get(item_code, {}) if metrics else {}
        value = bucket.get("value_biz_date")
        series.append(_to_float_or_none(value))
    return series


def _build_temperature_series(
    temp_map: Dict[date, Optional[float]],
    ordered_dates: Sequence[date],
) -> List[Optional[float]]:
    values: List[Optional[float]] = []
    for day in ordered_dates:
        value = temp_map.get(day)
        values.append(None if value is None else round(value, 2))
    return values


def _fill_daily_trend_section(
    session,
    section: Dict[str, Any],
    push_date: str,
    item_cn_to_code: Dict[str, str],
) -> None:
    """填充“10.每日对比趋势”板块的时间序列数据。"""
    if not isinstance(section, dict):
        return

    current_config = _normalize_metric_entries(section.get("本期"))
    peer_config = _normalize_metric_entries(section.get("同期"))
    if not current_config:
        return

    try:
        push_dt = date.fromisoformat(push_date)
    except ValueError:
        push_dt = date.today()
    start_dt = HEATING_SEASON_START if HEATING_SEASON_START <= push_dt else push_dt
    if start_dt > push_dt:
        start_dt = push_dt

    total_days = (push_dt - start_dt).days + 1
    if total_days <= 0:
        total_days = 1
    date_range = [start_dt + timedelta(days=idx) for idx in range(total_days)]
    labels = [dt.isoformat() for dt in date_range]
    peer_dates = [_add_years(dt, -1) for dt in date_range]
    peer_labels = [dt.isoformat() for dt in peer_dates]

    units_bucket = section.get("计量单位")
    units_map = units_bucket if isinstance(units_bucket, dict) else {}

    has_current_temp = any(_is_temperature_metric(entry["key"]) for entry in current_config)
    has_peer_temp = any(_is_temperature_metric(entry["key"]) for entry in peer_config)
    if has_current_temp and not has_peer_temp:
        for entry in current_config:
            if _is_temperature_metric(entry["key"]):
                peer_config.append({"key": entry["key"], "axis": entry.get("axis")})
        has_peer_temp = True

    temp_series_map = _fetch_daily_average_temperature_map(session, start_dt, push_dt)
    peer_temp_map: Optional[Dict[date, Optional[float]]] = None
    if has_peer_temp:
        peer_start = peer_dates[0] if peer_dates else start_dt
        peer_end = peer_dates[-1] if peer_dates else peer_start
        peer_temp_map = _fetch_daily_average_temperature_map(session, peer_start, peer_end)

    needs_group_current = any(not _is_temperature_metric(entry["key"]) for entry in current_config)
    needs_group_peer = any(not _is_temperature_metric(entry["key"]) for entry in peer_config)
    current_cache = (
        _build_group_metric_cache(session, date_range) if needs_group_current else {}
    )
    peer_cache = _build_group_metric_cache(session, peer_dates) if needs_group_peer else {}

    def build_series(
        entries: List[Dict[str, Any]],
        iso_dates: List[str],
        dates_obj: List[date],
        cache: Dict[str, Dict[str, Any]],
        temp_map: Optional[Dict[date, Optional[float]]],
    ) -> List[Dict[str, Any]]:
        series: List[Dict[str, Any]] = []
        for entry in entries:
            metric_key = entry["key"]
            axis = _resolve_metric_axis(metric_key, entry.get("axis"))
            unit_label = units_map.get(metric_key, "")
            if _is_temperature_metric(metric_key):
                values = _build_temperature_series(temp_map or {}, dates_obj)
            else:
                item_code = item_cn_to_code.get(metric_key, metric_key)
                values = _extract_group_metric_series(cache, iso_dates, item_code)
            series.append(
                {
                    "key": metric_key,
                    "axis": axis,
                    "unit": unit_label,
                    "values": [None if v is None else round(v, 2) for v in values],
                },
            )
        return series

    current_series = build_series(current_config, labels, date_range, current_cache, temp_series_map)
    peer_series = build_series(peer_config, peer_labels, peer_dates, peer_cache, peer_temp_map)

    section["本期"] = {
        "labels": labels,
        "series": current_series,
    }
    section["同期"] = {
        "labels": labels,
        "series": peer_series,
    }
    section["meta"] = {
        "start_date": start_dt.isoformat(),
        "end_date": push_dt.isoformat(),
        "peer_start_date": peer_dates[0].isoformat() if peer_dates else "",
        "peer_end_date": peer_dates[-1].isoformat() if peer_dates else "",
    }


def _fetch_average_temperature_between(
    session,
    start_date: date,
    end_date: date,
) -> Optional[float]:
    """直接从 calc_temperature_data 视图求指定日期区间的平均气温。"""
    if start_date > end_date:
        return None

    stmt = text(
        """
        SELECT AVG(aver_temp) AS avg_temp
          FROM calc_temperature_data
         WHERE date BETWEEN :start_date AND :end_date
        """,
    )
    result = session.execute(
        stmt,
        {"start_date": start_date, "end_date": end_date},
    ).scalar()
    if result is None:
        return None
    try:
        return float(result)
    except (TypeError, ValueError):
        return None


def _fetch_temperature_value_from_view(session, target_date: Optional[date]) -> Optional[float]:
    """读取 calc_temperature_data 中指定日期的平均气温。"""
    if target_date is None:
        return None
    stmt = text(
        """
        SELECT aver_temp
          FROM calc_temperature_data
         WHERE date = :target_date
        """,
    )
    result = session.execute(stmt, {"target_date": target_date}).scalar()
    if result is None:
        return None
    try:
        return float(result)
    except (TypeError, ValueError):
        return None


def _resolve_heating_season_start(anchor: date) -> date:
    """根据 anchor 所在年份计算供暖期起始日期。"""
    base_year = anchor.year
    season_start = date(base_year, HEATING_SEASON_START.month, HEATING_SEASON_START.day)
    if anchor < season_start:
        season_start = date(base_year - 1, HEATING_SEASON_START.month, HEATING_SEASON_START.day)
    return season_start


SUMMARY_PERIOD_CANONICAL = {
    "本日": "daily",
    "本月累计": "monthly",
    "本供暖期累计": "seasonal",
}

SUMMARY_PERIOD_FIELD_MAP = {
    "本日": ("value_biz_date", "value_peer_date"),
    "本月累计": ("sum_month_biz", "sum_month_peer"),
    "本供暖期累计": ("sum_ytd_biz", "sum_ytd_peer"),
}


def _resolve_period_field_pair(period_label: str, override_mode: Optional[str]) -> Optional[Tuple[str, str]]:
    if override_mode == "value":
        return ("value_biz_date", "value_peer_date")
    return SUMMARY_PERIOD_FIELD_MAP.get(period_label)


SUMMARY_PERIOD_ITEM_OVERRIDES = {
    # “净投诉量”在不同窗口需要独立指标，且月/供暖期值属于状态量
    "净投诉量": {
        "本日": {"item": "当日净投诉量", "mode": "value"},
        "本月累计": {"item": "本月累计净投诉量", "mode": "value"},
        "本供暖期累计": {"item": "本供暖期累计净投诉量", "mode": "value"},
    },
}

def _split_metric_label(label: str) -> Tuple[str, str]:
    """拆分“指标（单位）”格式的标签。"""
    text_label = str(label or "").strip()
    if not text_label:
        return "", ""
    match = re.match(r"^(.*?)(?:（(.*)）)?$", text_label)
    if not match:
        return text_label, ""
    base = match.group(1).strip()
    unit = (match.group(2) or "").strip()
    return base or text_label, unit


def _build_temperature_summary_metrics(session, target_date: Optional[date]) -> Dict[str, Optional[float]]:
    """构造平均气温的本期/同期、多窗口聚合结果。"""
    if target_date is None:
        return {"daily": None, "monthly": None, "seasonal": None}

    month_start = target_date.replace(day=1)
    season_start = _resolve_heating_season_start(target_date)

    daily_value = _fetch_temperature_value_from_view(session, target_date)
    month_avg = _fetch_average_temperature_between(session, month_start, target_date)
    season_avg = _fetch_average_temperature_between(session, season_start, target_date)

    def _round(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        return round(value, 2)

    return {
        "daily": _round(daily_value),
        "monthly": _round(month_avg),
        "seasonal": _round(season_avg),
    }


def _build_group_summary_metrics(
    metrics: Dict[str, Dict[str, Decimal]],
    item_cn_to_code: Dict[str, str],
    base_label: str,
    phase_name: str,
    mapping_source: Dict[str, Any],
) -> Dict[str, Optional[float]]:
    """根据配置映射获取 groups 指标的本期/同期多窗口值。"""

    def _resolve_item_code(raw_value: Any) -> str:
        candidate = str(raw_value or "").strip() or base_label
        return item_cn_to_code.get(candidate, candidate)

    canonical: Dict[str, Optional[float]] = {"daily": None, "monthly": None, "seasonal": None}
    period_overrides = SUMMARY_PERIOD_ITEM_OVERRIDES.get(base_label)

    for period_label, canonical_key in SUMMARY_PERIOD_CANONICAL.items():
        override_payload = period_overrides.get(period_label) if period_overrides else None
        override_mode: Optional[str] = None

        if isinstance(override_payload, dict):
            mapping_value = override_payload.get("item") or override_payload.get("value")
            override_mode = override_payload.get("mode")
        elif override_payload:
            mapping_value = override_payload
        else:
            mapping_value = mapping_source.get(period_label)

        item_code = _resolve_item_code(mapping_value)
        bucket = metrics.get(item_code)
        if not bucket:
            continue

        field_pair = _resolve_period_field_pair(period_label, override_mode)
        if not field_pair:
            continue
        field_name = field_pair[0 if phase_name == "本期" else 1]
        canonical[canonical_key] = _decimal_to_float(bucket.get(field_name))
    return canonical


def _fill_summary_fold_section(
    session,
    section: Dict[str, Any],
    push_date: str,
    item_cn_to_code: Dict[str, str],
) -> None:
    """填充“0.5卡片详细信息数据表（折叠）”内容。"""
    if not isinstance(section, dict):
        return

    try:
        push_dt = date.fromisoformat(push_date)
    except ValueError:
        push_dt = date.today()
    peer_dt = _add_years(push_dt, -1)

    metrics = _fetch_metrics_from_view(session, "groups", "Group", push_date)

    for phase_label, target_date in (("本期", push_dt), ("同期", peer_dt)):
        phase_bucket = section.get(phase_label)
        if not isinstance(phase_bucket, dict):
            continue
        for raw_label, metric_map in phase_bucket.items():
            if not isinstance(metric_map, dict):
                continue
            base_label, _ = _split_metric_label(raw_label)
            mapping_source = {
                period_label: metric_map.get(period_label)
                for period_label in SUMMARY_PERIOD_CANONICAL
            }
            if base_label == "平均气温":
                values = _build_temperature_summary_metrics(session, target_date)
            else:
                values = _build_group_summary_metrics(
                    metrics,
                    item_cn_to_code,
                    base_label,
                    phase_label,
                    mapping_source,
                )
            metric_map["本日"] = values.get("daily")
            metric_map["本月累计"] = values.get("monthly")
            metric_map["本供暖期累计"] = values.get("seasonal")


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

    # 其余累计指标根据配置读取 groups 视图，区分字段模式
    metrics = _fetch_metrics_from_view(session, "groups", "Group", push_date)
    mapping: Dict[str, Tuple[str, str]] = {
        "集团汇总供暖期标煤耗量": ("sum_consumption_std_coal_zhangtun", "sum_ytd"),
        "集团汇总供暖期可比煤价边际利润": ("eco_comparable_marginal_profit", "sum_ytd"),
        "集团汇总供暖期省市平台投诉量": ("amount_daily_service_complaints", "sum_ytd"),
        "集团汇总净投诉量": ("sum_season_total_net_complaints", "value"),
    }

    field_mode_map = {
        "sum_ytd": ("sum_ytd_biz", "sum_ytd_peer"),
        "value": ("value_biz_date", "value_peer_date"),
    }

    for label, (item_code, mode) in mapping.items():
        bucket = section.get(label)
        if not isinstance(bucket, dict):
            continue
        metric_payload = metrics.get(item_code, {})
        biz_field, peer_field = field_mode_map.get(mode, ("sum_ytd_biz", "sum_ytd_peer"))
        bucket["本期"] = _decimal_to_float(metric_payload.get(biz_field))
        bucket["同期"] = _decimal_to_float(metric_payload.get(peer_field))
