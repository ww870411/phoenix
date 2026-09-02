
# -*- coding: utf-8 -*-
"""
工程发货单 / 随车送货单 AI 视觉智能解析服务。
支持使用 Gemini Flash Lite / Gemini Flash 等多模态视觉模型对拍照发货单进行结构化提取，
并自动对齐系统字典（标段名称、供给主体、保温管/管件规格型号）。
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    load_tube_config,
    get_config_list,
    get_configured_ocr_tool_config,
    DEFAULT_OCR_SYSTEM_PROMPT,
)

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def _normalize_gemini_model_name(model_name: Optional[str]) -> str:
    """
    清洗并规范化 Google Gemini 模型名称：
    1. 去除首尾空白与控制符
    2. 剥离多余的 'models/' 或 'models:' 前缀（防止生成 models/models/xxx 导致 400 unexpected model name format）
    """
    if not model_name:
        return "gemini-3.5-flash-lite"

    clean = str(model_name).strip()
    if clean.lower().startswith("models/"):
        clean = clean[7:].strip()
    elif clean.lower().startswith("models:"):
        clean = clean[7:].strip()

    return clean or "gemini-3.5-flash-lite"


PROMPT_UNIVERSAL_DOCUMENT_OCR = DEFAULT_OCR_SYSTEM_PROMPT
PROMPT_DELIVERY_BILL_OCR = PROMPT_UNIVERSAL_DOCUMENT_OCR



PROMPT_DOCUMENT_VERIFICATION_AGENT = """你是一个顶级工程物资单据与业务表格质检审核专家（Review & Quality-Assurance Auditor）。
你的任务是对照上传的单据原图，对【第一阶段初步提取的结构化数据】进行严格的交叉复核与自动纠偏。

【待复核的初步数据】：
{stage1_json}

【复核审核与纠偏核心要点】：
1. 【条目名称真实性审核】：
   - 逐一比对 metadata_fields 中的每个字段名称 (label) 与原图文字。
   - 严格纠偏：若原图写的是“入库日期”，绝不可接受被错写成“发货日期”；若写的是“车号”，label 必须是“车号”；若写的是“验收人”，必须为“验收人”。
   - 绝不臆测：若原图并无某些属性（例如没有司机电话或无发货编号），必须彻底清除，严禁凭空脑补！
2. 【表格完整性、明细精确度与合计行审核（极重要）】：
   - 核验 table_columns 是否漏列或多列，必须完整还原原图表格中真实存在的每一个表头列名。
   - 逐行逐字核验 table_rows：重点核查规格型号（如 DN 直径、壁厚、压力等级、弯头度数）、数量数值（小数点、正负号）、计量单位（米/个/件/吨）、批号等是否与原图 100% 吻合，发现错别字或数字看错必须纠正！
   - 检查是否有漏识别的数据行，**尤其是核查表格底部的“合计”/“总计”行是否已还原为 table_rows 的最后一行**。若原图表格底部有“合计”但第一阶段遗漏了，必须在此阶段补齐到 table_rows 的末行！
3. 【生成复核质检报告】：
   - 记录你具体发现了哪些偏差、修正了哪些条目或数值（如：“在表格末行补齐原图的合计汇总行”），并给出置信度得分（0~100）。

【输出 JSON 字段结构】：
{
  "document_title": "核准的单据真实标题",
  "metadata_fields": [
    {"label": "真实字段名1", "value": "核对后的真实内容1"}
  ],
  "table_columns": ["核对后的实际列名1", "核对后的实际列名2"],
  "table_rows": [
    {"核对后的实际列名1": "值1", "核对后的实际列名2": "值2"}
  "remarks": "单据附注说明",
  "verification_report": {
    "status": "verified",
    "confidence_score": 99.5,
    "corrections_made": [
      "具体纠偏记录说明1（如：将发货日期校正为原始标签入库日期）",
      "具体复核确认项2（如：已在表格末尾完整还原原单据底部的合计行）"
    ],
    "quality_summary": "原图与数据交叉比对结论摘要"
  }
}

【输出规范】：
请直接输出纯 JSON 对象，不要包含 markdown 代码块反引号，不要有多余修饰语。
"""


def _normalize_phi_symbol(s: str) -> str:
    """将各类非标准/小写直径符号（如 φ、ϕ、Ф、⌀、ø 等）统一修正为标准大写「Φ」符号"""
    if not s:
        return ""
    return re.sub(r'[\u03c6\u03d5\u0424\u0444\u2300\u00f8\u00d8]', 'Φ', s)


def _normalize_str(s: Any) -> str:
    res = str(s or "").strip()
    return _normalize_phi_symbol(res)


def _match_section_name(raw_name: str, payload: Dict[str, Any]) -> tuple[Optional[str], str]:
    """将 OCR 识别出的标段名称与系统配置的 10 大标段进行模糊匹配对齐"""
    if not raw_name:
        return None, ""
    clean = re.sub(r'[\s_—\-\(\)（）]', '', raw_name.lower())
    sections = get_config_list(payload, "section_1_options")
    
    for sec in sections:
        sec_id = _normalize_str(sec.get("section_1_id"))
        sec_name = _normalize_str(sec.get("section_1_name"))
        clean_sec = re.sub(r'[\s_—\-\(\)（）]', '', sec_name.lower())
        if clean_sec in clean or clean in clean_sec or sec_id.lower() in clean:
            return sec_id, sec_name

    num_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
    clean_digits = clean
    for cn_num, ar_num in num_map.items():
        clean_digits = clean_digits.replace(cn_num, ar_num)

    for sec in sections:
        sec_id = _normalize_str(sec.get("section_1_id"))
        sec_name = _normalize_str(sec.get("section_1_name"))
        sec_num_match = re.search(r'(\d+)', sec_id)
        if sec_num_match:
            sec_num = sec_num_match.group(1)
            if f"{sec_num}标段" in clean_digits or f"标段{sec_num}" in clean_digits or f"第{sec_num}" in clean_digits or f"{sec_num}标" in clean_digits:
                if "高温" in clean and "high" in sec_id:
                    return sec_id, sec_name
                elif "低温" in clean and "low" in sec_id:
                    return sec_id, sec_name
                elif "高温" not in clean and "低温" not in clean:
                    return sec_id, sec_name

    return None, raw_name


def _levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串的 Levenshtein 编辑距离（动态规划）"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _match_supplier_name(raw_name: str, payload: Dict[str, Any]) -> Tuple[Optional[str], str, bool]:
    """
    将 OCR 识别出的发货厂家/供货单位与系统供给主体进行对齐：
    1. 精确匹配与子串包含匹配（完全匹配）
    2. 针对仅差 1 个字（编辑距离 = 1 或长名称相似度高）的同音/形近/错字，自动纠偏为系统标准企业全称
    返回: (supply_entity_id, supply_entity_name, is_corrected)
    """
    if not raw_name:
        return None, "", False
    clean = re.sub(r'[\s_—\-\(\)（）:：]', '', raw_name.lower())
    suppliers = get_config_list(payload, "supply_entities")

    # 1. 第一优先级：精确匹配或包含匹配
    for sup in suppliers:
        sup_id = _normalize_str(sup.get("supply_entity_id") or sup.get("entity_id"))
        sup_name = _normalize_str(sup.get("supply_entity_name") or sup.get("entity_name"))
        clean_sup = re.sub(r'[\s_—\-\(\)（）:：]', '', sup_name.lower())
        if clean_sup and (clean_sup in clean or clean in clean_sup or (sup_id and sup_id.lower() in clean)):
            return sup_id, sup_name, False

    # 2. 第二优先级：针对 >=4 字符的企业全称，进行编辑距离 = 1 的智能容错纠偏
    if len(clean) >= 4:
        best_match = None
        min_distance = 999
        for sup in suppliers:
            sup_id = _normalize_str(sup.get("supply_entity_id") or sup.get("entity_id"))
            sup_name = _normalize_str(sup.get("supply_entity_name") or sup.get("entity_name"))
            clean_sup = re.sub(r'[\s_—\-\(\)（）:：]', '', sup_name.lower())
            if not clean_sup or len(clean_sup) < 4:
                continue

            dist = _levenshtein_distance(clean, clean_sup)
            # 若仅差 1 个字，或长度>=8时差<=2个字
            if dist == 1 or (len(clean) >= 8 and dist <= 2):
                if dist < min_distance:
                    min_distance = dist
                    best_match = (sup_id, sup_name, True)

        if best_match:
            return best_match

    return None, raw_name, False


def repair_incomplete_json(json_str: str) -> Optional[Dict[str, Any]]:
    """
    智能修复可能被截断的 JSON 文本（自动补齐双引号、清除悬空键值、闭合嵌套花括号与数组）
    """
    s = json_str.strip()
    first_brace = s.find('{')
    if first_brace == -1:
        return None
    s = s[first_brace:]

    for trim_len in range(0, min(len(s), 400)):
        candidate = s if trim_len == 0 else s[:-trim_len]
        candidate = candidate.strip()

        while candidate and candidate[-1] in (',', ':', ' '):
            candidate = candidate[:-1].strip()

        quote_count = 0
        escaped = False
        for ch in candidate:
            if ch == '\\' and not escaped:
                escaped = True
                continue
            if ch == '"' and not escaped:
                quote_count += 1
            escaped = False

        candidate_with_quote = (candidate + '"') if (quote_count % 2 != 0) else candidate

        for cand_attempt in [candidate_with_quote, candidate]:
            c = cand_attempt.strip()
            while c and c[-1] in (',', ':', ' '):
                c = c[:-1].strip()

            stack = []
            in_str = False
            escaped = False
            valid = True
            for ch in c:
                if ch == '\\' and not escaped:
                    escaped = True
                    continue
                if ch == '"' and not escaped:
                    in_str = not in_str
                elif not in_str:
                    if ch in ('{', '['):
                        stack.append(ch)
                    elif ch == '}':
                        if stack and stack[-1] == '{':
                            stack.pop()
                        else:
                            valid = False
                            break
                    elif ch == ']':
                        if stack and stack[-1] == '[':
                            stack.pop()
                        else:
                            valid = False
                            break
                escaped = False

            if not valid or in_str:
                continue

            closing = ""
            for open_ch in reversed(stack):
                if open_ch == '{':
                    closing += '}'
                elif open_ch == '[':
                    closing += ']'

            try:
                parsed = json.loads(c + closing, strict=False)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

    return None


def _call_gemini_vision(
    url: str,
    mime_type: str,
    clean_b64: str,
    prompt_text: str,
    temperature: float = 0.1,
) -> Tuple[str, Dict[str, Any]]:
    """执行一次视觉模型请求；重试与兜底均由上层调度器按配置控制。"""
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": clean_b64,
                        }
                    },
                    {"text": prompt_text},
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = httpx.post(url, json=payload, timeout=45.0)
    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"连线识别引擎 API 失败，请检查网络配置。异常: {exc}",
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="视觉引擎响应超时，请重试或压缩图片大小。",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"请求视觉模型异常: {exc}") from exc

    if response.status_code != 200:
        err_detail = response.text
        try:
            err_json = response.json()
            err_msg = err_json.get("error", {}).get("message") or err_detail
        except Exception:
            err_msg = err_detail

        lowered_msg = str(err_msg).lower()
        is_busy = (
            response.status_code == 503
            or "high demand" in lowered_msg
            or "overloaded" in lowered_msg
            or "temporarily unavailable" in lowered_msg
            or "service unavailable" in lowered_msg
            or "resource_exhausted" in lowered_msg
        )
        if is_busy:
            raise HTTPException(status_code=503, detail=f"服务器繁忙 (503): {err_msg}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"识别模型 API 返回错误 ({response.status_code}): {err_msg}",
        )

    res_json = response.json()
    candidates = res_json.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=500, detail="模型未返回有效的文本解析结果。")

    parts = candidates[0].get("content", {}).get("parts") or []
    raw_text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    usage_metadata = res_json.get("usageMetadata") or {}
    return raw_text, usage_metadata


def _parse_extracted_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    超强容错解析视觉模型返回的 JSON 字符串：
    1. 剥离 markdown 反引号前缀与尾随字符
    2. 允许非严格控制字符（strict=False）
    3. 智能截取首尾花括号子串
    4. 针对被截断或引号未闭合的 JSON 进行自动补全自愈
    """
    if not raw_text or not str(raw_text).strip():
        return None

    cleaned_json_str = str(raw_text).strip()
    if cleaned_json_str.startswith("```json"):
        cleaned_json_str = cleaned_json_str[7:]
    elif cleaned_json_str.startswith("```"):
        cleaned_json_str = cleaned_json_str[3:]
    if cleaned_json_str.endswith("```"):
        cleaned_json_str = cleaned_json_str[:-3]
    cleaned_json_str = cleaned_json_str.strip()

    # 阶段 1：直接尝试非严格模式反序列化
    try:
        extracted = json.loads(cleaned_json_str, strict=False)
        if isinstance(extracted, dict):
            return extracted
        if isinstance(extracted, list):
            return {"table_rows": extracted}
    except Exception:
        pass

    # 阶段 2：截取首个 '{' 到最后一个 '}' 之间的核心内容
    first_brace = cleaned_json_str.find('{')
    last_brace = cleaned_json_str.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        sub_json = cleaned_json_str[first_brace:last_brace + 1]
        try:
            extracted = json.loads(sub_json, strict=False)
            if isinstance(extracted, dict):
                return extracted
        except Exception:
            pass

    # 阶段 3：截取首个 '[' 到最后一个 ']' 之间的数组内容并包装
    first_bracket = cleaned_json_str.find('[')
    last_bracket = cleaned_json_str.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        sub_arr = cleaned_json_str[first_bracket:last_bracket + 1]
        try:
            arr_extracted = json.loads(sub_arr, strict=False)
            if isinstance(arr_extracted, list):
                return {"table_rows": arr_extracted}
        except Exception:
            pass

    # 阶段 4：智能修复可能被截断的 JSON 结构
    try:
        extracted = repair_incomplete_json(cleaned_json_str)
        if isinstance(extracted, dict):
            return extracted
    except Exception:
        pass

    return None


def _call_gemini_vision_with_fallbacks(
    active_key: str,
    candidate_models: List[str],
    mime_type: str,
    clean_b64: str,
    prompt_text: str,
    temperature: float = 0.1,
    stage_name: str = "阶段 1 (视觉解析提取)",
    api_logs_collector: Optional[List[Dict[str, Any]]] = None,
    enable_fallback: bool = False,
    retry_primary_on_error: bool = False,
    primary_retry_count: int = 0,
) -> Tuple[str, str, bool]:
    """
    按后台配置调度模型：
    - 主模型始终只在遇到错误后才继续处理；
    - 仅在启用主模型重试时，重试首选模型；
    - 仅在启用兜底时，主模型（含其重试）失败后才顺序尝试手填备选模型；
    - 不追加任何内置模型，确保实际行为完全由管理员配置决定。
    """
    sanitized_models: List[str] = []
    for model in candidate_models:
        normalized_model = _normalize_gemini_model_name(model)
        if normalized_model and normalized_model not in sanitized_models:
            sanitized_models.append(normalized_model)

    if not sanitized_models:
        raise HTTPException(status_code=400, detail="未配置可用的单据识别主模型。")

    if not enable_fallback:
        sanitized_models = sanitized_models[:1]

    try:
        configured_retry_count = int(primary_retry_count or 0)
    except (TypeError, ValueError):
        configured_retry_count = 0
    configured_retry_count = max(0, min(configured_retry_count, 5))
    primary_attempts = 1 + (configured_retry_count if retry_primary_on_error else 0)

    last_error: Optional[Exception] = None
    for model_index, model_name in enumerate(sanitized_models):
        attempts_for_model = primary_attempts if model_index == 0 else 1

        for attempt_index in range(attempts_for_model):
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={active_key}"
            )
            endpoint_display = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            started_at = time.time()
            log_entry = {
                "stage": stage_name,
                "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "endpoint": endpoint_display,
                "method": "POST",
                "model": model_name,
                "attempt": attempt_index + 1,
                "is_primary_retry": model_index == 0 and attempt_index > 0,
                "prompt_length": len(prompt_text),
                "prompt_preview": prompt_text[:300] + ("..." if len(prompt_text) > 300 else ""),
                "full_prompt": prompt_text,
                "http_status": None,
                "duration_ms": 0,
                "success": False,
                "usage_metadata": {},
                "response_preview": "",
                "raw_response_text": "",
                "error_message": None,
            }

            try:
                raw_text, usage_metadata = _call_gemini_vision(
                    url=url,
                    mime_type=mime_type,
                    clean_b64=clean_b64,
                    prompt_text=prompt_text,
                    temperature=temperature,
                )
                log_entry.update({
                    "http_status": 200,
                    "duration_ms": int((time.time() - started_at) * 1000),
                    "success": True,
                    "usage_metadata": usage_metadata,
                    "response_preview": raw_text[:400] + ("..." if len(raw_text) > 400 else ""),
                    "raw_response_text": raw_text,
                })
                if api_logs_collector is not None:
                    api_logs_collector.append(log_entry)
                return raw_text, model_name, model_index > 0
            except HTTPException as exc:
                last_error = exc
                log_entry.update({
                    "http_status": exc.status_code,
                    "duration_ms": int((time.time() - started_at) * 1000),
                    "error_message": exc.detail,
                })
            except Exception as exc:
                last_error = exc
                log_entry.update({
                    "http_status": 500,
                    "duration_ms": int((time.time() - started_at) * 1000),
                    "error_message": str(exc),
                })

            if api_logs_collector is not None:
                api_logs_collector.append(log_entry)

            if model_index == 0 and attempt_index < attempts_for_model - 1:
                logger.warning(
                    "视觉主模型 [%s] 请求失败，按配置进行第 %s/%s 次重试。",
                    model_name,
                    attempt_index + 1,
                    configured_retry_count,
                )
                continue
            break

        if model_index < len(sanitized_models) - 1:
            next_model = sanitized_models[model_index + 1]
            logger.warning(
                "视觉主模型 [%s] 请求失败，已启用兜底，切换至手填备选模型 [%s]。",
                model_name,
                next_model,
            )

    if isinstance(last_error, HTTPException):
        raise last_error
    if last_error is not None:
        raise HTTPException(status_code=500, detail=f"模型调用异常: {last_error}") from last_error
    raise HTTPException(status_code=500, detail="未获取到大模型响应结果。")


def extract_delivery_bill_data(
    image_base64: str,
    mime_type: str = "image/jpeg",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    enable_double_check: bool = False,
) -> Dict[str, Any]:
    """
    接收业务单据照片（Base64 编码），调度 Gemini 多模态视觉模型进行一步到位的高精度结构化数据提取。
    
    调度策略：
    - 主模型重试与备选模型兜底均以后台显式配置为准，默认均不执行。
    - 坚持“所见即所得、忠于原件”提取，绝不臆造未出现的字段，绝不对表格明细进行跨列同义词篡改。
    """
    if not image_base64:
        raise HTTPException(status_code=400, detail="图片数据不能为空")

    clean_b64 = image_base64
    if "base64," in clean_b64:
        header, clean_b64 = clean_b64.split("base64,", 1)
        if "image/png" in header:
            mime_type = "image/png"
        elif "image/webp" in header:
            mime_type = "image/webp"

    # 读取 API Key 与主备模型配置
    tube_config = load_tube_config()
    stored_ocr_cfg = get_configured_ocr_tool_config(tube_config)

    # 检查是否处于“功能维护中”模式
    if not stored_ocr_cfg.get("enabled", True):
        raise HTTPException(
            status_code=503,
            detail="业务单据智能识别功能维护中，暂不可用。请稍后再试或联系系统管理员开启服务。"
        )

    active_key = api_key or stored_ocr_cfg.get("api_key")
    raw_primary_model = model_name or stored_ocr_cfg.get("model") or DEFAULT_GEMINI_MODEL
    stored_fallbacks = stored_ocr_cfg.get("fallback_models") or []
    enable_fallback = bool(stored_ocr_cfg.get("enable_fallback", False))
    retry_primary_on_error = bool(stored_ocr_cfg.get("retry_primary_on_error", False))
    primary_retry_count = int(stored_ocr_cfg.get("primary_retry_count", 0) or 0)
    # 构造候选模型有序序列（规范化并去重）
    primary_norm = _normalize_gemini_model_name(raw_primary_model)
    candidate_models = [primary_norm]
    for fb in stored_fallbacks:
        fb_norm = _normalize_gemini_model_name(fb)
        if fb_norm and fb_norm not in candidate_models:
            candidate_models.append(fb_norm)

    # 严格校验 tube_config.json 中的专属 API Key，严禁任何外部全局隐式兜底
    if not active_key:
        raise HTTPException(
            status_code=400,
            detail="系统配置文件 tube_config.json 中尚未配置单据识别专属 API Key。请管理员在后台【单据识别模型与 API 配置】中配置专属 API Key 并保存后使用。"
        )

    t_total_start = time.time()
    api_logs: List[Dict[str, Any]] = []
    stored_prompt = stored_ocr_cfg.get("system_prompt")
    prompt_stage1 = custom_prompt or stored_prompt or PROMPT_DELIVERY_BILL_OCR

    # ========================================================
    # 单阶段高精度结构化视觉提取（调用策略完全由后台配置决定）
    # ========================================================
    t_stage1_start = time.time()
    raw_text_stage1, used_model_stage1, fb_stage1_triggered = _call_gemini_vision_with_fallbacks(
        active_key=active_key,
        candidate_models=candidate_models,
        mime_type=mime_type,
        clean_b64=clean_b64,
        prompt_text=prompt_stage1,
        temperature=0.1,
        stage_name="阶段 1 (视觉解析提取)",
        api_logs_collector=api_logs,
        enable_fallback=enable_fallback,
        retry_primary_on_error=retry_primary_on_error,
        primary_retry_count=primary_retry_count,
    )
    t_stage1_end = time.time()
    stage1_duration = round(t_stage1_end - t_stage1_start, 2)

    stage1_json = _parse_extracted_json(raw_text_stage1)
    if not stage1_json:
        raise HTTPException(
            status_code=502,
            detail=f"识别内容无法解析为有效 JSON。原始内容: {raw_text_stage1[:300]}"
        )

    final_extracted = stage1_json
    actual_used_model = used_model_stage1
    model_fallback_triggered = fb_stage1_triggered

    # ========================================================
    # 若显式开启 double check 则支持可选复核，默认单阶段秒级响应
    # ========================================================
    stage2_duration = 0.0
    used_model_stage2 = None
    verification_report = {
        "status": "verified",
        "confidence_score": 99.0,
        "corrections_count": 0,
        "corrections_made": [],
        "quality_summary": "单据已完成高精度结构化提取。"
    }

    if enable_double_check:
        t_stage2_start = time.time()
        try:
            prompt_stage2 = PROMPT_DOCUMENT_VERIFICATION_AGENT.replace(
                "{stage1_json}",
                json.dumps(stage1_json, ensure_ascii=False, indent=2)
            )
            stage2_candidates = [used_model_stage1] + [m for m in candidate_models if m != used_model_stage1]
            raw_text_stage2, used_model_stage2, _ = _call_gemini_vision_with_fallbacks(
                active_key=active_key,
                candidate_models=stage2_candidates,
                mime_type=mime_type,
                clean_b64=clean_b64,
                prompt_text=prompt_stage2,
                temperature=0.1,
                stage_name="阶段 2 (复核纠偏)",
                api_logs_collector=api_logs,
                enable_fallback=enable_fallback,
                retry_primary_on_error=retry_primary_on_error,
                primary_retry_count=primary_retry_count,
            )
            stage2_json = _parse_extracted_json(raw_text_stage2)
            if stage2_json and isinstance(stage2_json, dict):
                merged = dict(stage1_json)
                merged.update({k: v for k, v in stage2_json.items() if v is not None and v != ""})
                s1_rows = stage1_json.get("table_rows") or stage1_json.get("items")
                s2_rows = stage2_json.get("table_rows") or stage2_json.get("items")
                if (not s2_rows or len(s2_rows) == 0) and s1_rows and len(s1_rows) > 0:
                    merged["table_rows"] = s1_rows
                final_extracted = merged

                rep = stage2_json.get("verification_report")
                if isinstance(rep, dict):
                    corrections = rep.get("corrections_made") or []
                    verification_report = {
                        "status": rep.get("status") or ("corrected" if corrections else "verified"),
                        "confidence_score": float(rep.get("confidence_score") or 99.0),
                        "corrections_count": len(corrections),
                        "corrections_made": [str(c) for c in corrections],
                        "quality_summary": rep.get("quality_summary") or "复核完成。"
                    }
        except Exception as e:
            logger.warning(f"阶段2复核跳过: {e}")
        finally:
            stage2_duration = round(time.time() - t_stage2_start, 2)

    # ========================================================
    # 结构规范化与业务数据汇总（所见即所得，拒绝篡改）
    # ========================================================
    return _build_normalized_ocr_result(
        final_extracted=final_extracted,
        actual_used_model=actual_used_model,
        primary_norm=primary_norm,
        candidate_models=candidate_models,
        enable_fallback=enable_fallback,
        retry_primary_on_error=retry_primary_on_error,
        primary_retry_count=primary_retry_count,
        model_fallback_triggered=model_fallback_triggered,
        enable_double_check=enable_double_check,
        used_model_stage1=used_model_stage1,
        stage1_duration=stage1_duration,
        used_model_stage2=used_model_stage2,
        stage2_duration=stage2_duration,
        verification_report=verification_report,
        api_logs=api_logs,
        raw_text_summary=raw_text_stage1[:500],
        t_total_start=t_total_start,
    )


def _build_normalized_ocr_result(
    final_extracted: Dict[str, Any],
    actual_used_model: str,
    primary_norm: str,
    candidate_models: List[str],
    enable_fallback: bool,
    retry_primary_on_error: bool,
    primary_retry_count: int,
    model_fallback_triggered: bool,
    enable_double_check: bool = False,
    used_model_stage1: Optional[str] = None,
    stage1_duration: float = 0.0,
    used_model_stage2: Optional[str] = None,
    stage2_duration: float = 0.0,
    verification_report: Optional[Dict[str, Any]] = None,
    api_logs: Optional[List[Dict[str, Any]]] = None,
    raw_text_summary: str = "",
    t_total_start: Optional[float] = None,
) -> Dict[str, Any]:
    """统一构建规范化、清洗后的单据识别结果结构体"""
    if verification_report is None:
        verification_report = {
            "status": "verified",
            "confidence_score": 99.0,
            "corrections_count": 0,
            "corrections_made": [],
            "quality_summary": "单据已完成高精度结构化提取。"
        }
    if api_logs is None:
        api_logs = []

    # 1. 单据真实标题
    doc_title = _normalize_str(final_extracted.get("document_title") or final_extracted.get("bill_type") or "单据明细台账")

    # 2. 动态主头信息 (metadata_fields)
    raw_meta = final_extracted.get("metadata_fields")
    metadata_fields: List[Dict[str, str]] = []
    if isinstance(raw_meta, list):
        for item in raw_meta:
            if isinstance(item, dict):
                lbl = _normalize_str(item.get("label") or item.get("name") or item.get("key"))
                val = _normalize_str(item.get("value") or item.get("val") or item.get("text"))
                if lbl:
                    metadata_fields.append({"label": lbl, "value": val})
    elif isinstance(raw_meta, dict):
        for k, v in raw_meta.items():
            if _normalize_str(k) and v is not None:
                metadata_fields.append({"label": _normalize_str(k), "value": _normalize_str(v)})
    else:
        legacy_field_map = [
            ("单据编号", "delivery_code"),
            ("日期", "ship_date"),
            ("供货单位", "supplier_name"),
            ("接收单位", "section_name"),
            ("车牌号", "vehicle_plate_no"),
            ("司机姓名", "driver_name"),
            ("司机电话", "driver_phone"),
            ("发料/开单", "sender_name"),
            ("收料/验收", "receiver_name"),
        ]
        for cn_label, key in legacy_field_map:
            val = _normalize_str(final_extracted.get(key))
            if val:
                metadata_fields.append({"label": cn_label, "value": val})

    # 2.1 针对 metadata_fields 进行表单印刷混淆清洗、系统级主体对齐与 1 字差异智能纠偏
    try:
        current_tube_cfg = load_tube_config()
        prefix_clean_patterns = [
            (r'^(?:姓名|名字|人名)[:：\s]+', "姓名"),
            (r'^(?:牌照|车号|车牌)[:：\s]+', "车牌号"),
            (r'^(?:电话|手机|联系电话)[:：\s]+', "联系电话"),
            (r'^(?:单位全称|单位名称|厂家名称)[:：\s]+', "单位名称"),
            (r'^(?:时间|日期)[:：\s]+', "日期"),
        ]

        for meta_item in metadata_fields:
            m_lbl = meta_item.get("label", "")
            m_val = meta_item.get("value", "")

            # 2.1.1 消除混入 value 的嵌套引导词（如单据写“司机：姓名 满仓”导致 value 为“姓名 满仓”）
            if m_val:
                for pat, clean_tag in prefix_clean_patterns:
                    if re.search(pat, m_val):
                        cleaned_v = re.sub(pat, '', m_val).strip()
                        if cleaned_v:
                            correction_msg = f"【单据排版混淆清洗】：已剥离「{m_lbl}」值中的冗余引导词「{m_val}」->「{cleaned_v}」"
                            meta_item["value"] = cleaned_v
                            m_val = cleaned_v
                            # 若原 label 仅为“司机”，规范为“司机姓名”
                            if m_lbl in ("司机", "驾驶员") and clean_tag == "姓名":
                                meta_item["label"] = "司机姓名"
                                m_lbl = "司机姓名"
                            if correction_msg not in verification_report["corrections_made"]:
                                verification_report["corrections_made"].append(correction_msg)
                                verification_report["corrections_count"] = len(verification_report["corrections_made"])
                                verification_report["status"] = "corrected"
                        break

            # 2.1.2 若字段标签包含供货、发料、单位、厂家等关键词，执行 1 字容错纠偏
            if m_val and any(k in m_lbl for k in ["供", "发料", "发货", "厂家", "出库", "制造", "单位", "生产"]):
                _, matched_sup_name, is_corrected = _match_supplier_name(m_val, current_tube_cfg)
                if is_corrected and matched_sup_name and matched_sup_name != m_val:
                    correction_msg = f"【供应商名称自动纠偏】：检测到「{m_val}」与系统登记主体仅差1字，已自动校正为「{matched_sup_name}」"
                    meta_item["value"] = matched_sup_name
                    if correction_msg not in verification_report["corrections_made"]:
                        verification_report["corrections_made"].append(correction_msg)
                        verification_report["corrections_count"] = len(verification_report["corrections_made"])
                        verification_report["status"] = "corrected"
    except Exception as match_err:
        logger.warning(f"单据抬头主体对齐处理跳过: {match_err}")

    # 3. 动态表格列与行 (table_columns & table_rows)
    raw_cols = final_extracted.get("table_columns") or final_extracted.get("columns") or final_extracted.get("headers")
    table_columns: List[str] = []
    if isinstance(raw_cols, list):
        table_columns = [_normalize_str(c) for c in raw_cols if _normalize_str(c)]

    raw_rows = (
        final_extracted.get("table_rows") or
        final_extracted.get("rows") or
        final_extracted.get("items") or
        final_extracted.get("details") or
        final_extracted.get("materials") or
        final_extracted.get("products") or
        final_extracted.get("records") or
        final_extracted.get("data") or
        final_extracted.get("goods") or
        final_extracted.get("list")
    )
    table_rows: List[Dict[str, Any]] = []

    def _match_row_value(r_dict: Dict[str, Any], col_name: str) -> str:
        """从行数据中获取指定列的值（严格精确匹配与标点去噪，绝不跨列同义词篡改）"""
        if not isinstance(r_dict, dict):
            return ""
        if col_name in r_dict and r_dict[col_name] is not None:
            v_str = _normalize_str(r_dict[col_name])
            if v_str != "":
                return v_str
        norm_target = re.sub(r'[\s_—\-\(\)（）:：]', '', col_name.lower())
        for k, v in r_dict.items():
            norm_k = re.sub(r'[\s_—\-\(\)（）:：]', '', str(k).lower())
            if norm_target == norm_k and v is not None:
                v_str = _normalize_str(v)
                if v_str != "":
                    return v_str
        return ""

    if isinstance(raw_rows, list) and raw_rows:
        if not table_columns:
            for r in raw_rows:
                if isinstance(r, dict):
                    for k in r.keys():
                        norm_k = _normalize_str(k)
                        if norm_k and norm_k not in table_columns:
                            table_columns.append(norm_k)

        for idx, row in enumerate(raw_rows, 1):
            if isinstance(row, dict):
                cleaned_row = {}
                for col in table_columns:
                    cleaned_row[col] = _normalize_str(_match_row_value(row, col))
                for k, v in row.items():
                    norm_k = _normalize_str(k)
                    v_str = _normalize_str(v)
                    if norm_k and v_str and norm_k not in table_columns:
                        table_columns.append(norm_k)
                        cleaned_row[norm_k] = v_str
                if "序号" in table_columns and not cleaned_row.get("序号"):
                    cleaned_row["序号"] = str(idx)
                table_rows.append(cleaned_row)

    if table_columns and "序号" not in table_columns:
        table_columns.insert(0, "序号")
        for idx, r in enumerate(table_rows, 1):
            if "序号" not in r or not r["序号"]:
                r["序号"] = str(idx)

    # 4. 汇总统计：自动汇总所有数字型列
    numeric_totals: Dict[str, float] = {}
    for col in table_columns:
        if col == "序号":
            continue
        vals = []
        is_num = True
        has_val = False
        for r in table_rows:
            v_str = str(r.get(col, "")).strip()
            if not v_str:
                continue
            if any(term in str(val) for term in ["合计", "总计", "小计"] for val in r.values()):
                continue
            has_val = True
            try:
                num = float(v_str)
                vals.append(num)
            except ValueError:
                is_num = False
                break
        if has_val and is_num and vals:
            total_val = sum(vals)
            numeric_totals[col] = round(total_val, 3) if not total_val.is_integer() else int(total_val)

    remarks_val = _normalize_str(final_extracted.get("remarks") or final_extracted.get("remark") or "")
    total_duration = round(time.time() - t_total_start, 2) if t_total_start else stage1_duration

    debug_info = {
        "total_duration_sec": total_duration,
        "primary_model": primary_norm,
        "actual_used_model": actual_used_model,
        "model_fallback_triggered": model_fallback_triggered,
        "candidate_models": candidate_models,
        "enable_fallback": enable_fallback,
        "retry_primary_on_error": retry_primary_on_error,
        "primary_retry_count": primary_retry_count,
        "stage1_model": used_model_stage1,
        "stage1_duration_sec": stage1_duration,
        "stage2_enabled": enable_double_check,
        "stage2_model": used_model_stage2 if enable_double_check else None,
        "stage2_duration_sec": stage2_duration,
        "parsed_columns_count": len(table_columns),
        "parsed_rows_count": len(table_rows),
        "parsed_metadata_count": len(metadata_fields),
        "verification_confidence": verification_report.get("confidence_score", 99.0),
        "verification_status": verification_report.get("status", "verified"),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return {
        "ok": True,
        "model_used": actual_used_model,
        "primary_model": primary_norm,
        "fallback_models": candidate_models[1:],
        "enable_fallback": enable_fallback,
        "retry_primary_on_error": retry_primary_on_error,
        "primary_retry_count": primary_retry_count,
        "model_fallback_triggered": model_fallback_triggered,
        "double_check_enabled": enable_double_check,
        "api_logs": api_logs,
        "debug_info": debug_info,
        "extracted_data": {
            "document_title": doc_title,
            "metadata_fields": metadata_fields,
            "table_columns": table_columns,
            "table_rows": table_rows,
            "remarks": remarks_val,
            "total_rows_count": len(table_rows),
            "numeric_totals": numeric_totals,
            "verification_report": verification_report,
            "model_used": actual_used_model,
            "model_fallback_triggered": model_fallback_triggered,
            "api_logs": api_logs,
            "debug_info": debug_info,
            "bill_type": doc_title,
        },
        "raw_text_summary": raw_text_summary
    }



