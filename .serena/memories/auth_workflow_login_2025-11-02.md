## 2025-11-02 登录、权限与审批进度改造
- 新增 `backend/services/auth_manager.py`、`backend/services/workflow_status.py`、`backend/schemas/auth.py`、`backend/api/v1/auth.py`，结合 `backend_data/账户信息.json`、`backend_data/auth/permissions.json` 提供 Bearer Token 登录、页面/单位过滤与审批权限；token 30 分钟滑动过期，配置热更新将清空会话。
- `/api/v1/auth/login|logout|me` 暴露登录流程；`daily_report_25_26` 路由默认依赖 `get_current_session` 并新增 `/workflow/status|approve|publish`。审批状态按实际业务日（东八区昨日）分桶；`backend_data/date.json` 记录“展示日期”，未发布时保持上一批数据，发布成功后由 `auth_manager.set_display_date()` 同步。
- 前端 Pinia `auth` 仓库负责 Token 持久化（sessionStorage）、权限过滤、审批/发布动作；路由守卫拦截未登录访问。`PageSelectView` 卡片展示“当前业务日期｜当前数据展示日期”并在具备权限时提供批准/发布按钮，`Sheets`/`LoginView`/`AppHeader` 等组件按角色隐藏或禁用操作。
- 回滚：删除新增模块及 `backend_data/auth/permissions.json`、`backend_data/date.json` 并还原调用逻辑即可退回原无鉴权实现。