"""
数据分析 AI 报告生成服务。

基于 Gemini SDK，负责：
- 读取 backend_data/api_key.json 中的 gemini_api_key / gemini_model；
- 根据数据分析查询结果构造提示词；
- 将任务提交至线程池并异步生成报告；
- 以内存字典维护任务状态，供 API 查询。
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import math
import statistics

import google.generativeai as genai

from backend.config import DATA_DIRECTORY

DATA_ROOT = Path(DATA_DIRECTORY)
API_KEY_PATH = DATA_ROOT / "api_key.json"
PERCENTAGE_SCALE_METRICS = {"rate_overall_efficiency"}

INSIGHT_PROMPT_TEMPLATE = """你是一名热电联产/城市集中供热行业的数据分析师。请阅读给定的 JSON 数据（已包含指标的同比/环比/趋势/温度相关性结果），仅输出结构化 JSON，不要出现 Markdown 或解释文字。

输出 JSON 结构：
{
  "headline": "一句话概括整体运行结论",
  "key_findings": [
    {
      "metric": "指标名称",
      "status": "up | down | stable",
      "evidence": "引用 value/delta(同比)/ring(环比)/stats 的文字，说明原因",
      "risk_level": "low | medium | high"
    }
  ],
  "temperature_effect": "若存在 trend_description 或 correlation，说明气温联动，否则写 \"无显著气温影响\"",
  "risks": ["列出潜在风险或需要关注的点，至少 1 条"],
  "recommendations": ["针对运行/调度/数据的建议，至少 1 条"],
  "notable_metrics": ["按照重要性列出 3~5 个指标 key 或标签，供下一阶段使用"]
}

要求：
- 必须使用中文；
- `key_findings` 至少 2 条，与 `notable_metrics` 对齐；
- `status` 依据 delta(同比) 与 ring(环比) 综合判断；
- 没有相关性的指标也可以写在 `key_findings`，但要解释依据。
"""

LAYOUT_PROMPT_TEMPLATE = """你是资深运营报告编辑。现在已得到：
1. 已预处理好的指标数据；
2. 阶段一输出的洞察 JSON。

请规划 HTML 报告的章节结构，并只输出 JSON。结构：
{
  "sections": [
    {
      "id": "overview | trend | temperature | risks",
      "title": "章节标题",
      "purpose": "这一章想传达的重点",
      "bullets": ["段落要点，引用 key_findings/risks/temperature_effect"],
      "metrics": ["本章重点指标 key 列表，可为空"]
    }
  ],
  "chart_plan": {
    "primary_metric": "建议放在左轴的指标 key",
    "temperature_metric": "若存在温度指标则指定 key，否则置空",
    "narrative": "图表想表达的故事，如走势/相关性"
  },
  "callouts": [
    {
      "title": "提示或警示标题",
      "body": "一句话说明",
      "level": "info | warning | danger"
    }
  ]
}

要求：
- `sections` 至少 3 个，顺序要合理；
- `callouts` 数组至少包含 1 条，用于页面醒目提示；
- 若没有温度指标，请把 `temperature_metric` 设为 null（而不是字符串）。
"""

CONTENT_PROMPT_TEMPLATE = """你现在的任务是“内容撰写”。请根据阶段一的洞察（Insight）和阶段二的规划（Layout），为报告的每个章节撰写具体的分析段落。

请只输出 JSON，结构如下：
{
  "section_contents": {
    "overview": "第一章的正文内容...",
    "trend": "第二章的正文内容...",
    "risks": "第三章的正文内容..."
  },
  "callouts": [
    {
      "title": "提示标题",
      "body": "提示内容",
      "level": "info | warning | danger"
    }
  ]
}

要求：
- `section_contents` 的 key 必须与阶段二 Layout 中定义的 `sections[].id` 一一对应；
- 内容要专业、客观，直接引用数据，不要说废话；
- 使用 HTML 标签（如 <p>, <ul>, <li>, <strong>）来排版段落内容，但不要包含外层容器；
- 不要输出完整的 HTML 页面，只输出段落内容。
"""

_logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()
_model: Optional[genai.GenerativeModel] = None
_model_name: Optional[str] = None


def _load_gemini_settings() -> Dict[str, str]:
    if not API_KEY_PATH.exists():
        raise RuntimeError(f"API Key 配置不存在：{API_KEY_PATH}")
    data = json.loads(API_KEY_PATH.read_text(encoding="utf-8"))
    api_key = data.get("gemini_api_key")
    model = data.get("gemini_model")
    if not api_key or not isinstance(api_key, str):
        raise RuntimeError("缺少 gemini_api_key 配置")
    if not model or not isinstance(model, str):
        raise RuntimeError("缺少 gemini_model 配置")
    return {"api_key": api_key, "model": model}


def _safe_json_dumps(payload: Dict[str, Any]) -> str:
    def _convert(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    return json.dumps(payload, ensure_ascii=False, default=_convert)


def _to_float_or_none(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_relative_rate(current: Optional[float], reference: Optional[float]) -> Optional[float]:
    if current is None or reference is None:
        return None
    if abs(reference) < 1e-9:
        return None
    return ((current - reference) / abs(reference)) * 100


def _format_percent_text(value: Optional[float]) -> str:
    if value is None or isinstance(value, float) and (value != value):
        return "—"
    return f"{value:+.2f}%"


def _classify_delta(value: Optional[float]) -> str:
    if value is None or isinstance(value, float) and (value != value):
        return "delta-muted"
    if value > 0:
        return "delta-positive"
    if value < 0:
        return "delta-negative"
    return "delta-neutral"


def _format_number(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "—"
    fmt = f"{{:,.{decimals}f}}"
    return fmt.format(value)


def _format_range_label(start: Optional[str], end: Optional[str]) -> str:
    if start and end:
        return start if start == end else f"{start} ~ {end}"
    return start or end or ""


def _build_ring_compare_payload(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ring_block = payload.get("ringCompare") or payload.get("ring_compare")
    if not isinstance(ring_block, dict):
        return None
    prev_totals = ring_block.get("prevTotals") or ring_block.get("prev_totals")
    if not isinstance(prev_totals, dict) or not prev_totals:
        note = ring_block.get("note")
        if note:
            return {
                "entries": [],
                "note": note,
                "current_range": _format_range_label(payload.get("start_date"), payload.get("end_date")),
                "previous_range": _format_range_label(
                    (ring_block.get("range") or {}).get("start"),
                    (ring_block.get("range") or {}).get("end"),
                ),
                "summary_lines": [],
            }
        return None

    rows = payload.get("rows") or []
    entries: List[Dict[str, Any]] = []
    for row in rows:
        key = row.get("key")
        if not key or key not in prev_totals:
            continue
        current_val = row.get("total_current")
        if current_val is None:
            current_val = row.get("current")
        current = _to_float_or_none(current_val)
        previous_raw = _to_float_or_none(prev_totals.get(key))
        previous = previous_raw * 100 if key in PERCENTAGE_SCALE_METRICS and previous_raw is not None else previous_raw
        if current is None or previous is None:
            continue
        decimals = int(row.get("decimals")) if isinstance(row.get("decimals"), int) else 2
        entries.append(
            {
                "key": key,
                "label": row.get("label") or key,
                "unit": row.get("unit") or "",
                "current": current,
                "previous": previous,
                "rate": _compute_relative_rate(current, previous),
                "decimals": decimals,
            }
        )

    range_info = ring_block.get("range") or {}
    previous_range_label = _format_range_label(range_info.get("start"), range_info.get("end"))
    current_range_label = _format_range_label(payload.get("start_date"), payload.get("end_date"))
    summary_lines: List[str] = []
    if entries:
        phrases = []
        for entry in entries[:3]:
            unit_text = entry["unit"]
            prev_text = _format_number(entry["previous"], entry["decimals"])
            rate_text = _format_percent_text(entry["rate"])
            phrases.append(f"{entry['label']} 上期 {prev_text}{unit_text}，环比 {rate_text}")
        suffix = "（其余略）" if len(entries) > 3 else ""
        range_note = f"（上期：{previous_range_label}）" if previous_range_label else ""
        summary_lines.append(f"【环比】{'；'.join(phrases)}{suffix}{range_note}")

    note = ring_block.get("note") or ("当前指标无可用环比数据" if not entries else "")

    return {
        "entries": entries,
        "note": note,
        "current_range": current_range_label,
        "previous_range": previous_range_label,
        "summary_lines": summary_lines,
    }


def _build_timeline_matrix(metrics: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    timeline_metrics = [m for m in metrics if m.get("timeline_entries")]
    if not timeline_metrics:
        return None
    date_set = set()
    prepared = []
    for metric in timeline_metrics:
        entries = metric.get("timeline_entries") or []
        mapping = {}
        for entry in entries:
            date_val = entry.get("date")
            if not date_val:
                continue
            mapping[date_val] = entry
            date_set.add(date_val)
        if mapping:
            prepared.append(
                {
                    "key": metric.get("key") or metric.get("label"),
                    "label": metric.get("label"),
                    "unit": metric.get("unit"),
                    "decimals": metric.get("decimals", 2),
                    "value_type": metric.get("value_type") or ("temperature" if metric.get("is_temperature") else None),
                    "entries": mapping,
                }
            )
    if not prepared:
        return None
    dates = sorted(date_set)
    rows: List[Dict[str, Any]] = []
    for date in dates:
        record = {"date": date}
        for metric in prepared:
            entry = metric["entries"].get(date) or {}
            curr = _to_float_or_none(entry.get("current"))
            peer = _to_float_or_none(entry.get("peer"))
            record[f"{metric['key']}__current"] = curr
            record[f"{metric['key']}__peer"] = peer
            record[f"{metric['key']}__delta"] = _compute_relative_rate(curr, peer)
        rows.append(record)
    summary_row = {"date": "总计"}
    has_summary = False
    for metric in prepared:
        entries = list(metric["entries"].values())
        current_values: List[float] = []
        peer_values: List[float] = []
        for entry in entries:
            if not entry:
                continue
            curr_val = _to_float_or_none(entry.get("current"))
            if curr_val is not None:
                current_values.append(curr_val)
            peer_val = _to_float_or_none(entry.get("peer"))
            if peer_val is not None:
                peer_values.append(peer_val)
        value_type = metric.get("value_type")
        if value_type == "constant":
            summary_current = current_values[0] if current_values else None
            summary_peer = peer_values[0] if peer_values else None
        elif value_type == "temperature":
            summary_current = statistics.fmean(current_values) if current_values else None
            summary_peer = statistics.fmean(peer_values) if peer_values else None
        else:
            summary_current = sum(current_values) if current_values else None
            summary_peer = sum(peer_values) if peer_values else None
        summary_delta = _compute_relative_rate(summary_current, summary_peer)
        summary_row[f"{metric['key']}__current"] = summary_current
        summary_row[f"{metric['key']}__peer"] = summary_peer
        summary_row[f"{metric['key']}__delta"] = summary_delta
        if (
            summary_current is not None
            or summary_peer is not None
            or summary_delta is not None
        ):
            has_summary = True
    if has_summary:
        rows.append(summary_row)
    return {
        "dates": dates,
        "metrics": prepared,
        "rows": rows,
        "summary": summary_row if has_summary else None,
    }


def _extract_json_block(raw: str) -> Optional[str]:
    if not raw:
        return None
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return raw[start : end + 1]


def _parse_json_response(raw: str, stage: str) -> Dict[str, Any]:
    if not raw:
        raise ValueError(f"{stage} 阶段返回为空")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        json_block = _extract_json_block(raw)
        if json_block:
            try:
                return json.loads(json_block)
            except json.JSONDecodeError:
                pass
        raise ValueError(f"{stage} 阶段 JSON 解析失败: {exc}")


def _call_model(prompt: str) -> str:
    model = _get_model()
    response = model.generate_content(prompt)
    text = (response.text or "").strip() if response else ""
    if not text and response and getattr(response, "candidates", None):
        parts = []
        for candidate in response.candidates:
            for part in getattr(candidate, "content", {}).parts or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    parts.append(part_text)
        text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("模型未返回内容")
    return text


def _run_json_stage(stage: str, prompt: str, retries: int = 2) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        raw = _call_model(prompt)
        try:
            return _parse_json_response(raw, stage)
        except ValueError as exc:  # pylint: disable=broad-except
            last_error = exc
            _logger.warning("%s 阶段第 %s 次解析失败: %s", stage, attempt, exc)
    raise RuntimeError(f"{stage} 阶段多次解析失败: {last_error}")



def _current_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update_job(job_id: str, **kwargs: Any) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id].update(kwargs)


def _get_model() -> genai.GenerativeModel:
    global _model, _model_name
    if _model is None:
        settings = _load_gemini_settings()
        genai.configure(api_key=settings["api_key"])
        _model_name = settings["model"]
        _model = genai.GenerativeModel(_model_name)
    return _model


def _preprocess_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    预处理 API 返回的原始 payload，为 Prompt 和 HTML 渲染准备数据。
    """
    rows = payload.get("rows") or []
    meta = {
        "unit_label": payload.get("unit_label"),
        "analysis_mode": payload.get("analysis_mode"),
        "analysis_mode_label": payload.get("analysis_mode_label"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
    }

    processed_metrics = []
    for row in rows:
        if row.get("missing"):
            continue

        label = row.get("label")
        unit = row.get("unit")
        decimals = row.get("decimals")
        if not isinstance(decimals, int):
            decimals = 2
        # 优先取 range 模式下的 total_current，否则取 current
        val = row.get("total_current")
        if val is None:
            val = row.get("current")

        # 简单的格式化辅助
        val_fmt = f"{val:.{decimals}f}" if isinstance(val, (int, float)) else "--"

        peer_total = row.get("total_peer")
        if peer_total is None:
            peer_total = row.get("peer")

        # 同比
        delta = row.get("total_delta") if row.get("total_delta") is not None else row.get("delta")
        if isinstance(delta, (int, float)):
            delta_fmt = f"{delta:+.2f}%"
            if delta > 0:
                delta_color = "#d32f2f" 
            elif delta < 0:
                delta_color = "#2e7d32"
            else:
                delta_color = "#7f8c8d"
        else:
            delta_fmt = "--"
            delta_color = "#7f8c8d"

        # 环比
        ring_value = row.get("ring_ratio")
        if isinstance(ring_value, (int, float)):
            ring_fmt = f"{ring_value:+.2f}%"
            if ring_value > 0:
                ring_color = "#d32f2f" 
            elif ring_value < 0:
                ring_color = "#2e7d32"
            else:
                ring_color = "#7f8c8d"
        else:
            ring_value = None
            ring_fmt = "--"
            ring_color = "#7f8c8d"

        # 构造 timeline_json (for echarts)
        timeline = row.get("timeline") or []
        chart_data = []
        for entry in timeline:
            d = entry.get("date")
            # 截取 MM-DD
            if d and len(d) >= 10:
                d_str = d[5:10]
            else:
                d_str = d or ""
            chart_data.append({
                "d": d_str,
                "v": entry.get("current"),
                "p": entry.get("peer")
            })
        
        processed_metrics.append({
            "key": row.get("key") or row.get("label"),
            "label": label,
            "unit": unit,
            "value": val,
            "peer_value": peer_total,
            "delta": delta,
            "delta_fmt": delta_fmt,
            "delta_color": delta_color,
            "ring": ring_value,
            "ring_fmt": ring_fmt,
            "ring_color": ring_color,
            "is_temperature": row.get("value_type") == "temperature",
            "value_type": row.get("value_type"),
            "decimals": decimals,
            "timeline_entries": timeline,
            "timeline_json": json.dumps(chart_data, ensure_ascii=False)
        })

    ring_compare = _build_ring_compare_payload(payload)
    if ring_compare:
        entries = ring_compare.get("entries") or []
        entry_by_key = {entry.get("key"): entry for entry in entries if entry.get("key")}
        entry_by_label = {entry.get("label"): entry for entry in entries if entry.get("label")}
        for metric in processed_metrics:
            if metric.get("ring") is not None:
                continue
            match = entry_by_key.get(metric.get("key")) or entry_by_label.get(metric.get("label"))
            if not match:
                continue
            rate = match.get("rate")
            if isinstance(rate, (int, float)):
                metric["ring"] = rate
                metric["ring_fmt"] = _format_percent_text(rate)
                if rate > 0:
                    metric["ring_color"] = "#d32f2f"
                elif rate < 0:
                    metric["ring_color"] = "#2e7d32"
                else:
                    metric["ring_color"] = "#7f8c8d"
            else:
                metric["ring"] = None

    timeline_matrix = _build_timeline_matrix(processed_metrics)

    return {
        "meta": meta,
        "metrics": processed_metrics,
        "ring_compare": ring_compare,
        "timeline_matrix": timeline_matrix,
        "raw_warnings": payload.get("warnings") or []
    }


def _build_insight_prompt(processed_data: Dict[str, Any]) -> str:
    data_json = _safe_json_dumps(processed_data)
    return f"{INSIGHT_PROMPT_TEMPLATE}\n\n### 数据\n{data_json}"


def _build_layout_prompt(processed_data: Dict[str, Any], insight_data: Dict[str, Any]) -> str:
    data_json = _safe_json_dumps(processed_data)
    insight_json = _safe_json_dumps(insight_data)
    return (
        f"{LAYOUT_PROMPT_TEMPLATE}\n\n### 数据\n{data_json}\n\n### 洞察\n{insight_json}"
    )


def _build_content_prompt(
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
) -> str:
    insight_json = _safe_json_dumps(insight_data)
    layout_json = _safe_json_dumps(layout_data)
    return (
        f"{CONTENT_PROMPT_TEMPLATE}\n\n### 洞察 JSON\n{insight_json}\n"
        f"\n### 版面规划 JSON\n{layout_json}\n"
    )


def _generate_report_html(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
    content_data: Dict[str, Any],
) -> str:
    """
    使用 Python 拼接 HTML，替代 LLM 渲染。
    """
    meta = processed_data.get("meta") or {}
    metrics = processed_data.get("metrics") or []
    timeline_matrix = processed_data.get("timeline_matrix") or {}
    sections = layout_data.get("sections") or []
    section_contents = content_data.get("section_contents") or {}
    callouts = content_data.get("callouts") or []
    
    # 1. 基础样式
    css = """
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8f9fa; color: #333; margin: 0; padding: 20px; }
        .header { margin-bottom: 24px; border-bottom: 2px solid #e0e0e0; padding-bottom: 16px; text-align: center; }
        .header h1 { margin: 0 0 12px 0; font-size: 28px; color: #2c3e50; letter-spacing: 1px; }
        .meta-info { font-size: 13px; color: #555; display: flex; justify-content: center; gap: 24px; flex-wrap: wrap; }
        .cards-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }
        .card { background: #fff; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 16px 20px; border-left: 5px solid #3498db; transition: transform 0.2s; }
        .card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,0.12); }
        .card h3 { margin: 0 0 10px 0; font-size: 15px; color: #7f8c8d; font-weight: 600; }
        .card .value { font-size: 26px; font-weight: 700; color: #2c3e50; margin-bottom: 6px; }
        .card .unit { font-size: 13px; color: #95a5a6; font-weight: normal; margin-left: 6px; }
        .card .delta-row { display: flex; justify-content: space-between; margin-top: 12px; font-size: 13px; border-top: 1px solid #f0f0f0; padding-top: 8px; }
        .card .delta-val { font-weight: 600; }
        .analysis-section { background: #fff; padding: 24px; border-radius: 10px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .analysis-section h2 { font-size: 20px; margin-top: 0; margin-bottom: 18px; border-left: 5px solid #27ae60; padding-left: 12px; color: #2c3e50; }
        .callouts { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }
        .callout { border-radius: 10px; padding: 16px 20px; border-left: 5px solid #3498db; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
        .callout.warning { border-left-color: #f39c12; }
        .callout.danger { border-left-color: #e74c3c; }
        .callout h4 { margin: 0 0 8px 0; font-size: 15px; color: #2c3e50; }
        .callout p { margin: 0; font-size: 14px; color: #555; line-height: 1.5; }
        .ring-section__header { margin-bottom: 10px; font-size: 14px; color: #475569; }
        .ring-section__note { font-size: 14px; color: #b45309; margin-top: 6px; }
        .ring-summary__table { margin-top: 12px; }
        .ring-summary__table td, .ring-summary__table th { text-align: center; }
        .ring-unit { font-size: 12px; color: #94a3b8; margin-left: 4px; }
        .ring-summary-line { margin-top: 10px; font-size: 14px; color: #334155; }
        .chart-wrapper { height: 420px; margin-top: 24px; border: 1px solid #eee; border-radius: 8px; padding: 12px; background: #fff; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
        th, td { border: 1px solid #e0e0e0; padding: 10px 12px; text-align: center; }
        th { background: #f4f6f7; color: #555; font-weight: 600; }
        tr:nth-child(even) { background: #fafafa; }
        .metric-selector { margin-bottom: 12px; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 200px; }
        .timeline-table th { background: #e2e8f0; color: #334155; }
        .timeline-table .sub-head th { background: #f8fafc; color: #475569; font-size: 13px; }
        .timeline-table td:first-child { font-weight: 600; color: #1e293b; }
        .delta-positive { color: #d32f2f; font-weight: 600; }
        .delta-negative { color: #2e7d32; font-weight: 600; }
        .delta-neutral { color: #475569; font-weight: 600; }
        .delta-muted { color: #94a3b8; font-weight: 600; }
    """

    # 2. 构建页面主体
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<style>{css}</style>",
        "<script src='https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'></script>",
        "</head><body>",
        f"<div class='header'><h1>智能分析报告：{insight_data.get('headline', '数据分析报告')}</h1>",
        "<div class='meta-info'>",
        f"<span>单位：{meta.get('unit_label')}</span>",
        f"<span>模式：{meta.get('analysis_mode_label')}</span>",
        f"<span>日期：{meta.get('start_date')} ~ {meta.get('end_date')}</span>",
        f"<span>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>",
        "</div></div>"
    ]

    # 3. 指标卡片
    html_parts.append("<div class='cards-container'>")
    for m in metrics:
        value_text = _format_number(m.get("value"), m.get("decimals", 2))
        delta_style = f"color: {m['delta_color']}"
        # Use .get() for ring properties to be safe, though _preprocess_payload should provide them
        ring_fmt = m.get('ring_fmt', '--')
        ring_color = m.get('ring_color', '#7f8c8d')

        html_parts.append(f"""
            <div class='card'>
                <h3>{m['label']}</h3>
                <div class='value'>{value_text}<span class='unit'>{m['unit'] or ''}</span></div>
                <div class='delta-row'>
                    <span>同比 <span style='{delta_style}' class='delta-val'>{m['delta_fmt']}</span></span>
                    <span>环比 <span style='color: {ring_color}' class='delta-val'>{ring_fmt}</span></span>
                </div>
            </div>
        """)
    html_parts.append("</div>")

    # 4. 重点提示
    if callouts:
        html_parts.append("<div class='callouts'>")
        for c in callouts:
            level = c.get('level', 'info')
            html_parts.append(f"""
                <div class='callout {level}'>
                    <h4>{c.get('title')}</h4>
                    <p>{c.get('body')}</p>
                </div>
            """)
    html_parts.append("</div>")

    # 同比比较
    yoy_entries = []
    for m in metrics:
        current = m.get("value")
        peer_val = m.get("peer_value")
        if current is None and peer_val is None:
            continue
        yoy_entries.append(
            {
                "label": m.get("label"),
                "unit": m.get("unit") or "",
                "current": current,
                "peer": peer_val,
                "delta": m.get("delta"),
                "decimals": m.get("decimals", 2),
            }
        )
    if yoy_entries:
        html_parts.append("<div class='analysis-section'>")
        html_parts.append("<h2>同比比较</h2>")
        html_parts.append(
            "<table class='ring-summary__table'><thead><tr>"
            "<th>指标</th><th>本期累计</th><th>同期累计</th><th>同比</th>"
            "</tr></thead><tbody>"
        )
        for entry in yoy_entries:
            current_text = _format_number(entry["current"], entry["decimals"])
            peer_text = _format_number(entry["peer"], entry["decimals"])
            delta_text = _format_percent_text(entry.get("delta"))
            unit_html = f"<span class='ring-unit'>{entry['unit']}</span>" if entry["unit"] else ""
            html_parts.append(
                "<tr>"
                f"<td>{entry['label']}</td>"
                f"<td>{current_text}{unit_html}</td>"
                f"<td>{peer_text}{unit_html}</td>"
                f"<td>{delta_text}</td>"
                "</tr>"
            )
        html_parts.append("</tbody></table></div>")

    ring_data = processed_data.get("ring_compare") or {}
    if ring_data and (ring_data.get("entries") or ring_data.get("note")):
        html_parts.append("<div class='analysis-section'>")
        html_parts.append("<h2>环比比较</h2>")
        header_bits = []
        if ring_data.get("current_range"):
            header_bits.append(f"本期：{ring_data['current_range']}")
        if ring_data.get("previous_range"):
            header_bits.append(f"上期：{ring_data['previous_range']}")
        if header_bits:
            html_parts.append(f"<p class='ring-section__header'>{' ｜ '.join(header_bits)}</p>")
        entries = ring_data.get("entries") or []
        if entries:
            html_parts.append("<table class='ring-summary__table'>")
            html_parts.append(
                "<thead><tr><th>指标</th><th>本期累计</th><th>上期累计</th><th>环比</th></tr></thead><tbody>"
            )
            for entry in entries:
                decimals = entry.get("decimals", 2)
                current_text = _format_number(entry.get("current"), decimals)
                prev_text = _format_number(entry.get("previous"), decimals)
                rate_text = _format_percent_text(entry.get("rate"))
                unit = entry.get("unit") or ""
                unit_html = f"<span class='ring-unit'>{unit}</span>" if unit else ""
                html_parts.append(
                    "<tr>"
                    f"<td>{entry.get('label')}</td>"
                    f"<td>{current_text}{unit_html}</td>"
                    f"<td>{prev_text}{unit_html}</td>"
                    f"<td>{rate_text}</td>"
                    "</tr>"
                )
            html_parts.append("</tbody></table>")
        elif ring_data.get("note"):
            html_parts.append(f"<p class='ring-section__note'>{ring_data['note']}</p>")
        if ring_data.get("summary_lines"):
            for line in ring_data["summary_lines"]:
                html_parts.append(f"<p class='ring-summary-line'>{line}</p>")
        html_parts.append("</div>")

    # 区间明细（逐日）
    timeline_metrics = timeline_matrix.get("metrics") or []
    timeline_rows = timeline_matrix.get("rows") or []
    if timeline_metrics and timeline_rows:
        html_parts.append("<div class='analysis-section'>")
        html_parts.append("<h2>区间明细（逐日）</h2>")
        html_parts.append("<table class='timeline-table'>")
        html_parts.append("<thead>")
        html_parts.append("<tr><th rowspan='2'>日期</th>")
        for metric in timeline_metrics:
            unit_html = f"<span class='ring-unit'>{metric.get('unit')}</span>" if metric.get("unit") else ""
            html_parts.append(f"<th colspan='3'>{metric.get('label')}{unit_html}</th>")
        html_parts.append("</tr>")
        html_parts.append("<tr class='sub-head'>")
        for _ in timeline_metrics:
            html_parts.append("<th>本期</th><th>同期</th><th>同比</th>")
        html_parts.append("</tr></thead><tbody>")
        for row in timeline_rows:
            date_label = row.get("date") or ""
            html_parts.append(f"<tr><td>{date_label}</td>")
            for metric in timeline_metrics:
                key = metric.get("key")
                decimals = metric.get("decimals", 2)
                current_val = _format_number(row.get(f"{key}__current"), decimals)
                peer_val = _format_number(row.get(f"{key}__peer"), decimals)
                delta_value = row.get(f"{key}__delta")
                delta_text = _format_percent_text(delta_value)
                delta_class = _classify_delta(delta_value)
                html_parts.append(f"<td>{current_val}</td>")
                html_parts.append(f"<td>{peer_val}</td>")
                html_parts.append(f"<td class='{delta_class}'>{delta_text}</td>")
            html_parts.append("</tr>")
        html_parts.append("</tbody></table></div>")

    # 5. 图表区域 (含数据注入)
    timeline_data_json = json.dumps([
        {
            "key": m["label"],  # Use label as key for simplicity in selector
            "label": m["label"],
            "unit": m["unit"],
            "is_temp": m["is_temperature"],
            "data": json.loads(m["timeline_json"])  # restore to list
        }
        for m in metrics if m.get("timeline_entries")
    ], ensure_ascii=False)
    
    chart_html = f"""
    <div class='analysis-section'>
        <h2>趋势分析</h2>
        <select id='metricSelect' class='metric-selector' onchange='updateChart()'></select>
        <div id='mainChart' class='chart-wrapper'></div>
        <script>
            var rawData = {timeline_data_json};
            var myChart = echarts.init(document.getElementById('mainChart'));
            var selector = document.getElementById('metricSelect');
            
            // Init Selector
            rawData.forEach(function(item, index) {{
                var opt = document.createElement('option');
                opt.value = index;
                opt.innerHTML = item.label;
                selector.appendChild(opt);
            }});

            function updateChart() {{
                var idx = selector.value;
                var currentMetric = rawData[idx];
                var tempMetric = rawData.find(m => m.is_temp) || null;
                
                var dates = currentMetric.data.map(i => i.d);
                var series = [];
                var yAxis = [
                    {{ type: 'value', name: currentMetric.unit || '', position: 'left' }}
                ];

                // 左轴：选定指标
                series.push({{
                    name: currentMetric.label + ' (本期)',
                    type: 'line',
                    data: currentMetric.data.map(i => i.v),
                    smooth: true,
                    yAxisIndex: 0,
                    itemStyle: {{ color: '#3498db' }}
                }});
                series.push({{
                    name: currentMetric.label + ' (同期)',
                    type: 'line',
                    data: currentMetric.data.map(i => i.p),
                    smooth: true,
                    lineStyle: {{ type: 'dashed' }},
                    yAxisIndex: 0,
                    itemStyle: {{ color: '#95a5a6' }}
                }});

                // 右轴：气温 (如果存在且不是自己)
                if (tempMetric && tempMetric.label !== currentMetric.label) {{
                    yAxis.push({{ type: 'value', name: '气温 ℃', position: 'right', splitLine: {{ show: false }} }});
                    series.push({{
                        name: '平均气温',
                        type: 'line',
                        data: tempMetric.data.map(i => i.v),
                        smooth: true,
                        yAxisIndex: 1,
                        itemStyle: {{ color: '#e67e22' }},
                        areaStyle: {{ opacity: 0.1 }}
                    }});
                }}

                var option = {{
                    tooltip: {{ trigger: 'axis' }},
                    legend: {{ bottom: 0 }},
                    grid: {{ top: 40, bottom: 30, left: 50, right: 50 }},
                    xAxis: {{ type: 'category', data: dates }},
                    yAxis: yAxis,
                    series: series
                }};
                myChart.setOption(option, true);
            }}
            
            if(rawData.length > 0) updateChart();
            window.onresize = function() {{ myChart.resize(); }};
        </script>
    </div>
    """
    html_parts.append(chart_html)

    # 6. 正文章节 + 表格
    for sec in sections:
        sec_id = sec.get("id")
        content = section_contents.get(sec_id, "暂无内容")
        
        # 渲染指标表格 (如果有 metrics 定义)
        table_html = ""
        sec_metrics_keys = sec.get("metrics") or []
        target_metrics = [m for m in metrics if m["label"] in sec_metrics_keys] # 简单按 Label 匹配
        
        if target_metrics:
            table_html += "<table><thead><tr><th>日期</th>"
            for m in target_metrics:
                table_html += f"<th>{m['label']}<br>本期</th><th>{m['label']}<br>同期</th>"
            table_html += "</tr></thead><tbody>"
            
            # 假设所有 timeline 长度一致，取第一个非空的
            sample_tl = next((m["timeline_entries"] for m in target_metrics if m.get("timeline_entries")), [])
            for i, entry in enumerate(sample_tl):
                date_str = entry["date"]
                table_html += f"<tr><td>{date_str}</td>"
                for m in target_metrics:
                    # 保护性取值
                    tl = m.get("timeline_entries") or []
                    if i < len(tl):
                        cur = tl[i].get("current")
                        peer = tl[i].get("peer")
                        c_val = f"{float(cur):.2f}" if cur is not None else "-"
                        p_val = f"{float(peer):.2f}" if peer is not None else "-"
                        table_html += f"<td>{c_val}</td><td>{p_val}</td>"
                    else:
                        table_html += "<td>-</td><td>-</td>"
                table_html += "</tr>"
            table_html += "</tbody></table>"

        html_parts.append(f"""
            <div class='analysis-section'>
                <h2>{sec.get('title')}</h2>
                <div class='insight-text'>{content}</div>
                {table_html}
            </div>
        """)

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def _generate_report(job_id: str, payload: Dict[str, Any]) -> None:
    try:
        meta = payload.get("meta") or {}
        _logger.info(
            "AI report job %s started (unit=%s, mode=%s, metrics=%s)",
            job_id,
            meta.get("unit_key") or meta.get("unit_label"),
            meta.get("analysis_mode"),
            ",".join(payload.get("resolved_metrics") or []),
        )
        processed_data = _preprocess_payload(payload)
        _update_job(job_id, status="running", stage="insight", started_at=_current_time_iso())

        insight_prompt = _build_insight_prompt(processed_data)
        insight_data = _run_json_stage("洞察分析", insight_prompt)
        _update_job(job_id, stage="layout", insight=insight_data)

        layout_prompt = _build_layout_prompt(processed_data, insight_data)
        layout_data = _run_json_stage("结构规划", layout_prompt)
        _update_job(job_id, stage="render", layout=layout_data)

        # NEW: 阶段三改为“内容撰写”，只生成段落 JSON
        content_prompt = _build_content_prompt(insight_data, layout_data)
        content_data = _run_json_stage("内容撰写", content_prompt)
        
        # Python 组装 HTML
        html_report = _generate_report_html(processed_data, insight_data, layout_data, content_data)

        _update_job(
            job_id,
            status="ready",
            stage="ready",
            report=html_report,
            model=_model_name,
            finished_at=_current_time_iso(),
        )
        _logger.info("AI report job %s finished successfully", job_id)
    except Exception as exc:  # pylint: disable=broad-except
        _logger.warning("生成 AI 报告失败: %s", exc)
        _update_job(
            job_id,
            status="failed",
            stage="failed",
            error=str(exc),
            finished_at=_current_time_iso(),
        )
        _logger.info("AI report job %s marked as failed", job_id)


def enqueue_ai_report_job(payload: Dict[str, Any]) -> str:
    """
    入队 AI 报告任务，返回 job_id。
    """
    job_id = uuid.uuid4().hex
    snapshot = {
        "job_id": job_id,
        "status": "pending",
        "stage": "pending",
        "created_at": _current_time_iso(),
        "started_at": None,
        "report": None,
        "error": None,
        "model": None,
        "insight": None,
        "layout": None,
    }
    with _lock:
        _jobs[job_id] = snapshot
    payload_copy = copy.deepcopy(payload)
    _executor.submit(_generate_report, job_id, payload_copy)
    _logger.info(
        "AI report job %s enqueued (unit=%s, metrics=%s)",
        job_id,
        payload.get("unit_key") or payload.get("unit_label"),
        ",".join(payload.get("resolved_metrics") or []),
    )
    return job_id


def get_report_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    读取 AI 报告任务状态。
    """
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        return copy.deepcopy(job)
