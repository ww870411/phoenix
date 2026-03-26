日期：2026-03-26
主题：daily_report_25_26 数据分析页后端多进程批量查询优化（阶段3）

背景：
- 用户明确指出生产环境本来就是 2 个 uvicorn workers，且数据看板页面已经有成熟的多进程任务分块实现，希望数据分析页也按同类思路做充分优化。
- 因此本轮不再停留在“前端多请求并发”，而是升级为后端单次批量请求 + 多进程单位分块执行。

实现：
1. `backend/projects/daily_report_25_26/api/legacy_full.py`
   - 新增 `DataAnalysisBatchQueryPayload`。
   - 新增 `DATA_ANALYSIS_BATCH_MAX_WORKERS` 与 worker 数计算函数。
   - 新增 `_build_data_analysis_unit_payload_dict(...)`，把批量请求拆成单位级 payload。
   - 新增 `_execute_data_analysis_batch_worker(...)`，在子进程中复用 `_execute_data_analysis_query_legacy(...)`，并把 `JSONResponse` 解析成可汇总的 dict；在 `_perf` 中追加 `worker_pid`。
   - 新增 `_execute_data_analysis_batch_query(...)`，使用 `ProcessPoolExecutor` 按单位并行执行，汇总 `results/errors/worker_count`。
   - 新增接口 `POST /data_analysis/query-batch`。
   - 保留原 `POST /data_analysis/query` 不变，继续服务单单位与 AI 报告触发场景。
2. `frontend/src/projects/daily_report_25_26/services/api.js`
   - 新增 `runDataAnalysisBatch(...)`。
3. `frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue`
   - `runAnalysis()` 改为单次调用 `runDataAnalysisBatch(...)`。
   - 页面只发一次批量请求，再按单位组装结果。
   - 新增 `[DataAnalysisView][batch]` 控制台日志，输出 `workerCount/requestedUnits/succeededUnits`。
   - 原单位级 `[DataAnalysisView][perf]` 保留，可继续观察每个单位的 `_perf`。

验证：
- `python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py backend/services/data_analysis.py` 通过。
- `frontend` 执行 `npm run build` 通过。
- 检索确认：
  - 后端已有 `ProcessPoolExecutor`、`/data_analysis/query-batch`
  - 前端已有 `runDataAnalysisBatch(...)`
  - 页面已切换到批量接口

风险与说明：
- 这是第一版后端多进程批量查询，以“单位”为分块粒度。
- 真实收益取决于数据库是否能承受多进程并行查询压力；如数据库成为瓶颈，需要继续调优 `DATA_ANALYSIS_BATCH_MAX_WORKERS`。
- 环比兜底逻辑当前仍可能在极少数未返回 `ringCompare` 的情况下走单单位补查，但主链路已经切换为后端多进程批量执行。