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
        # 优先取 range 模式下的 total_current，否则取 current
        val = row.get("total_current")
        if val is None:
            val = row.get("current")
        
        # 简单的格式化辅助
        val_fmt = f"{val:.2f}" if isinstance(val, (int, float)) else "--"
        
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
        ring = row.get("ring_ratio")
        if isinstance(ring, (int, float)):
            ring_fmt = f"{ring:+.2f}%"
            if ring > 0:
                ring_color = "#d32f2f" 
            elif ring < 0:
                ring_color = "#2e7d32"
            else:
                ring_color = "#7f8c8d"
        else:
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
            "label": label,
            "unit": unit,
            "value": val,
            "delta": delta,
            "delta_fmt": delta_fmt,
            "delta_color": delta_color,
            "ring_fmt": ring_fmt,
            "ring_color": ring_color,
            "is_temperature": row.get("value_type") == "temperature",
            "timeline_entries": timeline,
            "timeline_json": json.dumps(chart_data, ensure_ascii=False)
        })

    return {
        "meta": meta,
        "metrics": processed_metrics,
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
        .chart-wrapper { height: 420px; margin-top: 24px; border: 1px solid #eee; border-radius: 8px; padding: 12px; background: #fff; }
        table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
        th, td { border: 1px solid #e0e0e0; padding: 10px 12px; text-align: center; }
        th { background: #f4f6f7; color: #555; font-weight: 600; }
        tr:nth-child(even) { background: #fafafa; }
        .metric-selector { margin-bottom: 12px; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; min-width: 200px; }
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
        val = f"{m['value']:.2f}" if m['value'] is not None else "--"
        delta_style = f"color: {m['delta_color']}"
        # Use .get() for ring properties to be safe, though _preprocess_payload should provide them
        ring_fmt = m.get('ring_fmt', '--')
        ring_color = m.get('ring_color', '#7f8c8d')
        
        html_parts.append(f"""
            <div class='card'>
                <h3>{m['label']}</h3>
                <div class='value'>{val}<span class='unit'>{m['unit'] or ''}</span></div>
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

    # 5. 图表区域 (含数据注入)
    timeline_data_json = json.dumps([
        {
            "key": m["label"], # Use label as key for simplicity in selector
            "label": m["label"],
            "unit": m["unit"],
            "is_temp": m["is_temperature"],
            "data": json.loads(m["timeline_json"]) # restore to list
        }
        for m in metrics if m.get("timeline_json")
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
