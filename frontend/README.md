# 前端说明（Vue3 + Vite）

该目录使用 Vue3 + Vite 作为开发脚手架，业务模块 `daily_report_25_26` 与后端接口一一对应。

## 目录结构

```
frontend/
├─ src/
│  ├─ App.vue                 # 根组件
│  ├─ main.js                 # 应用入口
│  ├─ router/index.js         # 全局路由：/login、/projects、/projects/:projectKey/sheets、/projects/:projectKey/sheets/:sheetKey
│  ├─ stores/                 # Pinia store（占位）
│  └─ daily_report_25_26/
│     ├─ components/          # AppHeader、Breadcrumbs 等公共组件
│     ├─ constants/           # project_key、sheet 常量
│     ├─ pages/               # LoginView、ProjectSelectView、Sheets、DataEntryView
│     ├─ services/            # API 封装（api.js）
│     ├─ store/               # 业务状态（预留）
│     └─ styles/theme.css     # 统一视觉风格
├─ public/
├─ vite.config.js
└─ package.json
```

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
- `/projects/:projectKey/sheets` → `Sheets.vue`
  - 展示模板清单；按单位分组并以卡片呈现；点击表名进入填报页面；
  - `listSheets` 响应新增 `unit_name/sheet_name` 字段，以适配英文/中文双写。 
- `/projects/:projectKey/sheets/:sheetKey` → `DataEntryView.vue`
  - 使用 `@revolist/vue3-datagrid` 提供的 `RevoGrid` 组件渲染表格，自带自定义元素注册；
  - 通过 `@afteredit` 事件回调同步 `gridSource`，提交阶段汇总单元格生成 `cells`；
  - 模板 `columns` 的后两列分别为“今日日期”“去年同日”，用于展示对比列。
  - 首列在模板与历史数据完成加载后触发 `autoSizeFirstColumn()`，基于整列文本宽度动态设定列宽并再次调用 RevoGrid 自适应，支持任意单元格内容完整显示。
  - 通过 `:apply-on-close="true"` 启用 RevoGrid 内建的失焦自动保存机制，配合 `@afteredit` 更新本地状态，确保未按 Enter 的输入也能保留。

## API 交互要点

所有请求以 `/api/v1` 为前缀，`project_key` 统一为 `daily_report_25_26`。

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/projects/{project_key}/sheets` | 返回表格清单；单个条目同时包含 `单位名/表名` 以及 `unit_name/sheet_name` |
| `GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template` | 返回填报模板；`columns` 自动补齐当前日期与上一年度同日；`rows` 为二维数组 |
| `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit` | 占位（待实现） |
| `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query` | 占位（待实现） |

前端 `services/api.js` 会读取 `.env` 中的 `VITE_API_BASE`，默认 `http://127.0.0.1:8000`，可按部署场景调整。

## 与 @revolist/vue3-datagrid 的配合

- `DataEntryView.vue` 直接导入 `@revolist/vue3-datagrid` 默认导出的 `RevoGrid` 组件，无需手动调用 `defineCustomElements`；
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
