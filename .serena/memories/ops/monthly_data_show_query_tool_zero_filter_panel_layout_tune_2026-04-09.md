时间：2026-04-09
任务：调整 monthly_data_show/query-tool 页面“数据层次顺序 / 聚合开关 / 0值过滤”三联面板布局，解决 0值过滤 面板显示不全、聚合开关 面板略宽的问题。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. 布局层
- `.inline-layout` 三列宽度由原先较窄的第三列改为：主列保持、聚合列收窄、0值过滤列加宽。
- 中等宽度断点下同步调整三列比例。
2. 面板内部排版
- `aggregate-inline` 间距与内边距略收紧，避免“聚合开关”占用过多横向空间。
- `zero-filter-stack`、`zero-filter-modes`、`zero-filter-col` 添加 `min-width: 0`，避免网格子项撑破容器。
- `0值过滤` 面板中的开关文案和模式说明允许换行，避免长文案被裁切。
降级说明：涉及 `.vue` 与 `.md` 文件编辑，Serena 不适合直接做结构化修改，因此按 AGENTS 约定使用 `apply_patch`，并用本记忆留痕。
验证：前端 `npm run build` 通过。