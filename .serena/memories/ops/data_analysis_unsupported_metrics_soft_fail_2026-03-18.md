日期：2026-03-18
主题：数据分析页 unsupported metrics 软降级

问题：用户反馈在数据分析页一次选择多个指标、多个单位时，如果某个单位/口径没有某个指标，就会报错，页面可能没有任何查询结果。

定位：
- 前端 `DataAnalysisView.vue` 的 `runAnalysis()` 已支持按单位聚合错误，只有在所有单位都失败时才整体抛错。
- 真正导致单位级硬失败的是后端 `backend/projects/daily_report_25_26/api/legacy_full.py` 中 `_execute_data_analysis_query_legacy(...)` 对 `unsupported_metrics` 的处理：
  - 直接返回 `400`：`当前视图不支持以下指标: ...`

修复：
1. 移除 `unsupported_metrics` 的硬错误返回。
2. 改为：
   - 当前单位继续返回可查询指标结果；
   - 不支持的指标保留为缺失项；
   - `warnings` 增加提示：`当前视图不支持以下指标，已按缺失处理：...`
3. `profile=true` 时补充 `unsupported_metrics_count`。

边界：
- 仅对“当前视图不支持指标”做软降级。
- `未知单位`、`存在未配置的指标` 等配置错误仍保持硬失败。

验证：
- `python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py` 通过。

前置说明：
- 本次继续沿用上轮对 `legacy_full.py` 的结构化降级编辑方式，原因是该文件在本会话中多次出现 `apply_patch` 沙箱刷新失败。