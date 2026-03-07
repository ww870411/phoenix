时间：2026-03-07
主题：月报查询页“重置”按钮手机端溢出修正

现象：
- 用户反馈月报查询页手机宽度下，“重置”按钮跑到页面外边。

原因：
- MonthlyDataShowQueryToolView.vue 在 <=640px 断点下，将 .actions .btn 设为 width: 100%，但 .actions 容器仍保持横向 flex，导致第二个按钮横向溢出。

修正：
- 在 <=640px 断点下，将 .actions 改为纵向排列（flex-direction: column）。
- 保留按钮 width: 100%，使“查询 / 重置”按纵向整行排列。

验证：
- frontend 目录执行 npm run build，2026-03-07 构建通过。

影响范围：
- 仅前端移动端按钮区布局，无后端改动。