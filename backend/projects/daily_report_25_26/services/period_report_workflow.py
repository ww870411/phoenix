# -*- coding: utf-8 -*-
"""
周期运行汇报 工作流目录管理服务。

管理目录: backend_data/projects/daily_report_25_26/period_report/工作流
职责:
1. 集中管理与维护工作流规范文档 (.md)、模板引擎 (.html)、数据来源说明与材料结构要点等文件与子目录；
2. 提供文件列表（支持子目录归类）、在线内容读取（支持 Markdown 渲染阅览与 HTML 演示播放）、下载、上传、重命名与删除能力；
3. 实施严格的路径防穿越校验与东八区时间对齐。
"""

import io
import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, UploadFile
from backend.config import DATA_DIRECTORY

# 东八区（北京时间 UTC+8）时区定义
BEIJING_TZ = timezone(timedelta(hours=8))


def format_beijing_time(timestamp: float) -> str:
    """将文件 POSIX 时间戳严格格式化为东八区（UTC+8 北京时间）字符串。"""
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(BEIJING_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def format_file_size(size_bytes: int) -> str:
    """将字节数格式化为人类易读格式（B / KB / MB）。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


# 基础目录定位
STORAGE_ROOT_DIR = (DATA_DIRECTORY / "projects" / "daily_report_25_26" / "period_report").resolve()
WORKFLOW_DIR = (STORAGE_ROOT_DIR / "工作流").resolve()


def ensure_workflow_dir() -> Path:
    """确保工作流目录存在并返回该路径。"""
    WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    return WORKFLOW_DIR


def resolve_safe_workflow_path(rel_path: str, must_exist: bool = True) -> Path:
    """
    根据相对工作流目录的路径解析绝对路径，并严格校验防穿越。
    """
    base_dir = ensure_workflow_dir().resolve()
    clean_rel = rel_path.replace("\\", "/").strip().lstrip("/")
    if clean_rel.startswith("工作流/"):
        clean_rel = clean_rel[len("工作流/"):]

    target_path = (base_dir / clean_rel).resolve()
    if not target_path.is_relative_to(base_dir):
        raise HTTPException(400, "非法的文件路径（路径穿越拦截）")

    if must_exist and not target_path.exists():
        raise HTTPException(404, f"工作流文件不存在: {clean_rel}")

    return target_path


def get_file_kind(ext: str) -> str:
    """根据文件后缀推断展示类型。"""
    lower = ext.lower()
    if lower in ('.md', '.markdown'):
        return 'markdown'
    elif lower in ('.html', '.htm'):
        return 'html'
    elif lower in ('.xlsx', '.xls'):
        return 'excel'
    elif lower in ('.txt', '.json', '.yaml', '.yml'):
        return 'text'
    return 'other'


def list_workflow_files(folder: str = "") -> Dict[str, Any]:
    """
    按目录层级列出工作流目录下的直接子文件夹与直接子文件（非平铺展开）。
    支持面包屑导航、子目录进入与递归文件统计。
    """
    base_dir = ensure_workflow_dir()
    clean_folder = (folder or "").replace("\\", "/").strip().strip("/")
    if clean_folder in (".", "根目录", "全部"):
        clean_folder = ""

    # 解析当前目标目录
    if clean_folder:
        target_dir = resolve_safe_workflow_path(clean_folder, must_exist=True)
        if not target_dir.is_dir():
            raise HTTPException(400, "指定的路径不是有效目录")
    else:
        target_dir = base_dir

    dir_list: List[Dict[str, Any]] = []
    file_list: List[Dict[str, Any]] = []

    # 1. 扫描当前目录下的直接子项
    try:
        for entry in os.scandir(target_dir):
            entry_name = entry.name
            # 忽略隐藏文件或临时文件
            if entry_name.startswith('.'):
                continue
            entry_p = Path(entry.path)
            rel_p = entry_p.relative_to(base_dir).as_posix()
            stat = entry.stat()

            if entry.is_dir():
                # 统计子文件夹内的文件数量
                try:
                    sub_file_count = sum(1 for p in entry_p.rglob('*') if p.is_file() and not p.name.startswith('.'))
                except Exception:
                    sub_file_count = 0

                dir_list.append({
                    "name": entry_name,
                    "rel_path": rel_p,
                    "relative_path": rel_p,
                    "is_dir": True,
                    "kind": "folder",
                    "ext": "",
                    "item_count": sub_file_count,
                    "file_count": sub_file_count,
                    "size": 0,
                    "size_formatted": f"{sub_file_count} 个文件",
                    "updated_at": format_beijing_time(stat.st_mtime),
                    "created_at": format_beijing_time(stat.st_ctime),
                })
            elif entry.is_file():
                ext = entry_p.suffix.lower()
                file_list.append({
                    "name": entry_name,
                    "rel_path": rel_p,
                    "relative_path": rel_p,
                    "is_dir": False,
                    "kind": get_file_kind(ext),
                    "ext": ext,
                    "size": stat.st_size,
                    "size_formatted": format_file_size(stat.st_size),
                    "updated_at": format_beijing_time(stat.st_mtime),
                    "created_at": format_beijing_time(stat.st_ctime),
                })
    except Exception as exc:
        raise HTTPException(500, f"扫描工作流目录失败: {str(exc)}") from exc

    # 排序：文件夹按名称升序，文件按最后更新时间倒序
    dir_list.sort(key=lambda x: x["name"])
    file_list.sort(key=lambda x: x["updated_at"], reverse=True)

    # 组合列表：子文件夹始终排在最前面，直接文件排在后面
    combined_items = dir_list + file_list

    # 2. 构造面包屑导航
    breadcrumbs: List[Dict[str, str]] = [
        {"name": "工作流根目录", "path": ""}
    ]
    if clean_folder:
        parts = clean_folder.split('/')
        accum = []
        for p in parts:
            accum.append(p)
            breadcrumbs.append({
                "name": p,
                "path": "/".join(accum)
            })

    # 父级目录路径
    parent_folder = None
    if clean_folder:
        parent_p = Path(clean_folder).parent.as_posix()
        parent_folder = "" if parent_p == "." else parent_p

    # 全局总文件与总目录统计
    total_files = 0
    total_folders = 0
    if base_dir.exists():
        for root, dirs, files in os.walk(base_dir):
            total_dirs_in_walk = len([d for d in dirs if not d.startswith('.')])
            total_folders += total_dirs_in_walk
            total_files += len([f for f in files if not f.startswith('.')])

    return {
        "current_folder": clean_folder,
        "parent_folder": parent_folder,
        "breadcrumbs": breadcrumbs,
        "directories": dir_list,
        "files": file_list,
        "items": combined_items,
        "total_files": total_files,
        "total_folders": total_folders,
        "base_path": "backend_data/projects/daily_report_25_26/period_report/工作流"
    }


def create_workflow_folder(parent_folder: str, folder_name: str) -> Dict[str, Any]:
    """
    在工作流指定目录下创建新的子文件夹。
    """
    clean_name = (folder_name or "").strip()
    if not clean_name:
        raise HTTPException(400, "文件夹名称不能为空")

    clean_name = os.path.basename(clean_name.replace("\\", "/")).strip()
    clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_name).strip()
    if not clean_name or clean_name in ('.', '..'):
        raise HTTPException(400, "文件夹名称不合法")

    base_dir = ensure_workflow_dir()
    clean_parent = (parent_folder or "").replace("\\", "/").strip().strip("/")
    if clean_parent in (".", "根目录"):
        clean_parent = ""

    if clean_parent:
        parent_dir = (base_dir / clean_parent).resolve()
    else:
        parent_dir = base_dir

    if not parent_dir.is_relative_to(base_dir):
        raise HTTPException(400, "非法父级目录（路径穿越拦截）")

    target_dir = parent_dir / clean_name
    if target_dir.exists():
        raise HTTPException(400, f"该目录下已存在同名文件夹【{clean_name}】")

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        rel_p = target_dir.relative_to(base_dir).as_posix()
        stat = target_dir.stat()
        return {
            "ok": True,
            "name": clean_name,
            "rel_path": rel_p,
            "is_dir": True,
            "kind": "folder",
            "item_count": 0,
            "updated_at": format_beijing_time(stat.st_mtime),
            "message": f"子目录【{clean_name}】创建成功"
        }
    except Exception as exc:
        raise HTTPException(500, f"创建文件夹失败: {str(exc)}") from exc


def get_workflow_file_content(rel_path: str) -> Dict[str, Any]:
    """
    读取指定工作流文本文件的内容（如 Markdown、HTML 等）。
    """
    target_path = resolve_safe_workflow_path(rel_path, must_exist=True)
    if not target_path.is_file():
        raise HTTPException(400, "目标路径不是有效文件")

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        stat = target_path.stat()
        ext = target_path.suffix.lower()
        return {
            "name": target_path.name,
            "rel_path": rel_path.replace("\\", "/"),
            "ext": ext,
            "kind": get_file_kind(ext),
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "updated_at": format_beijing_time(stat.st_mtime),
            "created_at": format_beijing_time(stat.st_ctime),
            "content": content
        }
    except Exception as exc:
        raise HTTPException(500, f"读取工作流文件内容失败: {str(exc)}") from exc


def get_workflow_file_path(rel_path: str) -> Path:
    """
    获取安全的工作流文件路径供下载。
    """
    target_path = resolve_safe_workflow_path(rel_path, must_exist=True)
    if not target_path.is_file():
        raise HTTPException(400, "目标路径不是有效文件")
    return target_path


async def upload_workflow_file(file: UploadFile, folder: str = "") -> Dict[str, Any]:
    """
    上传文件至工作流目录（支持指定子目录）。
    """
    if not file.filename:
        raise HTTPException(400, "未选择上传文件")

    # 清洗文件名
    raw_name = os.path.basename(file.filename.strip().replace("\\", "/"))
    clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', raw_name).strip()
    if not clean_name or clean_name in ('.', '..'):
        raise HTTPException(400, "文件名不合法")

    base_dir = ensure_workflow_dir()
    target_dir = base_dir

    clean_folder = (folder or "").replace("\\", "/").strip().strip("/")
    if clean_folder and clean_folder != "根目录":
        target_dir = (base_dir / clean_folder).resolve()
        if not target_dir.is_relative_to(base_dir):
            raise HTTPException(400, "非法目标目录（路径穿越拦截）")
        target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / clean_name
    try:
        data = await file.read()
        target_path.write_bytes(data)
        stat = target_path.stat()
        rel_path = target_path.relative_to(base_dir).as_posix()
        ext = target_path.suffix.lower()
        parent_rel = target_path.parent.relative_to(base_dir).as_posix()
        folder_name = "根目录" if parent_rel == "." else parent_rel

        return {
            "ok": True,
            "name": clean_name,
            "rel_path": rel_path,
            "folder": folder_name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "updated_at": format_beijing_time(stat.st_mtime),
            "created_at": format_beijing_time(stat.st_ctime),
            "ext": ext,
            "kind": get_file_kind(ext),
            "message": "工作流文件上传成功"
        }
    except Exception as exc:
        raise HTTPException(500, f"上传工作流文件失败: {str(exc)}") from exc


def rename_workflow_file(rel_path: str, new_name: str) -> Dict[str, Any]:
    """
    重命名工作流文件或子目录，自动保留原扩展名并防穿越。
    """
    old_path = resolve_safe_workflow_path(rel_path, must_exist=True)
    clean_new = (new_name or "").strip()
    if not clean_new:
        raise HTTPException(400, "新名称不能为空")

    clean_new = os.path.basename(clean_new.replace("\\", "/")).strip()
    clean_new = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_new).strip()
    if not clean_new or clean_new in ('.', '..'):
        raise HTTPException(400, "新名称不合法")

    # 如果是文件，保持原扩展名
    if old_path.is_file():
        old_ext = old_path.suffix.lower()
        lower_new = clean_new.lower()
        if not lower_new.endswith(old_ext):
            for ext in ('.md', '.html', '.htm', '.xlsx', '.txt', '.json'):
                if lower_new.endswith(ext):
                    clean_new = clean_new[:-len(ext)]
                    break
            clean_new = f"{clean_new}{old_ext}"

    new_path = (old_path.parent / clean_new).resolve()
    base_dir = ensure_workflow_dir().resolve()

    if not new_path.is_relative_to(base_dir):
        raise HTTPException(400, "非法的新名称（路径穿越拦截）")

    if new_path == old_path:
        stat = new_path.stat()
        return {
            "ok": True,
            "name": new_path.name,
            "rel_path": new_path.relative_to(base_dir).as_posix(),
            "message": "名称未发生变更"
        }

    if new_path.exists():
        raise HTTPException(400, f"同目录下已存在同名项目【{new_path.name}】，请更换新名称")

    try:
        old_path.rename(new_path)
        stat = new_path.stat()
        rel_path = new_path.relative_to(base_dir).as_posix()
        ext = new_path.suffix.lower() if new_path.is_file() else ""
        return {
            "ok": True,
            "name": new_path.name,
            "rel_path": rel_path,
            "is_dir": new_path.is_dir(),
            "size": stat.st_size if new_path.is_file() else 0,
            "size_formatted": format_file_size(stat.st_size) if new_path.is_file() else "目录",
            "updated_at": format_beijing_time(stat.st_mtime),
            "created_at": format_beijing_time(stat.st_ctime),
            "ext": ext,
            "kind": "folder" if new_path.is_dir() else get_file_kind(ext),
            "message": f"工作流项目已成功重命名为【{new_path.name}】"
        }
    except Exception as exc:
        raise HTTPException(500, f"重命名失败: {str(exc)}") from exc


def delete_workflow_file(rel_path: str) -> Dict[str, Any]:
    """
    删除指定工作流文件或子目录。
    """
    target_path = resolve_safe_workflow_path(rel_path, must_exist=True)
    base_dir = ensure_workflow_dir().resolve()
    if target_path == base_dir:
        raise HTTPException(403, "禁止删除工作流根目录")

    try:
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
        return {
            "ok": True,
            "rel_path": rel_path,
            "message": "工作流项目删除成功"
        }
    except Exception as exc:
        raise HTTPException(500, f"删除失败: {str(exc)}") from exc


def create_workflow_archive(folder: str = "") -> Tuple[io.BytesIO, str]:
    """
    一键将工作流指定目录（或全量根目录）下的所有子目录与文件递归打包为 ZIP 内存流。
    返回: (BytesIO 字节流, 建议的中文文件名)
    """
    base_dir = ensure_workflow_dir().resolve()
    clean_folder = (folder or "").replace("\\", "/").strip().strip("/")
    if clean_folder in (".", "根目录", "全部"):
        clean_folder = ""

    # 解析目标打包目录
    if clean_folder:
        target_dir = resolve_safe_workflow_path(clean_folder, must_exist=True)
        if not target_dir.is_dir():
            raise HTTPException(400, "指定的路径不是有效目录")
        archive_root_name = target_dir.name
        safe_folder_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', target_dir.name)
        archive_filename = f"工作流_{safe_folder_name}_{datetime.now(BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}.zip"
    else:
        target_dir = base_dir
        archive_root_name = "工作流"
        archive_filename = f"工作流_全量资料_{datetime.now(BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}.zip"

    buf = io.BytesIO()
    # 使用 ZIP_DEFLATED 进行标准压缩
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(target_dir):
            # 过滤隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            root_path = Path(root)

            rel_to_target = root_path.relative_to(target_dir)

            # 写入当前子目录项（确保空子目录在解压后依然保留层级）
            if rel_to_target != Path('.'):
                zip_dir_path = (Path(archive_root_name) / rel_to_target).as_posix() + "/"
                dir_info = zipfile.ZipInfo(zip_dir_path)
                try:
                    mtime = datetime.fromtimestamp(root_path.stat().st_mtime, tz=timezone.utc).astimezone(BEIJING_TZ)
                    dir_info.date_time = (mtime.year, mtime.month, mtime.day, mtime.hour, mtime.minute, mtime.second)
                except Exception:
                    pass
                zf.writestr(dir_info, "")

            # 写入当前目录下的所有有效文件
            for file_name in files:
                if file_name.startswith('.'):
                    continue
                file_full_path = root_path / file_name
                if not file_full_path.is_file():
                    continue

                zip_file_path = (Path(archive_root_name) / rel_to_target / file_name).as_posix()
                try:
                    file_stat = file_full_path.stat()
                    file_bytes = file_full_path.read_bytes()
                    file_info = zipfile.ZipInfo(zip_file_path)
                    file_info.compress_type = zipfile.ZIP_DEFLATED
                    mtime = datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).astimezone(BEIJING_TZ)
                    file_info.date_time = (mtime.year, mtime.month, mtime.day, mtime.hour, mtime.minute, mtime.second)
                    zf.writestr(file_info, file_bytes)
                except Exception:
                    # 单个文件读取异常容错
                    pass

    buf.seek(0)
    return buf, archive_filename
