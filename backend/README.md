# 后端说明（FastAPI + 版本化路由）

本目录为 Phoenix 后端服务的当前骨架，采用“一个入口 + 多个路由模块”的结构：

- `main.py`：FastAPI 应用入口（创建 `app`，挂载 `/api/v1` 前缀，提供 `GET /healthz`）。
- `api/v1/`：v1 版本接口集合。
  - `routes.py`：v1 总路由（汇总与转发其他子路由）。
  - `daily_report_25_26.py`：项目接口集合（包含 `ping`、`sheets`、`template/submit/query` 占位接口）。
- `models/`、`schemas/`、`services/`：预留用于 ORM、Pydantic 与业务服务分层。

注意
- 当前已清理示例型实现与内存存储，仅保留连通性接口（`/healthz` 与 `/api/v1/*/ping`）。
- 后续你将按需新增实际业务 API，我们在对应模块内扩展即可。

---

## 使用 Docker（开发环境）

在仓库根目录：
```
docker compose up -d --build
```

说明（dev 标准）：
- 数据库：PostgreSQL 通过命名卷 `pg_data` 持久化数据。
- 后端：使用 uvicorn `--reload` 热更新；容器 `/app` 绑定挂载项目根目录，`/app/data` 绑定 `./backend_data`。
- 前端：使用 Node 容器跑 Vite 开发服务器（端口 5173），支持热更新。

访问：
- 后端健康检查：`http://127.0.0.1:8000/healthz`
- 后端连通性：`http://127.0.0.1:8000/api/v1/ping`
- 项目前缀连通性：`http://127.0.0.1:8000/api/v1/daily_report_25_26/ping`
- 前端（Vite）：`http://127.0.0.1:5173/`

---

## 本地开发（可选）

不使用 Docker 时：
```
python -m pip install fastapi "uvicorn[standard]"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 开发约定
- 命名统一：Python `snake_case`；路径字段与前端保持一致（如 `project_key`）。
- 目录约束：仅在允许目录（`backend/api|models|schemas|services`）内新增/修改代码。
- 多项目扩展：按照 `api/v1/<project_name>.py` 增加项目级命名空间，或在通用路由内以参数化区分。
- 数据与配置：容器内 `/app/data` 映射宿主 `./backend_data`（绑定挂载）。
## 结构快照（自动维护）
更新时间：2025-10-17

- 根目录
  - `Dockerfile`
  - `main.py`
  - `README.md`
  - `__init__.py`
- 目录
  - `api/`
    - `__init__.py`
    - `v1/`
      - `__init__.py`
      - `routes.py`  ← 统一挂载 `/api/v1/projects/daily_report_25_26`
      -（已合并）相关占位接口现位于 `daily_report_25_26.py`
  - `models/`
    - `__init__.py`
  - `schemas/`
    - `__init__.py`
  - `services/`
    - `__init__.py`

说明：以上为当前后端目录的真实结构快照，供前后端协作与定位参考；如有结构调整，将在后续会话中自动更新。
## 路由一览（当前实现）

- 统一前缀：`/api/v1`
- 健康检查：`GET /api/v1/healthz`
- 系统连通：`GET /api/v1/ping`（`backend/api/v1/routes.py`）
- 项目连通：`GET /api/v1/projects/daily_report_25_26/ping`（`backend/api/v1/daily_report_25_26.py`）
- 列出表清单：`GET /api/v1/projects/{project_key}/sheets`（当前实现固定为 `daily_report_25_26`，见 `backend/api/v1/daily_report_25_26.py`）
- 获取模板：`GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template`
- 提交数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit`
- 查询数据：`POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query`

说明：项目路径与项目代号统一为 `daily_report_25_26`，前后端一致。
