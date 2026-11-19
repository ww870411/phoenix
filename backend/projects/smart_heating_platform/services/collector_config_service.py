# -*- coding: utf-8 -*-
"""
智慧供热旁路采集配置与 Cookie 管理服务。

职责：
1. 原子持久化采集配置与源站 Session Cookie 至
   `DATA_DIRECTORY/projects/smart_heating_platform/config/collector_settings.json`；
2. 对前端读取请求做 Cookie 脱敏，避免会话凭据明文暴露；
3. 提供单线程串行、带间隔保护的只读连通性与 Cookie 有效性探测。
"""

from __future__ import annotations

import calendar
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from backend.config import DATA_DIRECTORY

PROJECT_KEY = "smart_heating_platform"
EAST_8 = timezone(timedelta(hours=8))

PUBLIC_SOURCE_URL = "http://124.93.31.19:6688"
INTRANET_SOURCE_URL = "http://192.168.1.206:6688"

_CONFIG_LOCK = threading.RLock()

DEFAULT_COLLECTOR_SETTINGS: Dict[str, Any] = {
    "source_mode": "public",  # public | intranet | custom
    "custom_base_url": "",
    "cookie": "",
    "scheduler_enabled": False,
    "snapshot_interval_minutes": 15,  # 15 | 30 | 60
    "hourly_offset_minutes": 0,
    "request_interval_seconds": 0.8,
    "request_timeout_seconds": 15.0,
    "table_bottom_sync_hours": 6,
    "updated_at": "",
    "updated_by": "",
    "last_test_result": None,
}


def _now_east8_str() -> str:
    """返回东八区当前时间字符串。"""
    return datetime.now(EAST_8).strftime("%Y-%m-%d %H:%M:%S")


def get_collector_config_path() -> Path:
    """获取采集配置 JSON 文件路径。"""
    config_dir = (Path(DATA_DIRECTORY) / "projects" / PROJECT_KEY / "config").resolve()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "collector_settings.json"


def normalize_cookie_input(raw_cookie: str) -> str:
    """规范化用户粘贴的 Cookie（兼容去除 Cookie: 前缀及补全 session=）。"""
    text = str(raw_cookie or "").strip()
    if not text:
        return ""
    if text.lower().startswith("cookie:"):
        text = text.split(":", 1)[1].strip()
    if "=" not in text and text.startswith("."):
        text = f"session={text}"
    return text


def mask_cookie(cookie: str) -> str:
    """对 Cookie 做脱敏掩码展示，保留首尾片段以便人工核对是否一致。"""
    if not cookie:
        return ""
    if len(cookie) <= 20:
        return f"{cookie[:4]}***{cookie[-4:]}" if len(cookie) > 8 else "***"
    return f"{cookie[:14]}...***...{cookie[-8:]}"


def validate_base_url(url: str) -> str:
    """校验 HTTP/HTTPS 基地址合法性并返回去尾斜杠结果。"""
    cleaned = str(url or "").strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("源站地址必须是合法的 http:// 或 https:// 地址")
    return cleaned


def resolve_effective_base_url(cfg: Dict[str, Any]) -> str:
    """根据当前 source_mode 解析实际采集基地址。"""
    mode = str(cfg.get("source_mode") or "public").strip().lower()
    if mode == "intranet":
        return INTRANET_SOURCE_URL
    if mode == "custom":
        custom = str(cfg.get("custom_base_url") or "").strip()
        if not custom:
            raise ValueError("已选择自定义地址模式，请先填写源站 URL")
        return validate_base_url(custom)
    return PUBLIC_SOURCE_URL


def _read_raw_config() -> Dict[str, Any]:
    """线程安全读取完整配置（含内部 Cookie，仅限后端服务内部使用）。"""
    path = get_collector_config_path()
    with _CONFIG_LOCK:
        cfg = dict(DEFAULT_COLLECTOR_SETTINGS)
        if path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    cfg.update(saved)
            except Exception:
                # 配置损坏时回退默认值，防止接口崩溃
                pass
        return cfg


def _write_raw_config(cfg: Dict[str, Any]) -> None:
    """线程安全原子写回配置文件（UTF-8 无 BOM）。"""
    path = get_collector_config_path()
    tmp_path = path.with_suffix(".json.tmp")
    with _CONFIG_LOCK:
        tmp_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)


def _to_public_view(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """将内部配置转为脱敏后的前端展示结构。"""
    cookie = str(cfg.get("cookie") or "")
    try:
        effective_url = resolve_effective_base_url(cfg)
    except ValueError:
        effective_url = PUBLIC_SOURCE_URL

    return {
        "source_mode": cfg.get("source_mode", "public"),
        "custom_base_url": cfg.get("custom_base_url", ""),
        "effective_base_url": effective_url,
        "public_preset_url": PUBLIC_SOURCE_URL,
        "intranet_preset_url": INTRANET_SOURCE_URL,
        "has_cookie": bool(cookie),
        "cookie_masked": mask_cookie(cookie),
        "cookie_length": len(cookie),
        "scheduler_enabled": bool(cfg.get("scheduler_enabled", False)),
        "snapshot_interval_minutes": int(cfg.get("snapshot_interval_minutes", 15)),
        "hourly_offset_minutes": int(cfg.get("hourly_offset_minutes", 0)),
        "request_interval_seconds": float(cfg.get("request_interval_seconds", 0.8)),
        "request_timeout_seconds": float(cfg.get("request_timeout_seconds", 15.0)),
        "table_bottom_sync_hours": int(cfg.get("table_bottom_sync_hours", 6)),
        "updated_at": cfg.get("updated_at") or "",
        "updated_by": cfg.get("updated_by") or "",
        "last_test_result": cfg.get("last_test_result"),
    }


def get_collector_settings_view() -> Dict[str, Any]:
    """获取脱敏后的采集设置（供管理前端展示）。"""
    return _to_public_view(_read_raw_config())


def update_collector_settings(payload: Dict[str, Any], operator: str) -> Dict[str, Any]:
    """更新并持久化采集设置与 Cookie（支持局部更新及仅清空/保留既有 Cookie）。"""
    with _CONFIG_LOCK:
        cfg = _read_raw_config()

        if "source_mode" in payload and payload["source_mode"] is not None:
            mode = str(payload["source_mode"]).strip().lower()
            if mode not in ("public", "intranet", "custom"):
                raise ValueError("source_mode 仅支持 public / intranet / custom")
            cfg["source_mode"] = mode

        if "custom_base_url" in payload and payload["custom_base_url"] is not None:
            raw_custom = str(payload["custom_base_url"]).strip()
            cfg["custom_base_url"] = validate_base_url(raw_custom) if raw_custom else ""

        if cfg["source_mode"] == "custom" and not cfg.get("custom_base_url"):
            raise ValueError("选择自定义源站模式时，custom_base_url 不能为空")

        if payload.get("clear_cookie"):
            cfg["cookie"] = ""
        elif payload.get("cookie") is not None:
            normalized = normalize_cookie_input(str(payload["cookie"]))
            if normalized:
                cfg["cookie"] = normalized

        if "scheduler_enabled" in payload and payload["scheduler_enabled"] is not None:
            cfg["scheduler_enabled"] = bool(payload["scheduler_enabled"])

        if "snapshot_interval_minutes" in payload and payload["snapshot_interval_minutes"] is not None:
            snap_min = int(payload["snapshot_interval_minutes"])
            if snap_min not in (15, 30, 60):
                raise ValueError("采样频率仅支持 15 / 30 / 60 分钟")
            cfg["snapshot_interval_minutes"] = snap_min

        if "hourly_offset_minutes" in payload and payload["hourly_offset_minutes"] is not None:
            offset = int(payload["hourly_offset_minutes"])
            if not 0 <= offset <= 59:
                raise ValueError("整点延迟分钟数必须在 0~59 之间")
            cfg["hourly_offset_minutes"] = offset

        if "request_interval_seconds" in payload and payload["request_interval_seconds"] is not None:
            interval = round(float(payload["request_interval_seconds"]), 2)
            if not 0.5 <= interval <= 5.0:
                raise ValueError("单线程请求间隔必须在 0.5~5.0 秒之间，以保护源站服务")
            cfg["request_interval_seconds"] = interval

        if "request_timeout_seconds" in payload and payload["request_timeout_seconds"] is not None:
            timeout = round(float(payload["request_timeout_seconds"]), 1)
            if not 3.0 <= timeout <= 60.0:
                raise ValueError("单次请求超时必须在 3~60 秒之间")
            cfg["request_timeout_seconds"] = timeout

        if "table_bottom_sync_hours" in payload and payload["table_bottom_sync_hours"] is not None:
            sync_hours = int(payload["table_bottom_sync_hours"])
            if not 1 <= sync_hours <= 24:
                raise ValueError("累计表底校准周期必须在 1~24 小时之间")
            cfg["table_bottom_sync_hours"] = sync_hours

        cfg["updated_at"] = _now_east8_str()
        cfg["updated_by"] = str(operator or "").strip()
        _write_raw_config(cfg)
        return _to_public_view(cfg)


def _probe_endpoint(
    client: httpx.Client,
    name: str,
    url: str,
    form_data: Optional[Dict[str, str]],
    headers: Dict[str, str],
) -> Dict[str, Any]:
    """执行单次安全的只读 POST 探测并提取摘要指标。"""
    started = time.perf_counter()
    try:
        resp = client.post(url, data=form_data, headers=headers)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        if resp.status_code != 200:
            return {
                "name": name,
                "ok": False,
                "status_code": resp.status_code,
                "elapsed_ms": elapsed_ms,
                "count": 0,
                "detail": f"HTTP {resp.status_code}" + ("（未登录或 Cookie 已失效）" if resp.status_code in (302, 401, 403, 500) else ""),
            }
        data = resp.json()
        if isinstance(data, dict):
            if isinstance(data.get("data"), list):
                count = len(data["data"])
                detail = f"返回记录 {count} 条"
            else:
                count = sum(len(v) for v in data.values() if isinstance(v, (dict, list)))
                detail = f"返回字典 {len(data)} 组，合计 {count} 条"
        elif isinstance(data, list):
            count = len(data)
            detail = f"返回列表 {count} 条"
        elif data is None:
            count = 0
            detail = "返回空结果 (null)"
        else:
            count = 0
            detail = "返回结构非 JSON 数组/字典"
        return {
            "name": name,
            "ok": True,
            "status_code": 200,
            "elapsed_ms": elapsed_ms,
            "count": count,
            "detail": detail,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "name": name,
            "ok": False,
            "status_code": None,
            "elapsed_ms": elapsed_ms,
            "count": 0,
            "detail": f"{type(exc).__name__}: {str(exc)[:160]}",
        }


def test_collector_connectivity(
    override_cookie: Optional[str] = None,
    override_source_mode: Optional[str] = None,
    override_custom_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    单线程顺序测试源站只读接口与当前 Cookie 有效性。

    注意：绝不在返回结果中回显明文 Cookie。
    """
    cfg = _read_raw_config()
    probe_cfg = dict(cfg)
    if override_source_mode:
        probe_cfg["source_mode"] = str(override_source_mode).strip().lower()
    if override_custom_base_url is not None:
        probe_cfg["custom_base_url"] = str(override_custom_base_url).strip()

    base_url = resolve_effective_base_url(probe_cfg)
    raw_cookie = override_cookie if (override_cookie is not None and str(override_cookie).strip()) else cfg.get("cookie", "")
    effective_cookie = normalize_cookie_input(str(raw_cookie or ""))

    interval = max(0.5, float(cfg.get("request_interval_seconds", 0.8)))
    timeout = float(cfg.get("request_timeout_seconds", 15.0))

    base_headers = {
        "User-Agent": "Phoenix-SmartHeating-Probe/1.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    checks: List[Dict[str, Any]] = []
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        # 1. 免 Cookie：上游工况五大字典
        checks.append(
            _probe_endpoint(
                client,
                "上游工况 (/gk_get_data/)",
                f"{base_url}/gk_get_data/",
                None,
                base_headers,
            )
        )
        time.sleep(interval)

        # 2. 免 Cookie：242 站一网快照与时间戳
        checks.append(
            _probe_endpoint(
                client,
                "换热站一网 (/get_yw_data/1)",
                f"{base_url}/get_yw_data/1",
                {"yw_selected": "1"},
                base_headers,
            )
        )

        # 3. 需 Cookie：2,097+ 户居民室温全量与 464 户商业用户日耗量
        if effective_cookie:
            cookie_headers = {**base_headers, "Cookie": effective_cookie}
            time.sleep(interval)
            checks.append(
                _probe_endpoint(
                    client,
                    "居民室温 (/jumin/)",
                    f"{base_url}/jumin/",
                    {"department_name": "0", "filter_level": "0", "isDownload": "1"},
                    cookie_headers,
                )
            )
            time.sleep(interval)
            now_e8 = datetime.now(EAST_8)
            last_day = calendar.monthrange(now_e8.year, now_e8.month)[1]
            checks.append(
                _probe_endpoint(
                    client,
                    "商户日报 (/getall_bb_shrb/)",
                    f"{base_url}/getall_bb_shrb/",
                    {
                        "selectof1": "0",
                        "selectof2": "0",
                        "selectof3": "1",
                        "options4": f"{now_e8.year}{now_e8.month}",
                        "lastDay": str(last_day),
                    },
                    cookie_headers,
                )
            )

    public_ok = all(item["ok"] for item in checks[:2])
    cookie_checks = checks[2:]
    if not effective_cookie:
        cookie_status = "missing"
        cookie_ok = False
    else:
        cookie_ok = all(item["ok"] for item in cookie_checks)
        cookie_status = "valid" if cookie_ok else "invalid"

    result = {
        "tested_at": _now_east8_str(),
        "base_url": base_url,
        "public_ok": public_ok,
        "cookie_status": cookie_status,
        "cookie_ok": cookie_ok,
        "checks": checks,
    }

    with _CONFIG_LOCK:
        latest_cfg = _read_raw_config()
        latest_cfg["last_test_result"] = result
        _write_raw_config(latest_cfg)

    return result
