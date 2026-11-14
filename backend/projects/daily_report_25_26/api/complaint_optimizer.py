"""投诉报表优化接口：复用项目登录鉴权，仅返回内存中的独立副本。同时支持金山文档 (KDocs) 12345 底表配置与同步。"""
import base64
from datetime import datetime
from pathlib import PurePath
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, Response
from pydantic import BaseModel

from backend.projects.daily_report_25_26.services.audit_log_service import (
    log_session_operation,
)
from backend.services.auth_manager import AuthSession, get_current_session, get_current_session_optional
from backend.services.excel_optimizer import optimize_workbook
from backend.projects.daily_report_25_26.services.complaint_statistics import calculate
from backend.projects.daily_report_25_26.services import kdocs_complaint_service

router = APIRouter(dependencies=[Depends(get_current_session)])
public_router = APIRouter()


class KDocsConfigPayload(BaseModel):
    share_link: Optional[str] = None
    share_id: Optional[str] = None
    wps_sid: Optional[str] = None
    description: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None


class KDocsTestPayload(BaseModel):
    share_link: Optional[str] = None
    wps_sid: Optional[str] = None


class KDocsSyncPayload(BaseModel):
    biz_date: Optional[str] = None


@router.post('/data_entry/complaints/statistics', summary='按业务日期直接统计投诉明细')
def complaint_statistics(file: UploadFile = File(...), biz_date: str = Form(...)):
    if not (file.filename or '').lower().endswith('.xlsx'):
        raise HTTPException(400, '请选择 .xlsx 工作簿。')
    data = file.file.read(30 * 1024 * 1024 + 1)
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(400, '单个工作簿请勿超过 30 MB。')
    try:
        return {'ok': True, 'data': calculate(data, biz_date)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post('/data_entry/complaints/optimize', summary='分析并下载去冗余的 Excel 投诉报表')
def optimize_complaint_report(file: UploadFile = File(...)):
    filename = PurePath((file.filename or '').replace('\\', '/')).name
    if not filename.lower().endswith('.xlsx'):
        raise HTTPException(400, '目前支持 .xlsx 工作簿；请先在 Excel/WPS 中将旧版 .xls 另存为 .xlsx。')
    data = file.file.read(30 * 1024 * 1024 + 1)
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(400, '单个工作簿请勿超过 30 MB。')
    try:
        optimized, report = optimize_workbook(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {'ok': True, 'filename': filename[:-5] + '_去冗余.xlsx', 'file_base64': base64.b64encode(optimized).decode('ascii'), 'report': report}


# ==============================================================================
# 金山文档 (KDocs) 12345 投诉底表接入与配置接口
# ==============================================================================

@public_router.get('/data_entry/complaints/kdocs/config', summary='获取金山文档 12345 底表配置')
def get_kdocs_config():
    """获取金山文档共享链接及 wps_sid 配置。"""
    cfg = kdocs_complaint_service.load_config()
    return {'ok': True, 'data': cfg}


@public_router.post('/data_entry/complaints/kdocs/config', summary='更新金山文档 12345 底表配置')
def update_kdocs_config(
    payload: KDocsConfigPayload,
    request: Request,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
):
    """更新并保存金山文档配置（包括链接、Cookie凭证、说明等）。"""
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    saved = kdocs_complaint_service.save_config(updates)
    log_session_operation(
        session,
        "UPDATE_CONFIG",
        "更新金山文档 12345 投诉底表接入配置",
        request=request,
        unit="供热分公司",
        resource_id="kdocs:complaint_config",
    )
    return {'ok': True, 'data': saved, 'message': '金山文档接入配置已成功保存！'}


@public_router.post('/data_entry/complaints/kdocs/test', summary='测试金山文档连通性与凭证有效性')
def test_kdocs_connectivity(payload: Optional[KDocsTestPayload] = None):
    """测试当前（或待保存）的金山文档凭证能否正常换取下载直链。"""
    share_link = payload.share_link if payload else None
    wps_sid = payload.wps_sid if payload else None

    success, msg, meta = kdocs_complaint_service.test_kdocs_connectivity(
        share_link=share_link,
        wps_sid=wps_sid,
    )
    return {'ok': success, 'message': msg, 'data': meta}


@public_router.post('/data_entry/complaints/kdocs/sync', summary='从金山文档一键抓取并自动计算当日投诉')
def sync_complaints_from_kdocs(
    request: Request,
    payload: Optional[KDocsSyncPayload] = None,
    session: Optional[AuthSession] = Depends(get_current_session_optional),
):
    """
    使用配置的 wps_sid 直接从金山文档下载最新 12345 底表并执行统计。
    """
    biz_date = payload.biz_date if payload and payload.biz_date else None
    if not biz_date:
        # 默认取系统当前基准业务日期或今日
        try:
            from backend.projects.daily_report_25_26.api.dashboard import _get_current_business_date
            biz_date = _get_current_business_date()
        except Exception:
            biz_date = datetime.now().strftime('%Y-%m-%d')

    try:
        file_bytes, filename = kdocs_complaint_service.download_kdocs_workbook_bytes()
    except Exception as exc:
        raise HTTPException(400, f'从金山文档下载文件失败: {exc}') from exc

    try:
        stats = calculate(file_bytes, biz_date)
        # 更新最后同步时间
        kdocs_complaint_service.save_config({
            'last_sync_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        log_session_operation(
            session,
            "IMPORT_COMPLAINT",
            f"通过金山文档底表【{filename}】拉取并统计 {biz_date} 12345 投诉量",
            request=request,
            unit="供热分公司",
            resource_id=f"GongRe_Sheet:{biz_date}",
            after_value={"filename": filename, "biz_date": biz_date},
        )
        return {
            'ok': True,
            'message': f'成功从金山文档拉取【{filename}】并完成 {biz_date} 投诉量统计！',
            'filename': filename,
            'biz_date': biz_date,
            'data': stats,
        }
    except Exception as exc:
        raise HTTPException(400, f'解析投诉底表失败: {exc}') from exc


@public_router.get('/data_entry/complaints/kdocs/download', summary='下载金山文档 12345 投诉底表 .xlsx 到本地')
def download_kdocs_file_to_local():
    """从金山文档拉取最新的 12345 投诉底表工作簿，并以附件形式提供给浏览器下载。"""
    try:
        file_bytes, filename = kdocs_complaint_service.download_kdocs_workbook_bytes()
    except Exception as exc:
        raise HTTPException(400, f'从金山文档下载文件失败: {exc}') from exc

    import urllib.parse
    encoded_filename = urllib.parse.quote(filename)
    headers = {
        'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
        'Access-Control-Expose-Headers': 'Content-Disposition',
    }
    return Response(
        content=file_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers=headers,
    )

