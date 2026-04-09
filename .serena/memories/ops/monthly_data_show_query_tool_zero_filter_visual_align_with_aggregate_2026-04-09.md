时间：2026-04-09
任务：让 monthly_data_show/query-tool 页“0值过滤”框内布局效仿“聚合开关”的选项版式。
用户要求：本框内布局效仿“聚合开关”中的选项，包括高度、位置等。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
- 将 `zero-filter-modes` 容器的白底边框、内边距、最小高度和垂直居中方式对齐到 `aggregate-inline` 的节奏。
- `zero-filter-stack` 收口为与聚合块一致的容器占位方式。
- `zero-filter-option` 回到单行展示，并统一选项高度与行高。
验证：前端 `npm run build` 通过。
降级说明：涉及 `.vue` 与 `.md` 文件编辑，Serena 不适合直接做结构化修改，因此按 AGENTS 约定使用 `apply_patch`，并以本记忆留痕。