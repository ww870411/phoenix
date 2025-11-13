2025-12-01：为 daily_report_25_26 数据看板实现文件缓存管控。
- 新增 backend/services/dashboard_cache.py 统一管理 backend_data/dashboard_cache.json，提供 normalize/publish/disable API。
- /dashboard 接口先查缓存，增加 cache_* 元数据，禁用状态下只读不写，并新增 POST /dashboard/cache/publish、POST /dashboard/cache/refresh、DELETE /dashboard/cache（需 can_publish 权限）。
- frontend/src/daily_report_25_26/pages/DashBoard.vue 顶部加入“发布缓存/刷新看板/禁用缓存”控件与状态提示，调用新增 API，动作后强制重新加载。
- backend/frontend README 与 configs/progress.md 已登记此次变更及降级说明。