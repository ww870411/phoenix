时间：2026-03-06
主题：前端移动端表格与录入页优化第一轮

前置说明：
- Serena 已激活项目并完成检索。
- 由于 Serena 对 Vue SFC 的结构化编辑支持有限，本轮按 AGENTS 约束降级使用 apply_patch，对目标页面做最小补丁。
- 降级范围：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue、frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue、frontend/src/projects/daily_report_25_26/pages/DataEntryView.vue，以及 configs/progress.md、frontend/README.md、backend/README.md。
- 回滚方式：反向撤销本轮补丁片段即可，不涉及接口或数据库结构变更。

改动摘要：
1. MonthlyDataShowQueryToolView.vue
- 为聊天预览表和查询结果表补充 table-wrap 横向滚动容器。
- 在 <=900px / <=640px 下压缩表格字号与 padding。
- compare-table 在 <=640px 时隐藏同期值、上期值、计划值列，保留当前值与比率列。

2. MonthlyDataPullEntryView.vue
- 为批量识别预览表和异常表增加 table-wrap 横向滚动容器。
- 为异常说明列设置最小宽度、自动换行和 break-word。
- 在 <=960px 下统一压缩表格字号与间距。

3. DataEntryView.vue
- 为 RevoGrid 外层容器补充横向滚动能力。
- 通过 :deep(revo-grid) 设置最小宽度，避免手机端压扁。
- 新增 mobile-grid-hint，仅在 <=768px 显示，提示手机端建议横屏或电脑端录入。

验证：
- 在 frontend 目录执行 npm run build，2026-03-06 构建通过。
- 未进行真机或浏览器移动端手动回归，后续建议优先检查 390px/430px 宽度下的月报查询、月报导入、日报录入页面观感。

证据：
- 本地构建命令：frontend 下 npm run build
- 构建结果：通过（vite build completed, exit code 0）