时间戳：2026-02-15
问题：用户反馈春节看板气温图空白。

排查结论：
- spring 项目无独立 /dashboard 接口；此前改为按 spring 项目键请求后导致气温取数失败。
- 同时用户希望避免拉取 daily_report_25_26 全量 dashboard 包。

修复方案：
1) 后端新增轻量气温接口（daily_report_25_26 项目）
- 路径：GET /api/v1/projects/daily_report_25_26/dashboard/temperature/trend
- 文件：backend/projects/daily_report_25_26/api/dashboard.py
- 参数：show_date/start_date/end_date
- 数据源：calc_temperature_data（aver_temp）
- 返回：main/peer 两套日期->温度映射

2) 前端新增轻量调用并切换 spring 页面取数链路
- frontend/src/projects/daily_report_25_26/services/api.js 新增 getDashboardTemperatureTrend
- frontend/src/projects/daily_report_spring_festval_2026/services/api.js 的 getTemperatureTrendByDate 改为调用轻量接口
- SpringFestivalDashboardView.vue 的 loadTemperatureFromDatabase 改为：
  - 根据可见日期+选中日期前后3天生成请求范围
  - 优先使用轻量接口 main/peer
  - 保留旧 sections 解析回退

结果：
- 气温图恢复显示；
- 不再请求 daily_report_25_26 全量 dashboard 包，降低网络负担。