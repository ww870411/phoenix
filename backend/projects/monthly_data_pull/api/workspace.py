# -*- coding: utf-8 -*-
"""
monthly_data_pull 工作台接口。
"""

from __future__ import annotations

import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from backend.projects.monthly_data_pull.services.engine import (
    StoredFileInfo,
    analyze_mapping,
    execute_mapping,
    get_sheet_names,
)
from backend.services.project_data_paths import get_project_root

PROJECT_KEY = "monthly_data_pull"
ALLOWED_EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm"}

router = APIRouter(tags=["monthly_data_pull"])
public_router = APIRouter(tags=["monthly_data_pull"])


class UploadedFileInfo(BaseModel):
    bucket: str
    stored_name: str
    sheet: str


class ExecuteRequest(BaseModel):
    mapping_file: str
    src_files: Dict[str, UploadedFileInfo]
    tgt_files: Dict[str, UploadedFileInfo]


def _workspace_root() -> Path:
    return get_project_root(PROJECT_KEY)


def _default_directories() -> Dict[str, Path]:
    root = _workspace_root()
    return {
        "root": root,
        "mapping_rules_dir": root / "mapping_rules",
        "source_reports_dir": root / "source_reports",
        "target_templates_dir": root / "target_templates",
        "outputs_dir": root / "outputs",
    }


def _bucket_to_dir_map() -> Dict[str, str]:
    return {
        "mapping_rules": "mapping_rules_dir",
        "source_reports": "source_reports_dir",
        "target_templates": "target_templates_dir",
        "outputs": "outputs_dir",
    }


def _ensure_default_directories() -> Dict[str, str]:
    dirs = _default_directories()
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return {key: str(value) for key, value in dirs.items()}


def _resolve_bucket_dir(bucket: str) -> Path:
    bucket_key = str(bucket or "").strip()
    mapping = _bucket_to_dir_map()
    path_key = mapping.get(bucket_key)
    if not path_key:
        allowed = ", ".join(mapping.keys())
        raise HTTPException(status_code=422, detail=f"bucket 非法，允许值：{allowed}")
    all_dirs = _default_directories()
    target = all_dirs[path_key]
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_filename(name: str) -> str:
    normalized = Path(str(name or "").strip()).name
    if not normalized:
        return "unnamed_file"
    invalid_chars = '<>:"/\\|?*'
    safe = "".join("_" if ch in invalid_chars else ch for ch in normalized)
    return safe.strip() or "unnamed_file"


def _ensure_allowed_excel_file(filename: str) -> None:
    suffix = Path(str(filename or "")).suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_EXCEL_SUFFIXES))
        raise HTTPException(status_code=422, detail=f"仅支持以下文件格式：{allowed}")


def _ensure_unique_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    index = 1
    while True:
        renamed = directory / f"{stem}_{timestamp}_{index}{suffix}"
        if not renamed.exists():
            return renamed
        index += 1


def _build_file_info(path: Path) -> Dict[str, object]:
    stat = path.stat()
    return {
        "name": path.name,
        "size_bytes": stat.st_size,
        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def _resolve_file_path(bucket: str, stored_name: str) -> Path:
    safe_name = _safe_filename(stored_name)
    file_path = (_resolve_bucket_dir(bucket) / safe_name).resolve()
    return file_path


def _cleanup_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


@router.get("/monthly-data-pull/ping", summary="monthly_data_pull 连通性检查")
def ping_monthly_data_pull():
    return {"ok": True, "project_key": PROJECT_KEY, "message": "monthly_data_pull ready"}


@router.get("/monthly-data-pull/workspace", summary="读取导表默认目录")
def get_monthly_data_pull_workspace():
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "paths": _ensure_default_directories(),
    }


@router.get("/monthly-data-pull/files", summary="读取默认目录文件列表")
def list_monthly_data_pull_files(
    bucket: str = Query(..., description="目录标识：mapping_rules/source_reports/target_templates/outputs"),
):
    target_dir = _resolve_bucket_dir(bucket)
    files: List[Dict[str, object]] = []
    for item in sorted(target_dir.iterdir(), key=lambda p: p.name.lower()):
        if item.is_file():
            files.append(_build_file_info(item))
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "bucket": bucket,
        "directory": str(target_dir),
        "files": files,
    }


@router.post("/monthly-data-pull/files/upload", summary="上传文件到默认目录")
async def upload_monthly_data_pull_files(
    bucket: str = Query(..., description="目录标识：mapping_rules/source_reports/target_templates/outputs"),
    files: List[UploadFile] = File(..., description="待上传文件"),
):
    if not files:
        raise HTTPException(status_code=422, detail="未选择上传文件")

    target_dir = _resolve_bucket_dir(bucket)
    uploaded: List[Dict[str, object]] = []

    for upload in files:
        _ensure_allowed_excel_file(upload.filename or "")
        original_name = _safe_filename(upload.filename or "")
        target_path = _ensure_unique_path(target_dir, original_name)
        content = await upload.read()
        target_path.write_bytes(content)
        uploaded.append(_build_file_info(target_path))

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "bucket": bucket,
        "directory": str(target_dir),
        "uploaded_count": len(uploaded),
        "uploaded": uploaded,
    }


@router.post("/monthly-data-pull/clear-workspace", summary="清空导表工作目录文件")
def clear_monthly_data_pull_workspace():
    dirs = _default_directories()
    buckets = ("mapping_rules", "source_reports", "target_templates", "outputs")
    cleared: Dict[str, int] = {}

    for bucket in buckets:
        key = _bucket_to_dir_map()[bucket]
        target_dir = dirs[key]
        target_dir.mkdir(parents=True, exist_ok=True)
        removed = 0
        for item in target_dir.rglob("*"):
            if not item.is_file():
                continue
            if item.name == ".gitkeep":
                continue
            item.unlink(missing_ok=True)
            removed += 1
        cleared[bucket] = removed

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "message": "工作目录清理完成",
        "cleared": cleared,
    }


@router.post("/monthly-data-pull/analyze-mapping", summary="解析映射表并返回关系分组")
async def analyze_monthly_mapping(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=422, detail="映射文件名为空")
    _ensure_allowed_excel_file(file.filename)

    mapping_dir = _resolve_bucket_dir("mapping_rules")
    target_path = _ensure_unique_path(mapping_dir, _safe_filename(file.filename))
    target_path.write_bytes(await file.read())
    try:
        data = analyze_mapping(target_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"解析映射表失败：{exc}") from exc
    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "filename": target_path.name,
        "data": data,
    }


@router.post("/monthly-data-pull/get-sheets", summary="上传文件并读取 sheet 列表")
async def get_monthly_file_sheets(
    bucket: str = Query(..., description="source_reports 或 target_templates"),
    file: UploadFile = File(...),
):
    if bucket not in {"source_reports", "target_templates"}:
        raise HTTPException(status_code=422, detail="bucket 仅允许 source_reports 或 target_templates")
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名为空")
    _ensure_allowed_excel_file(file.filename)

    target_dir = _resolve_bucket_dir(bucket)
    target_path = _ensure_unique_path(target_dir, _safe_filename(file.filename))
    target_path.write_bytes(await file.read())
    try:
        sheets = get_sheet_names(target_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取 sheet 失败：{exc}") from exc
    return {
        "ok": True,
        "bucket": bucket,
        "stored_name": target_path.name,
        "sheets": sheets,
    }


@router.post("/monthly-data-pull/execute", summary="执行导表写入")
def execute_monthly_data_pull(req: ExecuteRequest):
    mapping_path = _resolve_file_path("mapping_rules", req.mapping_file)
    if not mapping_path.exists():
        raise HTTPException(status_code=404, detail=f"映射文件不存在：{req.mapping_file}")

    bucket_paths = {
        "mapping_rules": _resolve_bucket_dir("mapping_rules"),
        "source_reports": _resolve_bucket_dir("source_reports"),
        "target_templates": _resolve_bucket_dir("target_templates"),
        "outputs": _resolve_bucket_dir("outputs"),
    }
    src_files = {
        key: StoredFileInfo(bucket=value.bucket, stored_name=value.stored_name, sheet=value.sheet)
        for key, value in req.src_files.items()
    }
    tgt_files = {
        key: StoredFileInfo(bucket=value.bucket, stored_name=value.stored_name, sheet=value.sheet)
        for key, value in req.tgt_files.items()
    }
    try:
        outputs = execute_mapping(mapping_path, src_files, tgt_files, bucket_paths)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"执行导表失败：{exc}") from exc

    return {
        "ok": True,
        "project_key": PROJECT_KEY,
        "output_count": len(outputs),
        "files": [path.name for path in outputs],
    }


@router.get("/monthly-data-pull/download/{filename}", summary="下载导表输出文件")
def download_monthly_output(filename: str):
    output_dir = _resolve_bucket_dir("outputs").resolve()
    target = (output_dir / _safe_filename(filename)).resolve()
    if not str(target).startswith(str(output_dir)):
        raise HTTPException(status_code=403, detail="非法文件路径")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="输出文件不存在")

    media_type = "application/octet-stream"
    if target.suffix.lower() == ".xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif target.suffix.lower() == ".json":
        media_type = "application/json"
    return FileResponse(path=str(target), filename=target.name, media_type=media_type)


@router.get("/monthly-data-pull/download-outputs-zip", summary="打包下载 outputs 目录")
def download_monthly_outputs_zip():
    outputs_dir = _resolve_bucket_dir("outputs").resolve()
    files = sorted([item for item in outputs_dir.iterdir() if item.is_file() and item.name != ".gitkeep"])
    if not files:
        raise HTTPException(status_code=404, detail="outputs 目录暂无可下载文件")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with tempfile.NamedTemporaryFile(prefix="monthly_data_pull_outputs_", suffix=".zip", delete=False) as tmp:
        zip_path = Path(tmp.name)

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in files:
            zip_file.write(file_path, arcname=file_path.name)

    return FileResponse(
        path=str(zip_path),
        filename=f"monthly_data_pull_outputs_{timestamp}.zip",
        media_type="application/zip",
        background=BackgroundTask(_cleanup_file, str(zip_path)),
    )
