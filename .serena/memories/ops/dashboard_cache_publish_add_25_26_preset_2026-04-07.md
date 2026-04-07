时间：2026-04-07
主题：日报数据看板与管理后台缓存发布新增 25-26 固定档位

变更摘要：
- backend/services/dashboard_cache.py：新增 resolve_publish_schedule(window, project_key, preset)，统一解析缓存发布档位；新增固定预设 `25-26`，返回 2025-11-01 至 2026-04-05 的完整每日日期序列。
- backend/projects/daily_report_25_26/api/dashboard.py：POST /dashboard/cache/publish 新增 preset 查询参数；当 preset=25-26 时，按整个供暖期生成发布 schedule，并在响应中返回 preset 与 selection_label。
- backend/api/v1/admin_console.py：POST /admin/cache/publish 同步新增 preset 查询参数，逻辑与数据看板入口保持一致。
- frontend/src/projects/daily_report_25_26/services/api.js：publishDashboardCache / publishAdminDashboardCache 新增对 preset 参数的支持；当传 preset 时不再拼接 days。
- frontend/src/projects/daily_report_25_26/pages/DashBoard.vue：缓存发布下拉框新增 25-26；选中后调用 publishDashboardCache(projectKey, { preset: '25-26' })；任务启动提示改为显示 selection_label 或当前档位标签。
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue：管理后台缓存发布下拉框同步新增 25-26；选中后调用 publishAdminDashboardCache({ preset: '25-26' })。
- configs/progress.md、frontend/README.md、backend/README.md 已同步记录。

验证证据：
- python -m py_compile backend/services/dashboard_cache.py backend/projects/daily_report_25_26/api/dashboard.py backend/api/v1/admin_console.py 通过。
- frontend 目录 npm run build 通过。

结果说明：
- 现在无论在日报数据看板页还是管理后台，只要选择 25-26 并点击发布缓存，都会发布 2025-11-01 至 2026-04-05 的每日日报缓存。