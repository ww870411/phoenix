时间：2026-02-12
用户诉求：
1) 气温图做标签防碰撞；
2) 业务日期虚线变浅；
3) 顶部四卡不再显示差异率，改为本期值后括号增减量。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现要点：
- 温度序列新增 labelLayout={hideOverlap:true, moveOverlap:'shiftY'}；
- markLine 颜色调整为 rgba(37, 99, 235, 0.32)；
- 新增 formatIncrement，用于输出“(+x.xx单位)”；
- 卡片模板改为主值+括号增减量，删除差异率文案；
- 煤耗/投诉 delta 改为 current-prior；
- 气温 delta 改为 main-peer。

验证：
- frontend 执行 npm run build 成功。

结果：
- 图表标签可读性提升，业务日期线更柔和；卡片口径符合“增减量”表达。