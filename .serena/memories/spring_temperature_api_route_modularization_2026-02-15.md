时间戳：2026-02-15
任务：按模块化原则将春节看板温度接口路由归位到 spring 项目。

原因：
- 用户指出温度 API 在 daily_report_25_26 路由下不符合 spring 项目边界。

变更文件：
1) backend/projects/daily_report_spring_festval_2026/api/temperature_trend.py（新增）
2) backend/projects/daily_report_spring_festval_2026/api/router.py
3) frontend/src/projects/daily_report_spring_festval_2026/services/api.js
4) frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
5) configs/progress.md
6) frontend/README.md
7) backend/README.md

改动摘要：
- 新增 spring 项目公开接口：GET /api/v1/projects/daily_report_spring_festval_2026/spring-dashboard/temperature/trend
- spring router 的 public_router 挂载 temperature_trend public_router
- 前端改为请求当前项目路径，不再耦合 daily_report_25_26 项目路径

结果：
- 温度接口路由归属与项目模块化一致；spring 页面 API 调用闭环在自身项目命名空间。