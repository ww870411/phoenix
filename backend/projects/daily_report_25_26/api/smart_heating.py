# -*- coding: utf-8 -*-
"""
智慧供热平台内网数据接入与实时工况查询 API
提供：
1. /push: 供办公电脑中继 Agent 推送实时采集数据 (首站 sz_data, 电厂 dc_data, 换热站 yw_data)
2. /latest: 供前端看板查询最新工况数据 (严格限定 Global_admin 权限)
3. /status: 查询中继 Agent 推送连通状态与更新时效
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import DATA_DIRECTORY
from backend.services.auth_manager import AuthSession, get_current_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smart-heating", tags=["smart_heating"])
public_router = APIRouter(prefix="/smart-heating", tags=["smart_heating"])

DATA_DIR = (Path(DATA_DIRECTORY) / "projects" / "daily_report_25_26" / "smart_heating").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
LATEST_FILE = DATA_DIR / "latest.json"
HISTORY_LOG = DATA_DIR / "history.jsonl"
RELAY_CONFIG_FILE = DATA_DIR / "relay_config.json"

DEFAULT_PUSH_TOKEN = "phoenix_smart_heating_secret_2026"

# 默认服务器中继配置（默认开启转发中继，方便本地开发环境接收）
DEFAULT_RELAY_CONFIG = {
    "forward_enabled": True,  # 默认打开中继转发
    "forward_target_url": "http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/smart-heating/receive-relay",
    "push_token": DEFAULT_PUSH_TOKEN,
    "remote_server_url": "https://platform.smartview.top",
}


def _load_relay_config() -> Dict[str, Any]:
    """读取服务器中继配置，若不存在则生成默认配置"""
    if not RELAY_CONFIG_FILE.exists():
        try:
            with open(RELAY_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_RELAY_CONFIG, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("写入默认中继配置失败: %s", e)
        return dict(DEFAULT_RELAY_CONFIG)
    try:
        with open(RELAY_CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
            cfg = dict(DEFAULT_RELAY_CONFIG)
            cfg.update(saved)
            return cfg
    except Exception as e:
        logger.warning("读取中继配置异常: %s", e)
        return dict(DEFAULT_RELAY_CONFIG)


def _save_relay_config(cfg: Dict[str, Any]):
    """持久化保存中继配置"""
    with open(RELAY_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _forward_payload_task(payload_dict: Dict[str, Any], target_url: str, push_token: str):
    """
    后台异步任务：向目标端点发送中继 POST 请求
    非阻塞执行，自动附带 Win7/开发机安全 SSL 兼容及 5 秒超时保护
    """
    if not target_url:
        return
    try:
        import urllib.request
        import ssl
        data_bytes = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Phoenix-Server-Relay/2.0",
            "X-Push-Token": push_token,
        }
        req = urllib.request.Request(target_url, data=data_bytes, headers=headers, method="POST")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            code = response.getcode()
            logger.info("✔ 中继转发数据包成功 -> %s (HTTP %s)", target_url, code)
    except Exception as e:
        logger.warning("⚠️ 中继转发至 %s 暂未连通: %s", target_url, e)

# 错别字与历史别名标准化字典 (严格修正“xxx机进气”为“xxx机进汽”等)
TYPO_CORRECTIONS = {
    "北海#1机进气": "北海#1机进汽",
    "北海#2机进气": "北海#2机进汽",
    "北海#3机抽气": "北海#3机抽汽",
    "北海首站进气参数": "北海首站进汽参数",
    "磐海": "碧海",
    "喜临门": "壹临门",
    "鸿霖大厦": "鸿源大厦",
    "桥北": "振北",
    "黑嘴子(融创)": "黑狮子(融创)",
    "德政西": "德源西",
    "春和雲树里": "春和爱邻里",
    "机车西山村区": "机车西山小区",
    "保利天禧I01": "保利天禧01",
    "保利天禧I04": "保利天禧04",
    "保利禧岸": "保利璟岸",
    "海涵庄园": "海珀庄园",
}

SZ_CATEGORY_CORRECTIONS = {
    "#1首站": "北海#1首站",
    "#2首站": "北海#2首站",
    "#3首站": "北海水炉",
    "香海首站": "香海首站",
}


def _clean_point_records(records: List[Dict[str, Any]], default_level1: str) -> List[Dict[str, Any]]:
    """清洗测点名称（修正错别字）并自动补齐规范分类"""
    cleaned_list = []
    for item in records:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        raw_name = str(row.get("name") or "").strip()
        standard_name = TYPO_CORRECTIONS.get(raw_name, raw_name)
        row["name"] = standard_name
        row["level1"] = row.get("level1") or default_level1
        
        # 补齐或校准二级分类
        if default_level1 == "首站":
            cat = row.get("category") or ""
            row["level2"] = SZ_CATEGORY_CORRECTIONS.get(cat, cat or "北海#1首站")
            row["category"] = row["level2"]
        elif default_level1 == "电厂":
            row["level2"] = row.get("category") or ("香海电厂" if "香海" in standard_name else "北海电厂")
            row["category"] = row["level2"]
        elif default_level1 in ("一次网", "一网"):
            row["level1"] = "一次网"
            row["level2"] = row.get("center_name") or "华乐中心"
            row["center_name"] = row["level2"]
            
        cleaned_list.append(row)
    return cleaned_list


class SmartHeatingPushPayload(BaseModel):
    push_token: Optional[str] = Field(None, description="推送凭证密钥")
    relay_token: Optional[str] = Field(None, description="中继凭证密钥 (兼容字段)")
    token: Optional[str] = Field(None, description="通用凭证密钥 (兼容字段)")
    timestamp: Optional[str] = Field(None, description="中继采集时间")
    source: Optional[str] = Field("192.168.1.206:6688", description="数据源标识")
    sz_data: List[Dict[str, Any]] = Field(default_factory=list, description="首站与管网环路数据")
    dc_data: List[Dict[str, Any]] = Field(default_factory=list, description="电厂与热源机组数据")
    yw_data: List[Dict[str, Any]] = Field(default_factory=list, description="换热站一次网实时数据")


def _read_latest_data() -> Dict[str, Any]:
    if not LATEST_FILE.exists():
        return {
            "ok": True,
            "timestamp": None,
            "received_at": None,
            "source": None,
            "sz_data": [],
            "dc_data": [],
            "yw_data": [],
        }
    try:
        with open(LATEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("读取智慧供热最新数据失败: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "sz_data": [],
            "dc_data": [],
            "yw_data": [],
        }


def _save_latest_data(payload_dict: Dict[str, Any]):
    temp_file = DATA_DIR / f"latest_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload_dict, f, ensure_ascii=False, indent=2)
    temp_file.replace(LATEST_FILE)


@public_router.post("/push", summary="接收办公电脑中继推送的实时工况数据")
async def push_smart_heating_data(
    background_tasks: BackgroundTasks,
    payload: SmartHeatingPushPayload = Body(...),
    x_push_token: Optional[str] = Header(None, alias="X-Push-Token"),
):
    """
    接收 Win7 办公电脑中继 Agent 定时抓取并推送的 JSON 数据包。
    支持 Header 或 Body 中的 token 验证。
    若开启了服务器中继转发（forward_enabled=True），自动异步转发至指定开发环境/次级中继目标。
    """
    token = x_push_token or payload.push_token or payload.relay_token or payload.token
    # 若配置了非空 token，校验是否匹配
    if DEFAULT_PUSH_TOKEN and token != DEFAULT_PUSH_TOKEN:
        raise HTTPException(status_code=401, detail="推送鉴权密钥无效，拒绝接收")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_epoch = time.time()
    data_record = {
        "ok": True,
        "timestamp": payload.timestamp or now_str,
        "received_at": now_str,
        "received_epoch": now_epoch,
        "is_live_push": True,
        "source": payload.source or "192.168.1.206:6688",
        "sz_data": _clean_point_records(payload.sz_data, "首站"),
        "dc_data": _clean_point_records(payload.dc_data, "电厂"),
        "yw_data": _clean_point_records(payload.yw_data, "一次网"),
    }

    try:
        _save_latest_data(data_record)
        # 追加轻量摘要至历史日志 (单行 JSON)
        try:
            with open(HISTORY_LOG, "a", encoding="utf-8") as log_f:
                summary_line = {
                    "time": now_str,
                    "sz_count": len(payload.sz_data),
                    "dc_count": len(payload.dc_data),
                    "yw_count": len(payload.yw_data),
                }
                log_f.write(json.dumps(summary_line, ensure_ascii=False) + "\n")
        except Exception as log_err:
            logger.warning("追加历史简报失败: %s", log_err)

        # 触发服务器中继转发 (若开关开启，默认打开)
        relay_cfg = _load_relay_config()
        if relay_cfg.get("forward_enabled", True):
            target_url = (relay_cfg.get("forward_target_url") or "").strip()
            if target_url:
                background_tasks.add_task(
                    _forward_payload_task,
                    data_record,
                    target_url,
                    relay_cfg.get("push_token") or DEFAULT_PUSH_TOKEN,
                )

        return {
            "ok": True,
            "message": "智慧供热实时数据接收成功",
            "received_at": now_str,
            "relay_forwarding": relay_cfg.get("forward_enabled", True),
            "counts": {
                "sz_data": len(payload.sz_data),
                "dc_data": len(payload.dc_data),
                "yw_data": len(payload.yw_data),
            },
        }
    except Exception as e:
        logger.exception("保存实时供热数据异常: %s", e)
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@public_router.post("/receive-relay", summary="接收来自上一级服务器中继转发的实时工况数据")
async def receive_relay_data(
    payload: SmartHeatingPushPayload = Body(...),
    x_push_token: Optional[str] = Header(None, alias="X-Push-Token"),
):
    """
    供本地开发环境 (即 localhost) 或下一级节点接收生产服务器中继转发的数据包。
    支持 Header 或 Body 中的 token 验证。
    """
    token = x_push_token or payload.push_token or payload.relay_token or payload.token
    relay_cfg = _load_relay_config()
    expected_token = relay_cfg.get("push_token") or DEFAULT_PUSH_TOKEN
    if expected_token and token != expected_token:
        raise HTTPException(status_code=401, detail="中继接收鉴权密钥无效，拒绝接收")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    now_epoch = time.time()
    data_record = {
        "ok": True,
        "timestamp": payload.timestamp or now_str,
        "received_at": now_str,
        "received_epoch": now_epoch,
        "is_live_push": True,
        "source": payload.source or "server-relay",
        "sz_data": _clean_point_records(payload.sz_data, "首站"),
        "dc_data": _clean_point_records(payload.dc_data, "电厂"),
        "yw_data": _clean_point_records(payload.yw_data, "一次网"),
    }

    try:
        _save_latest_data(data_record)
        return {
            "ok": True,
            "message": "开发环境成功接收并入库服务器中继数据",
            "received_at": now_str,
            "counts": {
                "sz_data": len(payload.sz_data),
                "dc_data": len(payload.dc_data),
                "yw_data": len(payload.yw_data),
            },
        }
    except Exception as e:
        logger.exception("保存中继数据异常: %s", e)
        raise HTTPException(status_code=500, detail=f"中继接收保存失败: {str(e)}")


@router.get("/latest", summary="获取最新智慧供热实时工况")
async def get_latest_smart_heating_data(
    session: AuthSession = Depends(get_current_session),
):
    """
    获取智慧供热最新工况数据。
    严格仅限 Global_admin 查看。
    若数据链路未连接（或超过 90 秒无有效推流），严格不返回任何历史数据，遵循“无连接即无数据”原则。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="智慧供热工况数据仅限 Global_admin 访问")

    data = _read_latest_data()
    is_live_push = bool(data.get("is_live_push"))
    received_epoch = data.get("received_epoch")
    is_online = False
    if is_live_push and received_epoch:
        try:
            diff = time.time() - float(received_epoch)
            is_online = 0 <= diff <= 180
        except Exception:
            pass

    # 严格遵循“没有连接就应该没有数据”原则：未在线时不下发任何测点数据
    if not is_online:
        return {
            "ok": True,
            "is_online": False,
            "data": {
                "ok": True,
                "is_live_push": False,
                "timestamp": None,
                "received_at": None,
                "source": None,
                "sz_data": [],
                "dc_data": [],
                "yw_data": [],
            },
            "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return {
        "ok": True,
        "is_online": True,
        "data": data,
        "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/status", summary="查询中继 Agent 连通状态")
async def get_smart_heating_status(
    session: AuthSession = Depends(get_current_session),
):
    """
    查询中继客户端的心跳与时效状态。
    严格仅限 Global_admin 访问。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 访问")

    data = _read_latest_data()
    is_live_push = bool(data.get("is_live_push"))
    received_epoch = data.get("received_epoch")
    received_at = data.get("received_at")
    is_online = False
    seconds_ago = None

    if is_live_push and received_epoch:
        try:
            diff = time.time() - float(received_epoch)
            seconds_ago = int(diff)
            # 必须在有效心跳周期内 (180秒 / 3分钟，兼容 1m 轮询) 接收过真实的同步推送才视为在线
            is_online = 0 <= diff <= 180
        except Exception:
            pass

    return {
        "ok": True,
        "is_online": is_online,
        "is_live_push": is_live_push,
        "seconds_ago": seconds_ago if is_online else None,
        "last_received_at": received_at if is_online else None,
        "counts": {
            "sz_data": len(data.get("sz_data", [])) if is_online else 0,
            "dc_data": len(data.get("dc_data", [])) if is_online else 0,
            "yw_data": len(data.get("yw_data", [])) if is_online else 0,
        },
    }


def _get_client_script_path() -> Optional[Path]:
    """
    多路径探测同步客户端脚本位置，优先读取运行数据目录下的客户端脚本：
    phoenix/backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py
    确保与服务器和用户指定的修改路径完全一致。
    """
    candidates = [
        # 1. 优先读取用户显式指定的运行数据目录 (DATA_DIRECTORY 挂载: /app/data 或 backend_data)
        Path(DATA_DIRECTORY) / "projects" / "daily_report_25_26" / "smart_heating_relay_win7.py",
        # 2. 备选：当前 daily_report_25_26 项目根目录下获取
        Path(__file__).resolve().parent.parent / "smart_heating_sync.py",
        Path(__file__).resolve().parent / "smart_heating_sync.py",
        # 3. 宿主机或项目根目录 configs/
        Path(__file__).resolve().parents[4] / "configs" / "smart_heating_relay_win7.py",
        Path("configs/smart_heating_relay_win7.py").resolve(),
        Path("/app/configs/smart_heating_relay_win7.py"),
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


@router.get("/client-script", summary="下载智慧供热数据同步客户端脚本")
async def download_client_script(
    session: AuthSession = Depends(get_current_session),
):
    """
    下载最新的 Win7 / Python 3.8 智慧供热数据同步客户端脚本。
    严格仅限 Global_admin 访问下载。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 下载客户端脚本")

    script_path = _get_client_script_path()
    if not script_path:
        raise HTTPException(status_code=404, detail="脚本文件不存在")

    return FileResponse(
        path=str(script_path),
        filename="smart_heating_relay_win7.py",
        media_type="text/x-python",
    )


@public_router.get("/relay-feed", summary="获取服务器最新中继数据流 (供开发环境拉取同步)")
async def get_relay_feed(
    token: Optional[str] = Query(None),
    x_push_token: Optional[str] = Header(None, alias="X-Push-Token"),
):
    """
    供开发环境 (localhost) 在公网服务器无法直接穿越 NAT 访问内网时，通过主动拉取方式同步最新中继数据。
    使用 push_token 鉴权。
    """
    req_token = x_push_token or token
    relay_cfg = _load_relay_config()
    expected_token = relay_cfg.get("push_token") or DEFAULT_PUSH_TOKEN
    if expected_token and req_token != expected_token:
        raise HTTPException(status_code=401, detail="中继数据拉取鉴权失败")

    if not relay_cfg.get("forward_enabled", True):
        raise HTTPException(status_code=403, detail="服务器中继转发功能当前已关闭")

    data = _read_latest_data()
    return {
        "ok": True,
        "relay_status": "enabled",
        "data": data,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


class RemoteSyncRequest(BaseModel):
    remote_url: Optional[str] = Field(None, description="远程服务器基础地址，如 https://platform.smartview.top")
    push_token: Optional[str] = Field(None, description="中继 Token")


@router.post("/sync-from-remote", summary="本地开发环境主动从远程服务器中继同步数据")
async def sync_from_remote_server(
    req: Optional[RemoteSyncRequest] = Body(default=None),
    session: AuthSession = Depends(get_current_session),
):
    """
    在开发环境 (localhost) 下，一键从远程生产服务器拉取最新数据并写入本地。
    限 Global_admin 访问。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 操作")

    relay_cfg = _load_relay_config()
    raw_remote = (
        (req and req.remote_url)
        or relay_cfg.get("remote_server_url")
        or "https://platform.smartview.top"
    ).strip()
    token = (req and req.push_token) or relay_cfg.get("push_token") or DEFAULT_PUSH_TOKEN

    # 智能解析 feed_url：自动兼容输入完整端点、项目路径或基础域名的不同写法
    if "/smart-heating/relay-feed" in raw_remote:
        feed_url = raw_remote
    elif "/api/v1/" in raw_remote:
        feed_url = f"{raw_remote.rstrip('/')}/smart-heating/relay-feed"
    else:
        feed_url = f"{raw_remote.rstrip('/')}/api/v1/projects/daily_report_25_26/smart-heating/relay-feed"

    import ssl
    import urllib.error
    import urllib.request

    req_obj = urllib.request.Request(
        feed_url,
        headers={
            "X-Push-Token": token,
            "User-Agent": "Phoenix-Dev-Sync/2.0",
        },
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req_obj, timeout=10, context=ctx) as resp:
            res_text = resp.read().decode("utf-8")
            res_json = json.loads(res_text)
            feed_data = res_json.get("data", {})
            if not feed_data or not feed_data.get("ok"):
                return {"ok": False, "message": "远程服务器未返回有效工况数据", "detail": res_json}

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            now_epoch = time.time()
            local_record = {
                "ok": True,
                "timestamp": feed_data.get("timestamp") or now_str,
                "received_at": now_str,
                "received_epoch": now_epoch,
                "is_live_push": True,
                "source": f"sync-from:{raw_remote}",
                "sz_data": _clean_point_records(feed_data.get("sz_data", []), "首站"),
                "dc_data": _clean_point_records(feed_data.get("dc_data", []), "电厂"),
                "yw_data": _clean_point_records(feed_data.get("yw_data", []), "一次网"),
            }
            _save_latest_data(local_record)
            return {
                "ok": True,
                "message": f"成功从远程服务器 ({feed_url}) 中继同步数据",
                "synced_at": now_str,
                "counts": {
                    "sz_data": len(local_record["sz_data"]),
                    "dc_data": len(local_record["dc_data"]),
                    "yw_data": len(local_record["yw_data"]),
                },
            }
    except urllib.error.HTTPError as he:
        err_content = he.read().decode("utf-8", errors="ignore")
        logger.warning("远程中继服务器请求失败 (%s): %s (URL: %s)", he.code, err_content, feed_url)
        return {
            "ok": False,
            "message": f"远程生产服务器返回状态码 {he.code}，请核实中继地址与密钥",
            "remote_url": feed_url,
            "detail": err_content,
        }
    except Exception as e:
        logger.exception("中继同步异常: %s (URL: %s)", e, feed_url)
        return {
            "ok": False,
            "message": f"中继同步异常: {str(e)}",
            "remote_url": feed_url,
        }


class RelayConfigUpdateRequest(BaseModel):
    forward_enabled: Optional[bool] = Field(None, description="中继转发开关 (默认 True)")
    forward_target_url: Optional[str] = Field(None, description="中继转发目标端点 URL")
    remote_server_url: Optional[str] = Field(None, description="上级远程服务器地址")


@router.get("/relay-config", summary="查询服务器中继配置")
async def get_relay_config(
    session: AuthSession = Depends(get_current_session),
):
    """
    查询当前服务器中继转发配置（开关状态、转发目标等）。
    严格仅限 Global_admin 访问。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 访问")
    cfg = _load_relay_config()
    return {"ok": True, "config": cfg, "data": cfg}


@router.post("/relay-config", summary="更新服务器中继配置 (开关与目标地址)")
async def update_relay_config(
    req: RelayConfigUpdateRequest = Body(...),
    session: AuthSession = Depends(get_current_session),
):
    """
    切换中继开关（打开/关闭，默认打开）或设置目标转发地址。
    严格仅限 Global_admin 访问。
    """
    if session.group != "Global_admin":
        raise HTTPException(status_code=403, detail="仅限 Global_admin 访问")
    cfg = _load_relay_config()
    if req.forward_enabled is not None:
        cfg["forward_enabled"] = req.forward_enabled
    if req.forward_target_url is not None:
        cfg["forward_target_url"] = req.forward_target_url.strip()
    if req.remote_server_url is not None:
        cfg["remote_server_url"] = req.remote_server_url.strip()
    _save_relay_config(cfg)
    return {"ok": True, "message": "中继配置更新成功", "config": cfg, "data": cfg}

