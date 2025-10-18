# 前端说明（Vue3 + Vite）

本前端以 Vue3 + Vite 为基础，采用“按项目隔离”的目录结构：

## 目录结构

```
frontend/
├─ src/
│  ├─ daily_report_25_26/           # 项目 daily_report_25_26 的隔离模块（仅保留常量与说明，业务由后续接入）
│  │  ├─ constants/                 # 常量（含 PROJECT_KEY）
│  │  └─ README.md                  # 模块说明
│  ├─ router/index.js               # 全局路由入口（当前未接入业务路由）
│  └─ App.vue                       # 根组件，渲染 <router-view />
└─ vite.config.js
```

## 路由设计
- 当前不包含任何业务路由。后续按项目模块接入时，再在 `src/router/index.js` 注册对应路由。

## 与后端的约定
- 统一使用 `project_key = 'daily_report_25_26'`（定义于 `src/daily_report_25_26/constants/index.js`）。
- 业务 API 由后端实现后，再在前端对应模块内封装与接入。

## 启动方式
开发模式：
```
cd frontend
npm install
npm run dev
```

Docker 模式（开发环境整套运行）：
```
docker compose up -d --build
```

访问：
- 前端（Vite）：`http://localhost:5173/`
- 后端：`http://localhost:8000/healthz`
## 结构快照（自动维护）
更新时间：2025-10-17

- 根目录
  - `Dockerfile`
  - `README.md`
  - `index.html`
  - `vite.config.js`
  - `nginx.conf`
  - `package.json`
- 目录
  - `public/`
  - `src/`
    - `App.vue`
    - `main.js`
    - `router/`
      - `index.js`  ← 新增路由：/login、/projects、/projects/:projectKey/sheets、/projects/:projectKey/sheets/:sheetKey
    - `stores/`
      - `counter.js`
    - `daily_report_25_26/`
      - `README.md`
      - `components/`
        - `AppHeader.vue`  ← 新增统一头部（商务蓝）
        - `Breadcrumbs.vue`  ← 新增面包屑导航（可点击返回层级）
      - `constants/`
        - `index.js`
        - `sheets.js`
      - `pages/`
        - `LoginView.vue`
        - `ProjectSelectView.vue`
        - `DashboardView.vue`
          - 访问时调用 `GET /api/v1/projects/{project_key}/sheets` 拉取表清单（单位/表名/键名），可点击进入填报
        - `DataEntryView.vue`
          - 顶部新增“← 返回仪表盘”按钮，快速回到仪表盘
          - 使用 `<revo-grid>` 渲染可编辑表格，支持单元格内直接编辑
      - `services/`
        - `api.js`
          - `listSheets(projectKey)`：获取项目下所有表清单
      - `store/`
      - `styles/`
        - `theme.css`  ← 商务蓝主题（按钮/卡片/表格/徽章/进度条/容器等）

## 依赖补充（前端）
- 新增：`@revolist/revogrid`（Web Components 高性能表格）
- 安装：在前端容器或本机运行 `npm install`/`pnpm install`（Compose 构建过程会自动安装依赖）
- 说明：`DataEntryView.vue` 通过 `import '@revolist/revogrid'` 引入组件（注册自定义元素 `<revo-grid>`），并用 `columns`+`source` 绑定数据；编辑后通过 `afteredit/afterEdit` 事件收集变更。
  - 注：该包未在 `exports` 暴露 css 入口，直接导入子路径 css 会触发 Vite 扫描错误；当前不导入官方 css，依赖组件内置样式与站点主题外观。

说明：以上为当前前端目录的真实结构快照，供前后端协作与定位参考；如有结构调整，将在后续会话中自动更新。
## 路由一览（当前实现）

- `/` → 重定向至 `/login`
- `/login` → `LoginView.vue`
- `/projects` → `ProjectSelectView.vue`
- `/projects/:projectKey/sheets` → `DashboardView.vue`
- `/projects/:projectKey/sheets/:sheetKey` → `DataEntryView.vue`

后端 API 对应（以 `/api/v1` 为前缀）：
- `GET /api/v1/ping`（系统连通）
- `GET /api/v1/projects/{project_key}/sheets`（表清单；当前实现固定为 `daily_report_25_26`）
- `GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template`（获取模板）
- `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit`（提交数据）
- `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query`（查询数据）

说明：项目路径与项目代号统一为 `daily_report_25_26`，前后端一致。

### 开发环境 API 基址

- 本地 `npm run dev` 默认读取 `.env.development`，其中 `VITE_API_BASE=http://127.0.0.1:8000`，由浏览器直接访问后端容器映射端口，避免 Vite Dev Server 自身 404。
- 如在 Docker Compose 内运行，可根据需要调整 `VITE_API_BASE` 指向对外暴露的后端地址；未设置时仍回退到相对路径，与 Nginx 反向代理行为一致。
