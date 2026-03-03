时间：2026-03-03。
问题：前端登录接口 POST /api/v1/auth/login 返回 404。
定位：backend/main.py 在导入 .api.v1.routes 失败时会将 v1_router 置空，导致 /api/v1 全部不可用。容器日志显示失败根因为 NameError: name 'Field' is not defined，源于 backend/projects/daily_report_25_26/api/legacy_full.py 中 AiSettingsPayload 使用 Field(default_factory=list) 但未导入 Field。
修复：将 pydantic 导入改为 from pydantic import BaseModel, Field, ValidationError。
验证：调用 POST http://127.0.0.1:8001/api/v1/auth/login（空JSON体）返回 422，说明路由已挂载并进入参数校验，不再是 404。
影响文件：backend/projects/daily_report_25_26/api/legacy_full.py；文档同步 configs/progress.md、backend/README.md、frontend/README.md。