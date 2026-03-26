日期：2026-03-26
主题：daily_report_25_26 数据分析页多单位并发查询优化（阶段2）

背景：
- 在完成 timeline 批量查询优化后，继续处理第二个明显瓶颈：前端多单位串行查询。
- 原逻辑位于 `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue` 的 `runAnalysis()`，使用 `for (const unitKey of targetUnits) { await runDataAnalysis(...) }`，总耗时会近似累加。

本轮实现：
1. 将多单位查询改为并发：
   - 使用 `const unitTasks = targetUnits.map(async (unitKey) => ...)`
   - 使用 `await Promise.allSettled(unitTasks)` 汇总结果
2. 保持兼容行为：
   - 单个单位失败时，仅将错误写入 `errors`，不阻断其它单位成功结果。
   - 仍按成功结果构造 `aggregatedResults` 并刷新页面。
   - AI 报告仍取首个成功返回的 `ai_report_job_id` 启动轮询，保持既有页面行为。
3. 文档同步：
   - `configs/progress.md`
   - `frontend/README.md`
   - `backend/README.md`

验证：
- `frontend` 执行 `npm run build` 通过。
- 代码中已确认 `Promise.allSettled`、`unitTasks`、`settledResults.forEach` 生效。

后续建议：
- 下一轮应直接用真实页面观察：
  - 单单位时 `_perf.analysis_timeline_ms` 是否下降
  - 多单位时总等待时间是否接近“最长单个单位耗时”而不再近似累加
- 如果数据库承压明显，再考虑新增后端“批量单位查询”接口，减少前端多次并发请求。