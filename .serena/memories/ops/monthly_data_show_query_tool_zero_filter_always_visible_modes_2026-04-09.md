时间：2026-04-09
任务：修正 monthly_data_show/query-tool 页“0值过滤”面板的交互与位置显示问题。
用户反馈：页面上只能看到“保留 0 值”，新增的过滤方式没有直接出现，而且该块位置偏下。
实现文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. 前端交互重构
- 将 `0值过滤` 从“checkbox + 条件展开模式”改为常显三选一：
  - `保留 0 值`
  - `逐条剔除 0 值`
  - `全月份均为 0 才剔除`
- 前端状态改为 `zeroFilterMode`，移除原来的 `excludeZeroValues` / `excludeZeroMode` 组合式交互。
2. 参数映射
- `zeroFilterMode='off'` 时：`exclude_zero_values=false`
- `zeroFilterMode='row' | 'all_months_group'` 时：`exclude_zero_values=true`，并继续传递对应的 `exclude_zero_mode`
3. 布局调整
- `zero-filter-stack` 改为顶部对齐，避免面板内容整体下沉。
- 常显模式下，新增选项进入默认可见状态。
降级说明：涉及 `.vue` 与 `.md` 文件编辑，Serena 不适合直接做结构化修改，因此按 AGENTS 约定使用 `apply_patch`，并以本记忆留痕。
验证：前端 `npm run build` 通过。