日期：2026-03-26
主题：daily_report_25_26 数据分析页逐日明细批量查询优化（阶段1）

背景：
- 用户确认长区间查询实际耗时很久，希望按“步骤1 重构 timeline 查询 + 步骤2 沿用 _perf 验证”推进。
- 页面累计模式的主要瓶颈来自 `backend/services/data_analysis.py` 的 `_query_analysis_timeline(...)`，原实现按天循环、逐天开 session、逐天设置 `phoenix.biz_date` 并查询日视图。

本轮实现：
1. `backend/services/data_analysis.py`
   - 抽出 `_query_analysis_timeline_iterative(...)` 保存旧逐天查询逻辑，作为回退路径。
   - 重写 `_query_analysis_timeline(...)`：
     - 使用 `generate_series(:start_date, :end_date, '1 day')` 生成区间日期。
     - 在单个 session / 单条 SQL 中，通过 `LATERAL + set_config('phoenix.biz_date', d.requested_date::text, true)` 驱动现有日视图批量返回逐日明细。
     - 若批量 SQL 在实际数据库环境失败，则记录 warning：`批量逐日明细查询失败，回退逐天查询`，并自动退回旧逻辑，保证功能不中断。
2. 文档同步：
   - `configs/progress.md`
   - `frontend/README.md`
   - `backend/README.md`

验证：
- `python -m py_compile backend/services/data_analysis.py backend/projects/daily_report_25_26/api/legacy_full.py` 通过。
- 代码中已确认保留原有 `_perf.analysis_timeline_ms` 计时口径，因此可直接在页面控制台用 `[DataAnalysisView][perf]` 对比优化前后长区间查询的 timeline 耗时。

说明：
- 本轮没有继续改前端多单位串行；先看 timeline 阶段是否已经显著下降，再决定是否做并发/批量单位查询。
- 本轮仍沿用现有日视图口径，没有重写 `analysis_company_daily / analysis_groups_daily / analysis_beihai_sub_daily` 视图定义，风险相对可控。