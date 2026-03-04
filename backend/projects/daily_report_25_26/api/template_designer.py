from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path as ApiPath
from pydantic import BaseModel, Field

from backend.services.auth_manager import AuthSession, get_current_session
from backend.services.project_data_paths import resolve_project_config_path

PROJECT_KEY = "daily_report_25_26"
TEMPLATE_DESIGNER_PAGE_KEY = "template_designer"
STORE_FILENAME = "template_designer_templates.json"

router = APIRouter(tags=["daily_report_25_26"])
public_router = APIRouter(tags=["daily_report_25_26"])


class TemplateDesignerColumn(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, description="列键名")
    label: str = Field(..., min_length=1, max_length=100, description="列标题")
    value_type: Literal["num", "text"] = Field(default="text", description="值类型")
    required: bool = Field(default=False, description="是否必填")


class TemplateDesignerTemplatePayload(BaseModel):
    template_key: str = Field(..., min_length=1, max_length=120, description="模板唯一键")
    template_name: str = Field(..., min_length=1, max_length=120, description="模板名称")
    table_type: Literal["tall", "matrix"] = Field(default="tall", description="表类型")
    description: str = Field(default="", max_length=500, description="模板说明")
    columns: List[TemplateDesignerColumn] = Field(default_factory=list, description="列定义")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="行定义")
    meta: Dict[str, Any] = Field(default_factory=dict, description="扩展配置")


class TemplateDesignerTemplateRecord(TemplateDesignerTemplatePayload):
    status: Literal["draft", "published"] = Field(default="draft")
    version: int = Field(default=1, ge=1)
    created_at: str
    updated_at: str
    published_at: Optional[str] = None


class TemplateDesignerListItem(BaseModel):
    template_key: str
    template_name: str
    table_type: Literal["tall", "matrix"]
    status: Literal["draft", "published"]
    version: int
    updated_at: str


class TemplateDesignerListResponse(BaseModel):
    templates: List[TemplateDesignerListItem]


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _store_path() -> Path:
    return resolve_project_config_path(PROJECT_KEY, STORE_FILENAME)


def _ensure_access(session: AuthSession) -> None:
    page_access = session.get_project_page_access(PROJECT_KEY)
    actions = session.get_project_action_flags(PROJECT_KEY)
    if TEMPLATE_DESIGNER_PAGE_KEY not in page_access and not actions.can_manage_modularization:
        raise HTTPException(status_code=403, detail="当前账号无模板设计器访问权限")


def _load_store() -> Dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {
            "updated_at": _utc_now_iso(),
            "templates": [],
        }
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("模板存储文件格式错误")
        templates = data.get("templates")
        if not isinstance(templates, list):
            data["templates"] = []
        if "updated_at" not in data:
            data["updated_at"] = _utc_now_iso()
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"读取模板存储失败: {exc}") from exc


def _save_store(data: Dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _utc_now_iso()
    try:
        import json

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"保存模板存储失败: {exc}") from exc


def _normalize_template_payload(payload: TemplateDesignerTemplatePayload) -> Dict[str, Any]:
    data = payload.model_dump()
    data["template_key"] = data["template_key"].strip()
    data["template_name"] = data["template_name"].strip()
    return data


@router.get(
    "/template_designer/templates",
    response_model=TemplateDesignerListResponse,
    summary="模板设计器：获取模板列表",
)
def list_template_designer_templates(session: AuthSession = Depends(get_current_session)):
    _ensure_access(session)
    store = _load_store()
    templates = store.get("templates") or []
    items: List[TemplateDesignerListItem] = []
    for item in templates:
        if not isinstance(item, dict):
            continue
        try:
            items.append(
                TemplateDesignerListItem(
                    template_key=str(item.get("template_key") or ""),
                    template_name=str(item.get("template_name") or ""),
                    table_type=item.get("table_type") or "tall",
                    status=item.get("status") or "draft",
                    version=int(item.get("version") or 1),
                    updated_at=str(item.get("updated_at") or ""),
                )
            )
        except Exception:
            continue
    items.sort(key=lambda x: x.updated_at, reverse=True)
    return TemplateDesignerListResponse(templates=items)


@router.get(
    "/template_designer/templates/{template_key}",
    response_model=TemplateDesignerTemplateRecord,
    summary="模板设计器：获取单个模板详情",
)
def get_template_designer_template(
    template_key: str = ApiPath(..., description="模板键"),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_access(session)
    target = template_key.strip()
    store = _load_store()
    for item in store.get("templates") or []:
        if isinstance(item, dict) and str(item.get("template_key") or "").strip() == target:
            return TemplateDesignerTemplateRecord(**item)
    raise HTTPException(status_code=404, detail="模板不存在")


@router.post(
    "/template_designer/templates",
    response_model=TemplateDesignerTemplateRecord,
    summary="模板设计器：创建模板",
)
def create_template_designer_template(
    payload: TemplateDesignerTemplatePayload,
    session: AuthSession = Depends(get_current_session),
):
    _ensure_access(session)
    normalized = _normalize_template_payload(payload)
    if not normalized["template_key"]:
        raise HTTPException(status_code=400, detail="template_key 不能为空")
    store = _load_store()
    templates = store.get("templates") or []
    existed = next(
        (
            item
            for item in templates
            if isinstance(item, dict)
            and str(item.get("template_key") or "").strip() == normalized["template_key"]
        ),
        None,
    )
    if existed:
        raise HTTPException(status_code=409, detail="模板键已存在")
    now = _utc_now_iso()
    record = {
        **normalized,
        "status": "draft",
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "published_at": None,
    }
    templates.append(record)
    store["templates"] = templates
    _save_store(store)
    return TemplateDesignerTemplateRecord(**record)


@router.put(
    "/template_designer/templates/{template_key}",
    response_model=TemplateDesignerTemplateRecord,
    summary="模板设计器：更新模板",
)
def update_template_designer_template(
    payload: TemplateDesignerTemplatePayload,
    template_key: str = ApiPath(..., description="模板键"),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_access(session)
    target = template_key.strip()
    normalized = _normalize_template_payload(payload)
    if normalized["template_key"] != target:
        raise HTTPException(status_code=400, detail="路径 template_key 与 payload.template_key 不一致")
    store = _load_store()
    templates = store.get("templates") or []
    for idx, item in enumerate(templates):
        if not isinstance(item, dict):
            continue
        if str(item.get("template_key") or "").strip() != target:
            continue
        now = _utc_now_iso()
        record = {
            **item,
            **normalized,
            "updated_at": now,
        }
        templates[idx] = record
        store["templates"] = templates
        _save_store(store)
        return TemplateDesignerTemplateRecord(**record)
    raise HTTPException(status_code=404, detail="模板不存在")


@router.post(
    "/template_designer/templates/{template_key}/publish",
    response_model=TemplateDesignerTemplateRecord,
    summary="模板设计器：发布模板",
)
def publish_template_designer_template(
    template_key: str = ApiPath(..., description="模板键"),
    session: AuthSession = Depends(get_current_session),
):
    _ensure_access(session)
    target = template_key.strip()
    store = _load_store()
    templates = store.get("templates") or []
    for idx, item in enumerate(templates):
        if not isinstance(item, dict):
            continue
        if str(item.get("template_key") or "").strip() != target:
            continue
        now = _utc_now_iso()
        record = {
            **item,
            "status": "published",
            "version": int(item.get("version") or 1) + 1,
            "updated_at": now,
            "published_at": now,
        }
        templates[idx] = record
        store["templates"] = templates
        _save_store(store)
        return TemplateDesignerTemplateRecord(**record)
    raise HTTPException(status_code=404, detail="模板不存在")
