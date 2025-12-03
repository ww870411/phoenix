## 2025-12-27 AI 报告环比字段修复
- 现象：开启智能报告并启用环比分析后，生成的洞察/正文未引用环比数据，Prompt 中的 `ring` 字段始终为 null。
- 根因：`backend/services/data_analysis_ai_report.py` 的 `_preprocess_payload` 仅输出 `ring_fmt/ring_color`，未透传数值 `ring_ratio`，LLM 读取不到 `ring`。
- 处理：在预处理阶段新增 `ring` 数值字段（直接取 `ring_ratio`），同时保留 `ring_fmt` 供 HTML 卡片显示，执行 `python -m py_compile backend/services/data_analysis_ai_report.py` 验证通过。
- 效果：AI 报告 JSON 现可引用环比百分比，HTML 模板仍展示环比列；如需回滚，只需恢复该 Python 文件。