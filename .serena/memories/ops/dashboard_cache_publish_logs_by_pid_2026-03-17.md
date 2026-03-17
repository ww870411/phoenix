时间：2026-03-17
任务：为 daily_report_25_26 缓存发布任务增加按进程可见的日志展示，便于调试多进程发布。
变更文件：
1) backend/services/dashboard_cache_job.py
2) frontend/src/projects/daily_report_25_26/pages/DashBoard.vue
3) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
实现摘要：
- 后端在 runtime 下新增 dashboard_cache_publish_logs/ 目录，按 pid 写入 `<pid>.jsonl` 日志；
- snapshot() 返回扩展字段 logs 与 logs_by_pid；
- 数据看板页原有“缓存发布日志”弹窗改为优先按 PID 分组显示；
- 管理后台“看板功能设置”区域增加最近日志尾部展示，并在任务状态中附带 PID 与 current_label。
说明：
- 当前发布任务主体仍是单个子进程，因此通常会先看到一个主 pid；
- 后续若继续把 evaluate_dashboard 内部板块拆为多个子进程，可直接复用现有 logs_by_pid 协议继续显示。
验证：
- `cache_publish_job_manager.snapshot('daily_report_25_26')` 已包含 keys: logs, logs_by_pid。
- 前端代码检索确认 DashBoard.vue 与 AdminConsoleView.vue 已接入 PID 日志显示。