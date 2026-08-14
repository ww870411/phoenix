"""
IP 地理位置解析服务（以系统内置高德开放平台 API 为核心主力 + IP-API / 太平洋网络多源容灾 + 内网私网智能识别）
"""
import ipaddress
import json
from typing import Dict, Any, Optional
import httpx

# 内存缓存，避免重复查询相同 IP
_IP_CACHE: Dict[str, Dict[str, Any]] = {}


def is_private_or_loopback_ip(ip_str: str) -> bool:
    """判断是否为内网、私有或本地回环 IP"""
    if not ip_str or not isinstance(ip_str, str):
        return True
    clean_ip = ip_str.strip()
    if clean_ip in ("localhost", "::1", "unknown", "127.0.0.1"):
        return True
    try:
        ip_obj = ipaddress.ip_address(clean_ip)
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved
    except ValueError:
        return False


def _get_system_amap_key() -> str:
    """从系统全局配置中获取当前有效的高德 API Key"""
    try:
        from backend.projects.insulation_pipe_supply_2026.services.config_service import (
            load_tube_config,
            get_configured_amap_config,
        )
        config_data = load_tube_config()
        amap_cfg = get_configured_amap_config(config_data)
        return str(amap_cfg.get("api_key") or "").strip()
    except Exception:
        return "7939c670de3699077dc6b498cd95346f"


def _normalize_isp(raw_isp: str) -> str:
    """标准化网络运营商中文名称"""
    if not raw_isp:
        return ""
    upper = str(raw_isp).upper()
    if "UNICOM" in upper or "CNC" in upper or "联通" in upper:
        return "中国联通"
    if "TELECOM" in upper or "CHINANET" in upper or "电信" in upper:
        return "中国电信"
    if "MOBILE" in upper or "CMNET" in upper or "移动" in upper:
        return "中国移动"
    if "TIETONG" in upper or "铁通" in upper:
        return "中国铁通"
    if "CERNET" in upper or "教育网" in upper:
        return "中国教育科研网"
    return str(raw_isp).strip()


def resolve_ip_location(ip_str: str) -> Dict[str, Any]:
    """
    解析 IP 归属地与网络运营商信息
    优先级:
    1. 私网/回环判断 (0ms 本地计算)
    2. 高德开放平台 Web 服务 API (官方权威主力源: http://restapi.amap.com/v3/ip)
    3. IP-API (国际中文容灾备用源，补充运营商或兜底)
    """
    if not ip_str or not str(ip_str).strip():
        return {
            "ip": ip_str or "",
            "is_private": True,
            "location": "未知地址",
            "city": "",
            "province": "",
            "adcode": "",
            "isp": "",
            "provider": "系统识别",
            "formatted": "未知地址",
        }
    
    clean_ip = str(ip_str).strip()
    
    # 命中缓存直接返回
    if clean_ip in _IP_CACHE:
        return _IP_CACHE[clean_ip]
    
    # 1. 内网 / 本地 / 私有 IP 识别 (0ms 本地规则)
    if clean_ip in ("127.0.0.1", "localhost", "::1"):
        res = {
            "ip": clean_ip,
            "is_private": True,
            "location": "本地回环 (Localhost)",
            "city": "本地",
            "province": "本地",
            "adcode": "",
            "isp": "本地网络",
            "provider": "本地识别",
            "formatted": "🏠 本地回环 (Localhost)",
        }
        _IP_CACHE[clean_ip] = res
        return res
    
    if is_private_or_loopback_ip(clean_ip):
        res = {
            "ip": clean_ip,
            "is_private": True,
            "location": "局域网 / 集团内网",
            "city": "内网",
            "province": "私网",
            "adcode": "",
            "isp": "私有网络",
            "provider": "内网识别",
            "formatted": "🏢 局域网 / 集团内网 (Private LAN)",
        }
        _IP_CACHE[clean_ip] = res
        return res

    result_data = None
    amap_key = _get_system_amap_key()

    # 2. 主力源: 高德开放平台 Web 服务 API (http://restapi.amap.com/v3/ip)
    if amap_key:
        try:
            url = f"http://restapi.amap.com/v3/ip?ip={clean_ip}&key={amap_key}"
            with httpx.Client(trust_env=False, timeout=3.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if str(data.get("status")) == "1" and str(data.get("infocode")) == "10000":
                        province = str(data.get("province") or "").strip()
                        city = str(data.get("city") or "").strip()
                        adcode = str(data.get("adcode") or "").strip()
                        
                        # 规避高德返回空列表 "[]" 的情况
                        if province == "[]":
                            province = ""
                        if city == "[]":
                            city = ""
                        if adcode == "[]":
                            adcode = ""

                        if province or city:
                            loc_parts = []
                            if province:
                                loc_parts.append(province)
                            if city and city != province:
                                loc_parts.append(city)
                            loc_str = " ".join(loc_parts) or "国内公网"
                            
                            fmt = f"📍 {loc_str}"
                            if adcode:
                                fmt += f" ({adcode})"

                            result_data = {
                                "ip": clean_ip,
                                "is_private": False,
                                "location": loc_str,
                                "city": city,
                                "province": province,
                                "adcode": adcode,
                                "isp": "",
                                "provider": "高德开放平台 (Amap)",
                                "formatted": fmt,
                            }
        except Exception as amap_ex:
            print(f"[IP Location Warning] 高德 IP 查询降级: {amap_ex}")

    # 3. 补充运营商 (ISP) 或兜底容灾: IP-API
    try:
        url = f"http://ip-api.com/json/{clean_ip}?lang=zh-CN"
        with httpx.Client(trust_env=False, timeout=2.5) as client:
            res = client.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    raw_isp = str(data.get("isp") or data.get("as") or "").strip()
                    isp_clean = _normalize_isp(raw_isp)
                    
                    if result_data:
                        if isp_clean:
                            result_data["isp"] = isp_clean
                            result_data["formatted"] = f"{result_data['formatted']} · {isp_clean}"
                    else:
                        region_name = str(data.get("regionName") or "").strip()
                        city = str(data.get("city") or "").strip()
                        loc_str = f"{region_name} {city}".strip() or "公网地址"
                        fmt = f"📍 {loc_str}"
                        if isp_clean:
                            fmt += f" · {isp_clean}"
                        result_data = {
                            "ip": clean_ip,
                            "is_private": False,
                            "location": loc_str,
                            "city": city,
                            "province": region_name,
                            "adcode": "",
                            "isp": isp_clean,
                            "provider": "IP-API (国际中文)",
                            "formatted": fmt,
                        }
    except Exception:
        pass

    # 4. 最终安全保底
    if not result_data:
        result_data = {
            "ip": clean_ip,
            "is_private": False,
            "location": "公网 IP",
            "city": "",
            "province": "",
            "adcode": "",
            "isp": "",
            "provider": "通用公网",
            "formatted": "🌐 公网 IP 地址",
        }

    _IP_CACHE[clean_ip] = result_data
    return result_data
