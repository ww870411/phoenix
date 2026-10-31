# -*- coding: utf-8 -*-
"""
主城区生产调度信息提取、入库与综合查询 API 路由
"""

import os
import shutil
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile, Query, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
from backend.projects.daily_report_25_26.services.dispatch_reconciliation import reconcile_report

from backend.projects.daily_report_25_26.services.dispatch_extractor import (
    extract_single_file,
    UnifiedDispatchExtractor
)
from backend.projects.daily_report_25_26.services.dispatch_db_service import (
    save_dispatch_reports,
    query_dispatch_reports,
    get_available_dispatch_dates,
    check_existing_dates
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dispatch", tags=["dispatch_info"])
public_router = APIRouter(prefix="/dispatch", tags=["dispatch_info"])

# 临时文件存放目录
TEMP_BASE_DIR = Path("backend_data/temp_dispatch").resolve()
TEMP_BASE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/extract", summary="提取调度文件 (DOCX / PDF)")
@public_router.post("/extract", summary="提取调度文件 (DOCX / PDF)")
async def extract_dispatch_files(
    files: List[UploadFile] = File(default=[]),
    folder_path: Optional[str] = Form(None),
    project_key: str = "daily_report_25_26"
):
    """
    支持上传多个 DOCX / PDF 文件，或指定服务器本地目录进行批量提取。
    返回解析结果、生成的临时文件 Token，以及与数据库已有日期的冲突比对。
    """
    token = str(uuid.uuid4())
    token_dir = TEMP_BASE_DIR / token
    upload_dir = token_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    extracted_results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    # 1. 处理上传的文件
    if files:
        for f in files:
            if not f.filename:
                continue
            ext = os.path.splitext(f.filename)[1].lower()
            if ext not in [".docx", ".pdf"]:
                continue
            # 自动创建父级目录，全面支持文件夹层级上传 (如 '25-26/2025年10月31日生产信息.docx')
            save_path = upload_dir / f.filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            content = await f.read()
            with open(save_path, "wb") as dest:
                dest.write(content)

    # 2. 处理服务器指定目录中的文件
    if folder_path and os.path.isdir(folder_path):
        for root, _, fnames in os.walk(folder_path):
            for fname in fnames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in [".docx", ".pdf"]:
                    src = os.path.join(root, fname)
                    dest = upload_dir / fname
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if not dest.exists():
                        try:
                            shutil.copy2(src, dest)
                        except Exception as e:
                            logger.warning("Failed to copy %s: %s", src, e)

    # 3. 递归遍历解析 upload_dir 下的全部文件 (支持各级子目录结构)
    target_files = sorted([p for p in upload_dir.rglob("*") if p.is_file() and p.suffix.lower() in [".docx", ".pdf"]])
    if not target_files:
        # 清理空目录
        shutil.rmtree(token_dir, ignore_errors=True)
        return {
            "ok": False,
            "message": "未找到有效的 .docx 或 .pdf 调度文件",
            "total_files": 0,
            "items": []
        }

    for fpath in target_files:
        try:
            report_data = extract_single_file(str(fpath), project_key=project_key)
            extracted_results.append(report_data)
        except Exception as e:
            logger.error("Extract failed for %s: %s", fpath.name, e)
            errors.append({"file": fpath.name, "error": str(e)})

    # 按业务日期升序排序
    extracted_results.sort(key=lambda x: x.get("biz_date") or "")

    # 将提取出的标准 JSON 保存在临时 token 目录下
    json_path = token_dir / "dispatch_extracted_batch.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(extracted_results, jf, ensure_ascii=False, indent=2)

    # 比对数据库中是否已存在部分业务日期
    biz_dates = [r["biz_date"] for r in extracted_results if r.get("biz_date")]
    existing_dates = check_existing_dates(biz_dates, project_key=project_key)

    return {
        "ok": True,
        "token": token,
        "total_files": len(target_files),
        "success_count": len(extracted_results),
        "error_count": len(errors),
        "errors": errors,
        "conflict_dates": existing_dates,
        "items": extracted_results
    }


@public_router.get("/download_json", summary="下载提取生成的标准 JSON 文件")
def download_extracted_json(token: str = Query(...)):
    """根据提取 Token 下载生成的标准 JSON 文件"""
    json_path = TEMP_BASE_DIR / token / "dispatch_extracted_batch.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="临时提取文件已过期或不存在，请重新提取")

    return FileResponse(
        path=str(json_path),
        filename="dispatch_extracted_batch.json",
        media_type="application/json"
    )


@public_router.post("/cleanup", summary="清理提取过程残留的临时文件")
def cleanup_temp_files(token: Optional[str] = Body(None, embed=True)):
    """清理指定 Token 产生的上传与临时导出文件"""
    if not token:
        # 如果未提供 token，清理超过 2 小时的遗留目录
        return {"ok": True, "message": "已跳过无 Token 清理"}

    token_dir = TEMP_BASE_DIR / token
    if token_dir.exists():
        try:
            shutil.rmtree(token_dir, ignore_errors=True)
            return {"ok": True, "message": f"临时文件清理完成 (Token: {token})"}
        except Exception as e:
            return {"ok": False, "message": f"清理失败: {e}"}
    return {"ok": True, "message": "临时文件不存在或已被清理"}


@router.post("/save_to_db", summary="一键入库 (支持冲突确认覆盖)")
@public_router.post("/save_to_db", summary="一键入库 (支持冲突确认覆盖)")
def save_dispatch_data(
    payload: Dict[str, Any] = Body(...),
    project_key: str = "daily_report_25_26"
):
    """
    接收待入库数据或 Token，并执行数据库写入：
    - payload 包含:
      * token: str (可选，若提供则从临时目录读取)
      * reports: List[Dict] (可选，若前端直接携带解析结果)
      * overwrite: bool (默认为 False，若有同日数据则中断并返回冲突日期；为 True 则覆盖更新)
    """
    token = payload.get("token")
    reports = payload.get("reports")
    overwrite = payload.get("overwrite", False)

    if not reports and token:
        json_path = TEMP_BASE_DIR / token / "dispatch_extracted_batch.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as jf:
                reports = json.load(jf)

    if not reports:
        raise HTTPException(status_code=400, detail="未提供有效入库数据")

    # 新记录和覆盖记录共用确认门槛，不能跳过状态冲突直接入库。
    choices = payload.get('status_resolutions') or {}
    if not isinstance(choices, dict) or any(v not in ('table', 'events') for v in choices.values()):
        raise HTTPException(status_code=400, detail='状态冲突选择无效')
    reports = [reconcile_report(r, choices) for r in reports]
    unresolved = [c for r in reports for c in r.get('status_conflicts', []) if not c.get('resolution')]
    if unresolved:
        return {'ok': False, 'has_status_conflict': True, 'status_conflicts': unresolved,
                'message': '请逐项选择以原表格或主设备事件为准后再入库'}
    result = save_dispatch_reports(reports, overwrite=overwrite, project_key=project_key)
    return result


@router.get("/query", summary="多维综合查询已入库调度信息")
@public_router.get("/query", summary="多维综合查询已入库调度信息")
def query_dispatch(
    project_key: str = "daily_report_25_26",
    biz_date: Optional[str] = Query(None, description="业务日期，如 2026-10-27"),
    start_date: Optional[str] = Query(None, description="起始业务日期"),
    end_date: Optional[str] = Query(None, description="截止业务日期"),
    keyword: Optional[str] = Query(None, description="关键字检索（人员、事件、工作票、地点等）"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """查询调度信息报表"""
    return query_dispatch_reports(
        project_key=project_key,
        biz_date=biz_date,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        limit=limit,
        offset=offset
    )


@router.get("/dates", summary="获取数据库中已有记录的所有业务日期")
@public_router.get("/dates", summary="获取数据库中已有记录的所有业务日期")
def list_dispatch_dates(project_key: str = "daily_report_25_26"):
    """获取所有已录入调度信息的日期列表"""
    dates = get_available_dispatch_dates(project_key=project_key)
    return {"ok": True, "dates": dates}


@router.post("/import_historical_configs", summary="一键载入 configs 目录下已提取的全量历史数据")
@public_router.post("/import_historical_configs", summary="一键载入 configs 目录下已提取的全量历史数据")
def import_historical_configs(
    overwrite: bool = Body(False, embed=True),
    project_key: str = "daily_report_25_26"
):
    """便捷载入 configs/10.28 dispatch_extracted_batch.json 中的 162 份历史标准化数据"""
    hist_path = Path("configs/10.28 dispatch_extracted_batch.json").resolve()
    if not hist_path.exists():
        raise HTTPException(status_code=404, detail="未找到 configs/10.28 dispatch_extracted_batch.json 文件")

    with open(hist_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = save_dispatch_reports(data, overwrite=overwrite, project_key=project_key)
    return result
