"""项目路由注册表。"""

from __future__ import annotations

from typing import Dict, Optional

from backend.projects.daily_report_25_26.api.router import (
    public_router as daily_report_public_router,
    router as daily_report_router,
)


PROJECT_ROUTER_REGISTRY: Dict[str, Dict[str, Optional[object]]] = {
    "daily_report_25_26": {
        "router": daily_report_router,
        "public_router": daily_report_public_router,
    },
}
