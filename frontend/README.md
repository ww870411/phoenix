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
  - 获取模板后交由 RevoGrid 渲染；
  - 模板 `columns` 的后两列分别为“今日日期”“去年同日”，用于展示对比列。 

## API 交互要点

所有请求以 `/api/v1` 为前缀，`project_key` 统一为 `daily_report_25_26`。

| 接口 | 说明 |
| --- | --- |
| `GET /api/v1/projects/{project_key}/sheets` | 返回表格清单；单个条目同时包含 `单位名/表名` 以及 `unit_name/sheet_name` |
| `GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template` | 返回填报模板；`columns` 自动补齐当前日期与上一年度同日；`rows` 为二维数组 |
| `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit` | 占位（待实现） |
| `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query` | 占位（待实现） |

前端 `services/api.js` 会读取 `.env` 中的 `VITE_API_BASE`，默认 `http://127.0.0.1:8000`，可按部署场景调整。

## 与 RevoGrid 的配合

- `handle_sheet_template`（前端待实现）需将模板的 `columns/rows` 转换为 RevoGrid 所需的列配置与数据源；
- 模板首行使用后端返回的四列表头（项目、计量单位、今日日期、去年同日）；
- 数据从第二行开始对应后端返回的 `rows`（二维数组），并根据列数动态渲染；
- RevoGrid 编辑结果通过 `afterEdit` 事件收集，最终调用 `submitData` 接口完成提交。

## 接口演进记录（2025-10-19）

- 模板接口返回结构已定型：`sheet_key/sheet_name/unit_name/columns/rows`；`columns[2]`、`columns[3]` 自动写入日期，无需前端手动拼装。 
- 模板清单接口兼容中文/英文键名，便于组件直接显示。
- 若模板缺失列名或数据，后端会返回 422，前端需引导用户检查模板配置。

## 环境变量

- `VITE_API_BASE`：前端调用后端的基础地址，开发默认 `http://127.0.0.1:8000`；
- 其余变量按需扩展。
