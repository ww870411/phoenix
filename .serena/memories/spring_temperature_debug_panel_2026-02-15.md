时间戳：2026-02-15
任务：用户要求在页面直接显示详细调试信息，排查气温曲线空白。

变更文件：
1) frontend/src/projects/daily_report_spring_festval_2026/services/api.js
2) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

前端调试增强内容：
- getTemperatureTrendByDate 返回 _debug：
  - source（命中层级）
  - attempts（每层尝试结果：ok/error/url/status等）
- 页面新增温度调试结构：
  - temperatureDebugInfo + temperatureDebugText
  - 图表下方 temp-debug-box 直接显示 JSON 调试信息
  - 默认 debugVisible=true，便于即时排障
- 展示字段包含：
  - 请求参数（selectedDate/start/end/windowDates）
  - 返回键、main/peer条数、映射条数
  - 样例数据点
  - 7天窗口逐日 main/peer 值和可见点数量

结果：
- 用户可在页面直接看到温度链路每个环节的命中和数据数量，快速定位空白根因。