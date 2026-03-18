日期：2026-03-18
主题：daily_report_25_26 数据展示页单 sheet 首屏加载分段计时

背景：用户确认导出已恢复正常，但 `Group_sum_show_Sheet` 首次打开仍约 31 秒，需要继续定位单页加载瓶颈。用户同时询问本轮对话最开始误改代码是否造成影响。已向用户明确说明：当时本地工作区确实被改动过，但这些改动后来已纳入正式授权的第一阶段优化并经后续修正与验证，当前不存在未处理的早期残留误改；只能确认当前状态已验证，不能倒推当时中间态一定无影响。

实施：
1. `backend/services/runtime_expression.py`
   - 为 `render_spec(...)` 增加可选 `_perf` 分段计时。
   - 计时项包括：`parse_context_ms`、`collect_companies_ms`、`prefetch_data_ms`、`temperature_fetch_ms`、`metrics_fetch_ms`、`constants_fetch_ms`、`prepare_render_ms`、`evaluate_rows_ms`、`finalize_output_ms`、`total_ms`。
   - 同时统计：`companies_needed_count`、`metrics_fetch_count`、`metrics_cache_hits`、`constants_fetch_count`、`constants_cache_hits`、`temperature_cache_hit`。
2. `backend/projects/daily_report_25_26/api/legacy_full.py`
   - `runtime_eval` 与 `runtime_eval_batch` 支持请求体 `profile: true`。
   - 当启用 `profile` 时，通过响应 `debug._perf` 返回上述分段耗时；与 `trace` 共存。
3. `frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue`
   - 单 sheet 加载请求默认带 `profile: true`。
   - 当后端返回 `debug._perf` 时，在浏览器控制台输出 `[DisplayRuntimeView][perf]`，便于现场查看首屏瓶颈。
4. 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已更新。

验证：
- `python -m py_compile backend/services/runtime_expression.py backend/projects/daily_report_25_26/api/legacy_full.py` 通过。
- `frontend` 执行 `npm run build` 通过。

影响边界：
- 不改变页面数据口径，不改变导出内容与表样。
- 当前只增加性能剖析信息；是否进入第二阶段并行/多进程优化，需以实际 `_perf` 结果为依据。