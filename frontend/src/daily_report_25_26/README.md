# daily_report_25_26 前端说明

## 登录与权限更新（2025-11-02）

- 新增 Pinia `auth` 仓库：统一管理 `/auth/login|me|logout` 调用、Token 持久化（sessionStorage）、页面/表格过滤与审批/发布操作。
- `router` 全局守卫在进入非 `/login` 路由前确保已登录；登录成功后自动跳转 `/projects`，退出后清空缓存并返回登录页。
- `services/api.js` 注入 Authorization 头并封装 `getWorkflowStatus/approveWorkflow/publishWorkflow`；`PageSelectView` 显示审批进度卡片并在具备权限时提供批准/发布按钮。
- 审批进度卡片额外展示“当前业务日期｜当前数据展示日期”：业务日取东八区昨日，展示日期来自 `backend_data/date.json`，在新业务日未发布前保持上一期数据。
- `LoginView`、`AppHeader`、`Sheets` 等组件按角色隐藏或禁用按钮；页面/表格列表在前端再次过滤，避免越权访问。
- 新增 `frontend/Dockerfile.prod`（Node → Nginx 多阶段构建）与 `deploy/nginx.conf`，供生产镜像使用；默认监听 80 端口并通过 `location /api/` 反向代理至后端服务 `backend:8000`。

## 页面结构更新（2025-11-01）

- 登录页 `/login`：录入账号信息后跳转至项目列表页。
- 项目列表页 `/projects`：读取 `/api/v1/projects` 展示可用项目。
- 页面选取页 `/projects/:projectKey/pages`：根据 `backend_data/项目列表.json` 中的 `pages` 配置，使用卡片选择目标页面。
- 表格列表页 `/projects/:projectKey/pages/:pageKey/sheets`：按卡片展示当前页面下的所有表格模板。
- 填报详情页 `/projects/:projectKey/pages/:pageKey/sheets/:sheetKey`：通过 RevoGrid 渲染模板并提交数据。
- 数据审批页 `/projects/:projectKey/pages/:pageKey/runtime/:sheetKey/approval`：调用运行时表达式接口并按模板 `accuracy`（含分项覆盖）格式化数值。
- 数据展示页 `/projects/:projectKey/pages/:pageKey/runtime/:sheetKey/display`：支持多级表头、列分组以及按模板 `accuracy` 控制的分项小数位。

所有与模板相关的接口均追加 `config` 查询参数，用于明确加载的 JSON 模板文件；未传入时后端回落至基础指标表。审批/展示页会在运行时追加一次 `getTemplate` 请求，以读取模板中的 `accuracy` 配置。

## 主要模块

- `components/AppHeader.vue`：全局页头与导航。
- `components/Breadcrumbs.vue`：面包屑导航，配合页面级状态使用。
- `pages/PageSelectView.vue`：新增页面选取视图，读取 `listPages` 接口。
- `pages/Sheets.vue`：展示表格列表并跳转至填报页面。
- `pages/DataEntryView.vue`：RevoGrid 实际填报逻辑，提交时会附带 `config` 参数确保命中正确模板。
- `pages/ApprovalView.vue`：运行时求值审批界面，支持 `accuracy` 默认值与分项精度（按“项目/指标”列匹配）并对差异列保留百分比。
- `pages/DisplayRuntimeView.vue`：展示页版本的运行时求值渲染，启用列分组、追踪信息及分项小数位控制。

## API 调用

统一由 `services/api.js` 负责，默认基地址为 `/api/v1`：

- `listProjects(force)`：获取项目列表，带缓存。
- `listPages(projectKey)`：读取某项目的页面配置。
- `listSheets(projectKey, configFile)`：按模板文件列出表格。
- `getTemplate(projectKey, sheetKey, { config })`：读取具体模板。
- `queryData(projectKey, sheetKey, payload, { config })`：查询历史填报记录。
- `submitData(projectKey, sheetKey, payload, { config })`：提交填报数据。
- `evalSpec(projectKey, body)`：运行时表达式求值；若响应包含 `accuracy_overrides`（后端从 `render_spec` 透传），审批/展示页直接使用该行级精度；否则退回 `getTemplate` 解析模板 `accuracy` 字段。

上述接口若返回非 2xx 状态会抛出异常，由页面组件统一处理并提示用户。
