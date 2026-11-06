# -*- coding: utf-8 -*-
"""
周期运行汇报 HTML 材料仓库管理服务。

职责：
1. 管理 backend_data/projects/daily_report_25_26/period_report/材料仓库 目录下的 HTML 汇报文件；
2. 提供文件列表查询、安全读取、保存、上传、下载与删除功能；
3. 联动识别工作流（工作流/1.html模板与使用说明）中的演示引擎母版，提供在线演示播放支持与防误删保护；
4. 实施严格的路径防穿越校验，确保仅限合法 HTML 文件的受控操作。
"""

import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from fastapi import HTTPException, UploadFile
from backend.config import DATA_DIRECTORY

# 东八区（北京时间 UTC+8）时区定义
BEIJING_TZ = timezone(timedelta(hours=8))


def format_beijing_time(timestamp: float) -> str:
    """
    将文件 POSIX 时间戳严格格式化为东八区（UTC+8 北京时间）易读字符串。
    避免因操作系统本地时区或 Docker 容器默认 UTC 导致的时间偏差。
    """
    try:
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(BEIJING_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

# 基础目录定位：统一使用系统配置的 DATA_DIRECTORY（容器环境挂载为 /app/data，本地环境为 backend_data）
STORAGE_ROOT_DIR = (DATA_DIRECTORY / "projects" / "daily_report_25_26" / "period_report").resolve()

# 专属文件仓库路径：材料仓库
STORAGE_DIR = (STORAGE_ROOT_DIR / "材料仓库").resolve()

# 工作流模板目录
WORKFLOW_DIR = (STORAGE_ROOT_DIR / "工作流").resolve()


def ensure_storage_dir() -> Path:
    """确保材料仓库目录存在并返回该路径。"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR


def format_file_size(size_bytes: int) -> str:
    """将字节数格式化为人类易读格式（B / KB / MB）。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def sanitize_filename(filename: str) -> str:
    """
    清洗文件名，防止路径穿越与非法字符。
    """
    if not filename:
        raise HTTPException(400, "文件名不能为空")
    
    # 提取纯文件名（去除可能携带的路径前缀）
    name = os.path.basename(filename.strip().replace("\\", "/"))
    # 去除 Windows/Linux 不合法字符
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip()
    
    if not name or name in ('.', '..'):
        raise HTTPException(400, "文件名不合法")
    
    # 支持 .html, .htm 与 .xlsx
    lower_name = name.lower()
    if lower_name.endswith(".xlsx"):
        pass
    elif not (lower_name.endswith(".html") or lower_name.endswith(".htm")):
        name += ".html"
        
    return name


def resolve_safe_path(rel_path: str, must_exist: bool = True, for_write: bool = False) -> Path:
    """
    根据相对路径解析绝对路径，并严格校验是否处于安全边界内（防止目录穿越）。
    写入/删除操作强制限定在 STORAGE_DIR（材料仓库）内；
    读取操作兼容 WORKFLOW_DIR（工作流模板）。
    """
    store_dir = ensure_storage_dir().resolve()
    root_dir = STORAGE_ROOT_DIR.resolve()
    clean_rel = rel_path.replace("\\", "/").strip().lstrip("/")

    # 判断是否为工作流或模板目录下的文件
    if clean_rel.startswith("工作流/") or "模板" in clean_rel:
        if for_write:
            raise HTTPException(403, "工作流核心模板受保护，禁止写入或删除")
        # 只读模式下允许解析工作流内部文件
        target_path = (root_dir / clean_rel).resolve()
        if not target_path.is_relative_to(root_dir):
            raise HTTPException(400, "非法的文件路径（路径穿越拦截）")
    else:
        # 去除可能携带的 "材料仓库/" 前缀
        if clean_rel.startswith("材料仓库/"):
            clean_rel = clean_rel[len("材料仓库/"):]
        target_path = (store_dir / clean_rel).resolve()
        if not target_path.is_relative_to(store_dir):
            raise HTTPException(400, "非法的文件路径（路径穿越拦截）")

    if must_exist and not target_path.exists():
        raise HTTPException(404, f"文件不存在: {clean_rel}")

    return target_path


def list_report_files() -> List[Dict[str, Any]]:
    """
    列出空间中的所有 HTML 报告文件与 XLSX 数据文件。
    1. 扫描材料仓库中的所有汇报与明细文件（is_template=False）；
    2. 兼容扫描工作流模板目录中的演示引擎母版（is_template=True）。
    """
    store_dir = ensure_storage_dir()
    file_list: List[Dict[str, Any]] = []
    allowed_exts = ('.html', '.htm', '.xlsx')

    # 1. 扫描材料仓库目录
    if store_dir.exists():
        for f in os.listdir(store_dir):
            lower_f = f.lower()
            if lower_f.endswith(allowed_exts):
                full_path = store_dir / f
                if full_path.is_file():
                    try:
                        stat = full_path.stat()
                        is_excel = lower_f.endswith('.xlsx')
                        file_list.append({
                            "name": f,
                            "rel_path": f,
                            "size": stat.st_size,
                            "size_formatted": format_file_size(stat.st_size),
                            "updated_at": format_beijing_time(stat.st_mtime),
                            "created_at": format_beijing_time(stat.st_ctime),
                            "is_template": False,
                            "kind": "excel" if is_excel else "html",
                            "ext": ".xlsx" if is_excel else ".html",
                        })
                    except Exception:
                        continue

    # 2. 扫描工作流模板目录
    if WORKFLOW_DIR.exists():
        for root, _, files in os.walk(WORKFLOW_DIR):
            for f in files:
                lower_f = f.lower()
                if lower_f.endswith(allowed_exts):
                    full_path = Path(root) / f
                    if full_path.is_file():
                        try:
                            stat = full_path.stat()
                            rel_to_root = full_path.relative_to(STORAGE_ROOT_DIR).as_posix()
                            is_excel = lower_f.endswith('.xlsx')
                            file_list.append({
                                "name": f,
                                "rel_path": rel_to_root,
                                "size": stat.st_size,
                                "size_formatted": format_file_size(stat.st_size),
                                "updated_at": format_beijing_time(stat.st_mtime),
                                "created_at": format_beijing_time(stat.st_ctime),
                                "is_template": True,
                                "kind": "excel" if is_excel else "html",
                                "ext": ".xlsx" if is_excel else ".html",
                            })
                        except Exception:
                            continue

    # 按最后修改时间倒序排列
    file_list.sort(key=lambda x: x["updated_at"], reverse=True)
    return file_list


def save_report_html(filename: str, content: str) -> Dict[str, Any]:
    """
    将分析材料一键保存至【材料仓库】。
    """
    if not content or not content.strip():
        raise HTTPException(400, "HTML 内容不能为空")

    safe_name = sanitize_filename(filename)
    target_path = resolve_safe_path(safe_name, must_exist=False, for_write=True)

    try:
        target_path.write_text(content, encoding="utf-8")
        stat = target_path.stat()
        return {
            "ok": True,
            "name": safe_name,
            "rel_path": safe_name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "is_template": False,
            "message": "已保存至材料仓库"
        }
    except Exception as exc:
        raise HTTPException(500, f"保存文件失败: {str(exc)}") from exc


async def upload_report_html(file: UploadFile) -> Dict[str, Any]:
    """
    上传外部 HTML 报告文件并保存至【材料仓库】。
    """
    if not file.filename:
        raise HTTPException(400, "未选择上传文件")
        
    safe_name = sanitize_filename(file.filename)
    if not (safe_name.lower().endswith(".html") or safe_name.lower().endswith(".htm")):
        raise HTTPException(400, "仅支持上传 .html 或 .htm 格式的分析汇报文件")

    target_path = resolve_safe_path(safe_name, must_exist=False, for_write=True)
    
    try:
        data = await file.read()
        target_path.write_bytes(data)
        stat = target_path.stat()
        return {
            "ok": True,
            "name": safe_name,
            "rel_path": safe_name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "is_template": False,
            "message": "已上传至材料仓库"
        }
    except Exception as exc:
        raise HTTPException(500, f"上传文件失败: {str(exc)}") from exc


def get_report_html_content(rel_path: str) -> Dict[str, Any]:
    """
    读取指定相对路径的 HTML 文本内容。
    """
    target_path = resolve_safe_path(rel_path, must_exist=True, for_write=False)
    if not target_path.is_file():
        raise HTTPException(400, "目标路径不是有效文件")

    try:
        content = target_path.read_text(encoding="utf-8", errors="replace")
        return {
            "name": target_path.name,
            "rel_path": rel_path.replace("\\", "/"),
            "content": content
        }
    except Exception as exc:
        raise HTTPException(500, f"读取文件内容失败: {str(exc)}") from exc


def get_report_file_path(rel_path: str) -> Path:
    """
    获取安全的文件路径供 FileResponse 下载。
    """
    target_path = resolve_safe_path(rel_path, must_exist=True, for_write=False)
    if not target_path.is_file():
        raise HTTPException(400, "目标路径不是有效文件")
    return target_path


def delete_report_file(rel_path: str) -> Dict[str, Any]:
    """
    删除材料仓库中的 HTML 报告文件，工作流模板文件禁止删除。
    """
    target_path = resolve_safe_path(rel_path, must_exist=True, for_write=True)
    
    try:
        target_path.unlink()
        return {
            "ok": True,
            "rel_path": rel_path,
            "message": "材料仓库文件删除成功"
        }
    except Exception as exc:
        raise HTTPException(500, f"删除文件失败: {str(exc)}") from exc


def rename_report_file(rel_path: str, new_name: str) -> Dict[str, Any]:
    """
    重命名材料仓库中的文件（仅限非模板材料）。
    自动保持原文件的有效扩展名（如 .html 或 .xlsx），防止破坏文件格式。
    """
    # 严格安全解析旧路径（for_write=True 强制限制在材料仓库，拒绝工作流核心模板）
    old_path = resolve_safe_path(rel_path, must_exist=True, for_write=True)
    if not old_path.is_file():
        raise HTTPException(400, "原路径不是有效文件")

    old_ext = old_path.suffix.lower()  # 如 .xlsx 或 .html / .htm
    clean_new = (new_name or "").strip()
    if not clean_new:
        raise HTTPException(400, "新文件名不能为空")

    # 去除可能携带的路径符号
    clean_new = os.path.basename(clean_new.replace("\\", "/")).strip()
    clean_new = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_new).strip()
    if not clean_new or clean_new in ('.', '..'):
        raise HTTPException(400, "新文件名不合法")

    # 规范化扩展名：
    # 1. 如果用户未提供扩展名，自动追加原扩展名 old_ext；
    # 2. 如果用户提供了已知扩展名但与原扩展名不一致，自动纠正剥离并补回原扩展名，防止误将 xlsx 改为 html
    lower_new = clean_new.lower()
    for ext in ('.xlsx', '.html', '.htm'):
        if lower_new.endswith(ext):
            clean_new = clean_new[:-len(ext)]
            break

    final_name = f"{clean_new}{old_ext}"
    safe_new_name = sanitize_filename(final_name)

    store_dir = ensure_storage_dir()
    new_path = (store_dir / safe_new_name).resolve()

    if not new_path.is_relative_to(store_dir):
        raise HTTPException(400, "非法的新文件名（路径穿越拦截）")

    # 如果新文件名与旧文件名完全相同，直接返回成功元数据
    if new_path == old_path:
        stat = new_path.stat()
        return {
            "ok": True,
            "old_path": rel_path,
            "name": new_path.name,
            "rel_path": new_path.name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "message": "文件名未发生变更"
        }

    if new_path.exists():
        raise HTTPException(400, f"材料仓库中已存在同名文件【{new_path.name}】，请更换其他名称")

    try:
        old_path.rename(new_path)
        stat = new_path.stat()
        is_excel = safe_new_name.lower().endswith('.xlsx')
        return {
            "ok": True,
            "old_path": rel_path,
            "name": new_path.name,
            "rel_path": new_path.name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "kind": "excel" if is_excel else "html",
            "message": f"文件已成功重命名为【{new_path.name}】"
        }
    except Exception as exc:
        raise HTTPException(500, f"重命名文件失败: {str(exc)}") from exc
