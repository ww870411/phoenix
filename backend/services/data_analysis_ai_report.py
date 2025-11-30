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

import google.generativeai as genai

from backend.config import DATA_DIRECTORY

DATA_ROOT = Path(DATA_DIRECTORY)
API_KEY_PATH = DATA_ROOT / "api_key.json"

PROMPT_TEMPLATE = """你是一名供热集团生产经营分析顾问，当前任务是为集团领导的周/月度经营汇报撰写“智能数据分析报告”。请严格遵循：
1. 报告必须完全基于给定 JSON 数据，禁止杜撰或补全未提供的数字。
2. 文字面向管理层，可直接粘贴进 PPT/Word 汇报，语气专业、结论导向、强调行动建议。
3. 输出 Markdown，段落顺序如下（无数据可省略相关段落）：
   ## 总体态势 —— 概括本期表现与同期/上期差异，简述气温对热负荷的影响。
   ## 核心亮点 —— 罗列 2~4 条积极信号，说明指标、原因及延续建议。
   ## 风险与异常 —— 罗列 2~4 条重点风险，指出偏差来源、潜在影响和建议措施。
   ## 计划执行 —— 对有计划值的指标说明完成率、落后/超计划程度，并给出原因分析。
   ## 趋势洞察 —— 结合逐日数据或相关性提示走势、波动点及温度与单耗/利润的关系。
4. 若存在 warnings 或数据缺失，需在“风险与异常”段落提示。
5. 引用指标时注明单位、同比/环比/计划完成率等百分比，并保留“较同期±X%”描述。
6. 最后一段可附 1~2 条后续跟进建议，帮助管理层快速决策。

JSON 数据：
{payload_json}
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
    prompt_payload = _build_prompt_payload(payload)
    payload_json = _safe_json_dumps(prompt_payload)
    return PROMPT_TEMPLATE.format(payload_json=payload_json)


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
