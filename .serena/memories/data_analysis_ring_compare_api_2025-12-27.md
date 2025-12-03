## 2025-12-27 /data_analysis/query 提供 ringCompare 数据
- 背景：AI 报告缺少“环比比较”数据源，原因是 `/data_analysis/query` 仅返回当前窗口 rows，前端通过额外的上一期查询在浏览器端构造 `ringCompare.prevTotals`；当开启智能报告时后端没有这一结构，导致报告渲染为空。
- 改动：在 `_execute_data_analysis_query_legacy` 中，当 `request_ai_report=true` 且为累计模式时，服务端自动计算上一窗口起止日期，查询分析视图 `_query_analysis_rows` 与 `_query_temperature_rows` 得到上一期 totals，并构建 `ringCompare = { range, prevTotals, note }` 写入响应（常量指标复用当前值）。同时将 `ringCompare` 的写入提前到 `enqueue_ai_report_job` 之前，保证 AI payload 中也包含该字段。
- 相关：`backend/services/data_analysis_ai_report.py` 现消费该字段（经 `_build_ring_compare_payload`）并在 HTML 中渲染“环比比较”表格/摘要。
- 回滚：恢复 `backend/api/v1/daily_report_25_26.py` 与 `backend/services/data_analysis_ai_report.py` 的对应修改即可。