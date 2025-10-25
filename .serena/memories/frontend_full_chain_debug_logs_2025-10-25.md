目的：定位前端 rows-only 渲染不显示数据的问题，覆盖路由→模板→查询→映射→RevoGrid 的调试日志。
时间：2025-10-25
文件：
- frontend/src/daily_report_25_26/pages/DataEntryView.vue
- frontend/src/daily_report_25_26/services/api.js
- configs/progress.md（记录变更摘要）
- frontend/README.md（补充调试日志说明）
关键变更：
- DataEntryView.vue：
  - 新增 [data-entry/route-init] 初始路由/查询参数日志。
  - 新增 watch 侦听：columns/rows/gridColumns/gridSource/bizDate/pageConfig。
  - reloadTemplate() 入参日志 [data-entry/reloadTemplate]。
  - onSubmit() 提交前快照 [data-entry/submit]。
  - RevoGrid afterEdit 事件日志 [revogrid/afterEdit]。
- services/api.js：
  - getTemplate/queryData/submitData 请求日志，含 config/search、payload 摘要。
重要约束：
- 保持 rows-only 渲染；未恢复/新增任何 cells 相关逻辑。
后续验证要点：
- 控制台应看到 gridColumns.length 与 gridSource.length > 0；若 UI 仍空白，排查 v-if(columns.length) 时序。