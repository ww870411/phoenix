"""投诉报表优化接口：复用项目登录鉴权，仅返回内存中的独立副本。"""
import base64
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.services.auth_manager import get_current_session
from backend.services.excel_optimizer import optimize_workbook

router = APIRouter(dependencies=[Depends(get_current_session)])


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
