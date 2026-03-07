"""
AI 报告模式与提示词注册表。

职责：
- 管理日报/月报不同模式的提示词模板；
- 提供模式归一化、模板解析、运行时指令加载；
- 为报告服务与后续 AI 应用复用模式定义。
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.services import ai_runtime

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


def resolve_prompt_data_char_limit() -> int:
    if ai_runtime.current_provider() == "newapi":
        return PROMPT_DATA_MAX_CHARS_NEWAPI
    return PROMPT_DATA_MAX_CHARS


def load_instruction_text(mode_id: str = AI_MODE_DAILY) -> str:
    data = ai_runtime.load_effective_ai_settings()
    if not data:
        return ""
    normalized_mode = normalize_ai_mode(mode_id)
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


def load_ai_runtime_flags() -> Dict[str, Any]:
    defaults = {"enable_validation": True, "allow_non_admin_report": False, "report_mode": "full"}
    data = ai_runtime.load_effective_ai_settings()
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


def normalize_ai_mode(mode_id: Any) -> str:
    raw = str(mode_id or "").strip()
    if raw in AI_MODE_TEMPLATE_REGISTRY:
        return raw
    return AI_MODE_DAILY


def resolve_mode_templates(mode_id: str) -> Dict[str, str]:
    normalized = normalize_ai_mode(mode_id)
    return AI_MODE_TEMPLATE_REGISTRY.get(normalized, AI_MODE_TEMPLATE_REGISTRY[AI_MODE_DAILY])


__all__ = [
    "AI_MODE_DAILY",
    "AI_MODE_MONTHLY",
    "AI_MODE_TEMPLATE_REGISTRY",
    "CONTENT_PROMPT_TEMPLATE",
    "FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE",
    "FAST_VALIDATION_PROMPT_TEMPLATE",
    "INSIGHT_PROMPT_TEMPLATE",
    "LAYOUT_PROMPT_TEMPLATE",
    "MONTHLY_CONTENT_PROMPT_TEMPLATE",
    "MONTHLY_FAST_INSIGHT_LAYOUT_PROMPT_TEMPLATE",
    "MONTHLY_FAST_VALIDATION_PROMPT_TEMPLATE",
    "MONTHLY_INSIGHT_PROMPT_TEMPLATE",
    "MONTHLY_LAYOUT_PROMPT_TEMPLATE",
    "MONTHLY_REVISION_PROMPT_TEMPLATE",
    "MONTHLY_VALIDATION_PROMPT_TEMPLATE",
    "PROMPT_DATA_MAX_CHARS",
    "PROMPT_DATA_MAX_CHARS_NEWAPI",
    "REVISION_PROMPT_TEMPLATE",
    "VALIDATION_PROMPT_TEMPLATE",
    "load_ai_runtime_flags",
    "load_instruction_text",
    "normalize_ai_mode",
    "resolve_mode_templates",
    "resolve_prompt_data_char_limit",
]
