# 后端说明（FastAPI）

该目录存放 Phoenix 项目的后端代码，采用「FastAPI + 版本化路由」的结构：

- `main.py`：FastAPI 应用入口，挂载 `/api/v1` 前缀并提供 `/healthz`。 
- `api/v1/routes.py`：顶层路由调度，将不同项目的路由注册到 `/api/v1/projects/*`。 
- `api/v1/daily_report_25_26.py`：`daily_report_25_26` 项目的业务路由，实现 `ping`、`sheets`、`template/submit/query` 等接口。 
- `models/`、`schemas/`、`services/`：预留 ORM、Pydantic、领域服务层。 

## 运行方式

Docker 开发环境：

```bash
docker compose up -d --build
```

本地直接运行：

```bash
python -m pip install fastapi "uvicorn[standard]"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

常用访问：

- 健康检查：`http://127.0.0.1:8000/healthz`
- 系统心跳：`http://127.0.0.1:8000/api/v1/ping`
- 项目心跳：`http://127.0.0.1:8000/api/v1/daily_report_25_26/ping`

## 目录快照（自动维护）

更新时间：2025-10-20

- 目录
  - `Dockerfile`
  - `main.py`
  - `README.md`
  - `api/`
    - `__init__.py`
    - `v1/`
      - `__init__.py`
      - `routes.py`（统一前缀 `/api/v1`）
      - `daily_report_25_26.py`（项目路由）
- `models/`、`schemas/`、`services/`（占位）
- 本次会话未调整后端代码结构，维持现状以与前端更新保持同步记录。

## 接口路线图（2025-10-19）

- `GET /api/v1/ping`：系统级心跳。
- `GET /api/v1/projects/{project_key}/sheets`：读取 `backend_data` 中的模板清单。返回字段包含：
  - `单位名`、`表名`：兼容旧有前端；
  - `unit_name`、`sheet_name`：便于英文字段访问。
- `GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template`：
  - 从候选文件（默认 `数据结构_基本指标表.json`、`数据结构_常量指标表.json`）读取指定模板；
  - 自动追加两列日期，返回结构为 `sheet_key/sheet_name/unit_name/columns/rows`；
  - `columns` 形如 `[项目, 计量单位, <今日（东八区）>, <去年同日>]`。
- `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/submit`：占位。
- `POST /api/v1/projects/{project_key}/sheets/{sheet_key}/query`：占位。

## 模板处理规则

1. 优先读取 `backend_data/数据结构_基本指标表.json`，若未命中则尝试 `数据结构_常量指标表.json`。
2. 查找到的模板字段会进行以下标准化：
   - 提取单位名、表名（支持多种键名）；
   - `columns` 自动补齐日期列（今日、去年同日）；
   - `rows` 兼容任意长度的数组，逐行按列表返回。
3. 当模板缺少 `列名` 或 `数据` 字段时，接口返回 422 以提示数据管理员处理。

## CORS 设置

- 默认允许 `http://localhost:5173`、`http://127.0.0.1:5173`。
- 通过环境变量 `PHOENIX_CORS_ORIGINS`（逗号分隔）扩展来源，例如：

```bash
PHOENIX_CORS_ORIGINS=http://localhost:5173,http://my-host
```

- Docker Compose 场景下，`backend` 服务会自动挂载 `./backend_data` 至容器 `/app/data`，保持模板与日志可追溯。
