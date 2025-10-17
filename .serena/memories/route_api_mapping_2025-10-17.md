前端路由与后端 API 映射（2025-10-17）

前端路由
- `/login` → LoginView
- `/projects` → ProjectSelectView
- `/projects/:projectKey/dashboard` → DashboardView
- `/projects/:projectKey/sheets/:sheetKey` → DataEntryView

后端 API（以 `/api/v1` 为前缀）
- `GET /ping`（系统连通）
- `GET /projects/daily_report_25_26/ping`（项目连通）
- `GET /projects/{project_key}/sheets`（当前实现固定 `daily_report_25_26`）
- `GET /projects/{project_key}/sheets/{sheet_key}/template`
- `POST /projects/{project_key}/sheets/{sheet_key}/submit`
- `POST /projects/{project_key}/sheets/{sheet_key}/query`

偏差记录
- 规范项目代号：`25-26daily_report`；代码路径：`daily_report_25_26`。前端以路由参数适配，联调不受影响。后续可在路由层增加别名或参数化以对齐。