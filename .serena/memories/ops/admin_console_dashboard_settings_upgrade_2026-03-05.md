时间：2026-03-05
需求：将 admin-console 的“看板缓存任务”升级为“看板功能设置”，增加业务日期自动读取与气温导入等数据看板相关功能按钮。

实现：
1) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 标题改为“看板功能设置”
- 新增业务日期输入与“读取业务日期”按钮（调用 /dashboard/date 并同步 refreshDate）
- 保留缓存操作：发布缓存、刷新单日、停止任务、禁用缓存
- 新增气温操作：导入气温（预览）、提交气温入库
- 新增状态提示文案（业务日期同步、气温预览/提交结果）

2) frontend/src/projects/daily_report_25_26/services/api.js
- 新增 getProjectDashboardBizDate(projectKey)
- 新增 importProjectTemperatureData(projectKey)
- 新增 commitProjectTemperatureData(projectKey)

说明：
- 后端未改动，复用既有接口：/dashboard/date、/dashboard/temperature/import、/dashboard/temperature/import/commit、/admin/cache/*

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md