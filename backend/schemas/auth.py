"""
认证与流程状态相关的 Pydantic 模型。
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, constr


class SheetRuleModel(BaseModel):
    mode: str = Field(default="all")
    sheets: List[str] = Field(default_factory=list)


class ActionFlagsModel(BaseModel):
    can_submit: bool = False
    can_approve: bool = False
    can_publish: bool = False


class PermissionsModel(BaseModel):
    page_access: List[str] = Field(default_factory=list)
    sheet_rules: Dict[str, SheetRuleModel] = Field(default_factory=dict)
    units_access: List[str] = Field(default_factory=list)
    actions: ActionFlagsModel = Field(default_factory=ActionFlagsModel)


class UserInfo(BaseModel):
    username: str
    group: str
    unit: Optional[str] = None
    hierarchy: int = 0


class LoginRequest(BaseModel):
    username: constr(min_length=1, strip_whitespace=True)
    password: constr(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int
    user: UserInfo
    permissions: PermissionsModel


class SessionResponse(BaseModel):
    user: UserInfo
    permissions: PermissionsModel


class LogoutResponse(BaseModel):
    ok: bool = True


class WorkflowApproveRequest(BaseModel):
    unit: constr(min_length=1, strip_whitespace=True)


class WorkflowPublishRequest(BaseModel):
    confirm: bool = True


class WorkflowUnitStatus(BaseModel):
    unit: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class WorkflowPublishStatus(BaseModel):
    status: str
    published_by: Optional[str] = None
    published_at: Optional[datetime] = None


class WorkflowStatusResponse(BaseModel):
    project_key: str
    biz_date: date
    units: List[WorkflowUnitStatus] = Field(default_factory=list)
    publish: WorkflowPublishStatus
