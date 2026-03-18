日期：2026-03-18
主题：daily_report_25_26 数据分析页性能链路梳理

目标页面：`/projects/daily_report_25_26/pages/data_analysis/data-analysis`

结论摘要：
1. 该页与展示页不同，不是单一重视图问题，而是前后端串行链路叠加。
2. 前端 `DataAnalysisView.vue` 的 `runAnalysis()` 对所选单位使用 `for...of + await` 串行调用 `runDataAnalysis(...)`；多单位时总耗时线性叠加。
3. 若后端未直接返回 `ring_compare`，前端还会为每个单位再发一次上一周期查询请求，进一步放大耗时。
4. 后端 `/data_analysis/query` 实际执行在 `legacy_full.py` 的 `_execute_data_analysis_query_legacy(...)`，其中可能串行执行：
   - `_query_analysis_rows(...)`
   - `_query_constant_rows(...)`
   - `_query_temperature_rows(...)`
   - 累计模式下 `_query_analysis_timeline(...)`
   - `_query_temperature_timeline(...)`
   - 上一周期对比查询
   - 计划比较查询
5. 最大风险点是 `backend/services/data_analysis.py` 的 `_query_analysis_timeline(...)`：当前按天循环，每天新建 session 并重新查一次视图，区间模式会明显放大。

当前判断：
- 该页更像“组合查询过长 + 多单位前端串行 + 区间模式日级循环”叠加，而不是单一 SQL/视图瓶颈。
- 若后续正式优化，建议先给 `/data_analysis/query` 增加 `_perf` 分段计时，再决定优先打前端串行还是重写 timeline 查询。

文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已记录。