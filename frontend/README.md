# 前端说明（Vue3 + Vite）

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 目录结构

```
frontend/
├─ .env.development         # 本地调试环境变量（API 基础路径等）
├─ Dockerfile               # 前端容器镜像定义
├─ nginx.conf               # Nginx 转发配置
├─ package.json
├─ vite.config.js
├─ src/
│  ├─ App.vue               # 根组件
│  ├─ main.js               # 应用入口
│  ├─ router/index.js       # 全局路由：/login、/projects、/projects/:projectKey/data_entry/sheets、/projects/:projectKey/data_entry/sheets/:sheetKey
│  ├─ stores/               # Pinia store（占位）
│  └─ daily_report_25_26/
│     ├─ components/        # AppHeader、Breadcrumbs 等公共组件
│     ├─ constants/         # project_key、sheet 常量
│     ├─ pages/             # LoginView、ProjectSelectView、Sheets、DataEntryView（动态渲染模板列，含解释说明）
│     ├─ services/          # API 封装（api.js）
│     ├─ store/             # 业务状态（预留）
│     └─ styles/theme.css   # 统一视觉风格
├─ public/
└─ README.md
```

## 结构快照更新（2025-10-28）

- 本次变更为后端 SQL 脚本中补充二级物化视图的“唯一索引（并发刷新支持）”，前端目录与页面结构不变、接口不变。
- 若后续展示页直接消费二级物化视图结果，将在 `daily_report_25_26/pages/` 下新增展示组件并同步更新本文结构说明。
 - 本轮后端新增“运行时表达式求值”模块（`backend/services/expression_eval.py`），作为后端内部计算能力，对前端结构与接口无影响。

## 启动方式

开发模式：

```bash
cd frontend
npm install
npm run dev
```

容器模式：

```bash
docker compose up -d --build
```

默认访问地址：`http://localhost:5173/`

## 路由与页面

- `/login` → `LoginView.vue`
- `/projects` → `ProjectSelectView.vue`
  - 首次进入时请求 `GET /api/v1/projects`，显示项目中文名列表并根据所选项目跳转。
- `/projects/:projectKey/data_entry/sheets` → `Sheets.vue`
  - 展示模板清单；按单位分组并以卡片呈现；点击表名进入填报页面；
  - `listSheets` 响应新增 `unit_name/sheet_name` 字段，以适配英文/中文双写。 
- `/projects/:projectKey/data_entry/sheets/:sheetKey` → `DataEntryView.vue`
  - 使用 `@revolist/vue3-datagrid` 提供的 `RevoGrid` 组件渲染表格，自带自定义元素注册；
  - 通过 `@afteredit` 事件回调同步 `gridSource`，提交阶段直接基于 `gridSource` 生成提交数据（rows-only）；
  - 模板 `columns` 会扫描列头中首次出现“计量单位”的位置，将该列及之前列标记为只读，其余列渲染本期/同期/解释说明等可编辑数据。
  - 模板响应中的所有 `*_dict` 字段会缓存至 `templateDicts.entries`，提交时逐项带回，扩展字典（中心/状态等）无需额外适配。
  - 首列在模板与历史数据完成加载后触发 `autoSizeFirstColumn()`，基于整列文本宽度动态设定列宽并再次调用 RevoGrid 自适应，支持任意单元格内容完整显示。
  - 通过 `:apply-on-close="true"` 启用 RevoGrid 内建的失焦自动保存机制，配合 `@afteredit` 更新本地状态，确保未按 Enter 的输入也能保留。

## API 交互要点

所有请求以 `/api/v1` 为前缀，`project_key` 统一为 `daily_report_25_26`。

### 变更记录（2025-10-23）
- 修复数据填报页日历联动：标准表在后端以“列头日期文本”决定每列的 `date`，现于 `pages/DataEntryView.vue` 中缓存原始列头 `baseColumns` 并在 `bizDate` 变更时重算列头与 `gridColumns` 名称，确保提交与展示使用最新日期。
- 通用查询接口（设计中）：保持现有 `services/api.js::queryData(projectKey, sheetKey, payload)` 用于“单表查询”；后续将新增“项目级聚合查询”接口，前端可在数据展示/常量页选择批量请求以减少 HTTP 次数。

### 变更记录（2025-10-28）
- 修复标准表日历切换后数据未刷新的问题：在 `DataEntryView.vue` 中新增 `applyStandardQueryResult`，统一处理 `/query` 回包的列头与 `rows` 回填；`loadTemplate` 首发查询与 `watch(bizDate)` 共同调用该方法，确保切换日期后即时刷新并保持首列自适应宽度，同时避免回包中的列头覆盖前端按昨日/同期替换后的显示。

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/projects` | 返回项目列表（`project_id/project_name`），供前端展示中文名 |
| `GET /api/v1/projects/{project_key}/data_entry/sheets` | 返回数据填报模板清单；单个条目同时包含 `单位名/表名` 以及 `unit_name/sheet_name` |
| `GET /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/template` | 返回填报模板；`columns` 先保留模板配置中的全部列（含“解释说明”等自定义列），再自动追加当前日期与上一年度同日；`rows` 为二维数组；同时附带模板定义的字典字段（如“项目字典”“单位字典”），提交时需保持字段名与内容不变 |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/submit` | 占位（待实现） |
| `POST /api/v1/projects/{project_key}/data_entry/sheets/{sheet_key}/query` | 占位（待实现） |

前端 `services/api.js` 会读取 `.env` 中的 `VITE_API_BASE`，默认 `http://127.0.0.1:8000`，可按部署场景调整。

## 与 @revolist/vue3-datagrid 的配合

- `DataEntryView.vue` 直接导入 `@revolist/vue3-datagrid` 默认导出的 `RevoGrid` 组件，无需手动调用 `defineCustomElements`；
  - 调试日志：已在 `DataEntryView.vue` 和 `services/api.js` 加入 rows-only 渲染链路的调试输出，包括：
    - `[data-entry/route-init]`、`[data-entry/reloadTemplate]`
    - `[revogrid/watch]`（columns/rows/gridColumns/gridSource 长度）
    - `[api/getTemplate]`、`[api/queryData/request]`、`[api/submitData/request]`
    - `[revogrid/afterEdit]`、`[data-entry/submit]`
  - 观察要点：当 `gridColumns.length > 0` 且 `gridSource.length > 0` 后，应能显示数据；若仍空白，检查模板容器的 `v-if="columns.length"` 是否及时更新。
- 模板首行使用后端返回的四列表头（项目、计量单位、今日日期、去年同日）； 
- 数据从第二行开始对应后端返回的 `rows`（二维数组），并根据列数动态渲染；
- 用户编辑后触发的 `afteredit/afterEdit` 事件统一由 `handleAfterEdit` 处理，同步更新 `gridSource` 与本地缓存，最终调用 `submitData` 接口提交。

## 接口演进记录（2025-10-19）

- 模板接口返回结构已定型：`sheet_key/sheet_name/unit_name/columns/rows`；`columns[2]`、`columns[3]` 自动写入日期，无需前端手动拼装。 
- 模板清单接口兼容中文/英文键名，便于组件直接显示。
- 若模板缺失列名或数据，后端会返回 422，前端需引导用户检查模板配置。

## 环境变量

- `VITE_API_BASE`：前端调用后端的基础地址，开发默认 `http://127.0.0.1:8000`；
- 其余变量按需扩展。
#
# 追加变更记录（2025-10-23）

- 修复交叉表（煤炭库存 Coal_inventory_Sheet）首屏空白：调整 `pages/DataEntryView.vue` 的 `loadTemplate()` 初始化顺序，先判定 `template_type==='crosstab'` 并调用 `setupCrosstabGrid` 初始化列与占位行，再执行镜像查询以回填 `columns/rows`，并避免后续渲染流程覆盖查询结果，确保打开页面即可显示默认日期数据。
# 追加说明：渲染流程（模板 + 镜像查询）

- 标准表（standard）
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 首屏：`getTemplate` → 占位符应用（含日期文字）→ `setupStandardGrid` 渲染 → 立刻调用 `queryData` 以 `rows` 回填网格；
- 调试：在应用 query 数据时，会弹出提示框显示响应中的 `request_id`，便于你核对具体是哪一次响应被渲染（若弹窗不可用则降级为控制台 `[query/request_id]` 日志）。
 - 统一行为：standard 与 crosstab 均只在模板加载完成后触发一次首发查询；不再执行二次 `loadExisting()` 查询。
  - 日期切换：重算列头文字 → `queryData` 回填当前日期数据；
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:541`（watch 处理）。

- 交叉表（crosstab，Coal_inventory_Sheet）
  - 首屏：`getTemplate` 后先确定 `template_type==='crosstab'`，调用 `setupCrosstabGrid` 初始化列与占位行 → 再 `queryData`，若返回 `columns` 则同步列头，并用 `rows` 重建 `gridSource`；
  - 日期切换：`queryData` 返回的 `columns/rows` 直接替换 `columns/gridSource`；
  - 关键代码：`pages/DataEntryView.vue:249`（`loadTemplate`）、`pages/DataEntryView.vue:592`（watch 处理）。

- 接口：`services/api.js:85` `queryData(projectKey, sheetKey, payload, { config })`。
## 数据获取与回填（2025-10-25 更新）

- `/template`：提供模板元信息（`columns`、`rows`、`*_dict` 等）。
- `/query`：现已与模板结构对齐，直接返回 `columns` + `rows`，前端仅消费 `rows` 与 `columns`。
- 已移除 cells 路径：不再读取或合并 `cells`，避免覆盖 `rows`。

### 前端回填要点（2025-10-25）
- 回填顺序与要点：
  - 若存在 `q.columns`，重建/对齐 `gridColumns`（`prop: c${i}`）。
  - 将 `q.rows` 映射为 `gridSource`：`{ c0, c1, ... }`，单元格统一转字符串或空串。
  - 同步设置内部 `rows` 为 `q.rows`，保持显示与提交一致。
## 运维提示：Docker 启动失败（数据库 unhealthy）

- 现象：`phoenix_db` 在编排启动时变为 `unhealthy`，日志包含 `invalid magic number`/`could not locate a valid checkpoint record`。
- 原因：数据库挂载目录 `./db_data` 的 WAL/检查点损坏。
- 建议：先尝试 `pg_resetwal -f "$PGDATA"` 修复；若仍失败，备份并清空 `./db_data` 后重新初始化数据库，再启动前端服务。
## 调试输出策略（2025-10-25）

- 已移除所有前端调试输出：不再使用 `console.*` 与 `alert(...)`。
- 不影响功能：模板加载与 rows-only 渲染流程保持一致。
- 如需排障，建议临时在本地分支加入日志，避免进入主干。
### 2025-10-27 视图规划沟通（AI 辅助）
- 当前会话仅讨论 PostgreSQL 视图设计，前端无需改动；待后端提供视图接口后再补充数据展示方案。
### 2025-10-27 审批表渲染对接（计划）
- 后端将提供“运行时表达式求值”服务，返回已替换表达式的 `columns + rows`（rows-only）结构。
- 前端保持 RevoGrid 渲染逻辑不变，仅消费后端返回的行数据；无需内置任何公式解析。
- 如需差异颜色/箭头等展示效果，可在拿到 `*_diff_rate()` 结果后按阈值做样式扩展（后续再议）。
