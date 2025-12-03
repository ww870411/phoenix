## 2025-12-27 AI 报告环比比较同步
- 背景：用户反馈网页“环比比较”板块有数据，但 AI 报告缺少对应段落。root cause：AI 流水线未消费 `/data_analysis/query` 的 `ringCompare`（上期区间+prevTotals），Prompt/HTML 都看不到该数据。
- 处理：`backend/services/data_analysis_ai_report.py` 新增 `_build_ring_compare_payload`，将 `ringCompare` 转换为 entries、范围标签与摘要写入 `processed_data['ring_compare']`；`_generate_report_html` 增加专门的“环比比较”section，渲染“指标/本期累计/上期累计/环比”表格和【环比】摘要，并在无数据时显示 warning。
- 结果：AI 报告与前端表现一致，LLM 也能在 Prompt 中引用完整的环比数据；通过 `python -m py_compile backend/services/data_analysis_ai_report.py` 验证。
- 回滚：恢复该 Python 文件即可移除此增强。