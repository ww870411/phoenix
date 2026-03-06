时间：2026-03-06
主题：数据填报页顶部开关在手机端过长占空间修正

现象：
- 用户反馈数据填报页顶部“是否校验”等开关在手机端被拉得过长，占据过多空间。

原因：
- DataEntryView.vue 的 <=768px 断点中，同时将 topbar__status-row 改为纵向拉伸，并把 .unit-analysis-inline 设为 width: 100%，导致本来应紧凑排列的状态开关变成长条。

修正：
- 保留 topbar__action-row 的纵向堆叠。
- 将 topbar__status-row 改回横向换行、左对齐布局。
- 取消 .unit-analysis-inline 的 width: 100%，改为内容自适应宽度。
- submit-time 改为独占一行，但不影响后续开关维持紧凑块状。

验证：
- frontend 目录执行 npm run build，2026-03-06 构建通过。
- 浏览器手机视口复测：顶部状态区已恢复紧凑块状布局，不再出现整行长条。