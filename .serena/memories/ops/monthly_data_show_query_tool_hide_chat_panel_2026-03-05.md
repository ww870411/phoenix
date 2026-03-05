时间：2026-03-05
目标：按用户要求临时隐藏 monthly_data_show query-tool 页面中的对话工具。

执行：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 改动：新增样式
  .card:has(> .chat-panel) { display: none; }
- 结果：对话助手卡片在页面中不再显示。

策略说明：
- 仅隐藏前端入口，不删除既有后端接口与对话实现，便于后续快速恢复。
- .vue 编辑使用 apply_patch（Serena 对该文件类型无稳定符号编辑）。

验证：
- npm run build（frontend）通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md