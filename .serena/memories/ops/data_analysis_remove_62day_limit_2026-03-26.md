日期：2026-03-26
主题：按用户要求移除 daily_report_25_26 数据分析页累计模式 62 天限制

前置说明：
- 用户明确要求先去掉该限制，因此本次直接移除后端显式阈值，不同步处理长区间性能优化。
- 该操作会让累计模式允许提交超过 62 天的区间，但 `_query_analysis_timeline(...)` 的逐日循环查询成本仍然保留。

代码变更：
1. `backend/projects/daily_report_25_26/api/legacy_full.py`
   - 删除 `MAX_TIMELINE_DAYS = data_analysis_service.MAX_TIMELINE_DAYS`。
   - 删除累计模式下 `range_days > MAX_TIMELINE_DAYS` 时直接返回 400 的逻辑。
2. `backend/services/data_analysis.py`
   - 删除 `MAX_TIMELINE_DAYS = 62`。
   - 删除 `execute_data_analysis_query(...)` 内同样的 62 天拦截逻辑。
3. 文档同步：
   - `configs/progress.md`
   - `frontend/README.md`
   - `backend/README.md`

验证：
- 检索确认：仓库 `backend/**/*.py` 中已无 `MAX_TIMELINE_DAYS` 与“累计模式暂只支持”残留。
- 命令验证：`python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py backend/services/data_analysis.py` 通过。

降级留痕：
- 本轮原计划使用 `apply_patch` 编辑，但连续两次失败：`windows sandbox: setup refresh failed with status exit code: 1`。
- 按仓库规则降级为 Desktop Commander 结构化编辑完成修改。

风险：
- 页面不会再因 62 天阈值被直接拒绝。
- 但长区间查询可能明显变慢，因为逐日 timeline 查询仍是按天循环、逐天开 session 执行。