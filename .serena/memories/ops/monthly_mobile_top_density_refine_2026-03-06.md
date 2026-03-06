时间：2026-03-06
主题：月报查询页与拉取页顶部密度收敛

目标：
- 继续按“掌上数据库”方向优化手机端工具页顶部筛选区、摘要区与按钮区的密度，减少默认占屏高度。

改动摘要：
1. MonthlyDataShowQueryToolView.vue
- 在 <=900px / <=640px 下收紧 monthly-query-main 的 padding 与区块间距。
- summary-grid 改为更紧凑的 3 列 / 2 列布局，压缩 summary-item 的 padding 与字号。
- actions 按钮区改为更弹性的紧凑排列，<=640px 下改为整行按钮。
- 下调 check-list.sections.compact 的默认最小/最大高度，减少筛选区默认高度。
- section-title-row / section-actions 在窄屏下改为更适合折行的布局。

2. MonthlyDataPullEntryView.vue
- 在 <=960px / <=640px 下收紧 monthly-main 的 padding 与区块间距。
- topbar-actions、preview-actions 改为更紧凑的弹性布局，<=640px 下改为整行按钮。
- 收紧 group-card 的内边距与标题间距。
- slot-actions 内按钮改为整行显示，减少局部拥挤。

验证：
- frontend 目录执行 npm run build，2026-03-06 构建通过。

影响范围：
- 仅前端移动端断点样式，无后端接口改动。