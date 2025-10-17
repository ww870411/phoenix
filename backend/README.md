# 后端说明（FastAPI + 版本化路由）

本目录为 Phoenix 后端服务的当前骨架，采用“一个入口 + 多个路由模块”的结构：

- `main.py`：FastAPI 应用入口（创建 `app`，挂载 `/api/v1` 前缀，提供 `GET /healthz`）。
- `api/v1/`：v1 版本接口集合。
  - `routes.py`：v1 总路由（汇总与转发其他子路由）。
  - `daily_report_25_26.py`：项目级命名空间（仅保留 `GET /api/v1/daily_report_25_26/ping`）。
- `models/`、`schemas/`、`services/`：预留用于 ORM、Pydantic 与业务服务分层。

注意
- 当前已清理示例型实现与内存存储，仅保留连通性接口（`/healthz` 与 `/api/v1/*/ping`）。
- 后续你将按需新增实际业务 API，我们在对应模块内扩展即可。

---

## 运行与验证

安装依赖：
```
python -m pip install fastapi "uvicorn[standard]"
```

启动（在项目根目录执行）：
```
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

或在 `backend/` 目录：
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

验证：
- `GET http://127.0.0.1:8000/healthz`
- `GET http://127.0.0.1:8000/api/v1/ping`
- `GET http://127.0.0.1:8000/api/v1/daily_report_25_26/ping`

---

## 开发约定
- 命名统一：Python `snake_case`；路径字段与前端保持一致（如 `project_key`）。
- 目录约束：仅在允许目录（`backend/api|models|schemas|services`）内新增/修改代码。
- 多项目扩展：按照 `api/v1/<project_name>.py` 增加项目级命名空间，或在通用路由内以参数化区分。

