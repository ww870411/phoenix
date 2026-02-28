# -*- coding: utf-8 -*-
"""
monthly_data_show 工作台接口。
"""

from __future__ import annotations

import csv
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from backend.projects.monthly_data_show.services.extractor import (
    ALLOWED_FIELDS,
    BLOCKED_COMPANIES,
    DEFAULT_SOURCE_COLUMNS,
    extract_rows,
    filter_fields,
    get_default_constant_rules,
    get_company_options,
    normalize_constant_rules,
)

PROJECT_KEY = "monthly_data_show"
ALLOWED_EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm"}

router = APIRouter(tags=["monthly_data_show"])
public_router = APIRouter(tags=["monthly_data_show"])


class InspectResponse(BaseModel):
    ok: bool
    project_key: str
    companies: List[str]
    blocked_companies: List[str]
    fields: List[str]
    default_selected_fields: List[str]
    source_columns: List[str]
    default_selected_source_columns: List[str]
    constants_enabled_default: bool
    constant_rules: List[dict]


def _ensure_allowed_excel_file(filename: str) -> None:
    suffix = Path(str(filename or "")).suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_EXCEL_SUFFIXES))
        raise HTTPException(status_code=422, detail=f"仅支持以下文件格式：{allowed}")


def _cleanup_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


@router.get("/monthly-data-show/ping", summary="monthly_data_show 连通性检查")
def ping_monthly_data_show():
    return {"ok": True, "project_key": PROJECT_KEY, "message": "monthly_data_show ready"}


@router.post("/monthly-data-show/inspect", response_model=InspectResponse, summary="上传文件并读取可选口径与字段")
async def inspect_monthly_data_show_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    _ensure_allowed_excel_file(file.filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")
    try:
        companies = get_company_options(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析文件失败：{exc}") from exc
    return InspectResponse(
        ok=True,
        project_key=PROJECT_KEY,
        companies=companies,
        blocked_companies=sorted(BLOCKED_COMPANIES),
        fields=list(ALLOWED_FIELDS),
        default_selected_fields=list(ALLOWED_FIELDS),
        source_columns=list(DEFAULT_SOURCE_COLUMNS),
        default_selected_source_columns=list(DEFAULT_SOURCE_COLUMNS),
        constants_enabled_default=True,
        constant_rules=get_default_constant_rules(),
    )


@router.post("/monthly-data-show/extract-csv", summary="按口径与字段提取并下载 CSV")
async def extract_monthly_data_show_csv(
    file: UploadFile = File(...),
    companies: List[str] = Form(default=[]),
    fields: List[str] = Form(default=[]),
    source_columns: List[str] = Form(default=[]),
    constants_enabled: bool = Form(default=False),
    constant_rules_json: str = Form(default="[]"),
):
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    _ensure_allowed_excel_file(file.filename)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")

    try:
        parsed_rules = json.loads(constant_rules_json or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"常量配置格式错误：{exc}") from exc

    normalized_rules = normalize_constant_rules(parsed_rules if isinstance(parsed_rules, list) else [])

    try:
        extracted_rows, _stats = extract_rows(
            file_bytes=content,
            filename=file.filename,
            selected_companies=companies or None,
            selected_source_columns=source_columns or None,
            constants_enabled=bool(constants_enabled),
            constant_rules=normalized_rules,
        )
        csv_rows = filter_fields(extracted_rows, fields)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"提取 CSV 失败：{exc}") from exc

    if not csv_rows:
        raise HTTPException(status_code=422, detail="未提取到数据，请检查所选口径与文件内容")

    selected_fields = [field for field in ALLOWED_FIELDS if field in set(fields)] or list(ALLOWED_FIELDS)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile(prefix="monthly_data_show_", suffix=".csv", delete=False, mode="w", encoding="utf-8-sig", newline="") as tmp:
        writer = csv.DictWriter(tmp, fieldnames=selected_fields)
        writer.writeheader()
        writer.writerows(csv_rows)
        csv_path = tmp.name

    download_name = f"monthly_data_show_extract_{timestamp}.csv"
    return FileResponse(
        path=csv_path,
        media_type="text/csv; charset=utf-8",
        filename=download_name,
        background=BackgroundTask(_cleanup_file, csv_path),
    )
