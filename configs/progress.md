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
- 决策：后端与前端统一使用 `project_key = 'daily_report_25_26'`（偏离原文档中的 `25-26daily_report`，按用户最新要求执行）。
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

回滚思路
- 前端目录层级：若需回滚为 `frontend/src/projects/25-26daily_report/`，可整体移动目录并在路由中调整导入路径与基路径。
- project_key 命名：若需回退为 `25-26daily_report`，只需将 `frontend/src/daily_report_25_26/constants/index.js` 中的 `PROJECT_KEY` 改回，并同步前端 API 调用参数与后端常量。
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
