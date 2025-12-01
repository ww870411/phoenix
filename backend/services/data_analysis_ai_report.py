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

INSIGHT_PROMPT_TEMPLATE = """你是一名热力行业数据分析师。请阅读给定的 JSON 数据（已包含指标的同比/环比/趋势/温度相关性结果），仅输出结构化 JSON，不要出现 Markdown 或解释文字。

输出 JSON 结构：
{
  "headline": "一句话概括整体运行结论",
  "key_findings": [
    {
      "metric": "指标名称",
      "status": "up | down | stable",
      "evidence": "引用 value/delta/ring/stats 的文字，说明原因",
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
- `status` 依据 delta/ring 与趋势判断；
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

REPORT_STYLE_CSS = """body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8f9fa; color: #333; margin: 0; padding: 20px; }
.header { margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; padding-bottom: 15px; text-align: center; }
.header h1 { margin: 0 0 10px 0; font-size: 28px; color: #2c3e50; letter-spacing: 1px; }
.meta-info { font-size: 13px; color: #555; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }
.meta-item { display: flex; align-items: center; gap: 5px; }
.meta-icon { color: #3498db; }
.metric-tags { margin-top: 10px; font-size: 12px; color: #7f8c8d; }
.cards-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin-bottom: 24px; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); padding: 12px 16px; border-left: 4px solid #3498db; }
.card h3 { margin: 0 0 8px 0; font-size: 14px; color: #7f8c8d; font-weight: 600; }
.card .value { font-size: 22px; font-weight: 700; color: #2c3e50; margin-bottom: 4px; }
.card .unit { font-size: 12px; color: #95a5a6; font-weight: normal; margin-left: 4px; }
.card .delta-row { display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; }
.card .delta-item { display: flex; flex-direction: column; }
.card .delta-label { color: #999; font-size: 10px; margin-bottom: 2px; }
.card .delta-val { font-weight: 600; }
.analysis-section { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.analysis-section h2 { font-size: 18px; margin-top: 0; border-left: 4px solid #27ae60; padding-left: 10px; color: #2c3e50; }
.insight-item { margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px dashed #eee; }
.insight-item:last-child { border-bottom: none; }
.insight-label { font-weight: 700; color: #34495e; }
.insight-text { font-size: 14px; line-height: 1.5; color: #555; }
.chart-container { background: #fff; padding: 16px; border-radius: 8px; height: 400px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: relative; }
.callouts { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 24px; }
.callout { border-radius: 8px; padding: 12px 16px; border-left: 4px solid #3498db; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.callout.warning { border-left-color: #f39c12; }
.callout.danger { border-left-color: #e74c3c; }
.callout h4 { margin: 0 0 6px 0; font-size: 14px; }
.callout p { margin: 0; font-size: 13px; color: #555; }
"""

REPORT_PROMPT_TEMPLATE = """你是高级报告撰稿人。请根据以下材料生成完整的 HTML5 报告：
1. 预处理后的指标数据；
2. 阶段一的洞察 JSON；
3. 阶段二的章节规划 JSON；
4. 必须使用的 CSS 片段（嵌入 <style>）。

输出要求：
- 完整 HTML 文本（含 <!DOCTYPE html>、<html>、<head>、<body>）；
- <head> 中嵌入提供的 CSS（不可使用 ```css 或 ```html 这类 Markdown 代码块）；
- 页头固定标题“智能分析报告”，并展示单位、分析模式、日期范围、生成时间（从 meta 中获取 unit_label/start_date/end_date 等字段）；缺失单位字段视为错误；
- 指标卡片按 `metrics` 数据渲染，引用 delta/ring 颜色；
- “数据洞察”区根据 sections 与 key_findings 生成多段落文字；
- “重点提示”区渲染 callouts；
- 最后插入一个引用 ECharts CDN 的双轴折线图脚本，series 数据来自 `metrics.timeline_json`；
- 为每个指标输出一个“逐日明细”表格（日期/本期/同期/同比），必须使用 `timeline_entries` 字段（已按日期给出 current/peer/delta_pct），若缺少该表视为不合格；
- 图表需要提供指标切换控件（如按钮或下拉），默认加载首个指标；切换时更新左轴数据，右轴保留气温指标，可直接遍历 `metrics.timeline_entries` 或 `timeline_json`；
- 全文使用中文，禁止输出任何 Markdown 代码块（包括 ```html/```css/```），只输出 HTML 内容。
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


def _build_insight_prompt(processed_data: Dict[str, Any]) -> str:
    data_json = _safe_json_dumps(processed_data)
    return f"{INSIGHT_PROMPT_TEMPLATE}\n\n### 数据\n{data_json}"


def _build_layout_prompt(processed_data: Dict[str, Any], insight_data: Dict[str, Any]) -> str:
    data_json = _safe_json_dumps(processed_data)
    insight_json = _safe_json_dumps(insight_data)
    return (
        f"{LAYOUT_PROMPT_TEMPLATE}\n\n### 数据\n{data_json}\n\n### 洞察\n{insight_json}"
    )


def _build_report_prompt(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
) -> str:
    data_json = _safe_json_dumps(processed_data)
    insight_json = _safe_json_dumps(insight_data)
    layout_json = _safe_json_dumps(layout_data)
    css_block = REPORT_STYLE_CSS.strip()
    return (
        f"{REPORT_PROMPT_TEMPLATE}\n\n### CSS（请直接写入 <style> 标签中）\n{css_block}\n"
        f"\n### 预处理数据\n{data_json}\n"
        f"\n### 洞察 JSON\n{insight_json}\n"
        f"\n### 版面规划 JSON\n{layout_json}\n"
    )


def _calculate_trend_stats(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算趋势特征：重点关注近期走势（后半段 vs 前半段）。"""
    if not timeline:
        return {}
    
    current_values = [float(t["current"]) for t in timeline if t.get("current") is not None]
    
    stats = {}
    if current_values:
        stats["current_avg"] = statistics.mean(current_values)
        
        # 计算“期内趋势”：后半段均值 vs 前半段均值
        n = len(current_values)
        if n >= 2:
            mid = n // 2
            first_half = current_values[:mid]
            second_half = current_values[mid:]
            avg1 = statistics.mean(first_half)
            avg2 = statistics.mean(second_half)
            
            if avg1 != 0:
                trend_pct = ((avg2 - avg1) / abs(avg1)) * 100
                stats["recent_trend_pct"] = round(trend_pct, 2)
                if trend_pct > 5:
                    stats["recent_trend_desc"] = "呈上升趋势"
                elif trend_pct < -5:
                    stats["recent_trend_desc"] = "呈下降趋势"
                else:
                    stats["recent_trend_desc"] = "走势平稳"
            else:
                stats["recent_trend_desc"] = "数据不足"

    return stats


def _calculate_correlation(data_x: List[float], data_y: List[float]) -> Optional[float]:
    """计算皮尔逊相关系数。"""
    if len(data_x) != len(data_y) or len(data_x) < 2:
        return None
    try:
        # 使用 statistics.correlation (Python 3.10+) 或手写简单实现
        if hasattr(statistics, 'correlation'):
            return statistics.correlation(data_x, data_y)
        
        # 简易实现
        n = len(data_x)
        sum_x = sum(data_x)
        sum_y = sum(data_y)
        sum_x_sq = sum(x * x for x in data_x)
        sum_y_sq = sum(y * y for y in data_y)
        sum_xy = sum(x * y for x, y in zip(data_x, data_y))
        
        denominator = math.sqrt((n * sum_x_sq - sum_x ** 2) * (n * sum_y_sq - sum_y ** 2))
        if denominator == 0:
            return 0
        numerator = n * sum_xy - sum_x * sum_y
        return numerator / denominator
    except Exception:
        return None


def _preprocess_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    核心预处理：清洗数据、计算同比、统计趋势、分析气温相关性。
    AI 将直接使用这里的计算结果，不再自行运算。
    """
    rows = payload.get("rows") or []
    processed_metrics = []
    
    # 1. 提取气温数据（如果有），用于计算相关性
    temp_timeline_map = {} # date -> temperature value
    for row in rows:
        if row.get("value_type") == "temperature" and row.get("timeline"):
            for t in row["timeline"]:
                if t.get("date") and t.get("current") is not None:
                    temp_timeline_map[t["date"]] = float(t["current"])
            break # 假设只有一个主气温指标

    for row in rows:
        # 基础数据提取
        current = row.get("total_current") if row.get("total_current") is not None else row.get("current")
        peer = row.get("total_peer") if row.get("total_peer") is not None else row.get("peer")
        
        # 1. 严格计算同比 (Delta)
        delta = None
        delta_color = "#333" # 默认黑色
        arrow = ""
        
        if current is not None and peer is not None and peer != 0:
            delta = ((float(current) - float(peer)) / abs(float(peer))) * 100
            # 颜色逻辑：升高用红色，下降用绿色
            if delta > 0:
                delta_color = "#d93025" # Red
                arrow = "↑"
            elif delta < 0:
                delta_color = "#188038" # Green
                arrow = "↓"

        # 1.5 环比 (Ring Growth) - 新增逻辑
        ring_rate = row.get("ring_growth")
        ring_fmt = "--"
        ring_color = "#666"
        if ring_rate is not None:
            r_val = float(ring_rate)
            r_arrow = "↑" if r_val > 0 else "↓" if r_val < 0 else ""
            ring_fmt = f"{r_arrow} {abs(r_val):.2f}%"
            ring_color = "#d93025" if r_val > 0 else "#188038" if r_val < 0 else "#666"
        
        # 2. 时间序列统计 (Stats)
        timeline = row.get("timeline") or []
        stats = _calculate_trend_stats(timeline)
        
        # 3. 时间序列明细 + 气温相关性
        correlation = None
        trend_desc = ""
        timeline_entries = []
        if timeline and temp_timeline_map:
            # 对齐数据
            metric_vals = []
            temp_vals = []
            for t in timeline:
                d = t.get("date")
                v = t.get("current")
                if d in temp_timeline_map and v is not None:
                    metric_vals.append(float(v))
                    temp_vals.append(temp_timeline_map[d])

            corr = _calculate_correlation(metric_vals, temp_vals)
            if corr is not None:
                correlation = round(corr, 2)
                if correlation < -0.6:
                    trend_desc = "与气温呈显著负相关(气温越低数值越高)"
                elif correlation > 0.6:
                    trend_desc = "与气温呈显著正相关"

        for entry in timeline:
            date_val = entry.get("date")
            current_val = entry.get("current")
            peer_val = entry.get("peer")
            delta_pct = None
            if (
                current_val is not None
                and peer_val is not None
                and peer_val not in (0, 0.0)
            ):
                try:
                    delta_pct = (
                        (float(current_val) - float(peer_val)) / abs(float(peer_val))
                    ) * 100
                except (ValueError, ZeroDivisionError):
                    delta_pct = None
            timeline_entries.append(
                {
                    "date": date_val,
                    "current": current_val,
                    "peer": peer_val,
                    "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
                }
            )

        processed_metrics.append({
            "label": row.get("label"),
            "unit": row.get("unit"),
            "value": current,
            "peer_value": peer,
            "delta_fmt": f"{arrow} {abs(delta):.2f}%" if delta is not None else "--",
            "delta_color": delta_color,
            "ring_fmt": ring_fmt,
            "ring_color": ring_color,
            "stats": stats,
            "correlation_with_temp": correlation,
            "trend_description": trend_desc,
            "is_temperature": row.get("value_type") == "temperature",
            "timeline_entries": timeline_entries,
            # 保留 timeline 供 ECharts 使用，但 AI 不需再读 timeline 计算
            "timeline_json": json.dumps([{
                "d": t.get("date"),
                "v": t.get("current"),
                "p": t.get("peer")
            } for t in timeline]) # 简化字段名以节省 Token
        })

    return {
        "meta": payload.get("meta"),
        "metrics": processed_metrics,
        "generated_at": _current_time_iso()
    }


def _build_prompt_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = payload.get("rows") or []
    trimmed_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        trimmed_rows.append(
            {
                "key": row.get("key"),
                "label": row.get("label"),
                "unit": row.get("unit"),
                "current": row.get("current"),
                "peer": row.get("peer"),
                "delta": row.get("delta"),
                "total_current": row.get("total_current"),
                "total_peer": row.get("total_peer"),
                "total_delta": row.get("total_delta"),
                "value_type": row.get("value_type"),
            },
        )

    meta = {
        "unit_key": payload.get("unit_key"),
        "unit_label": payload.get("unit_label"),
        "analysis_mode": payload.get("analysis_mode"),
        "analysis_mode_label": payload.get("analysis_mode_label"),
        "start_date": payload.get("start_date"),
        "end_date": payload.get("end_date"),
    }

    return {
        "meta": meta,
        "rows": trimmed_rows,
        "plan_comparison": payload.get("plan_comparison"),
        "warnings": payload.get("warnings"),
        "requested_metrics": payload.get("requested_metrics"),
        "resolved_metrics": payload.get("resolved_metrics"),
    }

def _get_model() -> genai.GenerativeModel:
    global _model, _model_name  # pylint: disable=global-statement
    if _model is not None:
        return _model
    settings = _load_gemini_settings()
    genai.configure(api_key=settings["api_key"])
    _model_name = settings["model"]
    _model = genai.GenerativeModel(_model_name)
    return _model


def _update_job(job_id: str, **updates: Any) -> None:
    with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id].update(updates)


def _current_time_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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

        report_prompt = _build_report_prompt(processed_data, insight_data, layout_data)
        html_report = _call_model(report_prompt)

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
