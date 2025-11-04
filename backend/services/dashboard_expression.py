# -*- coding: utf-8 -*-
"""
数据看板渲染引擎（初版）

职责：
- 读取数据看板配置（backend_data/数据结构_数据看板.json）
- 解析 show_date / push_date，处理默认日期回退逻辑
- 为 /dashboard API 提供统一的数据载体，后续可扩展数据库查询与指标计算

当前实现仍返回静态配置，未来会在 evaluate_dashboard 中补充数据库取数与表达式求值。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import HTTPException

from backend.config import DATA_DIRECTORY

DATA_ROOT = Path(DATA_DIRECTORY)
DASHBOARD_CONFIG_PATH = DATA_ROOT / "数据结构_数据看板.json"
DATE_CONFIG_PATH = DATA_ROOT / "date.json"


@dataclass
class DashboardResult:
    """标准化后的数据看板响应。"""

    project_key: str
    show_date: str
    push_date: str
    generated_at: str
    source: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_key": self.project_key,
            "show_date": self.show_date,
            "push_date": self.push_date,
            "generated_at": self.generated_at,
            "source": self.source,
            "data": self.data,
        }


def _read_json(path: Path) -> Any:
    """尝试使用常见编码读取 JSON 文件。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
        try:
            with path.open("r", encoding=enc) as fh:
                import json  # 局部导入，避免模块顶部不必要依赖

                return json.load(fh)
        except Exception:
            continue
    raise FileNotFoundError(f"无法读取 JSON：{path}")


def normalize_show_date(value: Optional[str]) -> str:
    """将 show_date 正规化为 YYYY-MM-DD 或空字符串。"""
    if value is None:
        return ""
    normalized = value.strip()
    if not normalized:
        return ""
    try:
        from datetime import datetime as _dt

        parsed = _dt.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="show_date 需为 YYYY-MM-DD 格式") from exc
    return parsed.isoformat()


def load_default_push_date() -> str:
    """从 date.json 中读取默认 push_date。"""
    if not DATE_CONFIG_PATH.exists():
        raise HTTPException(status_code=500, detail="日期配置文件不存在")
    try:
        payload = _read_json(DATE_CONFIG_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"读取日期配置失败: {exc}") from exc

    value = payload.get("set_biz_date")
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=500, detail="日期配置缺少 set_biz_date 或格式不正确")
    normalized = value.strip()
    try:
        from datetime import datetime as _dt

        parsed = _dt.strptime(normalized, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="日期配置 set_biz_date 需为 YYYY-MM-DD 格式") from exc
    return parsed.isoformat()


def load_dashboard_config() -> Dict[str, Any]:
    """读取数据看板配置。"""
    if not DASHBOARD_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="数据看板配置文件不存在")
    try:
        payload = _read_json(DASHBOARD_CONFIG_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"读取数据看板配置失败: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="数据看板配置需为对象类型")
    return payload


def evaluate_dashboard(project_key: str, show_date: str = "") -> DashboardResult:
    """核心入口：组装数据看板结果。目前直接返回配置，后续可在此进行数据库查询。"""
    normalized_show_date = normalize_show_date(show_date)
    push_date = normalized_show_date or load_default_push_date()
    payload = load_dashboard_config()

    # 当前阶段：仅替换配置中的展示日期字段
    data = dict(payload)
    data["展示日期"] = push_date

    generated_at = datetime.now().astimezone().isoformat()
    source = (
        str(DASHBOARD_CONFIG_PATH.relative_to(DATA_ROOT))
        if DASHBOARD_CONFIG_PATH.exists()
        else str(DASHBOARD_CONFIG_PATH)
    )

    return DashboardResult(
        project_key=project_key,
        show_date=normalized_show_date,
        push_date=push_date,
        generated_at=generated_at,
        source=source,
        data=data,
    )
