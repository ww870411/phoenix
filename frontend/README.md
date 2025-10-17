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
      - `index.js`  ← 新增路由：/login、/projects、/projects/:projectKey/dashboard、/projects/:projectKey/sheets/:sheetKey/fill
    - `stores/`
      - `counter.js`
    - `daily_report_25_26/`
      - `README.md`
      - `components/`
        - `AppHeader.vue`  ← 新增统一头部（商务蓝）
      - `constants/`
        - `index.js`
        - `sheets.js`
      - `pages/`
        - `LoginView.vue`
        - `ProjectSelectView.vue`
        - `DashboardView.vue`
        - `DataEntryView.vue`
      - `services/`
        - `api.js`
      - `store/`
      - `styles/`
        - `theme.css`  ← 商务蓝主题（按钮/卡片/表格/徽章/进度条/容器等）

说明：以上为当前前端目录的真实结构快照，供前后端协作与定位参考；如有结构调整，将在后续会话中自动更新。
