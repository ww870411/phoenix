# daily_report_25_26 前端说明

## 页面结构更新（2025-10-23）

- 登录页 `/login`：录入账号信息后跳转至项目列表页。
- 项目列表页 `/projects`：读取 `/api/v1/projects` 展示可用项目。
- 页面选取页 `/projects/:projectKey/pages`：根据 `backend_data/项目列表.json` 中的 `pages` 配置，使用卡片选择目标页面。
- 表格列表页 `/projects/:projectKey/pages/:pageKey/sheets`：按卡片展示当前页面下的所有表格模板。
- 填报详情页 `/projects/:projectKey/pages/:pageKey/sheets/:sheetKey`：通过 RevoGrid 渲染模板并提交数据。

所有与模板相关的接口均追加 `config` 查询参数，用于明确加载的 JSON 模板文件；未传入时后端回落至基础指标表。

## 主要模块

- `components/AppHeader.vue`：全局页头与导航。
- `components/Breadcrumbs.vue`：面包屑导航，配合页面级状态使用。
- `pages/PageSelectView.vue`：新增页面选取视图，读取 `listPages` 接口。
- `pages/Sheets.vue`：展示表格列表并跳转至填报页面。
- `pages/DataEntryView.vue`：RevoGrid 实际填报逻辑，提交时会附带 `config` 参数确保命中正确模板。

## API 调用

统一由 `services/api.js` 负责，默认基地址为 `/api/v1`：

- `listProjects(force)`：获取项目列表，带缓存。
- `listPages(projectKey)`：读取某项目的页面配置。
- `listSheets(projectKey, configFile)`：按模板文件列出表格。
- `getTemplate(projectKey, sheetKey, { config })`：读取具体模板。
- `queryData(projectKey, sheetKey, payload, { config })`：查询历史填报记录。
- `submitData(projectKey, sheetKey, payload, { config })`：提交填报数据。

上述接口若返回非 2xx 状态会抛出异常，由页面组件统一处理并提示用户。

