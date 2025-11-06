# daily_report_25_26 前端说明

## 仪表盘累计卡片气温数据准备（2025-11-12）

- 后端“9.累计卡片”段的 `供暖期平均气温` 字段现返回逐日数组（`[{ date, value }]`），包含推送日区间内所有日期以及同期映射；缺失数据以 `value = null` 标识。
- 前端在接入该段数据时，可直接用于折线/柱状多日比较，无需额外分段聚合；若暂不使用可忽略该字段，其他累计指标取值不受影响。
- 一旦需要回退旧版单值响应，请在前端代码中加入版本兼容判断或等待后端将函数恢复。

## 仪表盘累计摘要卡片（2025-11-12）

- `DashBoard.vue` 新增 `cumulativeSection` 系列计算属性，统一从 “9.累计卡片” 读取供暖期平均气温/可比煤价边际利润/标煤耗量/投诉量并比较同期数值。
- 仪表盘摘要区后四张 `summary-card` 现展示上述累计指标，数值后附括号显示与同期的增量（自动带正负号，支持千分位），视觉样式也改为描边无底色、无图标的简洁风格（`summary-card--outline`，高度下调约 10%）。
- 首页前四张摘要卡同样补充了同比增量显示：当日可比煤价边际利润、标煤消耗、投诉量均在括号中输出与同期差值，内部逻辑复用 `primary*Headline` 计算属性以保持格式一致。
- 原先用于煤炭库存、热/电/水单耗的紧凑卡片逻辑已移除；需要恢复时请回退 `DashBoard.vue` 中对应段落。

## 仪表盘单耗卡片布局与视觉调整（2025-11-11）

- `.dashboard-grid__item--unit` 栅格跨度改为 `span 12`，三张“供暖热/电/水单耗对比”卡片在 ≥1024px 视口下各自独占一行，并将对应图表高度提升至 `360px`。
- 本期柱统一为蓝色（#2563eb），同期柱改为高对比橙色（#f97316，含条纹），同时放宽柱宽及图表内边距以突出差异。
- 单耗卡片的数值标签现分别显示在本期/同期两根柱体上，不再组合在同一标签；若需恢复旧样式，可重新启用组合 formatter 并关闭同期标签。
- 其余卡片布局与响应式行为保持不变，窄屏仍按单列堆叠；若需恢复旧视觉，将 `.dashboard-grid__item--unit` 栅格跨度与 `useUnitConsumptionOption` 中的颜色/柱宽改回即可。

## 仪表盘“集团汇总”文案统一（2025-11-11）

- `backend_data/数据结构_数据看板.json` 与 `单位字典` 中的“集团全口径”全部替换为“集团汇总”，并把“3.”段标题更新为“集团汇总收入明细”。
- `DashBoard.vue`/`DashBoard888.vue` 的 fallback 列表、`resolveSection` 调用以及边际利润/投诉/煤耗等模块同步替换文本，避免前端本地数据残留旧称谓；新的 `resolveSection` 仍兼容旧标题以便回滚。
- 若需恢复旧名称，只需撤销上述文件并重新部署，接口结构未发生变化。

## 仪表盘单耗水平布局尝试（2025-11-11）

- `useUnitConsumptionOption` 新增 `orientation` 参数，目前三张单耗卡片以 `horizontal` 方式渲染条形图，卡片高度设为 450px（较试验初始的 300px 提升 1.5 倍），栅格跨度为 `span 4` 以便三图并排展示；公司顺序固定为“研究院→庄河环海→金普热电→北方热电→金州热电→主城区→集团汇总”（缺项自动跳过）。
- 仅为展示试验，后端数据结构未改；若需恢复竖向图表，将 `orientation` 传回 `vertical` 并按需调整栅格跨度。
- summary 模块新增 4 张紧凑卡片（煤炭库存、集团热/电/水单耗），使用 `summary-card--compact` 将高度压缩至原卡片的约 80%，配套独立配色与图标。

## 仪表盘段名序号化（2025-11-11）

- 新增 `resolveSection` 辅助，所有 `dashboardData.sections['N.xxx']` 访问切换为按编号前缀解析；模板改名后无需同步代码即可生效。
- 投诉分项卡片同时兼容“当日省市平台投诉量”“当日省市平台服务投诉量”等命名，`complaintMetricOrder/complaintMetricTitleMap` 已补充多语义映射。
- 若需恢复旧逻辑，可删除 `sectionIndexMap/resolveSection` 并将 `DashBoard.vue` 中的序号访问改回原始键名。

## 登录与权限更新（2025-11-02）

- 新增 Pinia `auth` 仓库：统一管理 `/auth/login|me|logout` 调用、Token 持久化（sessionStorage）、页面/表格过滤与审批/发布操作。
- `router` 全局守卫在进入非 `/login` 路由前确保已登录；登录成功后自动跳转 `/projects`，退出后清空缓存并返回登录页。
- `services/api.js` 注入 Authorization 头并封装 `getWorkflowStatus/approveWorkflow/publishWorkflow`；`PageSelectView` 显示审批进度卡片并在具备权限时提供批准/发布按钮。
- 审批进度卡片额外展示“当前业务日期｜当前数据展示日期”：业务日取东八区昨日，展示日期来自 `backend_data/date.json`，在新业务日未发布前保持上一期数据。
- `LoginView`、`AppHeader`、`Sheets` 等组件按角色隐藏或禁用按钮；页面/表格列表在前端再次过滤，避免越权访问。
- 新增 `frontend/Dockerfile.prod`（Node → Nginx 多阶段构建）与 `deploy/nginx.conf`，供生产镜像使用；默认监听 80 端口并通过 `location /api/` 反向代理至后端服务 `backend:8000`。
- 全局样式统一在 `src/main.js` 引入 `./daily_report_25_26/styles/theme.css`，避免刷新子路由（如 `/projects/daily_report_25_26/pages`）时主题缺失。
- `DataEntryView` 针对 `Unit_admin` / `unit_filler` 增加日期权限：可切换日期查看历史数据，但当选中日期 ≠ 当期业务日时，网格只读且“提交”按钮禁用。

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
