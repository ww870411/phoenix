时间：2026-02-12
用户诉求：
1) 气温图鼠标悬浮时标签保留2位小数；
2) 非悬浮状态也需标示业务日期位置及该日期本期/同期气温值。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现要点：
- 在 temperatureTrendOption 中新增 tooltip.formatter，统一格式为 xx.xx℃；
- 在本期序列增加 markLine（业务日期竖线）；
- 在本期/同期序列增加 markPoint（常驻标签：本期xx.xx℃、同期xx.xx℃）；
- 保持原有 selectedDate±3 的窗口逻辑。

验证：
- frontend 执行 npm run build 成功。

结果：
- 气温图在悬浮与常驻状态下均可明确读取业务日期及其本期/同期温度值。