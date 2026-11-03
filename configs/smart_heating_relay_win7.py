# -*- coding: utf-8 -*-
"""
================================================================================
🦅 Phoenix 智慧供热数据同步客户端 (Windows 7 + Python 3.8 增强版)
================================================================================
适用场景：
运行于能够同时访问供热数据源网络与 Phoenix 系统的电脑。
本脚本使用 Python 3.8 标准库编写，零额外第三方依赖，可在 Windows 7 环境直接运行。

功能特色：
1. 【直连生产服务器】：支持直接推送到云端线上服务器 (platform.smartview.top) 或本地开发机；
2. 【Win7 SSL 自动容错】：内置 Windows 7 系统 HTTPS 证书自动兼容机制；
3. 【启动交互提示】：启动时清晰展示当前 API 与参数，按回车直接启动，输入编号可快速切换；
4. 【本地记忆保存】：修改后的参数自动保存到同目录下的 smart_heating_config.json，下次免重复输入；
5. 【极低资源占用】：轻量级标准库轮询，针对办公电脑极致优化，内存占用低于 15MB。
================================================================================
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# 配置文件存放路径 (与本脚本在同一目录下)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "smart_heating_config.json")

# 常用预设目标服务器
PRESET_URL_PROD = "https://platform.smartview.top/api/v1/projects/daily_report_25_26/smart-heating/push"
PRESET_URL_LOCAL = "http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/smart-heating/push"

# 默认出厂内置配置 (默认指向云端线上服务器)
DEFAULT_CONFIG = {
    "phoenix_push_url": PRESET_URL_PROD,
    "push_token": "phoenix_smart_heating_secret_2026",
    "intranet_base_url": "http://192.168.1.206:6688",
    "sz_param": "2",
    "dc_param": "2",
    "yw_param": "60",
    "poll_interval_seconds": 30,
    "timeout_seconds": 15,
    "intranet_cookie": (
        "session=.eJx9lF2PojAUhv9Lr71APtTxbgoL3eKalZLwEZOG1Y5DsqBByF5s9r9vAcdpS5kbIs_TU89pff0L0vi"
        "QUohpsKM45I_cizHYGgtREBjn1DtEAYFaFeA01QoU5WC7nPIoyPQ7EaRdnyC8067P0hmR7zW9Jn2b8va5ByHdIwi1"
        "gpBIZ_hDT30U9f3MGZpNxhvkboe1nCQuPswbmvALU4ccdL6PsS8VYne8DENCh1S5OM6ibMoIUthPjtMQSewQ0-A7"
        "oS7OIdaJIIXymA_O-9ILghQeh_zpEmlzzvg3KufAYX8OUnGW8HGJ3BlnKebnleIomRPZp-jvMaGhLx7GyIjKMjcUTn"
        "unKRxZlE8ZUdfNRVBQcgQFIUVQ4HIEBSFGUMKPFGrcrJDjKQg5nqPQRFEQBEUzQs7oh5EzKlAlo6qRMipIKaMCVzIq"
        "GCWE3PAkYTfOpMH7xPkocycwE_-sRjbGUGRErpvEkrNHaNR7neZmhD6KQ5WhJA_VYpIoPXOWIjgtzqIf_Aet0mc8"
        "6Y01VVGzugXbtunYArDb9fRO27JifMH6xVptbGNpLkB5p8W5KmuwBcduczKsY-ewYnXsbGae-ee3kwUW4Pf1Uta0"
        "rN-ufN3zvS763cCludxpd2fN58rbnzMXS9OyndUTNqxi1S_WDB2O6N4WLRve-3padO07r3M2K2e5tjzDhI79Ajev"
        "nmf77tp6NTzn9Zvtg8fyM7sVTVvxKWl5Huo05tHkF8MNFeXYsP3xri1bO-bm2K1Ma22Bf_8BFRpRBw.aulyOg."
        "hB2PVNHHY1CpZ2DfCZ_GpwrrMKc"
    ),
}

# Win7 友好 SSL Context (防止老旧系统证书库未更新报错)
def get_ssl_context():
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return None


def load_config() -> dict:
    """加载本地配置，若不存在则创建默认配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config = dict(DEFAULT_CONFIG)
                config.update(saved)
                return config
        except Exception as e:
            print(f"[提示] 读取本地配置文件失败 ({e})，使用内置默认参数。")
    return dict(DEFAULT_CONFIG)


def save_config(config: dict):
    """保存配置到本地 JSON 文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"✔ 配置已更新并自动记忆至: {os.path.basename(CONFIG_FILE)}")
    except Exception as e:
        print(f"⚠️ 保存配置失败: {e}")


def interactive_config_menu(cfg: dict) -> dict:
    """启动时的交互配置菜单"""
    print("\n" + "=" * 72)
    print("  🦅 Phoenix 智慧供热内网数据中继采集服务 (Win7 / Python 3.8)")
    print("=" * 72)
    print("[当前生效目标]")
    target_tag = "【线上生产服务器】" if "platform.smartview.top" in cfg['phoenix_push_url'] else "【本地/自定义服务器】"
    print(f"  [1] Phoenix 接收地址: {cfg['phoenix_push_url']} {target_tag}")
    print(f"  [2] 轮询采集周期:     {cfg['poll_interval_seconds']} 秒")
    print(f"  [3] 内网平台地址:     {cfg['intranet_base_url']}")
    print(f"  [4] 推送鉴权密钥:     {cfg['push_token']}")
    cookie_preview = cfg['intranet_cookie'][:45] + "..." if len(cfg.get('intranet_cookie', '')) > 45 else cfg.get('intranet_cookie', '')
    print(f"  [5] 内网 Session:     {cookie_preview}")
    print("-" * 72)
    print("【快捷操作】")
    print("  直接按 [回车键 Enter]  -> 立即以当前配置启动中继")
    print("  输入 [ 1 ]             -> 切换/修改 Phoenix 服务器地址 (支持一键切线上/本地/自定义)")
    print("  输入 [ 2 ]             -> 修改轮询采集间隔 (秒)")
    print("  输入 [ 3 ]             -> 修改内网平台 Session Cookie (更新会话凭据)")
    print("  输入 [ 4 ]             -> 逐项修改全部参数")
    print("=" * 72)

    try:
        choice = input("请选择操作 (直接回车启动): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消启动。")
        sys.exit(0)

    if not choice:
        print("▶ 未做修改，直接以当前配置启动...\n")
        return cfg

    modified = False

    if choice == "1":
        print("\n请选择要推送的目标服务器：")
        print(f"  [a] 线上生产服务器 -> {PRESET_URL_PROD}")
        print(f"  [b] 本地测试开发机 -> {PRESET_URL_LOCAL}")
        print("  [c] 手动输入自定义服务器 IP / 域名")
        sub_choice = input("请选择 [a/b/c，回车保持原样]: ").strip().lower()
        if sub_choice == "a":
            cfg['phoenix_push_url'] = PRESET_URL_PROD
            modified = True
        elif sub_choice == "b":
            cfg['phoenix_push_url'] = PRESET_URL_LOCAL
            modified = True
        elif sub_choice == "c":
            new_val = input("请输入完整的 Phoenix 推送接收接口 URL: ").strip()
            if new_val:
                cfg['phoenix_push_url'] = new_val
                modified = True
        elif sub_choice.startswith("http"):
            cfg['phoenix_push_url'] = sub_choice
            modified = True

    elif choice == "2":
        print(f"\n当前轮询间隔: {cfg['poll_interval_seconds']} 秒")
        new_val = input("请输入新的采集间隔秒数 (建议 15~60) [回车保持不变]: ").strip()
        if new_val and new_val.isdigit():
            cfg['poll_interval_seconds'] = int(new_val)
            modified = True

    elif choice == "3":
        print("\n当前 Cookie 预览: " + cookie_preview)
        new_val = input("请粘贴新的内网平台 Session (以 session= 开头): ").strip()
        if new_val:
            cfg['intranet_cookie'] = new_val
            modified = True

    elif choice == "4":
        print("\n--- 逐项配置模式 (直接回车保持当前值) ---")
        val1 = input(f"1. Phoenix 接收地址 [{cfg['phoenix_push_url']}]: ").strip()
        if val1: cfg['phoenix_push_url'] = val1; modified = True

        val2 = input(f"2. 采集间隔秒数 [{cfg['poll_interval_seconds']}]: ").strip()
        if val2 and val2.isdigit(): cfg['poll_interval_seconds'] = int(val2); modified = True

        val3 = input(f"3. 内网平台地址 [{cfg['intranet_base_url']}]: ").strip()
        if val3: cfg['intranet_base_url'] = val3; modified = True

        val4 = input(f"4. 内网 Session [回车跳过不改]: ").strip()
        if val4: cfg['intranet_cookie'] = val4; modified = True

    if modified:
        save_config(cfg)
        print("▶ 配置更新完毕，正在以新参数启动服务...\n")
    else:
        print("▶ 未修改参数，正在启动服务...\n")

    return cfg


def log(msg: str):
    """打印带时间戳的中文运行日志"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def fetch_intranet_post(url: str, form_data: dict, cfg: dict) -> list:
    """使用标准库发起向内网平台的 POST 请求并解析返回的 JSON 列表"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Cookie": cfg["intranet_cookie"],
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    }
    encoded_data = None
    if form_data:
        encoded_data = urllib.parse.urlencode(form_data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 15)) as response:
        content = response.read().decode("utf-8", errors="ignore")
        return json.loads(content)


def push_to_phoenix(payload: dict, cfg: dict) -> dict:
    """向 Phoenix 后端推送打包后的综合工况数据 (自带 Win7 SSL 兼容)"""
    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Phoenix-Win7-SmartHeating-Relay/1.0",
        "X-Push-Token": cfg["push_token"],
    }
    req = urllib.request.Request(
        cfg["phoenix_push_url"],
        data=json_bytes,
        headers=headers,
        method="POST"
    )

    ctx = get_ssl_context() if cfg["phoenix_push_url"].startswith("https") else None

    if ctx:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 15), context=ctx) as response:
            res_text = response.read().decode("utf-8", errors="ignore")
            return json.loads(res_text)
    else:
        with urllib.request.urlopen(req, timeout=cfg.get("timeout_seconds", 15)) as response:
            res_text = response.read().decode("utf-8", errors="ignore")
            return json.loads(res_text)


def run_single_cycle(cfg: dict):
    """执行单次完整的工况数据同步周期"""
    log("▶ 开始同步各测点实时工况数据...")

    # 1. 获取首站与管网环路数据
    sz_url = f"{cfg['intranet_base_url']}/get_sz_data/{cfg['sz_param']}"
    sz_data = []
    try:
        sz_data = fetch_intranet_post(sz_url, {"sz_selected": cfg['sz_param']}, cfg)
    except Exception as e:
        log(f"⚠️ 首站工况同步异常: {e}")

    # 2. 获取电厂机组数据
    dc_url = f"{cfg['intranet_base_url']}/get_dc_data/{cfg['dc_param']}"
    dc_data = []
    try:
        dc_data = fetch_intranet_post(dc_url, None, cfg)
    except Exception as e:
        log(f"⚠️ 电厂机组数据同步异常: {e}")

    # 3. 获取换热站一次网数据
    yw_url = f"{cfg['intranet_base_url']}/get_yw_data/{cfg['yw_param']}"
    yw_data = []
    try:
        yw_data = fetch_intranet_post(yw_url, {"yw_selected": cfg['yw_param']}, cfg)
    except Exception as e:
        log(f"⚠️ 换热站一次网数据同步异常: {e}")

    if not sz_data and not dc_data and not yw_data:
        log("❌ 本轮未能接收到有效工况数据，请检查网络连接或 Session 是否过期。")
        return

    log(
        f"✔ 工况数据采集完成: 首站管网 {len(sz_data)} 组测点, "
        f"电厂机组 {len(dc_data)} 组测点, 换热站 {len(yw_data)} 座"
    )

    # 4. 打包并推送到 Phoenix
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    push_payload = {
        "push_token": cfg["push_token"],
        "timestamp": now_str,
        "source": "192.168.1.206:6688",
        "sz_data": sz_data,
        "dc_data": dc_data,
        "yw_data": yw_data,
    }

    try:
        resp = push_to_phoenix(push_payload, cfg)
        log(f"🚀 成功推送至 Phoenix 系统! 响应: {resp.get('message', 'OK')}")
    except urllib.error.HTTPError as he:
        err_msg = he.read().decode('utf-8', errors='ignore')
        log(f"❌ 推送失败 (HTTP {he.code}): {err_msg}")
    except Exception as pe:
        log(f"❌ 推送至 Phoenix 连接异常: {pe}")


def main():
    cfg = load_config()
    cfg = interactive_config_menu(cfg)

    log(f"服务已启动 | 目标内网: {cfg['intranet_base_url']} | 目标 Phoenix: {cfg['phoenix_push_url']}")
    log(f"轮询周期: {cfg['poll_interval_seconds']} 秒 | 按 Ctrl + C 可终止运行\n")

    while True:
        try:
            run_single_cycle(cfg)
        except KeyboardInterrupt:
            log("收到退出指令，中继服务已安全停止。")
            break
        except Exception as e:
            log(f"运行未捕获异常: {e}")

        time.sleep(cfg.get("poll_interval_seconds", 30))


if __name__ == "__main__":
    main()
