## 2025-11-02 登录与审批进度改造
- 新增 `backend/services/auth_manager.py`、`backend/services/workflow_status.py`、`backend/schemas/auth.py`、`backend/api/v1/auth.py`，结合 `backend_data/账户信息.json` 与 `backend_data/auth/permissions.json` 生成 Bearer Token 会话、页面/单位过滤、审批/发布权限；token 默认 30 分钟滑动过期。
- `/api/v1/auth/login|logout|me` 暴露登录流程；`daily_report_25_26` 路由默认依赖 `get_current_session`，并新增 `/workflow/status|approve|publish`（内存态，Biz 日=东八区昨日）。项目页面接口会根据 `permissions.page_access` 过滤可见页面。
- 前端使用 Pinia `auth` 仓库（sessionStorage 持久化），统一注入 Authorization 头、提供 `loadWorkflowStatus/approveUnit/publish`。路由守卫拦截未登录访问，`PageSelectView` 新增审批进度卡片，可按权限批准/发布，`Sheets`/登录页/页头等场景按角色过滤 UI。
- 回滚：删除新增模块与配置 `backend_data/auth/permissions.json` 并还原 `api`、`store` 调用逻辑，即可恢复原无鉴权实现。