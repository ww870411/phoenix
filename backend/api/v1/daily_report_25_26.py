"""
daily_report_25_26 项目级路由（v1）

说明：
- 作为项目隔离的路径前缀：`/api/v1/daily_report_25_26`；
- 后续可在此处实现 template/submit/query 等接口，形成与通用路由并存的“项目别名”入口；
- 便于前端以稳定路径访问当前项目，同时保留多项目扩展能力。
"""

from fastapi import APIRouter


router = APIRouter()


@router.get("/ping", summary="daily_report_25_26 连通性测试", tags=["daily_report_25_26"])
def ping_daily_report():
    """保留最小可用连通性接口。其他业务接口由后续实现。"""
    return {"ok": True, "project": "daily_report_25_26", "message": "pong"}
