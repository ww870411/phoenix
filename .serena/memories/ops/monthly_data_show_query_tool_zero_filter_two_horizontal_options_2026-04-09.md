时间：2026-04-09
任务：进一步简化 monthly_data_show/query-tool 页“0值过滤”面板文案与交互。
用户要求：移除“保留 0 值”字样，只保留“逐条剔除 0 值”“全月份均为 0 才剔除”两个选项，并水平排列。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. 交互层
- 删除页面上的“保留 0 值”可见选项。
- 保留两个并排的过滤选项，使用 checkbox 外观，但内部继续维护单一模式值 `zeroFilterMode`。
- 两项都不选时，等价于 `zeroFilterMode='off'`，即保留 0 值。
- 选中某一项时切换到对应模式；取消当前选中项时恢复 `off`。
2. 布局层
- `zero-filter-modes` 改为水平排列并允许换行。
3. 参数层
- `buildPayload()` 无需额外后端改动，继续根据 `zeroFilterMode` 映射 `exclude_zero_values` 与 `exclude_zero_mode`。
降级说明：涉及 `.vue` 与 `.md` 文件编辑，Serena 不适合直接做结构化修改，因此按 AGENTS 约定使用 `apply_patch`，并以本记忆留痕。
验证：前端 `npm run build` 通过。