时间：2026-02-12
用户诉求：
1) 移除气温图顶端“业务日期”文字，避免与标签重叠；
2) 默认显示所有气温点数据标签。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- temperatureTrendOption 中保留 markLine 竖线，但 markLine.label.show=false；
- 本期/同期系列都开启 label.show=true，分别 position=top/bottom，formatter 输出 xx.xx℃；
- 移除业务日期单点 markPoint，避免与全量标签重复叠加。

验证：
- frontend 执行 npm run build 成功。

结果：
- 图表默认可读全部温度标签，同时不再出现顶端“业务日期”重叠文本。