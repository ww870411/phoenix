"""生产运行汇报接口；仅精确匹配Global_admin组可读取日期、汇报及管理HTML文件空间。"""
from datetime import date
from urllib.parse import quote
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session
from .daily_brief import list_data_dates
from ..services.period_report import build_period_report, validate_period
from ..services.period_report_export import generate_period_report_xlsx, save_period_report_xlsx
from ..services.period_report_files import (
    delete_report_file,
    get_report_file_path,
    get_report_html_content,
    list_report_files,
    rename_report_file,
    save_report_html,
    upload_report_html,
    get_display_config,
    set_display_config,
    list_space_folders,
    create_space_folder,
    transfer_space_file,
)
from ..services.period_report_workflow import (
    create_workflow_archive,
    create_workflow_folder,
    delete_workflow_file,
    get_workflow_file_content,
    get_workflow_file_path,
    list_workflow_files,
    rename_workflow_file,
    upload_workflow_file,
)

router = APIRouter()


class SaveReportRequest(BaseModel):
    filename: str
    content: str


class RenameReportRequest(BaseModel):
    path: str
    new_name: str


class CreateFolderRequest(BaseModel):
    parent_folder: str = ""
    folder_name: str


class SetDisplayConfigRequest(BaseModel):
    mode: str
    target_file: str = ""


class CreateSpaceFolderRequest(BaseModel):
    space: str = "material"
    parent_folder: str = ""
    folder_name: str


class TransferSpaceFileRequest(BaseModel):
    source_space: str
    source_path: str
    target_space: str
    target_folder: str = ""
    action: str = "copy"
    overwrite: bool = False


def check_period_report_session(session: AuthSession):
    """生产运行汇报页面及材料仓库空间仅精确匹配 Global_admin 与 Group_admin 组。"""
    if session.group not in ('Global_admin', 'Group_admin'):
        raise HTTPException(403, '生产运行汇报仅限管理员访问')


def check_workflow_admin_session(session: AuthSession):
    """底层工作流目录空间与模板配置仅精确匹配 Global_admin 组。"""
    if session.group != 'Global_admin':
        raise HTTPException(403, '工作流目录空间仅限 Global_admin 访问')


@router.get('/period-report')
def period_report(start: date | None = None, end: date | None = None, include_prev: bool = True,
                  session: AuthSession = Depends(get_current_session)):
    check_period_report_session(session)
    if (start is None) != (end is None):
        raise HTTPException(422, '请同时提供起止日期')
    if start is not None:
        try:
            validate_period(start, end)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    with SessionLocal() as db:
        if start is None:
            dates = list_data_dates(db)
            return {'latestDate': dates[0] if dates else None}
        return build_period_report(db, start, end, include_prev)


@router.get('/period-report/files')
def get_files(session: AuthSession = Depends(get_current_session)):
    """列出空间中的所有 HTML 汇报文件。"""
    check_period_report_session(session)
    return {'items': list_report_files()}


@router.post('/period-report/files/save')
def save_file(payload: SaveReportRequest, session: AuthSession = Depends(get_current_session)):
    """一键保存当前生成的 HTML 汇报材料。"""
    check_period_report_session(session)
    return save_report_html(payload.filename, payload.content)


@router.post('/period-report/files/upload')
async def upload_file(file: UploadFile = File(...), session: AuthSession = Depends(get_current_session)):
    """上传外部 HTML 汇报文件。"""
    check_period_report_session(session)
    return await upload_report_html(file)


@router.get('/period-report/files/content')
def get_file_content(path: str = Query(..., description='文件的相对路径'),
                     session: AuthSession = Depends(get_current_session)):
    """获取指定 HTML 文件的内容用于预览播放。"""
    check_period_report_session(session)
    return get_report_html_content(path)


@router.get('/period-report/files/download')
def download_file(path: str = Query(..., description='文件的相对路径'),
                  session: AuthSession = Depends(get_current_session)):
    """下载指定的文件（支持 HTML 汇报材料与 XLSX 数据文件）。"""
    check_period_report_session(session)
    file_path = get_report_file_path(path)
    media_type = (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        if file_path.suffix.lower() == '.xlsx'
        else 'text/html'
    )
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type
    )


@router.get('/period-report/export-xlsx')
def export_xlsx(
    start: date = Query(..., description='开始日期'),
    end: date = Query(..., description='结束日期'),
    include_prev: bool = Query(True, description='是否包含上期值 (环比对标)'),
    save_to_space: bool = Query(False, description='是否保存至材料仓库空间'),
    filename: str | None = Query(None, description='自定义文件名'),
    session: AuthSession = Depends(get_current_session)
):
    """
    导出周期多维生产运行明细 XLSX 报表（包含每日气温等 5 个标准 Sheet）。
    支持直接浏览器流式下载，或一键保存至【材料仓库】供 Agent 深度分析。
    """
    check_period_report_session(session)
    try:
        validate_period(start, end)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    with SessionLocal() as db:
        if save_to_space:
            saved_meta = save_period_report_xlsx(db, start, end, include_prev, filename)
            return {"ok": True, "file": saved_meta}

        # 内存流式直接下载
        tag = "_生产数据明细(含上期).xlsx" if include_prev else "_生产数据明细.xlsx"
        out_name = filename or f"{start.isoformat()}_{end.isoformat()}{tag}"
        if not out_name.lower().endswith(".xlsx"):
            out_name += ".xlsx"

        stream = generate_period_report_xlsx(db, start, end, include_prev)
        encoded_name = quote(out_name)
        return Response(
            content=stream.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_name}"
            }
        )


@router.delete('/period-report/files')
def delete_file(path: str = Query(..., description='文件的相对路径'),
                session: AuthSession = Depends(get_current_session)):
    """删除指定的材料仓库文件（受保护的模板除外）。"""
    check_period_report_session(session)
    return delete_report_file(path)


@router.post('/period-report/files/rename')
def rename_file(payload: RenameReportRequest, session: AuthSession = Depends(get_current_session)):
    """重命名材料仓库中的文件（支持 HTML 汇报与 XLSX 数据明细，受保护模板除外）。"""
    check_period_report_session(session)
    return rename_report_file(payload.path, payload.new_name)


# ==================== 工作流目录（Workflow Space）专属管理接口 ====================

@router.get('/period-report/workflow/files')
def get_workflow_files(folder: str = Query("", description="子目录相对路径"),
                       session: AuthSession = Depends(get_current_session)):
    """按层级获取工作流目录下的直接子文件夹与文件（包含面包屑导航与统计）。"""
    check_workflow_admin_session(session)
    return list_workflow_files(folder)


@router.post('/period-report/workflow/folders/create')
def create_folder(payload: CreateFolderRequest, session: AuthSession = Depends(get_current_session)):
    """在工作流目录下创建新的子文件夹。"""
    check_workflow_admin_session(session)
    return create_workflow_folder(payload.parent_folder, payload.folder_name)


@router.get('/period-report/workflow/files/content')
def get_workflow_content(path: str = Query(..., description='文件的相对路径'),
                         session: AuthSession = Depends(get_current_session)):
    """读取指定工作流文档的内容（如 Markdown、HTML 模版等）。"""
    check_workflow_admin_session(session)
    return get_workflow_file_content(path)


@router.get('/period-report/workflow/files/download')
def download_workflow_file(path: str = Query(..., description='文件的相对路径'),
                           session: AuthSession = Depends(get_current_session)):
    """下载指定的工作流文件。"""
    check_workflow_admin_session(session)
    file_path = get_workflow_file_path(path)
    ext = file_path.suffix.lower()
    media_type = 'text/plain; charset=utf-8'
    if ext == '.html':
        media_type = 'text/html; charset=utf-8'
    elif ext == '.md':
        media_type = 'text/markdown; charset=utf-8'
    elif ext == '.xlsx':
        media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type
    )


@router.post('/period-report/workflow/files/upload')
async def upload_workflow(
    file: UploadFile = File(...),
    folder: str = Query("", description="目标子文件夹名称"),
    session: AuthSession = Depends(get_current_session)
):
    """上传文件至工作流目录。"""
    check_workflow_admin_session(session)
    return await upload_workflow_file(file, folder)


@router.post('/period-report/workflow/files/rename')
def rename_workflow(payload: RenameReportRequest, session: AuthSession = Depends(get_current_session)):
    """重命名工作流文件。"""
    check_workflow_admin_session(session)
    return rename_workflow_file(payload.path, payload.new_name)


@router.delete('/period-report/workflow/files')
def delete_workflow(path: str = Query(..., description='文件的相对路径'),
                    session: AuthSession = Depends(get_current_session)):
    """删除指定的工作流文件。"""
    check_workflow_admin_session(session)
    return delete_workflow_file(path)


@router.get('/period-report/workflow/archive')
def download_workflow_archive(
    folder: str = Query("", description="子目录相对路径，留空则打包全量工作流根目录"),
    session: AuthSession = Depends(get_current_session)
):
    """一键打包下载工作流目录（含所有子目录与文件，ZIP 格式）。"""
    check_workflow_admin_session(session)
    buffer, filename = create_workflow_archive(folder)
    quoted_filename = quote(filename)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{quoted_filename}"; filename*=utf-8\'\'{quoted_filename}',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
    )


# ==================== 页面默认展示配置接口 ====================

@router.get('/period-report/display-config')
def get_display_config_api(session: AuthSession = Depends(get_current_session)):
    """获取生产运行汇报页面的默认展示模式与文件。"""
    check_period_report_session(session)
    return get_display_config()


@router.post('/period-report/display-config')
def set_display_config_api(payload: SetDisplayConfigRequest, session: AuthSession = Depends(get_current_session)):
    """设定生产运行汇报页面的默认打开内容（仅限 Global_admin）。"""
    check_workflow_admin_session(session)
    operator = getattr(session, 'username', None) or session.group or 'Global_admin'
    return set_display_config(payload.mode, payload.target_file, operator)


# ==================== 空间目录与跨空间/内部传输接口 ====================

@router.get('/period-report/folders')
def get_folders_api(
    space: str = Query('material', description='空间标识: material 或 workflow'),
    session: AuthSession = Depends(get_current_session)
):
    """获取指定空间（材料空间或工作流空间）下的所有子文件夹列表。"""
    clean_space = (space or "").strip().lower()
    if clean_space in ("workflow", "工作流"):
        check_workflow_admin_session(session)
        actual_space = "workflow"
    else:
        check_period_report_session(session)
        actual_space = "material"

    return {
        "space": actual_space,
        "folders": list_space_folders(actual_space)
    }


@router.post('/period-report/folders/create-in-space')
def create_space_folder_api(
    payload: CreateSpaceFolderRequest,
    session: AuthSession = Depends(get_current_session)
):
    """在指定空间（材料空间或工作流空间）中新建子文件夹。"""
    clean_space = (payload.space or "").strip().lower()
    if clean_space in ("workflow", "工作流"):
        check_workflow_admin_session(session)
        actual_space = "workflow"
    else:
        check_period_report_session(session)
        actual_space = "material"

    return create_space_folder(actual_space, payload.parent_folder, payload.folder_name)


@router.post('/period-report/files/transfer')
def transfer_file_api(
    payload: TransferSpaceFileRequest,
    session: AuthSession = Depends(get_current_session)
):
    """
    跨空间（材料空间 ⇄ 工作流空间）或空间内部移动/复制文件。
    涉及工作流目录空间的传输操作仅限 Global_admin 执行；
    纯材料空间内部的移动/复制允许管理员执行。
    """
    clean_src_space = (payload.source_space or "").strip().lower()
    clean_dst_space = (payload.target_space or "").strip().lower()

    # 只要涉及工作流空间，必须严格为 Global_admin
    if clean_src_space in ("workflow", "工作流") or clean_dst_space in ("workflow", "工作流"):
        check_workflow_admin_session(session)
    else:
        check_period_report_session(session)

    actual_src = "workflow" if clean_src_space in ("workflow", "工作流") else "material"
    actual_dst = "workflow" if clean_dst_space in ("workflow", "工作流") else "material"

    return transfer_space_file(
        source_space=actual_src,
        source_path=payload.source_path,
        target_space=actual_dst,
        target_folder=payload.target_folder,
        action=payload.action,
        overwrite=payload.overwrite
    )
