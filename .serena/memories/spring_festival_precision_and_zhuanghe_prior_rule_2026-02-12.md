时间：2026-02-12
用户诉求：
1) 顶部卡片精度：气温1位小数，其余整数；
2) 气温图1位小数；
3) 原煤图整数，且本期/同期都有标签，颜色更明显；
4) 庄河同期值使用“剔除xxx”指标；
5) 标签防重叠。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现要点：
- 顶部卡片煤耗显示从2位改为0位（主值+增减量）；
- 气温图 toFixedText 改为1位；
- 原煤图 tooltip/label 改为整数显示；
- 原煤图颜色改为本期深蓝#1d4ed8、同期橙色#f59e0b；
- 庄河 prior 匹配规则：优先选择 metricName 含“原煤消耗量”且含“剔除”的指标，否则回退常规匹配；
- 本期/同期标签保留 labelLayout 防重叠。

验证：
- frontend 执行 npm run build 成功。

结果：
- 精度与口径满足新规范，原煤图本期/同期对比更清晰。