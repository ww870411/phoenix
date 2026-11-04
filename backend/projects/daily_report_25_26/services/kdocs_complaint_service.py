# -*- coding: utf-8 -*-
"""
金山文档 (KDocs) 12345 投诉底表自动拉取与接入服务。

主要职责：
1. 维护金山文档共享链接 (share_link/share_id) 与用户身份授权凭据 (wps_sid Cookie)；
2. 提供免登录直链解析与连通性验证能力；
3. 支持流式下载最新 .xlsx 投诉底表并调用 complaint_statistics 进行自动统计。
"""

import json
import logging
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 配置文件持久化路径
CONFIG_DIR = Path("backend_data/projects/daily_report_25_26/config")
CONFIG_FILE = CONFIG_DIR / "kdocs_complaint_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "share_link": "https://www.kdocs.cn/l/cj8e1PTQW0uN",
    "share_id": "cj8e1PTQW0uN",
    "wps_sid": "V02SdZ9VTFSbBK9yGbjfj93LeD4okis00ab8df8f0012fc69e2",
    "description": "2026-2027年度市12345诉求件统计底表（金山文档共享）",
    "auto_sync_enabled": False,
    "last_sync_time": "",
    "last_test_status": "",
    "last_test_time": "",
    "last_test_message": "",
}


def _get_ssl_context():
    """获取宽容度较高的 SSL 上下文，防止根证书链过旧导致校验失败"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None


def extract_share_id(link_or_id: str) -> str:
    """
    从完整的金山文档链接中提取 share_id。
    支持形如：
      https://www.kdocs.cn/l/cj8e1PTQW0uN
      https://kdocs.cn/l/cj8e1PTQW0uN?xxx=1
      cj8e1PTQW0uN
    """
    cleaned = (link_or_id or "").strip()
    if not cleaned:
        return ""
    match = re.search(r"kdocs\.cn/l/([a-zA-Z0-9_-]+)", cleaned)
    if match:
        return match.group(1)
    if "/" in cleaned:
        return cleaned.split("/")[-1].split("?")[0].strip()
    return cleaned


def load_config() -> Dict[str, Any]:
    """读取金山文档配置，若不存在则初始化默认配置并落盘"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("初始化默认金山文档配置失败: %s", exc)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(saved)
        # 补全 share_id
        if not merged.get("share_id") and merged.get("share_link"):
            merged["share_id"] = extract_share_id(merged["share_link"])
        return merged
    except Exception as exc:
        logger.warning("读取金山文档配置文件失败 (%s)，使用默认配置", exc)
        return dict(DEFAULT_CONFIG)


def save_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    """保存或更新金山文档配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current.update(json.load(f))
        except Exception:
            pass
    current.update(updates)

    # 规范化 link 和 id
    if "share_link" in updates and updates["share_link"]:
        extracted = extract_share_id(updates["share_link"])
        if extracted:
            current["share_id"] = extracted
    elif "share_id" in updates and updates["share_id"]:
        current["share_id"] = extract_share_id(updates["share_id"])

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)

    return current


def test_kdocs_connectivity(
    share_link: Optional[str] = None,
    wps_sid: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    测试金山文档连接与凭证有效性。
    若传入参数则优先使用，否则使用当前保存的配置。
    返回 (是否成功, 提示信息, 详细元数据)
    """
    cfg = load_config()
    actual_link = (share_link or cfg.get("share_link") or "").strip()
    actual_sid = (wps_sid or cfg.get("wps_sid") or "").strip()
    share_id = extract_share_id(actual_link) or cfg.get("share_id") or ""

    if not share_id:
        return False, "未能识别有效的金山文档分享 ID，请检查链接格式", {}
    if not actual_sid:
        return False, "未配置 wps_sid Cookie 凭证，无法获取下载授权", {}

    api_url = f"https://www.kdocs.cn/api/v3/office/file/{share_id}/download"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"wps_sid={actual_sid}",
        "Referer": f"https://www.kdocs.cn/l/{share_id}",
    }

    req = urllib.request.Request(api_url, headers=headers)
    ctx = _get_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(content)
            download_url = data.get("download_url") or data.get("url")

            if not download_url:
                err_msg = data.get("msg") or data.get("result") or "未返回有效的下载直链"
                return False, f"金山文档接口响应异常: {err_msg}", data

            # 从直链中提取文件名和大小参数
            parsed_dl = urllib.parse.urlparse(download_url)
            query_params = urllib.parse.parse_qs(parsed_dl.query)
            file_size_str = query_params.get("file_size", ["0"])[0]
            try:
                file_size_mb = f"{int(file_size_str) / (1024 * 1024):.2f} MB"
            except Exception:
                file_size_mb = "未知大小"

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success_msg = f"连接测试成功！已成功获取下载直链，文件大小约 {file_size_mb}。"

            # 回写测试状态到配置
            save_config({
                "last_test_status": "SUCCESS",
                "last_test_time": now_str,
                "last_test_message": success_msg,
            })

            return True, success_msg, {
                "share_id": share_id,
                "file_size": file_size_mb,
                "test_time": now_str,
                "download_url_preview": download_url[:80] + "...",
            }

    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="ignore")
        err_msg = f"HTTP {http_err.code}"
        try:
            err_json = json.loads(err_body)
            if "msg" in err_json:
                err_msg += f" - {err_json['msg']}"
        except Exception:
            err_msg += f" - {err_body[:100]}"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fail_msg = f"测试失败 ({err_msg})，请检查 wps_sid 是否已过期或被登出。"
        save_config({
            "last_test_status": "FAILED",
            "last_test_time": now_str,
            "last_test_message": fail_msg,
        })
        return False, fail_msg, {"error_body": err_body}

    except Exception as exc:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fail_msg = f"网络请求异常: {exc}"
        save_config({
            "last_test_status": "ERROR",
            "last_test_time": now_str,
            "last_test_message": fail_msg,
        })
        return False, fail_msg, {}


def download_kdocs_workbook_bytes() -> Tuple[bytes, str]:
    """
    使用当前配置下载金山文档中的工作簿二进制字节流。
    返回 (文件字节流, 文件名)
    """
    cfg = load_config()
    share_id = cfg.get("share_id") or extract_share_id(cfg.get("share_link") or "")
    wps_sid = (cfg.get("wps_sid") or "").strip()

    if not share_id or not wps_sid:
        raise ValueError("金山文档配置不完整，缺少 share_id 或 wps_sid")

    api_url = f"https://www.kdocs.cn/api/v3/office/file/{share_id}/download"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"wps_sid={wps_sid}",
        "Referer": f"https://www.kdocs.cn/l/{share_id}",
    }

    ctx = _get_ssl_context()
    req = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        download_url = data.get("download_url") or data.get("url")
        if not download_url:
            raise ValueError(f"未能获取金山文档下载直链: {data}")

    # 解析建议文件名
    parsed = urllib.parse.urlparse(download_url)
    filename = "12345诉求件统计表.xlsx"
    cd = urllib.parse.parse_qs(parsed.query).get("response-content-disposition", [""])[0]
    if "filename" in cd:
        match = re.search(r"filename\*=utf-8''([^;&]+)", cd)
        if match:
            filename = urllib.parse.unquote(match.group(1))

    # 流式下载二进制文件
    dl_req = urllib.request.Request(download_url, headers={"User-Agent": headers["User-Agent"]})
    with urllib.request.urlopen(dl_req, timeout=40, context=ctx) as dl_resp:
        file_bytes = dl_resp.read()

    return file_bytes, filename
