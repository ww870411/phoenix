时间：2026-02-26
任务：为全局管理后台新增服务器性能监控页面（第一版）。
后端：
- 文件：backend/api/v1/admin_console.py
- 新增接口：GET /api/v1/admin/system/metrics
- 返回字段：timestamp, uptime_seconds, platform, cpu, memory, disk, process, metrics_provider
- 权限：沿用 can_access_admin_console
- 采集：优先 psutil，异常回退基础占位
- 依赖：backend/requirements.txt 新增 psutil>=5.9.8
前端：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 新增标签页：系统监控
- 功能：立即刷新 + 自动刷新(5秒)、指标卡片展示
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
- 新增方法：getAdminSystemMetrics()
结果：管理后台内可直接查看服务器关键性能指标。