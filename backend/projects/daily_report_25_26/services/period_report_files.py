# -*- coding: utf-8 -*-
"""
周期运行汇报 HTML 材料仓库管理服务。

职责：
1. 管理 backend_data/projects/daily_report_25_26/period_report/材料仓库 目录下的 HTML 汇报文件；
2. 提供文件列表查询、安全读取、保存、上传、下载与删除功能；
3. 联动识别工作流（工作流/1.html模板与使用说明）中的演示引擎母版，提供在线演示播放支持与防误删保护；
4. 实施严格的路径防穿越校验，确保仅限合法 HTML 文件的受控操作。
"""

import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, UploadFile
from backend.config import DATA_DIRECTORY

# 东八区（北京时间 UTC+8）时区定义
BEIJING_TZ = timezone(timedelta(hours=8))

# 支持的图片扩展名集合
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp')


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

# 页面默认显示模式配置文件路径
DISPLAY_CONFIG_PATH = (STORAGE_ROOT_DIR / "display_config.json").resolve()


def get_display_config() -> Dict[str, Any]:
    """
    获取生产运行汇报页面的默认显示配置。
    若未设定，默认采用动态生成页（mode="generated"）。
    """
    if DISPLAY_CONFIG_PATH.exists():
        try:
            content = DISPLAY_CONFIG_PATH.read_text(encoding="utf-8")
            data = json.loads(content)
            mode = data.get("mode", "generated")
            target_file = data.get("target_file", "")
            return {
                "mode": mode if mode in ("generated", "custom_html") else "generated",
                "target_file": target_file if mode == "custom_html" else "",
                "updated_by": data.get("updated_by", ""),
                "updated_at": data.get("updated_at", ""),
            }
        except Exception:
            pass

    return {
        "mode": "generated",
        "target_file": "",
        "updated_by": "",
        "updated_at": "",
    }


def set_display_config(mode: str, target_file: str = "", operator: str = "") -> Dict[str, Any]:
    """
    由 Global_admin 设定生产运行汇报页面的默认打开内容。
    mode 可选：
      - 'generated': 默认自选周期图文动态生成汇报；
      - 'custom_html': 指定材料空间中的某份 HTML 汇报文档作为默认打开页。
    """
    clean_mode = (mode or "").strip().lower()
    if clean_mode not in ("generated", "custom_html"):
        raise HTTPException(400, "不支持的默认显示模式，仅支持 'generated' 或 'custom_html'")

    final_target = ""
    if clean_mode == "custom_html":
        clean_file = (target_file or "").strip()
        if not clean_file:
            raise HTTPException(400, "请指定材料空间中的 HTML 文件作为默认展示内容")

        # 检查指定文件在材料空间或工作流空间中的存在性与安全性
        safe_path = resolve_safe_path(clean_file, must_exist=True, for_write=False)
        if safe_path.suffix.lower() not in ('.html', '.htm'):
            raise HTTPException(400, "指定的默认展示文件必须为 HTML 格式")
        final_target = clean_file

    config_data = {
        "mode": clean_mode,
        "target_file": final_target,
        "updated_by": operator or "Global_admin",
        "updated_at": format_beijing_time(datetime.now().timestamp()),
    }

    try:
        STORAGE_ROOT_DIR.mkdir(parents=True, exist_ok=True)
        DISPLAY_CONFIG_PATH.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return config_data
    except Exception as exc:
        raise HTTPException(500, f"保存默认展示配置失败: {str(exc)}") from exc


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
    
    # 支持 .html, .htm, .xlsx 与各类常见图片格式
    lower_name = name.lower()
    if lower_name.endswith(".xlsx") or any(lower_name.endswith(ext) for ext in IMAGE_EXTS):
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
    列出空间中的所有 HTML 报告文件、XLSX 数据文件与各类图片文件。
    1. 递归扫描材料仓库中的所有汇报与明细文件（is_template=False），包含子文件夹识别；
    2. 兼容扫描工作流模板目录中的演示引擎母版（is_template=True）。
    """
    store_dir = ensure_storage_dir()
    file_list: List[Dict[str, Any]] = []
    allowed_exts = ('.html', '.htm', '.xlsx', *IMAGE_EXTS)

    # 1. 递归扫描材料仓库目录
    if store_dir.exists():
        for root, dirs, files in os.walk(store_dir):
            # 排除隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.'):
                    continue
                lower_f = f.lower()
                if lower_f.endswith(allowed_exts):
                    full_path = Path(root) / f
                    if full_path.is_file():
                        try:
                            stat = full_path.stat()
                            rel_to_store = full_path.relative_to(store_dir).as_posix()
                            parent_rel = full_path.parent.relative_to(store_dir).as_posix()
                            folder_name = "" if parent_rel == "." else parent_rel
                            is_excel = lower_f.endswith('.xlsx')
                            is_img = any(lower_f.endswith(ext) for ext in IMAGE_EXTS)
                            file_kind = "excel" if is_excel else ("image" if is_img else "html")
                            file_list.append({
                                "name": f,
                                "rel_path": rel_to_store,
                                "folder": folder_name,
                                "size": stat.st_size,
                                "size_formatted": format_file_size(stat.st_size),
                                "updated_at": format_beijing_time(stat.st_mtime),
                                "created_at": format_beijing_time(stat.st_ctime),
                                "is_template": False,
                                "kind": file_kind,
                                "ext": full_path.suffix.lower(),
                            })
                        except Exception:
                            continue

    # 2. 扫描工作流模板目录
    if WORKFLOW_DIR.exists():
        for root, dirs, files in os.walk(WORKFLOW_DIR):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.'):
                    continue
                lower_f = f.lower()
                if lower_f.endswith(allowed_exts):
                    full_path = Path(root) / f
                    if full_path.is_file():
                        try:
                            stat = full_path.stat()
                            rel_to_root = full_path.relative_to(STORAGE_ROOT_DIR).as_posix()
                            parent_rel = full_path.parent.relative_to(WORKFLOW_DIR).as_posix()
                            folder_name = "" if parent_rel == "." else parent_rel
                            is_excel = lower_f.endswith('.xlsx')
                            is_img = any(lower_f.endswith(ext) for ext in IMAGE_EXTS)
                            file_kind = "excel" if is_excel else ("image" if is_img else "html")
                            file_list.append({
                                "name": f,
                                "rel_path": rel_to_root,
                                "folder": folder_name,
                                "size": stat.st_size,
                                "size_formatted": format_file_size(stat.st_size),
                                "updated_at": format_beijing_time(stat.st_mtime),
                                "created_at": format_beijing_time(stat.st_ctime),
                                "is_template": True,
                                "kind": file_kind,
                                "ext": full_path.suffix.lower(),
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
    上传外部 HTML 报告或图片材料文件并保存至【材料仓库】。
    """
    if not file.filename:
        raise HTTPException(400, "未选择上传文件")
        
    safe_name = sanitize_filename(file.filename)
    allowed_upload_exts = ('.html', '.htm', *IMAGE_EXTS)
    if not any(safe_name.lower().endswith(ext) for ext in allowed_upload_exts):
        raise HTTPException(400, "仅支持上传 HTML 分析汇报与图片文件 (.jpg, .jpeg, .png, .gif, .webp, .svg, .bmp)")

    target_path = resolve_safe_path(safe_name, must_exist=False, for_write=True)
    
    try:
        data = await file.read()
        target_path.write_bytes(data)
        stat = target_path.stat()
        is_img = any(safe_name.lower().endswith(ext) for ext in IMAGE_EXTS)
        return {
            "ok": True,
            "name": safe_name,
            "rel_path": safe_name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "is_template": False,
            "kind": "image" if is_img else "html",
            "ext": target_path.suffix.lower(),
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
    for ext in ('.xlsx', '.html', '.htm', *IMAGE_EXTS):
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
        is_excel = safe_new_name.lower().endswith('.xlsx')
        is_img = any(safe_new_name.lower().endswith(ext) for ext in IMAGE_EXTS)
        return {
            "ok": True,
            "old_path": rel_path,
            "name": new_path.name,
            "rel_path": new_path.name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "kind": "excel" if is_excel else ("image" if is_img else "html"),
            "ext": new_path.suffix.lower(),
            "message": "文件名未发生变更"
        }

    if new_path.exists():
        raise HTTPException(400, f"材料仓库中已存在同名文件【{new_path.name}】，请更换其他名称")

    try:
        old_path.rename(new_path)
        stat = new_path.stat()
        is_excel = safe_new_name.lower().endswith('.xlsx')
        is_img = any(safe_new_name.lower().endswith(ext) for ext in IMAGE_EXTS)
        return {
            "ok": True,
            "old_path": rel_path,
            "name": new_path.name,
            "rel_path": new_path.name,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "created_at": format_beijing_time(stat.st_ctime),
            "updated_at": format_beijing_time(stat.st_mtime),
            "kind": "excel" if is_excel else ("image" if is_img else "html"),
            "ext": new_path.suffix.lower(),
            "message": f"文件已成功重命名为【{new_path.name}】"
        }
    except Exception as exc:
        raise HTTPException(500, f"重命名文件失败: {str(exc)}") from exc


# ==================== 空间目录管理与跨空间/空间内传输服务 ====================

def get_space_root(space: str) -> Path:
    """根据空间标识返回物理根目录。"""
    clean_space = (space or "").strip().lower()
    if clean_space in ("material", "材料空间", "材料仓库"):
        return ensure_storage_dir()
    elif clean_space in ("workflow", "工作流", "工作流目录"):
        WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
        return WORKFLOW_DIR
    else:
        raise HTTPException(400, f"未知的空间类型: {space}，仅支持 'material' 或 'workflow'")


def list_space_folders(space: str) -> List[Dict[str, str]]:
    """
    列出指定空间（材料空间或工作流空间）中的所有文件夹。
    根目录用 path="" 表示。
    """
    base_dir = get_space_root(space)
    folders: List[Dict[str, str]] = [
        {
            "name": "材料仓库根目录" if space == "material" else "工作流根目录",
            "path": ""
        }
    ]

    if base_dir.exists():
        for root, dirs, _ in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for d in sorted(dirs):
                full_d = Path(root) / d
                rel_p = full_d.relative_to(base_dir).as_posix()
                folders.append({
                    "name": rel_p,
                    "path": rel_p
                })

    return folders


def create_space_folder(space: str, parent_folder: str = "", folder_name: str = "") -> Dict[str, Any]:
    """在指定空间（材料空间或工作流空间）中创建新的子文件夹。"""
    base_dir = get_space_root(space)
    clean_name = (folder_name or "").strip()
    if not clean_name:
        raise HTTPException(400, "文件夹名称不能为空")

    clean_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', clean_name).strip()
    if not clean_name or clean_name in ('.', '..'):
        raise HTTPException(400, "文件夹名称不合法")

    clean_parent = (parent_folder or "").replace("\\", "/").strip().strip("/")
    if clean_parent in (".", "根目录", "全部"):
        clean_parent = ""

    target_parent = (base_dir / clean_parent).resolve() if clean_parent else base_dir
    if not target_parent.is_relative_to(base_dir):
        raise HTTPException(400, "非法的父文件夹路径（路径穿越拦截）")

    new_dir = (target_parent / clean_name).resolve()
    if not new_dir.is_relative_to(base_dir):
        raise HTTPException(400, "非法的新建目录路径（路径穿越拦截）")

    if new_dir.exists():
        raise HTTPException(400, f"目录【{clean_name}】已存在")

    try:
        new_dir.mkdir(parents=True, exist_ok=False)
        rel_to_base = new_dir.relative_to(base_dir).as_posix()
        return {
            "ok": True,
            "space": space,
            "name": clean_name,
            "rel_path": rel_to_base,
            "message": f"目录【{clean_name}】创建成功"
        }
    except Exception as exc:
        raise HTTPException(500, f"创建目录失败: {str(exc)}") from exc


def transfer_space_file(
    source_space: str,
    source_path: str,
    target_space: str,
    target_folder: str = "",
    action: str = "copy",
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    跨空间（材料空间 ⇄ 工作流目录空间）或在各自空间内部传输/移动文件。
    支持：
      - action="copy": 复制文件（保留原文件，目标生成副本）
      - action="move": 移动文件（移至目标文件夹，原位置删除）
    如果目标同名且 overwrite=False，则自动重命名追加副本序号，保障文件安全。
    """
    src_root = get_space_root(source_space)
    dst_root = get_space_root(target_space)

    clean_action = (action or "copy").strip().lower()
    if clean_action not in ("copy", "move"):
        raise HTTPException(400, "不支持的操作方式，仅支持 'copy'（复制）或 'move'（移动）")

    clean_src = (source_path or "").replace("\\", "/").strip().lstrip("/")
    # 去除可能携带的所属空间前缀
    if clean_src.startswith("材料仓库/"):
        clean_src = clean_src[len("材料仓库/"):]
    elif clean_src.startswith("工作流/"):
        clean_src = clean_src[len("工作流/"):]

    src_full = (src_root / clean_src).resolve()
    if not src_full.is_relative_to(src_root):
        raise HTTPException(400, "非法的源文件路径（路径穿越拦截）")

    if not src_full.exists():
        raise HTTPException(404, f"源文件不存在: {source_path}")

    if not src_full.is_file():
        raise HTTPException(400, "仅支持对具体文件进行传输或移动")

    # 目标目录解析
    clean_dst_folder = (target_folder or "").replace("\\", "/").strip().strip("/")
    if clean_dst_folder in (".", "根目录", "全部"):
        clean_dst_folder = ""
    if clean_dst_folder.startswith("材料仓库/"):
        clean_dst_folder = clean_dst_folder[len("材料仓库/"):]
    elif clean_dst_folder.startswith("工作流/"):
        clean_dst_folder = clean_dst_folder[len("工作流/"):]

    dst_dir = (dst_root / clean_dst_folder).resolve() if clean_dst_folder else dst_root
    if not dst_dir.is_relative_to(dst_root):
        raise HTTPException(400, "非法目标文件夹路径（路径穿越拦截）")

    dst_dir.mkdir(parents=True, exist_ok=True)

    # 计算目标文件完整路径与重名冲突处理
    target_file = dst_dir / src_full.name

    # 如果是同空间同目录下的移动，且文件名相同
    if src_full == target_file:
        if clean_action == "move":
            return {
                "ok": True,
                "action": clean_action,
                "source_space": source_space,
                "target_space": target_space,
                "target_rel_path": target_file.relative_to(dst_root).as_posix(),
                "target_name": target_file.name,
                "message": "源文件与目标文件路径完全一致，无需移动"
            }
        else:
            # 复制同名副本
            base_stem = src_full.stem
            ext = src_full.suffix
            counter = 1
            while target_file.exists():
                target_file = dst_dir / f"{base_stem}_副本{counter}{ext}"
                counter += 1
    elif target_file.exists() and not overwrite:
        # 目标已存在且未开启覆盖，自动重命名避开冲突
        base_stem = src_full.stem
        ext = src_full.suffix
        counter = 1
        while target_file.exists():
            target_file = dst_dir / f"{base_stem}_副本{counter}{ext}"
            counter += 1

    try:
        if clean_action == "move":
            shutil.move(str(src_full), str(target_file))
        else:
            shutil.copy2(str(src_full), str(target_file))

        rel_to_dst_space = target_file.relative_to(dst_root).as_posix()
        stat = target_file.stat()
        return {
            "ok": True,
            "action": clean_action,
            "source_space": source_space,
            "target_space": target_space,
            "source_name": src_full.name,
            "target_name": target_file.name,
            "target_rel_path": rel_to_dst_space,
            "target_folder": clean_dst_folder,
            "size": stat.st_size,
            "size_formatted": format_file_size(stat.st_size),
            "updated_at": format_beijing_time(stat.st_mtime),
            "message": f"文件已成功{'移动' if clean_action == 'move' else '复制'}至{target_space}空间"
        }
    except Exception as exc:
        raise HTTPException(500, f"文件传输失败: {str(exc)}") from exc
