"""
数据分析 AI 报告生成服务。

支持 gemini/newapi 双 provider，负责：
- 读取 backend_data/shared/ai_settings.json 中的 AI 配置；
- 根据数据分析查询结果构造提示词；
- 将任务提交至线程池并异步生成报告；
- 以内存字典维护任务状态，供 API 查询。
"""

from __future__ import annotations

import copy
import json
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import math
import statistics
import urllib.error
import urllib.request

import google.generativeai as genai

from backend.config import DATA_DIRECTORY
from backend.services.api_key_cipher import decrypt_api_key
from backend.services.project_data_paths import (
    resolve_global_ai_settings_path,
)

DATA_ROOT = Path(DATA_DIRECTORY)
GLOBAL_AI_SETTINGS_PATH = resolve_global_ai_settings_path()
PERCENTAGE_SCALE_METRICS = {"rate_overall_efficiency"}
AI_MODE_DAILY = "daily_analysis_v1"
AI_MODE_MONTHLY = "monthly_analysis_v1"
PROMPT_DATA_MAX_CHARS = 120000
PROMPT_DATA_MAX_CHARS_NEWAPI = 36000

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

VALIDATION_PROMPT_TEMPLATE = """你是一名严谨的能源行业数据审计员。现在需要对智能分析报告的最终内容进行核实，重点检查：
1. 报告正文中引用的数值、差异率（同比 delta、环比 ring）是否与提供的指标数据一致；
2. 逐日区间（timeline）中的本期/同期/同比描述是否与数据吻合；
3. 是否存在逻辑冲突或未说明的异常，例如宣称“环比下降”但数据为正；
4. 是否遗漏对关键指标的说明或误用了单位。

输入：
- `processed_data`：包含所有指标的原始数据（value、delta、ring、timeline 等）；
- `content_data`：阶段三“内容撰写”输出的段落。

输出仅限 JSON，结构如下：
{
  "status": "pass | warning | fail",
  "issues": [
    {
      "section": "对应段落或指标名称",
      "description": "发现的问题，尽量引用数据说明",
      "severity": "info | warning | error",
      "suggestion": "如何修复或需要补充的内容，可为空"
    }
  ],
  "notes": "整体结论或说明"
}

要求：
- 若所有检查通过且未发现问题，可令 status=pass、issues 为空，并在 notes 中说明已核实；
- 若发现轻微问题（如缺少引用）可设置 status=warning；重大数据矛盾需设为 fail；
- description 中要包含具体证据（指标名称、数值、日期等），避免空泛表述。
"""

REVISION_PROMPT_TEMPLATE = """你是一名能源行业的资深报告复核负责人。当前报告在核查阶段暴露出数据或逻辑问题，需要你在保持章节结构与 JSON 输出格式不变的前提下完成修订。

要求：
- 仔细阅读核查结果中的 issues，逐条修复或在正文中给出解释，禁止忽略；
- `section_contents` 的 key 必须与 layout.sections[].id 严格一致；
- 引用 processed_data 中真实的数值、同比/环比和单位，所有修订后的描述都要与数据吻合；
- 可以重写段落和提示，但需确保 callouts 至少保留 1 条有效信息；
- 若 issues 涉及遗漏指标或单位错误，必须在修订内容中显式更正。

输出结构需与内容撰写阶段完全相同：
{
  "section_contents": {...},
  "callouts": [...]
}
"""

# ========== 极速模式 Prompt ==========

FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE = """你是一名热电联产/城市集中供热行业的数据分析师。请阅读给定的 JSON 数据，一次性完成洞察分析和报告结构规划，仅输出结构化 JSON。

输出 JSON 结构：
{
  "insight": {
    "headline": "一句话概括整体运行结论",
    "key_findings": [
      {"metric": "指标名称", "status": "up|down|stable", "evidence": "引用数据说明原因", "risk_level": "low|medium|high"}
    ],
    "temperature_effect": "气温联动说明或'无显著气温影响'",
    "risks": ["潜在风险，至少1条"],
    "recommendations": ["建议，至少1条"]
  },
  "layout": {
    "sections": [
      {"id": "overview|trend|risks", "title": "章节标题", "purpose": "重点", "bullets": ["要点"], "metrics": []}
    ],
    "chart_plan": {"primary_metric": "指标key", "temperature_metric": null, "narrative": "图表故事"},
    "callouts": [{"title": "提示标题", "body": "说明", "level": "info|warning|danger"}]
  }
}

要求：
- 必须使用中文；
- key_findings 至少 2 条；
- sections 至少 2 个；
- callouts 至少 1 条。
"""

FAST_VALIDATION_PROMPT_TEMPLATE = """快速核查报告中引用的关键数值是否与原始数据一致。

只检查以下内容：
1. 同比（delta）数值是否正确引用；
2. 环比（ring）数值是否正确引用；
3. 累计值是否与数据一致。

输出 JSON：
{
  "status": "pass | warning",
  "issues": [{"section": "位置", "description": "问题描述", "severity": "info|warning"}],
  "notes": "简要结论"
}

要求：
- 只标记明显的数据错误；
- 不需要修订建议；
- 若无明显问题，status 设为 pass，issues 为空。
"""

MONTHLY_INSIGHT_PROMPT_TEMPLATE = """你是一名供热集团月报分析专家。请阅读给定 JSON 数据（已包含多口径、多指标、同比/环比/计划比及趋势信息），仅输出结构化 JSON，不要出现 Markdown 或解释文字。

输出 JSON 结构：
{
  "headline": "一句话概括本月整体运行结论",
  "key_findings": [
    {
      "metric": "口径/指标名称",
      "status": "up | down | stable",
      "evidence": "引用本期、同期、上期或计划值说明依据",
      "risk_level": "low | medium | high"
    }
  ],
  "temperature_effect": "若存在气温指标说明联动关系，否则写 \"无显著气温影响\"",
  "risks": ["列出至少 1 条风险点"],
  "recommendations": ["列出至少 1 条经营或调度建议"],
  "notable_metrics": ["按重要性列出 3~5 个指标 key 或标签"]
}

要求：
- 必须使用中文；
- key_findings 至少 2 条；
- 必须包含同比/环比/计划至少两类证据；
- 禁止编造数据。
"""

MONTHLY_LAYOUT_PROMPT_TEMPLATE = """你是月报经营分析报告编辑。请根据洞察结果规划月报结构，仅输出 JSON。

输出 JSON 结构：
{
  "sections": [
    {
      "id": "overview",
      "title": "章节标题",
      "purpose": "章节目的",
      "bullets": ["章节要点"],
      "metrics": ["本章重点指标 key 列表，可为空"]
    }
  ],
  "chart_plan": {
    "primary_metric": "建议主图指标 key",
    "temperature_metric": "若有气温则指定 key，否则 null",
    "narrative": "图表叙事主线"
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
- sections 必须且仅能为 4 个，且按以下顺序输出：
  1) overview
  2) coal_completion
  3) profit_cost_breakdown
  4) efficiency_and_actions
- 必须在各章节体现“同比/环比/计划”对比；
- callouts 至少 1 条。
"""

MONTHLY_CONTENT_PROMPT_TEMPLATE = """你现在的任务是“月报内容撰写”。请根据洞察（Insight）与结构规划（Layout）生成月报正文，仅输出 JSON。

输出 JSON 结构：
{
  "section_contents": {
    "overview": "章节正文 HTML",
    "coal_completion": "章节正文 HTML",
    "profit_cost_breakdown": "章节正文 HTML",
    "efficiency_and_actions": "章节正文 HTML"
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
- 必须使用中文；
- 必须明确写出“本期值、同期值、上期值、计划值”中的至少两类对比证据；
- 使用 HTML 片段标签（如 <p><ul><li><strong>），不要输出完整 HTML 文档；
- `section_contents` 的 key 必须且仅能是：
  - overview
  - coal_completion
  - profit_cost_breakdown
  - efficiency_and_actions
- 禁止编造数据，缺失数据要明确写“暂无”。
"""

MONTHLY_VALIDATION_PROMPT_TEMPLATE = """你是一名月报数据核查员。请核查报告内容与月报数据的一致性，仅输出 JSON。

核查重点：
1. 本期/同期/上期/计划值引用是否正确；
2. 同比/环比/计划差异率口径是否自洽（尤其分母绝对值口径）；
3. 是否存在“文字结论与数值方向相反”的问题；
4. 单位是否正确，是否混淆口径与指标。

输出 JSON：
{
  "status": "pass | warning | fail",
  "issues": [
    {
      "section": "章节或指标",
      "description": "问题描述（需含证据）",
      "severity": "info | warning | error",
      "suggestion": "修复建议，可为空"
    }
  ],
  "notes": "核查结论"
}
"""

MONTHLY_REVISION_PROMPT_TEMPLATE = """你是一名月报报告复核负责人。请根据核查问题修订正文，保持 JSON 输出结构不变。

要求：
- 逐条处理 validation.issues，不得忽略；
- 保持 `section_contents` 键集合与 layout.sections[].id 完全一致；
- 修订时优先保留“口径 -> 指标 -> 对比结论”的叙述结构；
- 禁止编造数据，若数据不足须显式说明；
- callouts 至少保留 1 条。

输出：
{
  "section_contents": {...},
  "callouts": [...]
}
"""

MONTHLY_FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE = """你是一名供热集团月报分析师。请基于月报 JSON 数据一次性输出“洞察+结构规划”，仅输出 JSON。

输出 JSON：
{
  "insight": {
    "headline": "一句话月报结论",
    "key_findings": [
      {"metric": "口径/指标", "status": "up|down|stable", "evidence": "证据", "risk_level": "low|medium|high"}
    ],
    "temperature_effect": "气温影响结论或无显著影响",
    "risks": ["至少1条"],
    "recommendations": ["至少1条"]
  },
  "layout": {
    "sections": [
      {"id": "overview", "title": "标题", "purpose": "目的", "bullets": ["要点"], "metrics": []}
    ],
    "chart_plan": {"primary_metric": "指标key", "temperature_metric": null, "narrative": "图表叙事"},
    "callouts": [{"title": "提示", "body": "内容", "level": "info|warning|danger"}]
  }
}
"""

MONTHLY_FAST_VALIDATION_PROMPT_TEMPLATE = """快速核查月报正文与关键对比数据是否一致，仅输出 JSON。

重点只检查：
1. 同比/环比/计划比方向是否正确；
2. 关键值是否引用错误；
3. 单位是否明显错误。

输出 JSON：
{
  "status": "pass | warning",
  "issues": [{"section": "位置", "description": "问题", "severity": "info|warning"}],
  "notes": "结论"
}
"""

AI_MODE_TEMPLATE_REGISTRY = {
    AI_MODE_DAILY: {
        "insight": INSIGHT_PROMPT_TEMPLATE,
        "layout": LAYOUT_PROMPT_TEMPLATE,
        "content": CONTENT_PROMPT_TEMPLATE,
        "validation": VALIDATION_PROMPT_TEMPLATE,
        "revision": REVISION_PROMPT_TEMPLATE,
        "fast_insight_layout": FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE,
        "fast_validation": FAST_VALIDATION_PROMPT_TEMPLATE,
    },
    AI_MODE_MONTHLY: {
        "insight": MONTHLY_INSIGHT_PROMPT_TEMPLATE,
        "layout": MONTHLY_LAYOUT_PROMPT_TEMPLATE,
        "content": MONTHLY_CONTENT_PROMPT_TEMPLATE,
        "validation": MONTHLY_VALIDATION_PROMPT_TEMPLATE,
        "revision": MONTHLY_REVISION_PROMPT_TEMPLATE,
        "fast_insight_layout": MONTHLY_FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE,
        "fast_validation": MONTHLY_FAST_VALIDATION_PROMPT_TEMPLATE,
    },
}

_logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=2)
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()
_runtime_client: Optional[Dict[str, Any]] = None
_runtime_signature: Optional[str] = None
_runtime_model_name: Optional[str] = None


def reset_gemini_client() -> None:
    """清空已缓存的 AI 客户端实例，确保下次调用重新读取配置。"""

    global _runtime_client, _runtime_signature, _runtime_model_name
    _runtime_client = None
    _runtime_signature = None
    _runtime_model_name = None


def _safe_read_settings_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _load_effective_ai_settings() -> Dict[str, Any]:
    return _safe_read_settings_json(GLOBAL_AI_SETTINGS_PATH)


def _normalize_provider(value: Any) -> str:
    provider = str(value or "gemini").strip().lower()
    return provider if provider in {"gemini", "newapi"} else "gemini"


def _decode_api_key(raw_value: Any) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""
    decoded = decrypt_api_key(text)
    if text.startswith("sk-") and not decoded.startswith("sk-"):
        return text
    if text.startswith("AIza") and not decoded.startswith("AIza"):
        return text
    return decoded


def _resolve_active_provider_record(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    providers_raw = data.get("providers")
    if not isinstance(providers_raw, list) or not providers_raw:
        return None
    records: List[Dict[str, Any]] = []
    for idx, raw in enumerate(providers_raw):
        if not isinstance(raw, dict):
            continue
        kind = _normalize_provider(raw.get("kind") or raw.get("provider"))
        provider_id = str(raw.get("id") or "").strip() or f"provider_{idx + 1}"
        api_keys_raw = raw.get("api_keys")
        encrypted_keys = api_keys_raw if isinstance(api_keys_raw, list) else []
        keys = [_decode_api_key(k) for k in encrypted_keys if str(k or "").strip()]
        records.append(
            {
                "id": provider_id,
                "name": str(raw.get("name") or "").strip(),
                "kind": kind,
                "base_url": str(raw.get("base_url") or "").strip(),
                "model": str(raw.get("model") or "").strip(),
                "api_keys": keys,
            }
        )
    if not records:
        return None
    active_id = str(data.get("active_provider_id") or "").strip()
    if active_id:
        hit = next((r for r in records if str(r.get("id") or "") == active_id), None)
        if hit:
            return hit
    return records[0]


def _load_gemini_settings(data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if data is None:
        data = _load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")

    # 优先尝试读取 gemini_api_keys 列表
    raw_keys = data.get("gemini_api_keys")
    api_key = ""
    if isinstance(raw_keys, list) and len(raw_keys) > 0:
        # 取第一个 Key 并解密
        first_raw = str(raw_keys[0] or "")
        if first_raw:
            api_key = _decode_api_key(first_raw)
    
    # 回退：尝试读取旧的 gemini_api_key
    if not api_key:
        raw_single_key = data.get("gemini_api_key")
        if raw_single_key:
            api_key = _decode_api_key(str(raw_single_key))

    model = data.get("gemini_model")
    if not api_key or not isinstance(api_key, str):
        raise RuntimeError("缺少有效的 gemini_api_key 配置 (请检查 gemini_api_keys 列表)")
    if not model or not isinstance(model, str):
        raise RuntimeError("缺少 gemini_model 配置")
    return {"api_key": api_key, "model": model}


def _load_newapi_settings(data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    if data is None:
        data = _load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")

    base_url = str(data.get("newapi_base_url") or "").strip()
    if not base_url:
        raise RuntimeError("缺少 newapi_base_url 配置")
    model = str(data.get("newapi_model") or "").strip()
    if not model:
        raise RuntimeError("缺少 newapi_model 配置")

    raw_keys = data.get("newapi_api_keys")
    api_key = ""
    if isinstance(raw_keys, list) and raw_keys:
        first_raw = str(raw_keys[0] or "")
        if first_raw:
            api_key = _decode_api_key(first_raw)

    if not api_key:
        raw_single_key = data.get("newapi_api_key")
        if raw_single_key:
            api_key = _decode_api_key(str(raw_single_key))
    if not api_key:
        raise RuntimeError("缺少有效的 newapi_api_key 配置 (请检查 newapi_api_keys 列表)")
    return {"api_key": api_key, "model": model, "base_url": base_url}


def _load_ai_provider_settings() -> Dict[str, Any]:
    data = _load_effective_ai_settings()
    if not data:
        raise RuntimeError(f"API Key 配置不存在：{GLOBAL_AI_SETTINGS_PATH}")
    active_record = _resolve_active_provider_record(data)
    if active_record is not None:
        provider = _normalize_provider(active_record.get("kind"))
        api_keys = active_record.get("api_keys") or []
        api_key = str(api_keys[0] or "").strip() if isinstance(api_keys, list) and api_keys else ""
        model = str(active_record.get("model") or "").strip()
        if not api_key:
            raise RuntimeError("当前生效 Provider 缺少 API Key")
        if not model:
            raise RuntimeError("当前生效 Provider 缺少模型名")
        if provider == "newapi":
            base_url = str(active_record.get("base_url") or "").strip()
            if not base_url:
                raise RuntimeError("当前生效 New API Provider 缺少 Base URL")
            return {
                "provider": "newapi",
                "api_key": api_key,
                "model": model,
                "base_url": base_url,
            }
        return {
            "provider": "gemini",
            "api_key": api_key,
            "model": model,
        }

    provider = _normalize_provider(data.get("provider"))
    settings: Dict[str, Any]
    if provider == "newapi":
        settings = _load_newapi_settings(data)
    else:
        settings = _load_gemini_settings(data)
    settings["provider"] = provider
    return settings


def _current_provider() -> str:
    try:
        data = _load_effective_ai_settings()
        active_record = _resolve_active_provider_record(data)
        if active_record is not None:
            return _normalize_provider(active_record.get("kind"))
        return _normalize_provider(data.get("provider"))
    except Exception:  # pylint: disable=broad-except
        return "gemini"


def _resolve_prompt_data_char_limit() -> int:
    if _current_provider() == "newapi":
        return PROMPT_DATA_MAX_CHARS_NEWAPI
    return PROMPT_DATA_MAX_CHARS


def _load_instruction_text(mode_id: str = AI_MODE_DAILY) -> str:
    data = _load_effective_ai_settings()
    if not data:
        return ""
    normalized_mode = _normalize_ai_mode(mode_id)
    candidates: List[str]
    if normalized_mode == AI_MODE_MONTHLY:
        candidates = ["instruction_monthly"]
    else:
        candidates = ["instruction_daily"]
    for key in candidates:
        instruction = data.get(key)
        if isinstance(instruction, str):
            text = instruction.strip()
            if text:
                return text
    return ""


def _load_ai_runtime_flags() -> Dict[str, Any]:
    defaults = {"enable_validation": True, "allow_non_admin_report": False, "report_mode": "full"}
    data = _load_effective_ai_settings()
    if not data:
        return defaults
    flags = defaults.copy()
    if isinstance(data, dict):
        if "enable_validation" in data:
            flags["enable_validation"] = bool(data["enable_validation"])
        if "allow_non_admin_report" in data:
            flags["allow_non_admin_report"] = bool(data["allow_non_admin_report"])
        if "report_mode" in data:
            flags["report_mode"] = str(data["report_mode"]) if data["report_mode"] in ("full", "fast") else "full"
    return flags


def _safe_json_dumps(payload: Dict[str, Any]) -> str:
    def _convert(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    return json.dumps(payload, ensure_ascii=False, default=_convert)


def _to_score(value: Any) -> float:
    numeric = _to_float_or_none(value)
    return abs(numeric) if numeric is not None else 0.0


def _trim_processed_data_for_prompt(
    processed_data: Dict[str, Any],
    metric_limit: int,
    timeline_limit: int,
    include_timeline_matrix: bool = True,
) -> Dict[str, Any]:
    data = copy.deepcopy(processed_data or {})
    metrics_raw = data.get("metrics")
    metrics: List[Dict[str, Any]] = metrics_raw if isinstance(metrics_raw, list) else []
    ranked = []
    for idx, metric in enumerate(metrics):
        ranked.append(
            (
                (
                    1000.0 if metric.get("is_temperature") else 0.0
                )
                + _to_score(metric.get("delta"))
                + _to_score(metric.get("ring"))
                + _to_score(metric.get("value")),
                idx,
                metric,
            )
        )
    ranked.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    kept_metrics = [item[2] for item in ranked[: max(1, metric_limit)]]
    keep_keys = set()
    keep_labels = set()
    for metric in kept_metrics:
        key = str(metric.get("key") or "").strip()
        label = str(metric.get("label") or "").strip()
        if key:
            keep_keys.add(key)
        if label:
            keep_labels.add(label)
        metric.pop("timeline_json", None)
        timeline_entries = metric.get("timeline_entries")
        if isinstance(timeline_entries, list):
            metric["timeline_entries"] = timeline_entries[-max(1, timeline_limit) :]
    data["metrics"] = kept_metrics

    ring_compare = data.get("ring_compare")
    if isinstance(ring_compare, dict):
        entries = ring_compare.get("entries")
        if isinstance(entries, list):
            ring_compare["entries"] = [
                entry
                for entry in entries
                if str(entry.get("key") or "").strip() in keep_keys
                or str(entry.get("label") or "").strip() in keep_labels
            ]

    plan_compare = data.get("plan_compare")
    if isinstance(plan_compare, dict):
        entries = plan_compare.get("entries")
        if isinstance(entries, list):
            plan_compare["entries"] = [
                entry
                for entry in entries
                if str(entry.get("key") or "").strip() in keep_keys
                or str(entry.get("label") or "").strip() in keep_labels
            ]

    timeline_matrix = data.get("timeline_matrix")
    if include_timeline_matrix and isinstance(timeline_matrix, dict):
        trimmed_matrix: Dict[str, Any] = {}
        for key, entries in timeline_matrix.items():
            key_text = str(key or "").strip()
            if key_text not in keep_keys and key_text not in keep_labels:
                continue
            if isinstance(entries, list):
                trimmed_matrix[key_text] = entries[-max(1, timeline_limit) :]
            else:
                trimmed_matrix[key_text] = entries
        data["timeline_matrix"] = trimmed_matrix
    elif not include_timeline_matrix:
        data.pop("timeline_matrix", None)

    warnings = data.get("raw_warnings")
    if isinstance(warnings, list) and len(warnings) > 20:
        data["raw_warnings"] = warnings[:20]
    return data


def _serialize_prompt_processed_data(processed_data: Dict[str, Any]) -> str:
    char_limit = _resolve_prompt_data_char_limit()
    candidates = [
        (100, 31, True),
        (80, 20, True),
        (60, 12, True),
        (45, 8, False),
        (30, 5, False),
    ]
    last_json = "{}"
    last_payload: Dict[str, Any] = {}
    for metric_limit, timeline_limit, include_matrix in candidates:
        payload = _trim_processed_data_for_prompt(
            processed_data,
            metric_limit=metric_limit,
            timeline_limit=timeline_limit,
            include_timeline_matrix=include_matrix,
        )
        data_json = _safe_json_dumps(payload)
        last_json = data_json
        last_payload = payload
        if len(data_json) <= char_limit:
            if metric_limit < 100 or timeline_limit < 31 or not include_matrix:
                meta = payload.get("meta")
                if isinstance(meta, dict):
                    meta["prompt_compaction"] = (
                        f"metrics<= {metric_limit}, timeline<= {timeline_limit}, "
                        f"timeline_matrix={'on' if include_matrix else 'off'}"
                    )
            return _safe_json_dumps(payload)
    if isinstance(last_payload.get("meta"), dict):
        last_payload["meta"]["prompt_compaction"] = "max_compaction_applied"
    return _safe_json_dumps(last_payload) if last_payload else last_json


def _normalize_ai_mode(mode_id: Any) -> str:
    raw = str(mode_id or "").strip()
    if raw in AI_MODE_TEMPLATE_REGISTRY:
        return raw
    return AI_MODE_DAILY


def _resolve_mode_templates(mode_id: str) -> Dict[str, str]:
    normalized = _normalize_ai_mode(mode_id)
    return AI_MODE_TEMPLATE_REGISTRY.get(normalized, AI_MODE_TEMPLATE_REGISTRY[AI_MODE_DAILY])


def _sanitize_user_prompt(user_prompt: Any, max_len: int = 2000) -> str:
    text = str(user_prompt or "").strip()
    if not text:
        return ""
    if len(text) > max_len:
        return text[:max_len]
    return text


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
        for entry in entries:
            unit_text = entry["unit"]
            curr_text = _format_number(entry["current"], entry["decimals"])
            prev_text = _format_number(entry["previous"], entry["decimals"])
            rate_text = _format_percent_text(entry["rate"])
            summary_lines.append(
                f"{entry['label']} 本期 {curr_text}{unit_text}，上期 {prev_text}{unit_text}，环比 {rate_text}"
            )

    note = ring_block.get("note") or ("当前指标无可用环比数据" if not entries else "")

    return {
        "entries": entries,
        "note": note,
        "current_range": current_range_label,
        "previous_range": previous_range_label,
        "summary_lines": summary_lines,
    }


def _build_plan_compare_payload(plan_payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(plan_payload, dict):
        return None
    entries_raw = plan_payload.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        return None
    entries: List[Dict[str, Any]] = []
    summary_phrases: List[str] = []
    for entry in entries_raw:
        if not isinstance(entry, dict):
            continue
        plan_value = _to_float_or_none(entry.get("plan_value")) or 0.0
        actual_value = _to_float_or_none(entry.get("actual_value"))
        completion_rate = _to_float_or_none(entry.get("completion_rate"))
        label = entry.get("label") or entry.get("key") or "未命名指标"
        unit = entry.get("unit") or ""
        decimals = 2
        entries.append(
            {
                "label": label,
                "unit": unit,
                "plan_value": plan_value,
                "actual_value": actual_value,
                "completion_rate": completion_rate,
                "decimals": decimals,
                "plan_type": entry.get("plan_type") or "plan",
            }
        )
        plan_text = _format_number(plan_value, decimals)
        actual_text = _format_number(actual_value, decimals)
        completion_text = _format_percent_text(completion_rate)
        summary_phrases.append(
            f"{label} 计划 {plan_text}{unit}，本期 {actual_text}{unit}，完成率 {completion_text}"
        )
    if not entries:
        return None
    period_start = plan_payload.get("period_start")
    period_end = plan_payload.get("period_end")
    period_text = _format_range_label(period_start, period_end)
    month_label = plan_payload.get("month_label") or (period_start[:7] if isinstance(period_start, str) else "")
    return {
        "entries": entries,
        "period_text": period_text,
        "month_label": month_label,
        "summary_lines": summary_phrases,
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


def _extract_retry_delay_seconds(error_text: str) -> int:
    if not error_text:
        return 20
    candidates: List[int] = []
    match_retry_in = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", error_text, flags=re.IGNORECASE)
    if match_retry_in:
        try:
            candidates.append(int(math.ceil(float(match_retry_in.group(1)))))
        except (TypeError, ValueError):
            pass
    match_retry_block = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_text, flags=re.IGNORECASE)
    if match_retry_block:
        try:
            candidates.append(int(match_retry_block.group(1)))
        except (TypeError, ValueError):
            pass
    return max([20, *candidates])


def _is_quota_or_rate_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    if "429" in text:
        return True
    keywords = [
        "quota exceeded",
        "rate limit",
        "resource has been exhausted",
        "generatecontentinputtokenspermodelperminute",
    ]
    return any(word in text for word in keywords)


def _is_transient_gateway_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    transient_tokens = [
        "http 500",
        "http 502",
        "http 503",
        "http 504",
        "gateway time-out",
        "gateway timeout",
        "timed out",
        "connection reset",
    ]
    return any(token in text for token in transient_tokens)


def _extract_response_text(response: Any) -> str:
    text = (response.text or "").strip() if response else ""
    if text:
        return text
    if response and getattr(response, "candidates", None):
        parts = []
        for candidate in response.candidates:
            for part in getattr(candidate, "content", {}).parts or []:
                part_text = getattr(part, "text", "")
                if part_text:
                    parts.append(part_text)
        text = "\n".join(parts).strip()
    return text


def _extract_newapi_response_text(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first, dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        if isinstance(content, str):
            text = content.strip()
            if text:
                return text
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    part_text = item.get("text")
                    if isinstance(part_text, str):
                        parts.append(part_text)
            text = "\n".join(part for part in parts if part).strip()
            if text:
                return text
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        text = output_text.strip()
        if text:
            return text
    return ""


def _build_newapi_chat_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise RuntimeError("newapi_base_url 不能为空")
    lower = normalized.lower()
    if lower.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _call_newapi_chat(prompt: str, settings: Dict[str, Any], timeout_seconds: int = 120) -> str:
    url = _build_newapi_chat_url(str(settings.get("base_url") or ""))
    request_body = {
        "model": str(settings.get("model") or ""),
        "messages": [{"role": "user", "content": prompt}],
    }
    request_data = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Phoenix-AI-Client/1.0",
            "Authorization": f"Bearer {str(settings.get('api_key') or '')}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        if exc.code == 403 and "1010" in detail:
            raise RuntimeError(
                "New API 调用失败: HTTP 403 error code 1010（网关拒绝）。"
                f"请检查 base_url 是否为 API 域名与接口路径，当前请求地址: {url}。"
                "若该服务有防火墙/来源限制，请放行服务端请求。"
            ) from exc
        raise RuntimeError(f"New API 调用失败: HTTP {exc.code} {detail} (url={url})") from exc
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(f"New API 调用失败: {exc}") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"New API 返回内容不是有效 JSON: {raw_text[:300]}") from exc
    text = _extract_newapi_response_text(payload if isinstance(payload, dict) else {})
    if not text:
        raise RuntimeError("New API 未返回有效文本内容")
    return text


def _test_gemini_connection(api_key: str, model: str) -> Dict[str, Any]:
    if not api_key:
        raise RuntimeError("Gemini API Key 不能为空")
    if not model:
        raise RuntimeError("Gemini 模型不能为空")
    genai.configure(api_key=api_key)
    runtime_model = genai.GenerativeModel(model)
    response = runtime_model.generate_content("请仅回复: ok")
    text = _extract_response_text(response)
    if not text:
        raise RuntimeError("Gemini 测试调用成功但未返回文本")
    return {"provider": "gemini", "model": model, "message": text[:120]}


def _test_newapi_connection(base_url: str, api_key: str, model: str) -> Dict[str, Any]:
    if not base_url:
        raise RuntimeError("New API Base URL 不能为空")
    if not api_key:
        raise RuntimeError("New API Key 不能为空")
    if not model:
        raise RuntimeError("New API 模型不能为空")
    text = _call_newapi_chat(
        "请仅回复: ok",
        {"base_url": base_url, "api_key": api_key, "model": model},
        timeout_seconds=60,
    )
    return {"provider": "newapi", "model": model, "message": text[:120]}


def run_ai_connection_test(payload: Dict[str, Any]) -> Dict[str, Any]:
    active_record = _resolve_active_provider_record(payload if isinstance(payload, dict) else {})
    if active_record is not None:
        provider = _normalize_provider(active_record.get("kind"))
        keys = active_record.get("api_keys") or []
        first_key = str(keys[0] or "").strip() if isinstance(keys, list) and keys else ""
        model = str(active_record.get("model") or "").strip()
        if provider == "newapi":
            return _test_newapi_connection(
                str(active_record.get("base_url") or "").strip(),
                first_key,
                model,
            )
        return _test_gemini_connection(first_key, model)

    provider = _normalize_provider(payload.get("provider"))
    if provider == "newapi":
        newapi_keys = payload.get("newapi_api_keys")
        first_key = ""
        if isinstance(newapi_keys, list) and newapi_keys:
            first_key = str(newapi_keys[0] or "").strip()
        return _test_newapi_connection(
            str(payload.get("newapi_base_url") or "").strip(),
            first_key,
            str(payload.get("newapi_model") or "").strip(),
        )
    gemini_keys = payload.get("api_keys")
    first_key = ""
    if isinstance(gemini_keys, list) and gemini_keys:
        first_key = str(gemini_keys[0] or "").strip()
    return _test_gemini_connection(
        first_key,
        str(payload.get("model") or "").strip(),
    )


def _current_runtime_model_name() -> str:
    return str(_runtime_model_name or "")


def _call_model(prompt: str, retries: int = 3) -> str:
    runtime = _get_runtime_client()
    provider = str(runtime.get("provider") or "gemini")
    last_error: Optional[Exception] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            if provider == "newapi":
                text = _call_newapi_chat(prompt, runtime)
            else:
                model = runtime.get("client")
                response = model.generate_content(prompt)
                text = _extract_response_text(response)
            if not text:
                raise RuntimeError("模型未返回内容")
            return text
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            if _is_quota_or_rate_error(exc) and attempt < retries:
                delay_seconds = _extract_retry_delay_seconds(str(exc))
                _logger.warning(
                    "%s 限流/配额触发，第 %s/%s 次调用失败，%s 秒后自动重试：%s",
                    provider,
                    attempt,
                    retries,
                    delay_seconds,
                    exc,
                )
                time.sleep(delay_seconds)
                continue
            if _is_transient_gateway_error(exc) and attempt < retries:
                _logger.warning(
                    "%s 网关/超时错误，第 %s/%s 次调用失败，2 秒后重试：%s",
                    provider,
                    attempt,
                    retries,
                    exc,
                )
                time.sleep(2)
                continue
            raise
    raise RuntimeError(f"模型调用失败: {last_error}")


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


def _get_runtime_client() -> Dict[str, Any]:
    global _runtime_client, _runtime_signature, _runtime_model_name
    settings = _load_ai_provider_settings()
    provider = str(settings.get("provider") or "gemini")
    signature_parts = [provider, str(settings.get("model") or "")]
    if provider == "newapi":
        signature_parts.append(str(settings.get("base_url") or ""))
    signature_parts.append(str(settings.get("api_key") or "")[:12])
    signature = "|".join(signature_parts)
    if _runtime_client is not None and _runtime_signature == signature:
        return _runtime_client

    if provider == "newapi":
        _runtime_client = {
            "provider": "newapi",
            "api_key": str(settings.get("api_key") or ""),
            "base_url": str(settings.get("base_url") or ""),
            "model": str(settings.get("model") or ""),
        }
        _runtime_model_name = str(settings.get("model") or "")
    else:
        genai.configure(api_key=str(settings.get("api_key") or ""))
        model_name = str(settings.get("model") or "")
        _runtime_client = {
            "provider": "gemini",
            "model": model_name,
            "client": genai.GenerativeModel(model_name),
        }
        _runtime_model_name = model_name
    _runtime_signature = signature
    return _runtime_client


def _preprocess_payload(payload: Dict[str, Any], mode_id: str = AI_MODE_DAILY) -> Dict[str, Any]:
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
    plan_compare = _build_plan_compare_payload(payload.get("plan_comparison"))
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
        "mode_id": _normalize_ai_mode(mode_id),
        "metrics": processed_metrics,
        "ring_compare": ring_compare,
        "plan_compare": plan_compare,
        "timeline_matrix": timeline_matrix,
        "raw_warnings": payload.get("warnings") or []
    }


def _prepend_instruction_block(prompt: str, instruction: str, user_prompt: str = "") -> str:
    blocks: List[str] = []
    extra = (instruction or "").strip()
    if extra:
        blocks.append(f"### AI 指令（最高优先级）\n{extra}")
    user_text = _sanitize_user_prompt(user_prompt)
    if user_text:
        blocks.append(
            "### 用户本次附加要求（在不破坏 JSON 输出结构和数据真实性前提下尽量满足）\n"
            f"{user_text}"
        )
    if not blocks:
        return prompt
    return "\n\n".join(blocks + [prompt])


def _build_insight_prompt(
    processed_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = INSIGHT_PROMPT_TEMPLATE,
) -> str:
    data_json = _serialize_prompt_processed_data(processed_data)
    base = f"{template}\n\n### 数据\n{data_json}"
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_fast_insight_layout_prompt(
    processed_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE,
) -> str:
    """极速模式：合并洞察分析和结构规划为一个阶段"""
    data_json = _serialize_prompt_processed_data(processed_data)
    base = f"{template}\n\n### 数据\n{data_json}"
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_fast_validation_prompt(
    processed_data: Dict[str, Any],
    content_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = FAST_VALIDATION_PROMPT_TEMPLATE,
) -> str:
    """极速模式：轻量验证 Prompt"""
    data_json = _serialize_prompt_processed_data(processed_data)
    content_json = _safe_json_dumps(content_data)
    base = (
        f"{template}\n\n### 指标数据\n{data_json}"
        f"\n\n### 报告内容 JSON\n{content_json}\n"
    )
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_layout_prompt(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = LAYOUT_PROMPT_TEMPLATE,
) -> str:
    data_json = _serialize_prompt_processed_data(processed_data)
    insight_json = _safe_json_dumps(insight_data)
    base = f"{template}\n\n### 数据\n{data_json}\n\n### 洞察\n{insight_json}"
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_content_prompt(
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = CONTENT_PROMPT_TEMPLATE,
) -> str:
    insight_json = _safe_json_dumps(insight_data)
    layout_json = _safe_json_dumps(layout_data)
    base = (
        f"{template}\n\n### 洞察 JSON\n{insight_json}\n"
        f"\n### 版面规划 JSON\n{layout_json}\n"
    )
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_validation_prompt(
    processed_data: Dict[str, Any],
    content_data: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = VALIDATION_PROMPT_TEMPLATE,
) -> str:
    data_json = _serialize_prompt_processed_data(processed_data)
    content_json = _safe_json_dumps(content_data)
    base = (
        f"{template}\n\n### 指标数据\n{data_json}"
        f"\n\n### 报告内容 JSON\n{content_json}\n"
    )
    return _prepend_instruction_block(base, instruction, user_prompt)


def _build_revision_prompt(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
    previous_content: Dict[str, Any],
    validation_result: Dict[str, Any],
    instruction: str = "",
    user_prompt: str = "",
    template: str = REVISION_PROMPT_TEMPLATE,
) -> str:
    data_json = _serialize_prompt_processed_data(processed_data)
    insight_json = _safe_json_dumps(insight_data)
    layout_json = _safe_json_dumps(layout_data)
    content_json = _safe_json_dumps(previous_content)
    validation_json = _safe_json_dumps(validation_result)
    base = (
        f"{template}\n\n### 指标数据\n{data_json}\n"
        f"\n### 洞察 JSON\n{insight_json}\n"
        f"\n### 版面规划 JSON\n{layout_json}\n"
        f"\n### 现有正文 JSON\n{content_json}\n"
        f"\n### 核查问题 JSON\n{validation_json}\n"
    )
    return _prepend_instruction_block(base, instruction, user_prompt)


def _normalize_sections_for_mode(
    mode_id: str,
    raw_sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if mode_id != AI_MODE_MONTHLY:
        return raw_sections or []
    monthly_blueprint = [
        ("overview", "一、基本概况"),
        ("coal_completion", "二、标煤耗量完成情况"),
        ("profit_cost_breakdown", "三、边际利润与收入成本拆解"),
        ("efficiency_and_actions", "四、单耗诊断与下步建议"),
    ]
    section_map: Dict[str, Dict[str, Any]] = {}
    for sec in raw_sections or []:
        sec_id = str(sec.get("id") or "").strip()
        if sec_id:
            section_map[sec_id] = sec
    normalized: List[Dict[str, Any]] = []
    for sec_id, default_title in monthly_blueprint:
        base = section_map.get(sec_id) or {}
        normalized.append(
            {
                "id": sec_id,
                "title": str(base.get("title") or default_title),
                "purpose": str(base.get("purpose") or ""),
                "bullets": base.get("bullets") or [],
                "metrics": base.get("metrics") or [],
            }
        )
    return normalized


def _generate_monthly_report_html(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
    content_data: Dict[str, Any],
    validation_data: Optional[Dict[str, Any]] = None,
) -> str:
    meta = processed_data.get("meta") or {}
    metrics = processed_data.get("metrics") or []
    sections = _normalize_sections_for_mode(AI_MODE_MONTHLY, layout_data.get("sections") or [])
    section_contents = content_data.get("section_contents") or {}
    validation_block = validation_data or {}

    css = """
        body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", Arial, sans-serif; background: #f5f7fb; color: #0f172a; margin: 0; padding: 28px; }
        .paper { max-width: 980px; margin: 0 auto; background: #fff; border: 1px solid #dbe2ef; border-radius: 6px; padding: 34px 42px; box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08); }
        .report-title { text-align: center; margin: 0; font-size: 30px; letter-spacing: 1px; }
        .report-subtitle { text-align: center; margin: 10px 0 2px; font-size: 16px; color: #334155; }
        .report-meta { margin-top: 16px; border-top: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; padding: 10px 0; font-size: 13px; color: #475569; display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
        .chapter { margin-top: 20px; }
        .chapter h2 { margin: 0 0 10px; font-size: 21px; color: #0f172a; font-weight: 700; }
        .chapter .content { font-size: 16px; line-height: 2.0; color: #1f2937; text-indent: 2em; }
        .chapter .content p { margin: 8px 0; text-indent: 2em; }
        .chapter .content ul, .chapter .content ol { margin: 8px 0 8px 24px; padding: 0; text-indent: 0; }
        .chapter .content li { margin: 4px 0; text-indent: 0; }
        .appendix { margin-top: 24px; border-top: 1px dashed #cbd5e1; padding-top: 12px; }
        .appendix h3 { margin: 0 0 10px; font-size: 17px; color: #1e3a8a; }
        .chart-section { margin-top: 24px; }
        .chart-section h3 { margin: 0 0 10px; font-size: 17px; color: #1e3a8a; }
        .chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .chart-card { border: 1px solid #dbe2ef; border-radius: 6px; padding: 10px; background: #fff; }
        .chart-card h4 { margin: 0 0 8px; font-size: 14px; color: #334155; }
        .chart-box { width: 100%; height: 340px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { border: 1px solid #cbd5e1; padding: 8px 10px; text-align: center; }
        th { background: #f1f5f9; color: #1e3a8a; font-weight: 700; }
        .unit { color: #64748b; margin-left: 4px; font-size: 12px; }
        .delta-positive { color: #b91c1c; font-weight: 700; }
        .delta-negative { color: #15803d; font-weight: 700; }
        .delta-neutral { color: #334155; font-weight: 700; }
        .delta-muted { color: #94a3b8; font-weight: 700; }
        .review { margin-top: 18px; font-size: 14px; color: #334155; }
        .footer { margin-top: 28px; text-align: center; color: #94a3b8; font-size: 12px; }
    """

    html_parts: List[str] = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<style>{css}</style>",
        "<script src='https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'></script>",
        "</head><body><div class='paper'>",
        "<h1 class='report-title'>生产运行简报</h1>",
        f"<p class='report-subtitle'>{str(insight_data.get('headline') or '月度经营分析')}</p>",
        "<div class='report-meta'>",
        f"<span>分析口径：{meta.get('unit_label') or '月报查询'}</span>",
        f"<span>分析期间：{meta.get('start_date') or '—'} ~ {meta.get('end_date') or '—'}</span>",
        f"<span>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</span>",
        "</div>",
    ]

    for section in sections:
        sec_id = section.get("id")
        sec_title = section.get("title") or ""
        sec_html = section_contents.get(sec_id) or "<p>暂无内容。</p>"
        html_parts.append(
            "<section class='chapter'>"
            f"<h2>{sec_title}</h2>"
            f"<div class='content'>{sec_html}</div>"
            "</section>"
        )

    yoy_entries = []
    for metric in metrics:
        current = metric.get("value")
        peer_val = metric.get("peer_value")
        delta = metric.get("delta")
        if current is None and peer_val is None and delta is None:
            continue
        yoy_entries.append(
            {
                "label": metric.get("label"),
                "unit": metric.get("unit") or "",
                "current": current,
                "peer": peer_val,
                "delta": delta,
                "decimals": metric.get("decimals", 2),
            }
        )
    yoy_entries = yoy_entries[:30]

    chart_rows: List[Dict[str, Any]] = []
    for row in yoy_entries:
        current_numeric = _to_float_or_none(row.get("current"))
        delta_numeric = _to_float_or_none(row.get("delta"))
        if current_numeric is None and delta_numeric is None:
            continue
        chart_rows.append(
            {
                "label": str(row.get("label") or ""),
                "current": current_numeric,
                "delta": delta_numeric,
            }
        )
    if chart_rows:
        top_delta = sorted(
            [x for x in chart_rows if x.get("delta") is not None],
            key=lambda x: abs(float(x.get("delta") or 0.0)),
            reverse=True,
        )[:10]
        top_current = sorted(
            [x for x in chart_rows if x.get("current") is not None],
            key=lambda x: abs(float(x.get("current") or 0.0)),
            reverse=True,
        )[:10]
        top_delta.reverse()
        top_current.reverse()
        top_delta_json = json.dumps(top_delta, ensure_ascii=False)
        top_current_json = json.dumps(top_current, ensure_ascii=False)
        html_parts.append(
            "<section class='chart-section'>"
            "<h3>附图：关键指标可视化</h3>"
            "<div class='chart-grid'>"
            "<div class='chart-card'><h4>图1：同比差异率 Top10（绝对值）</h4><div id='monthlyChartDelta' class='chart-box'></div></div>"
            "<div class='chart-card'><h4>图2：本期值 Top10（绝对值）</h4><div id='monthlyChartCurrent' class='chart-box'></div></div>"
            "</div>"
            "<script>"
            f"const __deltaData = {top_delta_json};"
            f"const __currentData = {top_current_json};"
            "const __dEl = document.getElementById('monthlyChartDelta');"
            "const __cEl = document.getElementById('monthlyChartCurrent');"
            "if (window.echarts && __dEl && __deltaData.length) {"
            "  const c1 = window.echarts.init(__dEl);"
            "  c1.setOption({"
            "    tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},"
            "    grid:{left:140,right:20,top:30,bottom:24},"
            "    xAxis:{type:'value',axisLabel:{formatter:'{value}%'}},"
            "    yAxis:{type:'category',data:__deltaData.map(x=>x.label),axisLabel:{width:120,overflow:'truncate'}},"
            "    series:[{type:'bar',data:__deltaData.map(x=>x.delta),itemStyle:{color:(p)=> (p.value||0)>=0 ? '#b91c1c' : '#15803d'}}]"
            "  });"
            "  window.addEventListener('resize', ()=>c1.resize());"
            "}"
            "if (window.echarts && __cEl && __currentData.length) {"
            "  const c2 = window.echarts.init(__cEl);"
            "  c2.setOption({"
            "    tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},"
            "    grid:{left:140,right:20,top:30,bottom:24},"
            "    xAxis:{type:'value'},"
            "    yAxis:{type:'category',data:__currentData.map(x=>x.label),axisLabel:{width:120,overflow:'truncate'}},"
            "    series:[{type:'bar',data:__currentData.map(x=>x.current),itemStyle:{color:'#1d4ed8'}}]"
            "  });"
            "  window.addEventListener('resize', ()=>c2.resize());"
            "}"
            "</script>"
            "</section>"
        )

    if yoy_entries:
        html_parts.append("<section class='appendix'><h3>附：关键指标同比数据表</h3><table><thead><tr><th>指标</th><th>本期值</th><th>同期值</th><th>同比差异率</th></tr></thead><tbody>")
        for entry in yoy_entries:
            decimals = entry.get("decimals", 2)
            unit = entry.get("unit") or ""
            unit_html = f"<span class='unit'>{unit}</span>" if unit else ""
            delta_val = entry.get("delta")
            html_parts.append(
                "<tr>"
                f"<td>{entry.get('label') or ''}</td>"
                f"<td>{_format_number(entry.get('current'), decimals)}{unit_html}</td>"
                f"<td>{_format_number(entry.get('peer'), decimals)}{unit_html}</td>"
                f"<td class='{_classify_delta(delta_val)}'>{_format_percent_text(delta_val)}</td>"
                "</tr>"
            )
        html_parts.append("</tbody></table></section>")

    if validation_block:
        status = (validation_block.get("status") or "pending").lower()
        status_label = {"pass": "核对通过", "warning": "存在提示", "fail": "发现异常"}.get(status, "待核对")
        html_parts.append(f"<section class='review'><p><strong>智能核对：</strong>{status_label}</p></section>")

    html_parts.append("<div class='footer'>本报告由系统自动生成，仅供经营分析参考。</div></div></body></html>")
    return "\n".join(html_parts)


def _generate_report_html(
    processed_data: Dict[str, Any],
    insight_data: Dict[str, Any],
    layout_data: Dict[str, Any],
    content_data: Dict[str, Any],
    validation_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    使用 Python 拼接 HTML，替代 LLM 渲染。
    """
    meta = processed_data.get("meta") or {}
    metrics = processed_data.get("metrics") or []
    timeline_matrix = processed_data.get("timeline_matrix") or {}
    mode_id = _normalize_ai_mode(processed_data.get("mode_id"))
    if mode_id == AI_MODE_MONTHLY:
        return _generate_monthly_report_html(
            processed_data=processed_data,
            insight_data=insight_data,
            layout_data=layout_data,
            content_data=content_data,
            validation_data=validation_data,
        )
    sections = _normalize_sections_for_mode(mode_id, layout_data.get("sections") or [])
    section_contents = content_data.get("section_contents") or {}
    callouts = content_data.get("callouts") or []
    validation_block = validation_data or {}
    
    # 1. 基础样式
    css = """
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8f9fa; color: #333; margin: 0; padding: 20px; }
        .header { margin-bottom: 24px; border-bottom: 2px solid #e0e0e0; padding-bottom: 16px; text-align: center; }
        .header h1 { margin: 0 0 8px 0; font-size: 28px; color: #2c3e50; letter-spacing: 1px; }
        .header .sub-title { margin: 0 0 12px 0; font-size: 16px; color: #475569; line-height: 1.4; font-weight: 500; }
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
        .timeline-table-wrap { width: 100%; overflow-x: auto; }
        .timeline-table { min-width: 640px; }
        .timeline-table th { background: #e2e8f0; color: #334155; position: sticky; top: 0; z-index: 3; }
        .timeline-table th:first-child { left: 0; z-index: 4; }
        .timeline-table .sub-head th { background: #f8fafc; color: #475569; font-size: 13px; }
        .timeline-table td:first-child { font-weight: 600; color: #1e293b; position: sticky; left: 0; background: #fff; z-index: 2; }
        .delta-positive { color: #d32f2f; font-weight: 600; }
        .delta-negative { color: #2e7d32; font-weight: 600; }
        .delta-neutral { color: #475569; font-weight: 600; }
        .delta-muted { color: #94a3b8; font-weight: 600; }
        .self-review__status { font-size: 15px; margin: 0 0 8px 0; }
        .self-review__status--pass { color: #15803d; }
        .self-review__status--warning { color: #b45309; }
        .self-review__status--fail { color: #b91c1c; }
        .self-review__issues { list-style: disc; padding-left: 20px; color: #475569; }
        .self-review__issues li { margin-bottom: 6px; }
        .self-review__issue-tag { font-weight: 600; margin-right: 6px; }
        .self-review__notes { font-size: 14px; color: #475569; margin-top: 8px; }
    """

    # 2. 构建页面主体
    html_parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<style>{css}</style>",
        "<script src='https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'></script>",
        "</head><body>",
        "<div class='header'><h1>智能分析报告（BETA）</h1>",
        f"<h2 class='sub-title'>{insight_data.get('headline', '数据分析报告')}</h2>",
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

    if mode_id != AI_MODE_MONTHLY:
        # 日报：保留既有硬性结构（同比/环比/计划/逐日明细）
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
            summary_phrases = []
            for entry in yoy_entries:
                unit_text = entry.get("unit") or ""
                current_text = _format_number(entry["current"], entry["decimals"])
                peer_text = _format_number(entry["peer"], entry["decimals"])
                delta_text = _format_percent_text(entry.get("delta"))
                summary_phrases.append(
                    f"{entry['label']} 本期 {current_text}{unit_text}，同期 {peer_text}{unit_text}，同比 {delta_text}"
                )
            for phrase in summary_phrases:
                html_parts.append(f"<p class='ring-summary-line'>{phrase}</p>")
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

        plan_data = processed_data.get("plan_compare") or {}
        plan_entries = plan_data.get("entries") or []
        if plan_entries:
            html_parts.append("<div class='analysis-section'>")
            html_parts.append("<h2>计划比较</h2>")
            note_bits = []
            if plan_data.get("month_label"):
                note_bits.append(f"计划月份：{plan_data['month_label']}")
            if plan_data.get("period_text"):
                note_bits.append(f"期间：{plan_data['period_text']}")
            if note_bits:
                html_parts.append(f"<p class='ring-section__header'>{' ｜ '.join(note_bits)}</p>")
            html_parts.append(
                "<table class='ring-summary__table'><thead><tr>"
                "<th>指标</th><th>截至本期末</th><th>月度计划</th><th>完成率</th>"
                "</tr></thead><tbody>"
            )
            for entry in plan_entries:
                decimals = entry.get("decimals", 2)
                actual_text = _format_number(entry.get("actual_value"), decimals)
                plan_text = _format_number(entry.get("plan_value"), decimals)
                completion_text = _format_percent_text(entry.get("completion_rate"))
                unit = entry.get("unit") or ""
                unit_html = f"<span class='ring-unit'>{unit}</span>" if unit else ""
                html_parts.append(
                    "<tr>"
                    f"<td>{entry.get('label')}</td>"
                    f"<td>{actual_text}{unit_html}</td>"
                    f"<td>{plan_text}{unit_html}</td>"
                    f"<td>{completion_text}</td>"
                    "</tr>"
                )
            html_parts.append("</tbody></table>")
            summary_lines = plan_data.get("summary_lines") or []
            for line in summary_lines:
                html_parts.append(f"<p class='ring-summary-line'>【计划】{line}</p>")
            html_parts.append("</div>")

        timeline_metrics = timeline_matrix.get("metrics") or []
        timeline_rows = timeline_matrix.get("rows") or []
        if timeline_metrics and timeline_rows:
            html_parts.append("<div class='analysis-section'>")
            html_parts.append("<h2>区间明细（逐日）</h2>")
            html_parts.append("<div class='timeline-table-wrap'>")
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
            html_parts.append("</tbody></table></div></div>")
    else:
        # 月报：图文并茂展示“同比/环比/计划”三类关键比较，不沿用日报硬性章节块
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
        ring_data = processed_data.get("ring_compare") or {}
        ring_entries = ring_data.get("entries") or []
        plan_data = processed_data.get("plan_compare") or {}
        plan_entries = plan_data.get("entries") or []
        if yoy_entries or ring_entries or plan_entries:
            html_parts.append("<div class='analysis-section'>")
            html_parts.append("<h2>月度关键对比图表</h2>")
            if yoy_entries:
                html_parts.append("<h3>同比对比</h3>")
                html_parts.append(
                    "<table class='ring-summary__table'><thead><tr><th>指标</th><th>本期</th><th>同期</th><th>同比</th></tr></thead><tbody>"
                )
                for entry in yoy_entries:
                    decimals = entry.get("decimals", 2)
                    unit = entry.get("unit") or ""
                    unit_html = f"<span class='ring-unit'>{unit}</span>" if unit else ""
                    html_parts.append(
                        "<tr>"
                        f"<td>{entry.get('label')}</td>"
                        f"<td>{_format_number(entry.get('current'), decimals)}{unit_html}</td>"
                        f"<td>{_format_number(entry.get('peer'), decimals)}{unit_html}</td>"
                        f"<td>{_format_percent_text(entry.get('delta'))}</td>"
                        "</tr>"
                    )
                html_parts.append("</tbody></table>")
            if ring_entries:
                html_parts.append("<h3>环比对比</h3>")
                html_parts.append(
                    "<table class='ring-summary__table'><thead><tr><th>指标</th><th>本期</th><th>上期</th><th>环比</th></tr></thead><tbody>"
                )
                for entry in ring_entries:
                    decimals = entry.get("decimals", 2)
                    unit = entry.get("unit") or ""
                    unit_html = f"<span class='ring-unit'>{unit}</span>" if unit else ""
                    html_parts.append(
                        "<tr>"
                        f"<td>{entry.get('label')}</td>"
                        f"<td>{_format_number(entry.get('current'), decimals)}{unit_html}</td>"
                        f"<td>{_format_number(entry.get('previous'), decimals)}{unit_html}</td>"
                        f"<td>{_format_percent_text(entry.get('rate'))}</td>"
                        "</tr>"
                    )
                html_parts.append("</tbody></table>")
            if plan_entries:
                html_parts.append("<h3>计划对比</h3>")
                html_parts.append(
                    "<table class='ring-summary__table'><thead><tr><th>指标</th><th>本期</th><th>计划</th><th>完成率</th></tr></thead><tbody>"
                )
                for entry in plan_entries:
                    decimals = entry.get("decimals", 2)
                    unit = entry.get("unit") or ""
                    unit_html = f"<span class='ring-unit'>{unit}</span>" if unit else ""
                    html_parts.append(
                        "<tr>"
                        f"<td>{entry.get('label')}</td>"
                        f"<td>{_format_number(entry.get('actual_value'), decimals)}{unit_html}</td>"
                        f"<td>{_format_number(entry.get('plan_value'), decimals)}{unit_html}</td>"
                        f"<td>{_format_percent_text(entry.get('completion_rate'))}</td>"
                        "</tr>"
                    )
                html_parts.append("</tbody></table>")
            html_parts.append("</div>")

    review_section: List[str] = []
    if validation_block:
        status = (validation_block.get("status") or "pending").lower()
        status_label_map = {
            "pass": "核对通过",
            "warning": "存在提示",
            "fail": "发现异常",
            "pending": "待核对",
        }
        status_label = status_label_map.get(status, "待核对")
        review_section.append("<div class='analysis-section'>")
        review_section.append("<h2>智能核对结果</h2>")
        review_section.append(
            f"<p class='self-review__status self-review__status--{status}'><strong>结论：</strong>{status_label}</p>"
        )
        issues = validation_block.get("issues") or []
        if issues:
            review_section.append("<ul class='self-review__issues'>")
            for issue in issues:
                section = issue.get("section") or "未注明段落"
                desc = issue.get("description") or "无描述"
                level = (issue.get("severity") or "").lower() or "info"
                suggestion = issue.get("suggestion")
                review_section.append(
                    "<li>"
                    f"<span class='self-review__issue-tag'>[{section} / {level}]</span>"
                    f"{desc}"
                    f"{f'（建议：{suggestion}）' if suggestion else ''}"
                    "</li>"
                )
            review_section.append("</ul>")
        notes = validation_block.get("notes")
        if notes:
            review_section.append(f"<p class='self-review__notes'>{notes}</p>")
        review_section.append("</div>")

    # 7. 底部免责声明
    html_parts.append("""
        <div style='text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #9ca3af; font-size: 12px;'>
            <p>本报告根据查询数据自动生成，仅供参考</p>
        </div>
    """)

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
            var defaultIndex = rawData.findIndex(function(item) {{ return !item.is_temp; }});
            if (defaultIndex < 0) {{ defaultIndex = 0; }}
            selector.value = defaultIndex;

            function updateChart() {{
                var idx = parseInt(selector.value, 10);
                if (isNaN(idx) || idx < 0 || idx >= rawData.length) {{ idx = 0; }}
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

                // 右轴：气温参考线
                if (tempMetric) {{
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
    html_parts.extend(review_section)

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
        mode_id = _normalize_ai_mode(payload.get("ai_mode_id"))
        mode_templates = _resolve_mode_templates(mode_id)
        user_prompt = _sanitize_user_prompt(payload.get("ai_user_prompt"))
        _logger.info(
            "AI report job %s started (unit=%s, mode=%s, ai_mode=%s, metrics=%s)",
            job_id,
            meta.get("unit_key") or meta.get("unit_label"),
            meta.get("analysis_mode"),
            mode_id,
            ",".join(payload.get("resolved_metrics") or []),
        )
        processed_data = _preprocess_payload(payload, mode_id=mode_id)
        extra_instruction = _load_instruction_text(mode_id)
        feature_flags = _load_ai_runtime_flags()
        enable_validation_stage = feature_flags.get("enable_validation", True)
        report_mode = feature_flags.get("report_mode", "full")
        _update_job(job_id, status="running", stage="insight", started_at=_current_time_iso())

        validation_data = None

        if report_mode == "fast":
            # ========== 极速模式：合并 Insight + Layout ==========
            _logger.info("AI report job %s using FAST mode", job_id)
            fast_prompt = _build_fast_insight_layout_prompt(
                processed_data,
                extra_instruction,
                user_prompt,
                mode_templates["fast_insight_layout"],
            )
            combined_data = _run_json_stage("洞察+规划", fast_prompt)
            insight_data = combined_data.get("insight") or {}
            layout_data = combined_data.get("layout") or {}
            _update_job(job_id, stage="content", insight=insight_data, layout=layout_data)

            content_prompt = _build_content_prompt(
                insight_data,
                layout_data,
                extra_instruction,
                user_prompt,
                mode_templates["content"],
            )
            content_data = _run_json_stage("内容撰写", content_prompt)

            if enable_validation_stage:
                _update_job(job_id, stage="review", content=content_data)
                fast_validation_prompt = _build_fast_validation_prompt(
                    processed_data,
                    content_data,
                    extra_instruction,
                    user_prompt,
                    mode_templates["fast_validation"],
                )
                validation_data = _run_json_stage("快速核查", fast_validation_prompt)
                _update_job(job_id, validation=validation_data)
                # 极速模式不触发 Revision，只记录警告
            else:
                _update_job(job_id, stage="content", content=content_data)
        else:
            # ========== 完整模式：5 阶段流程 ==========
            insight_prompt = _build_insight_prompt(
                processed_data,
                extra_instruction,
                user_prompt,
                mode_templates["insight"],
            )
            insight_data = _run_json_stage("洞察分析", insight_prompt)
            _update_job(job_id, stage="layout", insight=insight_data)

            layout_prompt = _build_layout_prompt(
                processed_data,
                insight_data,
                extra_instruction,
                user_prompt,
                mode_templates["layout"],
            )
            layout_data = _run_json_stage("结构规划", layout_prompt)
            _update_job(job_id, stage="content", layout=layout_data)

            content_prompt = _build_content_prompt(
                insight_data,
                layout_data,
                extra_instruction,
                user_prompt,
                mode_templates["content"],
            )
            content_data = _run_json_stage("内容撰写", content_prompt)

            if enable_validation_stage:
                _update_job(job_id, stage="review", content=content_data)
                validation_prompt = _build_validation_prompt(
                    processed_data,
                    content_data,
                    extra_instruction,
                    user_prompt,
                    mode_templates["validation"],
                )
                validation_data = _run_json_stage("检查核实", validation_prompt)
                _update_job(job_id, validation=validation_data)

                status = (validation_data.get("status") or "").lower() if validation_data else ""
                issues = (validation_data or {}).get("issues") or []
                needs_revision = bool(issues) and status in {"warning", "fail"}
                if needs_revision:
                    _logger.info(
                        "AI report job %s entering revision stage (status=%s, issues=%d)",
                        job_id,
                        status,
                        len(issues),
                    )
                    _update_job(job_id, stage="revision_pending")
                    revision_prompt = _build_revision_prompt(
                        processed_data,
                        insight_data,
                        layout_data,
                        content_data,
                        validation_data,
                        extra_instruction,
                        user_prompt,
                        mode_templates["revision"],
                    )
                    content_data = _run_json_stage("内容修订", revision_prompt)
                    _update_job(job_id, stage="revision_content", content=content_data)
                    validation_prompt = _build_validation_prompt(
                        processed_data,
                        content_data,
                        extra_instruction,
                        user_prompt,
                        mode_templates["validation"],
                    )
                    validation_data = _run_json_stage("复核检查", validation_prompt)
                    _update_job(job_id, stage="review", validation=validation_data)
            else:
                _update_job(job_id, stage="content", content=content_data)

        html_report = _generate_report_html(
            processed_data,
            insight_data,
            layout_data,
            content_data,
            validation_data,
        )

        _update_job(
            job_id,
            status="ready",
            stage="ready",
            report=html_report,
            model=_current_runtime_model_name(),
            ai_mode_id=mode_id,
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
        "ai_mode_id": _normalize_ai_mode(payload.get("ai_mode_id")),
        "created_at": _current_time_iso(),
        "started_at": None,
        "report": None,
        "error": None,
        "model": None,
        "insight": None,
        "layout": None,
        "content": None,
        "validation": None,
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
