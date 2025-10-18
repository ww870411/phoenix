# 项目推进记录（progress）

说明：本记录用于跟踪本次会话内的重要决策、改动与偏差，便于审计与后续回溯。

注意：受限于当前环境未接入 Serena 工具链，登记留痕暂以本文件替代；后续可将内容同步至知识库。

---

## 2025-10-17 会话内变更概览

1) 读取与确认全局规范
- 动作：读取 `AGENTS.md` 并确认项目总体设计、允许/禁改目录与接口规范。
- 备注：首次读取为确保中文编码，临时使用了 PowerShell 读取（偏差点），后续所有“修改”均遵循 `apply_patch`。

2) 仓库结构盘点
- 动作：梳理现有目录与文件，发现缺少 `backend/`、`docs/`、`docker-compose.yml` 等；`configs/` 中已有两份数据结构 JSON。
- 结论：先补齐后端骨架与前端隔离目录，逐步推进。

3) 创建后端骨架（FastAPI）
- 新增目录：`backend/app/`、`backend/app/api/`、`backend/app/api/v1/`、`backend/app/models/`、`backend/app/schemas/`、`backend/app/services/`。
- 新增文件：
  - `backend/app/main.py`：应用入口，提供 `GET /healthz` 与挂载 `/api/v1`。
  - `backend/app/api/v1/routes.py`：基础连通性 `GET /api/v1/ping`。
  - 其他 `__init__.py` 与 `backend/README.md` 说明。

4) 运行指导与问题排查
- 现象：在 `backend/` 目录执行 `uvicorn backend.app.main:app` 报 `ModuleNotFoundError: backend`。
- 结论：需在项目根目录执行，或在 `backend/` 下使用 `uvicorn app.main:app`；已给出两种可行命令与说明。

5) 前端隔离目录创建（项目名：daily_report_25_26）
- 原规范中的 `frontend/src/projects/…` 层级较深；根据最新指令改为与 `src/` 并列的项目目录。
- 新增目录与文件：
  - `frontend/src/daily_report_25_26/` 下：`pages/`（Dashboard.vue、Sheet.vue）、`components/`（ProjectHeader.vue）、`store/`、`services/`（api.js）、`constants/`（index.js）、`routes.js`、`README.md`。
- 说明：`services/api.js` 仅封装项目专属 API 调用，不修改禁改的 `frontend/src/api/`。

6) 统一 project_key 与接入路由
- 决策：后端与前端统一使用 `project_key = 'daily_report_25_26'`（按用户最新要求执行）。
- 前端改动：
  - `constants/index.js` 将 `PROJECT_KEY` 统一为 `daily_report_25_26`。
  - `router/index.js` 接入并启用该模块路由，根路径重定向至 `/daily_report_25_26`。
  - `App.vue` 渲染 `<router-view />`，以显示路由页面。

7) 后端 API 路径增加项目级前缀
- 决策：在通用前缀 `/api/v1` 之下，新增项目级前缀 `/daily_report_25_26`，形成路径隔离（示例：`GET /api/v1/daily_report_25_26/ping`）。
- 改动：
  - 新增 `backend/api/v1/daily_report_25_26.py`，提供项目级 `ping`。
  - 在 `backend/api/v1/routes.py` 中 `include_router(..., prefix="/daily_report_25_26")`。
  - 更新 `backend/README.md`，说明“通用 + 项目别名”并存策略与启动命令修正。
- 说明：此前存在 `backend/app/` 与 `backend/` 两套结构，现以 `backend/` 为主；`backend/app/` 中的同名文件不参与运行，后续统一清理时再处理。

8) 去除 `/projects/{project_key}` 路径层
- 决策：统一采用“项目别名前缀”风格：`/api/v1/daily_report_25_26/...`，不再使用 `/projects/{project_key}` 层级。
- 改动：
  - 前端 `src/daily_report_25_26/services/api.js` 更新 3 个接口路径，去除 `/projects` 段。
  - 前端 `README.md` 更新接口示例为新风格。
  - 后端 `README.md` 更新计划接口为新风格。
- 说明：请求体中仍保留 `project_key` 字段用于后续后端校验（可选），不影响路径风格；如需完全移除，可在实现接口时同步调整。

9) 实现 daily_report_25_26 最小三接口
- 改动：
  - `backend/api/v1/daily_report_25_26.py` 增加 Pydantic 模型与内存存储，实现：
    - `GET /api/v1/daily_report_25_26/sheets/{sheet_key}/template`
    - `POST /api/v1/daily_report_25_26/sheets/{sheet_key}/submit`
    - `POST /api/v1/daily_report_25_26/sheets/{sheet_key}/query`
  - `backend/README.md` 增补验证示例。
- 说明：当前实现为内存态（随进程重启丢失），仅用于前后端联调与占位；后续将替换为 SQLAlchemy + PostgreSQL 的幂等写入与查询。

10) 清理历史遗留目录 backend/app/
- 动作：删除 `backend/app/api/v1/daily_report_25_26.py`；现以 `backend/` 下结构为唯一有效路径。
- 说明：`backend/app/` 目录仅作早期骨架残留，当前运行入口与路由均在 `backend/` 顶层；后续如再出现残留文件，将继续清理，避免歧义。

---

11) 清理示例与占位代码
- 后端：
  - 精简 `backend/api/v1/daily_report_25_26.py`，移除示例模板/提交/查询及内存存储，仅保留 `GET /ping`。
  - 重写 `backend/README.md`，保留运行方式与连通性验证，去除示例接口描述。
- 前端：
  - 删除 `src/daily_report_25_26/pages/*`、`components/ProjectHeader.vue`、`services/api.js`、`store/index.js`、`routes.js`。
- 更新 `src/router/index.js`，去除对示例路由的挂载，当前不注册业务路由。
- 更新 `frontend/README.md`，改为“待接入业务路由”的说明。

12) 初始化 Git 仓库并完成首次提交
- 新增：根目录 `.gitignore`（Python/Node/Vite/编辑器与系统文件忽略）。
- 执行：`git init`、`git add -A`、`git branch -M main`、`git commit -m 'chore: initial commit'`。
- 说明：远端推送未在本地直接执行，后续按 README 指引添加 remote 并 `git push -u origin main`。

13) Docker 化与容器编排
- 新增：`backend/Dockerfile`（uvicorn 运行 FastAPI）。
- 新增：`frontend/Dockerfile`（Node 构建 + Nginx 运行，供未来生产使用）。
- 新增：`frontend/nginx.conf`（静态与代理配置）。
- 新增：`docker-compose.yml`（`db`/`backend`/`frontend`）。
- 新增：`backend_data/README.md`（说明绑定挂载目录用途）。
- 更新：`backend/README.md`、`frontend/README.md`（加入 Docker 启动说明）。

14) 调整为开发环境标准（Compose）
- backend：启用 `uvicorn --reload`，将项目根 `./` 挂载到容器 `/app`，`./backend_data` 挂载到 `/app/data`。
- frontend：改为使用 `node:20-alpine` 容器运行 Vite 开发服务器，端口 `5173`；挂载 `./frontend:/app`，并使用命名卷 `frontend_node_modules` 存放依赖。
- 访问：前端 `http://localhost:5173/`，后端 `http://localhost:8000/`，数据库端口 `5432` 保持不变。

回滚思路
- 前端目录层级：当前目录为 `frontend/src/daily_report_25_26/`，与项目代号一致。
- project_key 命名：统一为 `daily_report_25_26`，`frontend/src/daily_report_25_26/constants/index.js` 中 `PROJECT_KEY` 已为该值。
- 路径级隔离：如需撤销项目级前缀，仅在 `backend/api/v1/routes.py` 移除 `include_router`，并从前端改回通用路径。

验证清单
- 后端：
  - 启动：`uvicorn backend.main:app --reload`
  - 健康：`GET /healthz` 返回 `{ ok: true }`。
  - 通用：`GET /api/v1/ping` 返回 `{ ok: true, message: 'pong' }`。
  - 项目前缀：`GET /api/v1/daily_report_25_26/ping` 与三接口可用。
- 前端：
  - 启动：`cd frontend && npm install && npm run dev`。
  - 页面：访问 `/daily_report_25_26`、`/daily_report_25_26/sheets/demo` 可见占位页面。
## 2025-10-17 会话记录

- 背景：用户确认项目框架已就绪，约定由 AI 维护后端与前端 README 的结构说明，并在每次会话后更新 `configs/progress.md`。
- 本次变更：
  - 更新 `backend/README.md` 增加“结构快照（自动维护）”。
  - 更新 `frontend/README.md` 增加“结构快照（自动维护）”。
  - 未变更代码逻辑，仅同步文档快照。
  - 新增前端页面与路由：
    - 页面：`LoginView.vue`（登录）、`ProjectSelectView.vue`（项目选择）、`DashboardView.vue`（仪表盘/表选择+状态）、`DataEntryView.vue`（数据填报）。
    - 路由：`/login`、`/projects`、`/projects/:projectKey/sheets`、`/projects/:projectKey/sheets/:sheetKey/fill`。
    - 服务封装：`src/daily_report_25_26/services/api.js` 实现 `/template`、`/submit`、`/query` 三接口调用。
    - 常量：`src/daily_report_25_26/constants/sheets.js` 维护临时表清单（后续由后端枚举接口替换）。
- 受限与偏差（留痕）：
  - Serena 工具不可用，依据全局指南 3.9 触发条件降级到 Codex CLI：
    - 使用安全读取（仅列出目录结构）与 `apply_patch` 写入文档；未进行任何破坏性操作。
  - 影响范围：文档类文件，便于协作与可审计。
  - 回滚思路：如需回退，恢复 README 与 progress 至上一版本文本即可。
- 涉及文件：
  - `backend/README.md`
  - `frontend/README.md`
  - `configs/progress.md`
  - `frontend/src/daily_report_25_26/constants/sheets.js`
  - `frontend/src/daily_report_25_26/services/api.js`
  - `frontend/src/daily_report_25_26/pages/LoginView.vue`
  - `frontend/src/daily_report_25_26/pages/ProjectSelectView.vue`
  - `frontend/src/daily_report_25_26/pages/DashboardView.vue`
  - `frontend/src/daily_report_25_26/pages/DataEntryView.vue`
  - `frontend/src/router/index.js`

### 2025-10-17 20:02 环境事件（留痕）
- 现象：执行 `docker compose up --build` 报错：`unable to get image 'postgres:15-alpine'`，并提示 `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.`
- 结论：Windows 环境下 Docker Desktop 未运行/未连接 Linux 引擎（或未安装/未启用 WSL2）。Compose 的 `version` 字段提示为过时警告，不影响本次错误本质。
- 处置建议：
  1) 启动 Docker Desktop，并确保“Use the WSL 2 based engine”已勾选；“Settings > Resources > WSL Integration”中为默认发行版开启集成；确保处于“Linux containers”模式。
  2) 验证：`docker version`、`docker info` 正常返回；随后执行 `docker pull postgres:15-alpine` 预拉镜像；再执行 `docker compose up --build`。
  3) 如 `wsl -l -v` 显示无 Linux 发行版，请安装并将默认版本设为 WSL2，重启 Docker Desktop 后重试。
- 回滚/旁路：无代码改动，无需回滚；待 Docker Desktop 可用后再执行 Compose。
- 后续事项：如需消除 `version` 过时警告，可在确认环境稳定后由我移除 `docker-compose.yml` 顶部 `version` 键；不影响功能。

### 2025-10-17 UI 美化（留痕）
- 目标：在不引入新依赖的前提下，美化登录、项目选择、仪表盘与填报页面，统一配色、按钮、卡片、表格与徽章样式；本次迭代为“蓝色商务风”。
- 动作：
  - 新增统一头部组件：`frontend/src/daily_report_25_26/components/AppHeader.vue`，带品牌与登出入口。
  - 强化主题样式：`frontend/src/daily_report_25_26/styles/theme.css` 改为商务蓝配色，新增进度条、卡片标题、按钮风格等；表格头渐变、阴影与圆角调整。
  - 页面接入：项目选择、仪表盘、数据填报三页引入 `<AppHeader />`；四页均引入主题样式。
  - 仪表盘增强：新增进度条显示填报进度（已填/总数）。
  - 新增面包屑导航：`frontend/src/daily_report_25_26/components/Breadcrumbs.vue`，并接入项目选择、仪表盘、数据填报页面；支持点击返回到对应层级。
  - 数据填报页新增显眼返回：在 `DataEntryView.vue` 顶部加入“← 返回仪表盘”按钮，便于高频返回。
- 影响范围：前端样式与模板结构（无业务逻辑变更）。
- 回滚思路：移除 `<AppHeader />` 引用及 `theme.css` 的改动，恢复旧结构即可。
### 2025-10-17 前端集成 RevoGrid（留痕）
- 目标：使用 RevoGrid 渲染数据填报表格，支持就地编辑、性能更优。
- 动作：
  - 在 `frontend/package.json` 增加依赖：`revo-grid`。
  - 在 `DataEntryView.vue` 引入 `revo-grid` 组件与样式，构造 `gridColumns`/`gridSource`，并监听 `afteredit/afterEdit` 事件同步数据。
  - 提交时从 `gridSource` 汇总单元格，按接口规范构造 `cells`。
- 影响范围：前端数据填报页的表格渲染方式；业务接口不变。
- 回滚思路：删掉 `revo-grid` 相关导入与模板，恢复为原来的 `<table>` 渲染；或移除依赖并重新安装。
- 追加修正：npm 安装失败是因包名错误（`revo-grid` 不存在）。已改为 `@revolist/revogrid` 并更新导入路径为 `@revolist/revogrid/dist/revogrid.js` 与 `@revolist/revogrid/dist/revogrid.css`。
### 2025-10-17 路由精简（留痕）
- 目标：简化数据填报页路由，去掉 `/fill` 与 `biz_date` 查询参数，采用更直观的层级。
- 变更：
  - 路由：`/projects/:projectKey/sheets/:sheetKey`（替代原 `/projects/:projectKey/sheets/:sheetKey/fill`）。
  - 导航调整：
    - Dashboard → DataEntry 链接移除查询参数。
    - DataEntry 顶部返回仪表盘不再附带 `biz_date` 查询参数。
    - 面包屑生成逻辑同步，无 `/fill`。 
- 影响范围：前端路由与页面跳转；接口与业务逻辑不变。
- 回滚思路：将上述改动恢复为带 `/fill` 的旧路径并恢复相关跳转参数。
### 2025-10-17 后端路由统一（留痕）
- 目标：按约定统一到 `/api/v1/projects/daily_report_25_26`，并先创建三大接口占位，待数据格式对齐后补齐实现。
- 动作：
  -（合并调整）占位路由现统一至 `backend/api/v1/daily_report_25_26.py`：
    - `GET /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/template`
    - `POST /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/submit`
    - `POST /api/v1/projects/daily_report_25_26/sheets/{sheet_key}/query`
  - 重写 `backend/api/v1/routes.py`，统一 include 到 `/projects/daily_report_25_26` 前缀。
- 影响范围：仅新增/调整后端路由占位，不含业务逻辑；前端可先仅用于连通性验证。
- 回滚思路：恢复旧版 `routes.py` 并移除新增项目路由文件即可。
### 2025-10-17 仪表盘表清单联动（留痕）
- 目标：前端仪表盘访问时向后端请求表清单，后端从挂载目录 `backend_data/数据结构_基本指标表.json` 读取并整理，返回 {sheet_key: {单位名, 表名}} 结构。
- 后端：
  - `GET /api/v1/projects/daily_report_25_26/sheets`（文件：`backend/api/v1/daily_report_25_26.py`）。
  - 仅聚焦 `backend_data/数据结构_基本指标表.json`（不再兜底其它 JSON）；字段名容错（单位名/表名）。
  - 重要决策：不再改写源 `sheet_key`，严格按文件原键名返回（不进行 `_constant_sheet` → `_sheet` 的规范化）。
  - 修复路径解析：从后端文件定位到项目根目录 `.../phoenix`（`parents[3]`），确保读取的是 `phoenix/backend_data` 而非 `phoenix/backend/backend_data`。
- 前端：
  - `services/api.js` 新增 `listSheets(projectKey)`。
  - `DashboardView.vue` 改为在 `onMounted` 调用 `listSheets` 渲染单位名/表名，并保留“去填报”跳转；增加错误提示，当文件不存在时给出友好文案。
- 影响范围：仪表盘数据来源与后端只读接口；业务写入不受影响。
- 回滚思路：前端改回使用本地常量 `constants/sheets.js`；后端保留只读接口不影响其他功能。
- 项目键统一对齐（补充）：
  - 前端项目选择页使用 `project_key = daily_report_25_26`，与后端统一前缀 `/api/v1/projects/daily_report_25_26` 保持一致，避免 404。
### 2025-10-17 前端路由与后端 API 映射（留痕）

- 会话目标：梳理前端主要页面/路由，并给出与之对应的后端 API 列表与路径前缀，确保前后端命名与接口保持一致。
- 证据来源：
  - 前端：`frontend/src/router/index.js`、`frontend/src/daily_report_25_26/services/api.js`
  - 后端：`backend/main.py`、`backend/api/v1/routes.py`、`backend/api/v1/daily_report_25_26.py`
- 关键发现：
  - API 前缀：`/api/v1`
  - 项目路径当前实现固定为：`/projects/daily_report_25_26`，与项目代号一致；前端以动态 `:projectKey` 传参已适配。

前端主要路由（name → path → 组件）：
- login → `/login` → `LoginView.vue`
- projects → `/projects` → `ProjectSelectView.vue`
- dashboard → `/projects/:projectKey/sheets` → `DashboardView.vue`
- data-entry → `/projects/:projectKey/sheets/:sheetKey` → `DataEntryView.vue`

对应后端 API（完整路径均以 `/api/v1` 为前缀）：
- 系统连通：`GET /api/v1/ping`
- 项目连通：`GET /api/v1/projects/daily_report_25_26/ping`
- 列表表清单：`GET /api/v1/projects/{project_key}/sheets`（当前实现为固定 `daily_report_25_26`）
- 获取模板：`GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template`
- 提交数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit`
- 查询数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query`

请求/响应（与规范一致，后端目前为占位实现）：
- 模板响应字段：`sheet_key, sheet_name, columns, rows`
- 提交请求字段：`project_key, sheet_key, sheet_name, biz_date, cells[]`
- 查询请求字段：`project_key, sheet_key, biz_date`

偏差与回滚预案：
- 偏差：无（项目路径与代号统一为 `daily_report_25_26`）。
- 影响：仅影响 URL 可读性，不影响前后端联调（前端以路由参数传入）。
- 回滚/对齐思路：后端在路由汇总处支持参数化 `{project_key}` 或新增别名挂载；在变更前保留既有路径以平滑迁移。

本次变更：
- 未修改任何业务代码；仅更新文档（本记录、backend/frontend README 路由与结构段落）。
### 2025-10-17 Dashboard 页面访问链路复盘（留痕）

- 路由守卫：`frontend/src/router/index.js:39` 检查 `localStorage['phoenix_token']`；无 token 且目标页非 `login` 时重定向登录；有 token 且访问 `login` 时跳转项目页。
- 进入页面：命中路由 `/projects/:projectKey/sheets`（`frontend/src/router/index.js:21`），加载 `DashboardView.vue`。
- 初始化拉取：`onMounted` 调用 `listSheets(projectKey)`（`frontend/src/daily_report_25_26/pages/DashboardView.vue:71,73`）→ 发起 `GET /api/v1/projects/{projectKey}/sheets`（`frontend/src/daily_report_25_26/services/api.js:14-17`）。
- 后端响应：由 `backend/api/v1/routes.py:24` 挂载到 `daily_report_25_26.py:list_sheets_placeholder`，读取 `backend_data/数据结构_基本指标表.json` 构造 `{sheet_key: {单位名, 表名}}` 返回。
- 前端分组渲染：将对象转数组并赋值 `sheets`（`:74,79`），按“单位名” `computed` 分组（`:86`），模板 `v-for` 渲染卡片与清单（`:22,25`）。
- 进度计算：循环调用 `refreshStatus(s)`（`:58`）→ 先 `GET /template`（`:62`）计算总单元格数（列索引≥2 × 行数，`:63-64`），再 `POST /query`（`:66`）统计已填单元格（`:67-68`），用于展示状态/百分比。
 - 现状提示：`/template` 与 `/query` 为占位实现（`backend/api/v1/daily_report_25_26.py`），可能导致进度为 0% 或运行时报错（`tpl.columns` 缺失）；表清单缺失则前端显示错误占位（`:81`）。

### 2025-10-17 修复 list_sheets 读取结构（留痕）

- 问题：后端 `list_sheets` 仅按“字典结构”解析 JSON；`backend_data/数据结构_基本指标表.json` 实际为“对象数组”，导致返回 500/404，前端提示“无法获取表清单…”。
- 处理：
  - 兼容两种结构：若为 `dict`，以键为 `sheet_key`；若为 `list`，以中文“表名”作为 `sheet_key`（前端通过 `encodeURIComponent` 已兼容中文路径）。
  - 代码位置：`backend/api/v1/daily_report_25_26.py:list_sheets_placeholder`。
- 影响：前端可正常拉取表清单并渲染分组；占位接口仍不影响后续 `template/query` 的替换实现。

### 2025-10-17 API 文件合并（留痕）

- 变更背景：按用户要求，去除多余文件命名差异，将 `projects_daily_report_25_26.py` 内容整合至 `daily_report_25_26.py`，统一作为本项目 API 文件。
- 具体修改：
  - 合并占位接口（sheets/template/submit/query）到 `backend/api/v1/daily_report_25_26.py`。
  - 更新 `backend/api/v1/routes.py` 导入：改为 `from .daily_report_25_26 import router as project_router`。
  - 删除 `backend/api/v1/projects_daily_report_25_26.py`。
- 路由前缀：保持不变（`/api/v1/projects/daily_report_25_26`），前端无需改动。
- 前端/后端调试留痕（临时开关）
  - （已于同日“调试代码回收”步骤清理）后端临时调试写入：`backend/api/v1/daily_report_25_26.py` 引入 `_dbg_write`，在 `/sheets`、`/template`、`/query`、`/debug/frontend` 中写入 `phoenix/error.md` 与 `poenix/error.md`。
  - （已清理）前端上报：`frontend/src/daily_report_25_26/services/debug.js` 提供 `logDebug`；`DashboardView.vue` 中在 `onMounted`、`listSheets` 成功/失败、`refreshStatus` 阶段插桩。
  - （已删除）临时日志文件：`error.md`（根目录）及 `poenix/error.md`（容错拼写）。
  - 回收建议：问题定位完成后，可移除上述插桩与日志文件。← 已执行，详见下文。

### 2025-10-17 调试代码回收（留痕）

- 已完成占位调试的清理：
  - 删除 `backend/api/v1/daily_report_25_26.py` 中 `_dbg_write`、调试路由与日志写入，恢复精简实现。
  - 移除前端 `logDebug` 上报（删除 `services/debug.js` 和 Dashboard 内相关调用）。
  - 删除临时日志文件 `error.md`、`poenix/error.md`。
- 若后续需要排障，可通过版本控制手动恢复上述调试工具。

### 2025-10-17 Dashboard 刷新按钮调整（留痕）

- UI：移除每行表项上的 “刷新状态” 按钮，改为顶部统一按钮，避免重复渲染控件。
- 行为：新增 `refreshAll()`（`DashboardView.vue`），循环调用 `refreshStatus`；在 `onMounted` 后自动拉取并可通过顶部按钮手动刷新。
- 影响：界面更简洁，刷新逻辑一致；若后续需要逐表刷新，可按需在 `refreshStatus` 基础上扩展。

### 2025-10-17 项目路由重命名（留痕）

- 需求：将 Dashboard 访问地址从 `/projects/:projectKey/dashboard` 调整为 `/projects/:projectKey/sheets`，避免与数据填报子路由混淆。
- 代码：`frontend/src/router/index.js`、`ProjectSelectView.vue`、`DataEntryView.vue`、`components/Breadcrumbs.vue` 全部改用新路径；保持路由 name 不变（仍为 `dashboard`）。
- 文档：`frontend/README.md`、`configs/logs.md`、`configs/progress.md` 已同步更新描述。
- 影响：原路径将不再匹配，历史书签需更新；页面功能与组件装载逻辑保持不变。

### 2025-10-17 本地开发 API 基址统一（留痕）

- 目标：解决 Vite 开发服务器访问 `/api/*` 落到自身导致 404 的问题，使本地与 Docker/Nginx 行为一致。
- 变更：
  - `frontend/src/daily_report_25_26/services/api.js` 引入 `resolveApiPath`，统一拼接 `VITE_API_BASE`，默认保留相对路径。
  - `frontend/src/daily_report_25_26/services/debug.js` 复用 `resolveApiPath`，确保调试日志同源。
  - 新增 `frontend/.env.development`，默认将 `VITE_API_BASE` 指向 `http://127.0.0.1:8000`，本地 `npm run dev` 即可直连后端。
- 后续：如需切换到 Docker Compose，可在环境变量中调整 `VITE_API_BASE`，保持统一配置。问题定位结束时记得清理临时调试日志与插桩。
 - 追加修复：为跨域访问配置 CORS（`backend/main.py`），默认允许 `localhost/127.0.0.1:5173`，并支持通过环境变量 `PHOENIX_CORS_ORIGINS` 自定义域名，解决浏览器直接访问后端时的跨域报错。

### 2025-10-19 看板页面命名与路径同步（留痕）

- 背景：前端路由使用 `/projects/:projectKey/sheets`，需保持组件命名一致。
- 变更内容：
  - `frontend/src/daily_report_25_26/pages/Sheets.vue`：以新文件取代 `DashboardView.vue`，结构与逻辑沿用原实现，并恢复单位卡片 + 状态进度的卡片式布局。
  - `frontend/src/router/index.js`：懒加载路径更新为 `pages/Sheets.vue`。
  - `frontend/README.md`、`backend/README.md`：同步更新命名描述。
- 影响范围：前端页面引用路径，后端无变动。
- 回滚方案：如需恢复旧命名，重新创建 `DashboardView.vue` 并调整引用路径即可。
