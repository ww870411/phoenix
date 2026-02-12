时间：2026-02-12
用户诉求：
1) 处理数据标签与横坐标标签重叠；
2) 四卡颜色对齐 daily_report_25_26 顶部四卡；
3) 将煤耗图改为业务日期当日各口径耗原煤量对比（集团汇总、主城区、金州、北方、金普、庄河），并显示数据标签。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现要点：
- 气温图：增加 grid.bottom 与 xAxis.axisLabel.margin，保留 labelLayout 防碰撞；
- 四卡配色：采用主看板同风格蓝/绿/橙/红（新增 summary-card--success）；
- 煤耗图：重构为 selectedDate 当日口径柱图，固定6口径并做同义key回退；
- 柱图显示两位小数标签。

验证：
- frontend 执行 npm run build 成功。

结果：
- 气温图标签与坐标轴重叠明显缓解；四卡风格统一；煤耗图满足业务日期口径对比需求。