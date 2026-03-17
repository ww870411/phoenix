时间：2026-03-17
背景：用户要求将数据看板页与管理后台中的缓存发布日志，从按 PID 展示改为按业务分块卡片展示，不在页面暴露 PID，仅显示业务含义与进度状态。
变更文件：
- backend/services/dashboard_cache_job.py
- frontend/src/projects/daily_report_25_26/pages/DashBoard.vue
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
实现摘要：
1. 后端在 dashboard_cache_job.py 中新增 GROUP_LABELS，并扩展 _append_log 支持 group 字段。
2. 状态快照新增 worker_groups 字段，由 _load_worker_groups 根据 SECTION_GROUPS、结果文件和最近日志生成，字段包含 key、label、sections、status、message、updated_at。
3. _run_section_group 与分组启动日志改为写入 group 标识，供前端业务分块展示使用。
4. DashBoard.vue 的缓存发布日志弹窗改为“业务分块卡片 + 最近日志”结构，移除 PID 展示。
5. AdminConsoleView.vue 的缓存发布状态区域同步改为业务分块卡片与最近日志，状态文案中移除 PID。
验证：
- python -m py_compile backend/services/dashboard_cache_job.py 通过
- frontend 执行 npm run build 成功（首次因沙箱 spawn EPERM 失败，随后经用户授权提升权限后构建通过）
备注：按用户要求，本轮未更新 configs/progress.md、frontend/README.md、backend/README.md。