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
from typing import Any, Dict, Optional

import math
import statistics
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from backend.config import DATA_DIRECTORY

DATA_ROOT = Path(DATA_DIRECTORY)
API_KEY_PATH = DATA_ROOT / "api_key.json"

PROMPT_TEMPLATE = """你是一个数据可视化专家。请基于以下**已预处理好的 JSON 数据**，生成一个 HTML 单页报告。

### 关键原则（严禁修改数据）
1. **直接引用**：JSON 中的 `value`, `delta_percent`, `correlation_with_temp` 等字段都是**已经计算好**的精确值。请直接在 HTML 中显示它们，**绝对不要**自己重新计算同比或汇总。
2. **趋势描述**：利用 `trend_description` 字段的内容来描述指标与气温的关系。

### 核心需求
1. **可视化（ECharts）**：
   - 使用 `metrics` 数组中的 `timeline_json` 数据绘制图表。
   - **图表 1：双轴趋势图**
     - 左轴：选择一个核心指标（如供热量/耗煤量）。
     - 右轴：气温（如果 `is_temperature=true` 的指标存在）。
     - 使用 ECharts `dataset` 或直接填入 data。
2. **排版布局**：
   - **概览卡片**：顶部横排展示关键指标（名称、数值、单位、同比红绿箭头）。
   - **详细分析**：下方展示图表，并配以文字说明（引用 `stats` 中的极值、均值）。

### 输出格式
- 完整的 HTML5 (含 <!DOCTYPE html>)。
- 内联 CSS 美化。
- 无 Markdown 标记。

### 数据内容
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


def _calculate_trend_stats(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算时间序列的统计特征：极值、均值、波动。"""
    if not timeline:
        return {}
    
    current_values = [float(t["current"]) for t in timeline if t.get("current") is not None]
    peer_values = [float(t["peer"]) for t in timeline if t.get("peer") is not None]
    
    stats = {}
    if current_values:
        stats["current_max"] = max(current_values)
        stats["current_min"] = min(current_values)
        stats["current_avg"] = statistics.mean(current_values)
    
    if peer_values:
        stats["peer_avg"] = statistics.mean(peer_values)

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
        if current is not None and peer is not None and peer != 0:
            delta = ((float(current) - float(peer)) / abs(float(peer))) * 100
        
        # 2. 时间序列统计 (Stats)
        timeline = row.get("timeline") or []
        stats = _calculate_trend_stats(timeline)
        
        # 3. 气温相关性 (Correlation)
        correlation = None
        trend_desc = ""
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

        processed_metrics.append({
            "label": row.get("label"),
            "unit": row.get("unit"),
            "value": current,
            "peer_value": peer,
            "delta_percent": round(delta, 2) if delta is not None else None,
            "stats": stats,
            "correlation_with_temp": correlation,
            "trend_description": trend_desc,
            "is_temperature": row.get("value_type") == "temperature",
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


def _build_prompt_text(payload: Dict[str, Any]) -> str:
    # 1. 先进行 Python 端的精密计算和预处理
    processed_data = _preprocess_payload(payload)
    # 2. 将处理后的干净数据转为 JSON 字符串
    payload_json = _safe_json_dumps(processed_data)
    # 3. 拼接 Prompt
    return PROMPT_TEMPLATE + "\n" + payload_json


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
        prompt = _build_prompt_text(payload)
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
        _update_job(
            job_id,
            status="ready",
            report=text,
            model=_model_name,
            finished_at=_current_time_iso(),
        )
        _logger.info("AI report job %s finished successfully", job_id)
    except Exception as exc:  # pylint: disable=broad-except
        _logger.warning("生成 AI 报告失败: %s", exc)
        _update_job(
            job_id,
            status="failed",
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
        "created_at": _current_time_iso(),
        "report": None,
        "error": None,
        "model": None,
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
