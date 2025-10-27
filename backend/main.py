"""
FastAPI 应用入口

说明：
- 提供最小可运行服务与健康检查接口；
- 挂载 v1 版本的业务路由（保持与 AGENTS.md 规范一致的前缀 `/api/v1`）。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

try:
    # 延迟导入以避免循环依赖
    from .api.v1.routes import router as v1_router
except Exception as e:  # 保底避免导入错误影响应用启动
    logging.exception("Failed to import v1 routes: %s", e)
    v1_router = None


APP_NAME = "Phoenix Backend"
API_PREFIX = "/api"
API_VERSION = "v1"


def create_app() -> FastAPI:
    """创建并返回 FastAPI 应用实例。"""
    app = FastAPI(title=APP_NAME, version=API_VERSION)

    # 启动时输出关键信息，便于排障 DATA_DIRECTORY 与路由挂载
    try:
        from .config import DATA_DIRECTORY
        data_dir = str(DATA_DIRECTORY)
    except Exception:
        data_dir = "<unresolved>"

    # 健康检查（K8s/Compose 均可用）
    @app.get("/healthz", summary="存活检查", tags=["system"])
    def healthz():
        return {"ok": True, "app": APP_NAME, "version": API_VERSION, "data_directory": data_dir}

    # CORS：统一本地/容器跨域访问（默认允许 localhost/127.0.0.1）
    cors_origins_env = os.getenv("PHOENIX_CORS_ORIGINS", "")
    if cors_origins_env:
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    else:
        allowed_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost",
            "http://127.0.0.1",
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载 v1 路由前缀：/api/v1
    if v1_router is not None:
        app.include_router(v1_router, prefix=f"{API_PREFIX}/{API_VERSION}")
        logging.info("Mounted v1 router at %s/%s", API_PREFIX, API_VERSION)
    else:
        logging.warning("v1 router not mounted (import failed). Endpoints under /api/v1 are unavailable.")

    return app


app = create_app()


if __name__ == "__main__":
    # 便于本地直接运行：python -m backend.app.main
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
