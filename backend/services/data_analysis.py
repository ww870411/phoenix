from __future__ import annotations

import copy
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from fastapi.responses import JSONResponse
from sqlalchemy import bindparam, text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services import data_analysis_ai_report

import re
from decimal import Decimal

logger = logging.getLogger(__name__)

MAX_TIMELINE_DAYS = 62
TEMPERATURE_COLUMN_MAP = {
    "aver_temp": "aver_temp",
    "max_temp": "max_temp",
    "min_temp": "min_temp",
}
TEMPERATURE_UNIT = "℃"


def build_schema_payload(
    raw_payload: Dict[str, Any],
    data_file: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[JSONResponse]]:
    page_section = raw_payload.get("data_analysis_page")
    if not isinstance(page_section, dict):
        page_section = raw_payload if isinstance(raw_payload, dict) else None
    if not isinstance(page_section, dict):
        return None, JSONResponse(
            status_code=500,
            content={"ok": False, "message": "数据分析配置格式错误"},
        )

    units_section = page_section.get("单位选择") or {}
    unit_dict_raw = units_section.get("单位字典") or {}
    unit_dict = {
        str(key): str(value)
        for key, value in unit_dict_raw.items()
        if isinstance(key, str)
    }

    view_mapping = units_section.get("视图映射")
    if not isinstance(view_mapping, dict):
        view_mapping = {}
    available_views: Set[str] = set()
    for mapping in view_mapping.values():
        if isinstance(mapping, dict):
            for view_name in mapping.keys():
                if isinstance(view_name, str) and view_name.strip():
                    available_views.add(view_name.strip())

    metrics_section = page_section.get("指标选择") or {}

    def _normalize_metric_dict(source: Any) -> Dict[str, str]:
        if not isinstance(source, dict):
            return {}
        normalized: Dict[str, str] = {}
        for key, value in source.items():
            if not isinstance(key, str):
                continue
            normalized[key] = str(value) if value is not None else key
        return normalized

    legacy_metric_dict = _normalize_metric_dict(metrics_section.get("项目字典") or {})
    primary_metric_dict = _normalize_metric_dict(
        metrics_section.get("主要指标字典")
        or metrics_section.get("primary_metrics_dict")
    )
    adjustment_metric_dict = _normalize_metric_dict(
        metrics_section.get("调整指标字典")
        or metrics_section.get("adjustment_metrics_dict")
    )
    constant_metric_dict = _normalize_metric_dict(
        metrics_section.get("常量指标字典")
        or metrics_section.get("constant_metrics_dict")
    )
    temperature_metric_dict = _normalize_metric_dict(
        metrics_section.get("气温指标字典")
        or metrics_section.get("temperature_metrics_dict")
    )

    if (
        not primary_metric_dict
        and not adjustment_metric_dict
        and not constant_metric_dict
        and not temperature_metric_dict
    ):
        primary_metric_dict = legacy_metric_dict
    else:
        for key, value in legacy_metric_dict.items():
            if (
                key not in primary_metric_dict
                and key not in constant_metric_dict
                and key not in adjustment_metric_dict
                and key not in temperature_metric_dict
            ):
                primary_metric_dict[key] = value

    def _merge_metric_dicts(dicts: Sequence[Dict[str, str]]) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        for block in dicts:
            for key, value in block.items():
                if key not in merged:
                    merged[key] = value
        return merged

    metric_dict = _merge_metric_dicts(
        [primary_metric_dict, adjustment_metric_dict, constant_metric_dict, temperature_metric_dict]
    )
    metric_decimals_map = metrics_section.get("指标小数位") or metrics_section.get("metric_decimal_places") or {}
    metric_decimals: Dict[str, int] = {}
    default_decimal = int(metrics_section.get("默认小数位") or metrics_section.get("default_decimal_places") or 2)
    for key in metric_dict.keys():
        raw = metric_decimals_map.get(key)
        try:
            metric_decimals[key] = int(raw)
        except (TypeError, ValueError):
            metric_decimals[key] = default_decimal

    metric_view_mapping = metrics_section.get("视图映射")
    if not isinstance(metric_view_mapping, dict):
        metric_view_mapping = {}

    date_defaults = raw_payload.get("日期选择")
    if not isinstance(date_defaults, dict):
        date_defaults = {}

    def _options_from_dict(source: Dict[str, str]) -> List[Dict[str, str]]:
        return [
            {"value": key, "label": value if value else key}
            for key, value in source.items()
        ]

    def _options_from_keys(keys: Sequence[str], label_source: Dict[str, str]) -> List[Dict[str, str]]:
        options: List[Dict[str, str]] = []
        for key in keys:
            if not isinstance(key, str):
                continue
            label = label_source.get(key, key)
            options.append({"value": key, "label": label if label else key})
        return options

    display_units_raw = units_section.get("显示单位") or units_section.get("display_units")
    display_unit_keys: List[str] = []

    def _match_unit_key(candidate: str) -> Optional[str]:
        if not candidate:
            return None
        if candidate in unit_dict:
            return candidate
        for key, label in unit_dict.items():
            if label == candidate:
                return key
        return None

    if isinstance(display_units_raw, (list, tuple, set)):
        seen: Set[str] = set()
        for entry in display_units_raw:
            if entry is None:
                continue
            normalized = _match_unit_key(str(entry).strip())
            if normalized and normalized not in seen:
                seen.add(normalized)
                display_unit_keys.append(normalized)
    if not display_unit_keys:
        display_unit_keys = list(unit_dict.keys())

    unit_options_all = _options_from_dict(unit_dict)
    display_unit_options = _options_from_keys(display_unit_keys, unit_dict)
    if not display_unit_options:
        display_unit_options = unit_options_all[:]

    primary_label = str(metrics_section.get("主要指标名称") or "主要指标")
    adjustment_label = str(metrics_section.get("调整指标名称") or "调整指标")
    constant_label = str(metrics_section.get("常量指标名称") or "常量指标")
    temperature_label = str(metrics_section.get("气温指标名称") or "气温指标")

    primary_metric_options = _options_from_dict(primary_metric_dict)
    adjustment_metric_options = _options_from_dict(adjustment_metric_dict)
    constant_metric_options = _options_from_dict(constant_metric_dict)
    temperature_metric_options = _options_from_dict(temperature_metric_dict)
    metric_groups_payload: List[Dict[str, Any]] = []
    if primary_metric_options:
        metric_groups_payload.append(
            {"key": "primary", "label": primary_label, "options": primary_metric_options}
        )
    if adjustment_metric_options:
        metric_groups_payload.append(
            {"key": "adjustment", "label": adjustment_label, "options": adjustment_metric_options}
        )
    if constant_metric_options:
        metric_groups_payload.append(
            {"key": "constant", "label": constant_label, "options": constant_metric_options}
        )
    if temperature_metric_options:
        metric_groups_payload.append(
            {"key": "temperature", "label": temperature_label, "options": temperature_metric_options}
        )

    mode_label_map = {"单日数据": "daily", "累计数据": "range"}
    analysis_modes: List[Dict[str, Any]] = []
    for idx, (label, mapping) in enumerate(view_mapping.items()):
        if not isinstance(mapping, (dict, list)):
            mapping = {}
        analysis_modes.append(
            {
                "value": mode_label_map.get(label, f"mode_{idx}"),
                "label": label,
            }
        )
    if not analysis_modes:
        analysis_modes = [
            {"value": "daily", "label": "单日数据"},
            {"value": "range", "label": "累计数据"},
        ]

    def _normalize_view_list(value: Any) -> List[str]:
        normalized: List[str] = []
        if isinstance(value, (list, tuple, set)):
            for entry in value:
                if isinstance(entry, str) and entry.strip():
                    normalized.append(entry.strip())
        return normalized

    def _resolve_view_alias(name: str) -> str:
        if not isinstance(name, str):
            return name
        candidate = name.strip()
        if not candidate:
            return candidate
        if candidate in available_views:
            return candidate
        if candidate.endswith("_analysis"):
            core = candidate[: -len("_analysis")]
            prefixed = f"analysis_{core}"
            return prefixed if prefixed in available_views else candidate
        if candidate.startswith("analysis_"):
            core = candidate[len("analysis_") :]
            suffixed = f"{core}_analysis"
            if suffixed in available_views:
                return suffixed
        prefixed = f"analysis_{candidate}"
        if prefixed in available_views:
            return prefixed
        return candidate

    metric_group_views: Dict[str, List[str]] = {}
    group_label_lookup: Dict[str, str] = {}
    for group in metric_groups_payload:
        key = str(group.get("key") or "")
        label = str(group.get("label") or key)
        if key:
            group_label_lookup[key] = key
        if label:
            group_label_lookup[label] = key

    for raw_group, target_views in metric_view_mapping.items():
        normalized_group = str(raw_group or "").strip()
        if not normalized_group:
            continue
        resolved_key = group_label_lookup.get(normalized_group)
        if not resolved_key or resolved_key == "constant":
            continue
        normalized_views = _normalize_view_list(target_views)
        if normalized_views:
            resolved_views = []
            for candidate in normalized_views:
                resolved_name = _resolve_view_alias(candidate)
                if resolved_name not in resolved_views:
                    resolved_views.append(resolved_name)
            metric_group_views[resolved_key] = resolved_views

    content = {
        "ok": True,
        "config_path": str(data_file),
        "unit_dict": unit_dict,
        "unit_options": unit_options_all,
        "display_unit_keys": display_unit_keys,
        "display_unit_options": display_unit_options,
        "view_mapping": view_mapping,
        "metric_dict": metric_dict,
        "primary_metric_dict": primary_metric_dict,
        "adjustment_metric_dict": adjustment_metric_dict,
        "constant_metric_dict": constant_metric_dict,
        "temperature_metric_dict": temperature_metric_dict,
        "metric_options": _options_from_dict(metric_dict),
        "primary_metric_options": primary_metric_options,
        "adjustment_metric_options": adjustment_metric_options,
        "constant_metric_options": constant_metric_options,
        "temperature_metric_options": temperature_metric_options,
        "metric_groups": metric_groups_payload,
        "metric_view_mapping": metric_view_mapping,
        "metric_group_views": metric_group_views,
        "metric_decimals": metric_decimals,
        "date_defaults": date_defaults,
        "analysis_modes": analysis_modes,
    }
    return content, None


def execute_data_analysis_query(payload, schema_payload: Dict[str, Any]) -> JSONResponse:
    unit_dict = schema_payload.get("unit_dict") or {}
    metric_dict = schema_payload.get("metric_dict") or {}
    metric_groups = schema_payload.get("metric_groups") or []
    metric_group_views = schema_payload.get("metric_group_views") or {}
    metric_decimals = schema_payload.get("metric_decimals") or {}

    ordered_metrics = _unique_metric_keys(payload.metrics)
    if not ordered_metrics:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": "至少需要选择一个指标"},
        )

    unit_key = (payload.unit_key or "").strip()
    if not unit_key or unit_key not in unit_dict:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"未知单位: {unit_key or '未提供'}"},
        )
    unit_label = unit_dict.get(unit_key, unit_key)

    unknown_metrics = [key for key in ordered_metrics if key not in metric_dict]
    if unknown_metrics:
        labels = [metric_dict.get(key, key) for key in unknown_metrics]
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"存在未配置的指标: {', '.join(labels)}"},
        )

    analysis_mode_value = (payload.analysis_mode or "daily").strip().lower()
    if analysis_mode_value not in {"daily", "range"}:
        analysis_mode_value = "daily"

    start_date = payload.start_date
    end_date = payload.end_date if payload.end_date else payload.start_date
    if analysis_mode_value == "range":
        if payload.end_date is None:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "累计模式需同时提供结束日期"},
            )
        if start_date > end_date:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "message": "起始日期不得晚于结束日期"},
            )
    else:
        end_date = start_date

    range_days = (end_date - start_date).days + 1
    if analysis_mode_value == "range" and range_days > MAX_TIMELINE_DAYS:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "message": f"累计模式暂只支持 {MAX_TIMELINE_DAYS} 天内的区间，请缩小日期范围。",
            },
        )

    analysis_modes = schema_payload.get("analysis_modes") or []
    mode_label = next(
        (item.get("label") for item in analysis_modes if item.get("value") == analysis_mode_value),
        None,
    )
    if not mode_label:
        mode_label = "单日数据" if analysis_mode_value == "daily" else "累计数据"

    active_view_name = _resolve_active_view_name(
        schema_payload.get("view_mapping") or {},
        mode_label,
        unit_label,
        analysis_mode_value,
    )
    view_mapping = schema_payload.get("view_mapping") or {}

    metric_group_lookup = _build_metric_group_lookup(metric_groups)
    analysis_metric_keys: List[str] = []
    constant_metric_keys: List[str] = []
    temperature_metric_keys: List[str] = []
    temperature_view_name: Optional[str] = None
    unsupported_metrics: List[str] = []

    for key in ordered_metrics:
        group_key = metric_group_lookup.get(key, "primary")
        if group_key == "constant":
            constant_metric_keys.append(key)
            continue
        if group_key == "temperature":
            temperature_metric_keys.append(key)
            if temperature_view_name is None:
                candidates = metric_group_views.get("temperature") or []
                temperature_view_name = candidates[0] if candidates else "calc_temperature_data"
            continue
        allowed_views = metric_group_views.get(group_key) or []
        if allowed_views and active_view_name not in allowed_views:
            unsupported_metrics.append(key)
            continue
        analysis_metric_keys.append(key)

    if unsupported_metrics:
        labels = [metric_dict.get(key, key) for key in unsupported_metrics]
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": f"当前视图不支持以下指标: {', '.join(labels)}"},
        )

    try:
        analysis_rows = _query_analysis_rows(
            active_view_name,
            unit_key,
            analysis_metric_keys,
            start_date,
            end_date,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"查询分析视图失败: {exc}"},
        )

    try:
        constant_rows = _query_constant_rows(unit_key, constant_metric_keys)
    except Exception as exc:  # pylint: disable=broad-except
        return JSONResponse(
            status_code=500,
            content={"ok": False, "message": f"查询常量指标失败: {exc}"},
        )

    temperature_rows: Dict[str, Dict[str, Any]] = {}
    temperature_column_lookup: Dict[str, str] = {}
    if temperature_metric_keys:
        view_name = temperature_view_name or "calc_temperature_data"
        temperature_column_lookup = _build_temperature_column_lookup(temperature_metric_keys)
        try:
            temperature_result, temperature_column_lookup = _query_temperature_rows(
                view_name,
                temperature_metric_keys,
                start_date,
                end_date,
                analysis_mode_value,
            )
            temperature_rows = temperature_result
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "message": str(exc)})
        except Exception as exc:  # pylint: disable=broad-except
            return JSONResponse(
                status_code=500,
                content={"ok": False, "message": f"查询气温指标失败: {exc}"},
            )
    timeline_rows_map: Dict[str, List[Dict[str, Any]]] = {}
    if analysis_mode_value == "range":
        if analysis_metric_keys:
            fallback_timeline_view = (
                "analysis_groups_daily"
                if unit_key in {"Group", "ZhuChengQu"}
                else "analysis_company_daily"
            )
            timeline_view_name = _resolve_unit_view(
                view_mapping,
                "单日数据",
                unit_label,
                fallback=fallback_timeline_view,
            )
            if timeline_view_name:
                try:
                    timeline_rows_map.update(
                        _query_analysis_timeline(
                            timeline_view_name,
                            unit_key,
                            analysis_metric_keys,
                            start_date,
                            end_date,
                        )
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("生成逐日明细失败: %s", exc)
        if constant_metric_keys:
            const_value_map: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
            for key in constant_metric_keys:
                row = constant_rows.get(key)
                if row:
                    const_value_map[key] = (_decimal_to_float(row.get("value")), _decimal_to_float(row.get("peer")))
            for key, (val, peer_val) in const_value_map.items():
                timeline_rows_map[key] = _build_constant_timeline(val, peer_val, start_date, end_date)
        if temperature_metric_keys and temperature_column_lookup:
            try:
                temp_timeline = _query_temperature_timeline(
                    temperature_view_name or "calc_temperature_data",
                    temperature_column_lookup,
                    start_date,
                    end_date,
                )
                timeline_rows_map.update(temp_timeline)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("生成气温逐日明细失败: %s", exc)

    rows_payload: List[Dict[str, Any]] = []
    missing_metrics: List[Dict[str, str]] = []
    resolved_keys: List[str] = []

    for key in ordered_metrics:
        label = metric_dict.get(key, key)
        source = analysis_rows.get(key)
        value_type = "analysis"
        source_view = active_view_name if source else None
        decimals = metric_decimals.get(key, 2)
        if source is None:
            source = constant_rows.get(key)
            if source is not None:
                value_type = "constant"
                source_view = "constant_data"
        if source is None:
            source = temperature_rows.get(key)
            if source is not None:
                value_type = "temperature"
                source_view = source.get("source_view")
        if source is None:
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": None,
                    "current": None,
                    "peer": None,
                    "delta": None,
                    "value_type": metric_group_lookup.get(key, "primary"),
                    "source_view": None,
                    "missing": True,
                    "decimals": decimals,
                },
            )
            missing_metrics.append({"key": key, "label": label})
            continue

        resolved_keys.append(key)
        timeline_entries = timeline_rows_map.get(key, [])
        timeline_current_sum = (
            sum(entry["current"] for entry in timeline_entries if entry.get("current") is not None)
            if timeline_entries
            else None
        )
        timeline_peer_sum = (
            sum(entry["peer"] for entry in timeline_entries if entry.get("peer") is not None)
            if timeline_entries
            else None
        )
        if value_type == "constant":
            current_value = _decimal_to_float(source.get("value"))
            peer_value = _decimal_to_float(source.get("peer"))
            total_current = current_value
            total_peer = peer_value
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "period": source.get("period"),
                    "peer_period": source.get("peer_period"),
                    "missing": False,
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                },
            )
        elif value_type == "temperature":
            current_value = _decimal_to_float(source.get("value"))
            peer_value = _decimal_to_float(source.get("peer"))
            is_missing = source.get("missing")
            if analysis_mode_value == "range" and timeline_entries:
                avg_current, _ = _average_numeric(timeline_entries, "current")
                avg_peer, _ = _average_numeric(timeline_entries, "peer")
            else:
                avg_current = None
                avg_peer = None
            total_current = avg_current if avg_current is not None else current_value
            total_peer = avg_peer if avg_peer is not None else peer_value
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "missing": bool(is_missing),
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                },
            )
            if is_missing:
                missing_metrics.append({"key": key, "label": label})
        else:
            current_value = _decimal_to_float(source.get("value_biz_date"))
            peer_value = _decimal_to_float(source.get("value_peer_date"))
            total_current = timeline_current_sum if timeline_current_sum is not None else current_value
            total_peer = timeline_peer_sum if timeline_peer_sum is not None else peer_value
            rows_payload.append(
                {
                    "key": key,
                    "label": label,
                    "unit": source.get("unit"),
                    "current": current_value,
                    "peer": peer_value,
                    "delta": _compute_delta(current_value, peer_value),
                    "value_type": value_type,
                    "source_view": source_view,
                    "biz_date": source.get("biz_date").isoformat() if source.get("biz_date") else None,
                    "peer_date": source.get("peer_date").isoformat() if source.get("peer_date") else None,
                    "missing": False,
                    "decimals": decimals,
                    "timeline": timeline_entries,
                    "total_current": total_current,
                    "total_peer": total_peer,
                    "total_delta": _compute_delta(total_current, total_peer),
                },
            )

    warnings: List[str] = []
    if missing_metrics:
        warnings.append(
            "以下指标暂无可返回数据：{}".format(", ".join(item["label"] for item in missing_metrics))
        )

    plan_comparison_payload: Optional[Dict[str, Any]] = None
    if _is_same_month(start_date, end_date):
        plan_comparison_payload = _build_plan_comparison_payload(
            unit_key,
            unit_label,
            ordered_metrics,
            rows_payload,
            metric_dict,
            start_date,
            end_date,
            analysis_mode_value,
            schema_payload.get("view_mapping") or {},
        )

    response_payload = {
        "ok": True,
        "config_path": schema_payload.get("config_path"),
        "unit_key": unit_key,
        "unit_label": unit_label,
        "analysis_mode": analysis_mode_value,
        "analysis_mode_label": mode_label,
        "view": active_view_name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "rows": rows_payload,
        "requested_metrics": ordered_metrics,
        "resolved_metrics": resolved_keys,
        "missing_metrics": missing_metrics,
        "warnings": warnings,
    }
    if plan_comparison_payload:
        response_payload["plan_comparison"] = plan_comparison_payload

    if getattr(payload, "request_ai_report", False):
        try:
            # 准备 ring comparison 数据
            # 逻辑复刻自 DataAnalysisView.vue: computePreviousRangeForRing
            ai_payload = copy.deepcopy(response_payload)
            
            if analysis_mode_value == "range" and start_date and end_date:
                prev_start_date = None
                prev_end_date = None
                
                # 判断是否整月
                is_full_month = False
                if start_date.day == 1:
                    import calendar
                    _, last_day = calendar.monthrange(start_date.year, start_date.month)
                    if end_date.day == last_day:
                        is_full_month = True
                
                if is_full_month:
                    # 上月
                    first_day_this_month = date(start_date.year, start_date.month, 1)
                    prev_end_date = first_day_this_month - timedelta(days=1)
                    prev_start_date = date(prev_end_date.year, prev_end_date.month, 1)
                else:
                    # 平移周期
                    span = (end_date - start_date).days + 1
                    prev_end_date = start_date - timedelta(days=1)
                    prev_start_date = start_date - timedelta(days=span)
                
                if prev_start_date and prev_end_date:
                    try:
                        # 执行上期查询
                        prev_analysis_rows = _query_analysis_rows(
                            active_view_name,
                            unit_key,
                            analysis_metric_keys,
                            prev_start_date,
                            prev_end_date
                        )
                        
                        # 将上期数据注入 current rows
                        for row in ai_payload.get("rows", []):
                            key = row.get("key")
                            if not key or row.get("value_type") != "analysis":
                                continue
                                
                            prev_data = prev_analysis_rows.get(key)
                            if prev_data:
                                prev_val = _decimal_to_float(prev_data.get("value_biz_date"))
                                # 注入 ring_prev 字段
                                row["ring_prev"] = prev_val
                                
                                # 计算环比 (Ring Growth)
                                curr_val = row.get("total_current") if row.get("total_current") is not None else row.get("current")
                                if curr_val is not None and prev_val is not None and prev_val != 0:
                                    ring_rate = ((curr_val - prev_val) / abs(prev_val)) * 100
                                    row["ring_growth"] = ring_rate
                                    
                    except Exception as e:
                        logger.warning(f"AI 报告准备环比数据失败: {e}")

            job_id = data_analysis_ai_report.enqueue_ai_report_job(ai_payload)
            if job_id:
                response_payload["ai_report_job_id"] = job_id
        except Exception as exc:
            logger.warning("触发 AI 报告生成失败: %s", exc)

    return JSONResponse(status_code=200, content=response_payload)


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return default


def _build_metric_group_lookup(groups: Sequence[Dict[str, Any]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for group in groups or []:
        group_key = str(group.get("key") or "").strip() or "primary"
        options = group.get("options") or []
        if not isinstance(options, list):
            continue
        for option in options:
            value = option.get("value")
            if isinstance(value, str) and value:
                lookup[value] = group_key
    return lookup


def _unique_metric_keys(metrics: Sequence[str]) -> List[str]:
    ordered: List[str] = []
    seen: Set[str] = set()
    for value in metrics or []:
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _shift_year(value: date, years: int = 1) -> Optional[date]:
    target_year = value.year - years
    try:
        return date(target_year, value.month, value.day)
    except ValueError:
        return None


def _average_numeric(entries: List[Dict[str, Any]], field: str) -> Tuple[Optional[float], int]:
    values = [entry.get(field) for entry in entries if entry.get(field) is not None]
    count = len(values)
    if not count:
        return None, 0
    return sum(values) / count, count


def _build_constant_timeline(
    value: Optional[float],
    peer_value: Optional[float],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    if start_date > end_date:
        return []
    entries: List[Dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        peer_date = _shift_year(current)
        entries.append(
            {
                "date": current.isoformat(),
                "current": _decimal_to_float(value),
                "peer": _decimal_to_float(peer_value),
                "peer_date": peer_date.isoformat() if peer_date else None,
            }
        )
        current += timedelta(days=1)
    return entries


def _is_same_month(start: date, end: date) -> bool:
    return start.year == end.year and start.month == end.month


def _month_bounds(value: date) -> Tuple[date, date]:
    month_start = date(value.year, value.month, 1)
    if value.month == 12:
        next_month = date(value.year + 1, 1, 1)
    else:
        next_month = date(value.year, value.month + 1, 1)
    month_end = next_month - timedelta(days=1)
    return month_start, month_end


def _resolve_row_value_for_plan(row: Optional[Dict[str, Any]], analysis_mode: str) -> Optional[float]:
    if not row:
        return None
    if analysis_mode == "range":
        if row.get("total_current") is not None:
            return _to_float_or_none(row.get("total_current"))
    return _to_float_or_none(row.get("current"))


def _compute_completion_rate(actual: Optional[float], planned: Optional[float]) -> Optional[float]:
    actual_value = _to_float_or_none(actual)
    plan_value = _to_float_or_none(planned)
    if actual_value is None or plan_value in (None, 0):
        return None
    if abs(plan_value) < 1e-9:
        return None
    return (actual_value / plan_value) * 100


def _resolve_active_view_name(
    view_mapping: Dict[str, Any],
    mode_label: str,
    unit_label: str,
    analysis_mode_value: str,
) -> str:
    target = view_mapping.get(mode_label)
    if isinstance(target, dict):
        for view_name, units in target.items():
            if isinstance(units, (list, tuple, set)) and unit_label in units:
                return view_name
    return "company_daily_analysis" if analysis_mode_value == "daily" else "company_sum_analysis"


def _resolve_unit_view(
    view_mapping: Dict[str, Any],
    mode_label: str,
    unit_label: str,
    fallback: Optional[str] = None,
) -> Optional[str]:
    target = view_mapping.get(mode_label)
    if isinstance(target, dict):
        for view_name, units in target.items():
            if isinstance(units, (list, tuple, set)) and unit_label in units:
                return view_name
    return fallback


def _query_analysis_rows(
    view_name: str,
    unit_key: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
) -> Dict[str, Dict[str, Any]]:
    if not metric_keys:
        return {}
    sanitized = _sanitize_identifier(view_name)
    if sanitized is None:
        raise ValueError(f"非法视图名称: {view_name}")
    stmt = (
        text(
            f"""
            SELECT company, company_cn, item, item_cn, unit, biz_date, peer_date,
                   value_biz_date, value_peer_date
            FROM {sanitized}
            WHERE company = :company
              AND item IN :items
            """
        ).bindparams(bindparam("items", expanding=True))
    )
    with SessionLocal() as session:
        with session.begin():
            _apply_analysis_window_settings(session, sanitized, start_date, end_date)
            rows = session.execute(
                stmt,
                {"company": unit_key, "items": list(metric_keys)},
            ).mappings().all()
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        item_key = row.get("item")
        if isinstance(item_key, str) and item_key and item_key not in result:
            result[item_key] = dict(row)
    return result



def _query_analysis_timeline(
    view_name: str,
    unit_key: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
) -> Dict[str, List[Dict[str, Any]]]:
    if not metric_keys:
        return {}
    if start_date > end_date:
        return {}
    sanitized = _sanitize_identifier(view_name)
    if sanitized is None:
        raise ValueError(f"非法视图名称: {view_name}")
    stmt = (
        text(
            f"""
            SELECT item, item_cn, unit, biz_date, peer_date,
                   value_biz_date, value_peer_date
            FROM {sanitized}
            WHERE company = :company
              AND item IN :items
            """
        ).bindparams(bindparam("items", expanding=True))
    )
    timeline: Dict[str, List[Dict[str, Any]]] = {}
    current = start_date
    while current <= end_date:
        with SessionLocal() as session:
            with session.begin():
                session.execute(
                    text("SET LOCAL phoenix.biz_date = :biz_date"),
                    {"biz_date": current.isoformat()},
                )
                rows = session.execute(
                    stmt,
                    {"company": unit_key, "items": list(metric_keys)},
                ).mappings().all()
        for row in rows:
            item_key = row.get("item")
            if not isinstance(item_key, str) or not item_key:
                continue
            entry = {
                "date": row.get("biz_date").isoformat()
                if isinstance(row.get("biz_date"), date)
                else current.isoformat(),
                "current": _decimal_to_float(row.get("value_biz_date")),
                "peer": _decimal_to_float(row.get("value_peer_date")),
                "peer_date": row.get("peer_date").isoformat()
                if isinstance(row.get("peer_date"), date)
                else None,
            }
            timeline.setdefault(item_key, []).append(entry)
        current += timedelta(days=1)
    return timeline

def _sanitize_identifier(value: str) -> Optional[str]:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate):
        return candidate
    return None


def _apply_analysis_window_settings(
    session,
    view_name: str,
    start_date: date,
    end_date: date,
) -> None:
    lowered = view_name.lower()
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    if "sum" in lowered:
        session.execute(text("SET LOCAL phoenix.sum_start_date = :start_date"), {"start_date": start_str})
        session.execute(text("SET LOCAL phoenix.sum_end_date = :end_date"), {"end_date": end_str})
    else:
        session.execute(text("SET LOCAL phoenix.biz_date = :biz_date"), {"biz_date": start_str})


def _decimal_to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _compute_delta(current: Optional[float], peer: Optional[float]) -> Optional[float]:
    if current is None or peer in (None, 0):
        return None
    if abs(peer) < 1e-9:
        return None
    return ((current - peer) / peer) * 100


def _shift_period_label(label: Optional[str]) -> Optional[str]:
    if not label:
        return None
    parts = str(label).split("-")
    if len(parts) != 2:
        return None
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        return None
    return f"{start - 1:02d}-{end - 1:02d}"


def _query_constant_rows(unit_key: str, metric_keys: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    if not metric_keys:
        return {}
    stmt = (
        text(
            """
            SELECT DISTINCT ON (item)
                company,
                company_cn,
                item,
                item_cn,
                unit,
                value,
                period,
                operation_time
            FROM constant_data
            WHERE company = :company
              AND item IN :items
            ORDER BY
                item,
                COALESCE(NULLIF(split_part(period, '-', 1), '')::int, 0) DESC,
                COALESCE(NULLIF(split_part(period, '-', 2), '')::int, 0) DESC,
                operation_time DESC
            """
        ).bindparams(bindparam("items", expanding=True))
    )
    with SessionLocal() as session:
        rows = session.execute(
            stmt,
            {"company": unit_key, "items": list(metric_keys)},
        ).mappings().all()
    result: Dict[str, Dict[str, Any]] = {}
    peer_requests: Dict[str, str] = {}
    for row in rows:
        item_key = row.get("item")
        if not isinstance(item_key, str) or not item_key:
            continue
        if item_key in result:
            continue
        result[item_key] = dict(row)
        peer_period = _shift_period_label(row.get("period"))
        if peer_period:
            peer_requests[item_key] = peer_period

    if peer_requests:
        peer_stmt = (
            text(
                """
                SELECT DISTINCT ON (item, period)
                    item, period, value, operation_time
                FROM constant_data
                WHERE company = :company
                  AND item IN :items
                  AND period IN :periods
                ORDER BY item, period, operation_time DESC
                """
            )
            .bindparams(bindparam("items", expanding=True))
            .bindparams(bindparam("periods", expanding=True))
        )
        with SessionLocal() as session:
            peer_rows = session.execute(
                peer_stmt,
                {
                    "company": unit_key,
                    "items": list(peer_requests.keys()),
                    "periods": list(set(peer_requests.values())),
                },
            ).mappings().all()
        peer_lookup: Dict[Tuple[str, str], Any] = {}
        for row in peer_rows:
            item = row.get("item")
            period = row.get("period")
            if isinstance(item, str) and isinstance(period, str):
                peer_lookup[(item, period)] = row.get("value")
        for item_key, row in result.items():
            peer_period = peer_requests.get(item_key)
            if not peer_period:
                continue
            peer_value = peer_lookup.get((item_key, peer_period))
            if peer_value is not None:
                row["peer"] = peer_value
                row["peer_period"] = peer_period
            else:
                row["peer"] = None
                row["peer_period"] = peer_period
    return result


def _query_plan_month_rows(
    unit_key: str,
    unit_label: str,
    metric_keys: Sequence[str],
    metric_dict: Dict[str, str],
    period_start: date,
    plan_type: str = "plan",
) -> Dict[str, Dict[str, Any]]:
    if not metric_keys:
        return {}
    company_conditions = ["company = :company_key", "company_cn = :company_key"]
    params: Dict[str, Any] = {
        "plan_type": plan_type,
        "period_start": period_start,
        "company_key": unit_key,
    }
    normalized_label = (unit_label or "").strip()
    if normalized_label and normalized_label != unit_key:
        company_conditions.extend(["company = :company_label", "company_cn = :company_label"])
        params["company_label"] = normalized_label
    unique_metric_keys = list(dict.fromkeys(metric_keys))
    params["item_keys"] = unique_metric_keys
    item_conditions = ["item IN :item_keys"]
    metric_labels: List[str] = []
    for key in unique_metric_keys:
        label_value = metric_dict.get(key)
        if isinstance(label_value, str):
            normalized = label_value.strip()
            if normalized:
                metric_labels.append(normalized)
    if metric_labels:
        deduped_labels = list(dict.fromkeys(metric_labels))
        params["item_labels"] = deduped_labels
        item_conditions.append("item_cn IN :item_labels")
    query = f"""
        SELECT item, item_cn, unit, period::date AS period, value, type
        FROM paln_and_real_month_data
        WHERE type = :plan_type
          AND period::date = :period_start
          AND ({' OR '.join(company_conditions)})
          AND ({' OR '.join(item_conditions)})
    """
    stmt = text(query).bindparams(bindparam("item_keys", expanding=True))
    if "item_labels" in params:
        stmt = stmt.bindparams(bindparam("item_labels", expanding=True))
    with SessionLocal() as session:
        rows = session.execute(stmt, params).mappings().all()
    key_lookup = set(unique_metric_keys)
    label_lookup: Dict[str, str] = {}
    for key in unique_metric_keys:
        label_value = metric_dict.get(key)
        if isinstance(label_value, str):
            normalized = label_value.strip()
            if normalized and normalized not in label_lookup:
                label_lookup[normalized] = key
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        matched_key: Optional[str] = None
        item_key = row.get("item")
        if isinstance(item_key, str) and item_key in key_lookup:
            matched_key = item_key
        else:
            item_cn = row.get("item_cn")
            if isinstance(item_cn, str):
                normalized = item_cn.strip()
                matched_key = label_lookup.get(normalized)
        if matched_key and matched_key not in result:
            materialized = dict(row)
            materialized["value"] = _decimal_to_float(materialized.get("value"))
            result[matched_key] = materialized
    return result


def _build_temperature_column_lookup(metric_keys: Sequence[str]) -> Dict[str, str]:
    column_lookup: Dict[str, str] = {}
    for key in metric_keys:
        column = TEMPERATURE_COLUMN_MAP.get(key)
        if not column:
            raise ValueError(f"气温指标 {key} 缺少对应列映射")
        column_lookup[key] = column
    return column_lookup


def _query_temperature_rows(
    view_name: str,
    metric_keys: Sequence[str],
    start_date: date,
    end_date: date,
    analysis_mode: str,
    column_lookup: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    if not metric_keys:
        return {}, {}
    sanitized = _sanitize_identifier(view_name)
    if sanitized is None:
        raise ValueError(f"非法气温视图: {view_name}")

    column_lookup = column_lookup or _build_temperature_column_lookup(metric_keys)
    columns = sorted(set(column_lookup.values()))
    if not columns:
        return {}, column_lookup

    row: Optional[Dict[str, Any]] = None
    peer_row: Optional[Dict[str, Any]] = None
    with SessionLocal() as session:
        if analysis_mode == "range":
            select_clause = ", ".join(f"AVG({col}) AS {col}" for col in columns)
            stmt = text(
                f"""
                SELECT {select_clause}
                FROM {sanitized}
                WHERE date BETWEEN :start AND :end
                """
            )
            row = session.execute(
                stmt,
                {"start": start_date, "end": end_date},
            ).mappings().first()
            peer_start = _shift_year(start_date)
            peer_end = _shift_year(end_date)
            if peer_start and peer_end:
                peer_stmt = text(
                    f"""
                    SELECT {select_clause}
                    FROM {sanitized}
                    WHERE date BETWEEN :start AND :end
                    """
                )
                peer_row = session.execute(
                    peer_stmt,
                    {"start": peer_start, "end": peer_end},
                ).mappings().first()
        else:
            select_clause = ", ".join(columns)
            stmt = text(
                f"""
                SELECT {select_clause}
                FROM {sanitized}
                WHERE date = :target
                LIMIT 1
                """
            )
            row = session.execute(
                stmt,
                {"target": start_date},
            ).mappings().first()
            peer_target = _shift_year(start_date)
            if peer_target:
                peer_stmt = text(
                    f"""
                    SELECT {select_clause}
                    FROM {sanitized}
                    WHERE date = :target
                    LIMIT 1
                    """
                )
                peer_row = session.execute(
                    peer_stmt,
                    {"target": peer_target},
                ).mappings().first()

    result: Dict[str, Dict[str, Any]] = {}
    for key, column in column_lookup.items():
        value = row.get(column) if row else None
        peer_value = peer_row.get(column) if peer_row else None
        result[key] = {
            "value": _decimal_to_float(value),
            "peer": _decimal_to_float(peer_value),
            "unit": TEMPERATURE_UNIT,
            "source_view": sanitized,
            "missing": value is None,
        }
    return result, column_lookup


def _query_temperature_timeline(
    view_name: str,
    column_lookup: Dict[str, str],
    start_date: date,
    end_date: date,
) -> Dict[str, List[Dict[str, Any]]]:
    if start_date > end_date or not column_lookup:
        return {}
    sanitized = _sanitize_identifier(view_name)
    if sanitized is None:
        raise ValueError(f"非法气温视图: {view_name}")
    columns = sorted(set(column_lookup.values()))
    select_clause = ", ".join(["date"] + columns)
    with SessionLocal() as session:
        current_rows = session.execute(
            text(
                f"""
                SELECT {select_clause}
                FROM {sanitized}
                WHERE date BETWEEN :start AND :end
                """
            ),
            {"start": start_date, "end": end_date},
        ).mappings().all()
    peer_start = _shift_year(start_date)
    peer_end = _shift_year(end_date)
    peer_rows = []
    if peer_start and peer_end:
        with SessionLocal() as session:
            peer_rows = session.execute(
                text(
                    f"""
                    SELECT {select_clause}
                    FROM {sanitized}
                    WHERE date BETWEEN :start AND :end
                    """
                ),
                {"start": peer_start, "end": peer_end},
            ).mappings().all()
    peer_map: Dict[date, Dict[str, Any]] = {}
    for row in peer_rows:
        peer_date_val = row.get("date")
        if isinstance(peer_date_val, date):
            peer_map[peer_date_val] = dict(row)
    timeline: Dict[str, List[Dict[str, Any]]] = {}
    current_date = start_date
    while current_date <= end_date:
        current_row = next(
            (row for row in current_rows if isinstance(row.get("date"), date) and row.get("date") == current_date),
            None,
        )
        peer_date_val = _shift_year(current_date)
        peer_row = peer_map.get(peer_date_val) if peer_date_val else None
        for key, column in column_lookup.items():
            entry = {
                "date": current_date.isoformat(),
                "current": _decimal_to_float(current_row.get(column)) if current_row else None,
                "peer": _decimal_to_float(peer_row.get(column)) if peer_row else None,
                "peer_date": peer_date_val.isoformat() if peer_date_val else None,
            }
            timeline.setdefault(key, []).append(entry)
        current_date += timedelta(days=1)
    return timeline


def _build_plan_comparison_payload(
    unit_key: str,
    unit_label: str,
    metric_keys: Sequence[str],
    rows_payload: Sequence[Dict[str, Any]],
    metric_dict: Dict[str, str],
    start_date: date,
    end_date: date,
    analysis_mode: str,
    view_mapping: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not metric_keys or not _is_same_month(start_date, end_date):
        return None
    period_start, period_end = _month_bounds(start_date)
    plan_rows = _query_plan_month_rows(unit_key, unit_label, metric_keys, metric_dict, period_start)
    if not plan_rows:
        return None
    row_lookup: Dict[str, Dict[str, Any]] = {}
    for row in rows_payload or []:
        key = row.get("key")
        if isinstance(key, str) and key not in row_lookup:
            row_lookup[key] = row
    plan_actual_lookup: Dict[str, Optional[float]] = {}
    plan_view_name = _resolve_active_view_name(
        view_mapping,
        "累计数据",
        unit_label,
        "range",
    )
    if not plan_view_name:
        plan_view_name = "company_sum_analysis"
    try:
        month_actual_rows = _query_analysis_rows(plan_view_name, unit_key, metric_keys, period_start, end_date)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("查询计划累计值失败: unit=%s view=%s err=%s", unit_key, plan_view_name, exc)
        month_actual_rows = {}
    for key, payload in month_actual_rows.items():
        plan_actual_lookup[key] = _decimal_to_float(payload.get("value_biz_date"))
    entries: List[Dict[str, Any]] = []
    for key in metric_keys:
        plan_row = plan_rows.get(key)
        if not plan_row:
            continue
        plan_value = _to_float_or_none(plan_row.get("value"))
        if plan_value is None:
            continue
        row = row_lookup.get(key)
        label = (row.get("label") if row else None) or metric_dict.get(key, key)
        unit = (row.get("unit") if row else None) or plan_row.get("unit")
        actual_value = plan_actual_lookup.get(key)
        if actual_value is None:
            actual_value = _resolve_row_value_for_plan(row, analysis_mode)
        entries.append(
            {
                "key": key,
                "label": label,
                "unit": unit,
                "plan_value": plan_value,
                "actual_value": actual_value,
                "completion_rate": _compute_completion_rate(actual_value, plan_value),
                "plan_type": plan_row.get("type") or "plan",
            }
        )
    if not entries:
        return None
    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "month_label": f"{period_start.year}-{period_start.month:02d}",
        "entries": entries,
        "source": "paln_and_real_month_data",
    }
