时间戳：2026-02-15
背景：用户提供调试文件显示温度数据与窗口点数均正常，但图表仍空白。

判断：
- 数据链路已通，问题收敛到 ECharts 渲染层。

改动：
- 文件：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- temperatureTrendOption 增加强制可见配置：
  - animation=false
  - 显式 color
  - lineStyle/itemStyle/symbol/symbolSize
  - connectNulls=false
  - yAxis min/max 由窗口有效值计算
- 调试输出 temperatureDebugText 增加 echartsPayload：
  - xAxisData
  - mainSeries
  - peerSeries

结果：
- 页面可直接比对“映射值”与“最终 ECharts 入参”，用于锁定渲染问题。