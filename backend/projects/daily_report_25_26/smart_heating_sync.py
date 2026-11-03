# -*- coding: utf-8 -*-
"""
================================================================================
🦅 Phoenix 智慧供热数据同步客户端 (Windows 7 + Python 3.8 全网全量版)
================================================================================
适用场景：
运行于能够同时访问供热内网 (192.168.1.206) 与 Phoenix 系统的 Win7 办公电脑。
本脚本使用 Python 3.8 纯标准库编写，零额外第三方依赖，开箱即用。

全网监控范围：
1. 【电厂侧】全覆盖：
   - 北海电厂 (ID 2): 23 组机组测点 (汽机进抽汽、主汽、燃气炉群等)
   - 香海电厂 (ID 3): 35 组机组测点 (锅炉主汽、汽机进抽汽、低真空循环水等)
2. 【首站侧】全覆盖：
   - #1 首站 (ID 2): 16 组回路 (东环、南环、北网供回补水、板换、热泵等)
   - #2 首站 (ID 3): 8 组回路 (北2首高温水供回补水、循环泵、蒸汽等)
   - #3 首站 (ID 4): 20 组回路 (北首3#水炉出口、厂界供水、循环泵等)
   - 香海首站 (ID 5): 10 组回路 (香首高温水供回补水、一期/二期蒸汽等)
3. 【换热站】9 大运营中心全覆盖 (242 座换热站)：
   - ID 60: 华乐中心 (20 座)
   - ID 61: 胜利中心 (35 座)
   - ID 62: 双兴中心 (21 座)
   - ID 63: 香炉礁中心 (18 座)
   - ID 64: 兴工中心 (28 座)
   - ID 65: 春海中心 (29 座)
   - ID 66: 大纺中心 (17 座)
   - ID 67: 友好中心 (37 座)
   - ID 68: 东港中心 (37 座)
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

# 分区中文名称映射
DC_MAP = {
    2: "北海电厂",
    3: "香海电厂",
}

SZ_MAP = {
    2: "#1首站",
    3: "#2首站",
    4: "#3首站",
    5: "香海首站",
}

YW_MAP = {
    60: "华乐中心",
    61: "胜利中心",
    62: "双兴中心",
    63: "香炉礁中心",
    64: "兴工中心",
    65: "春海中心",
    66: "大纺中心",
    67: "友好中心",
    68: "东港中心",
}

# 默认内置出厂配置
DEFAULT_CONFIG = {
    "phoenix_push_url": PRESET_URL_PROD,
    "push_token": "phoenix_smart_heating_secret_2026",
    "intranet_base_url": "http://192.168.1.206:6688",
    "dc_list": [2, 3],
    "sz_list": [2, 3, 4, 5],
    "yw_list": [60, 61, 62, 63, 64, 65, 66, 67, 68],
    "poll_interval_seconds": 30,
    "timeout_seconds": 15,
    "intranet_cookie": (
        "session=.eJx9lF2PojAUhv8L114giF93Agvd4pqVkvARk4bVjkOyoEHIXmz2v-8BHKctZW6IPM859bT19a-WRMeE2pj6e4oDeGRuhLWtPuMFsaOMusfQJ7ZS-ThJlAKFmbadj3nop-qVCFLWxwjvlfVpMiGyg2LWuBtTXD5zbZsekG0rBSGhysBDTT0UdvNMGZqOttfL_R4rOYkdfJw2NIYLkzfZ6-wQYU9oxM5wGbqAjol0ccDCdMwIkthPwEmABHaMqP-dUAdnNlYJP7HFbT45zKUWBEk8CuDpEGFxYPCN0jkA7M5BaE5j2C4RJwOWYDivBIfxlEg_RXePMQ08_jAGRmSWOgF32ntF48DCbMyIXDcVQU6JEeSEEEGOixHkBB9BAT9TqHCTQownJ8R4DkIRRU4QFE4IMaMfRswoR6WMykbIKCeFjHJcyihnpBCCgSRhJ0qFjXeJ81DqjGDK_1kNbIghz4jYN4olsGdo5Hsd52aAHooCmaE4C-RmEkszA0uQPW5Owx_wg5bpK570zuoyr1jVaNumbtlMY_fb-Z02RcmgYLUxlxvdMqCyeND8UhaVttVO7fqsm6fWYvny1C6YcYHPb2dTm2m_b9eiokX1doO613uVd6tp1_r6oO2D1Z-V9z8XEHPDXFjLF6xZycpfrO4nHNCjyRvWv3f9NG-bd-iz1ktrvjJd3bCtxcZe71x34Tkrc6e71u7bwtOe5Rd2z-umhF3S4tL3KcxzyC8213cUw8CLj3dl28oy1qd2aZgrU_v3HxeXUQk.aumL-A.LAW_yxLpOahZZybbx5cMHyDxDXs"
    ),
}


def get_ssl_context():
    """Win7 友好 SSL Context (防止老旧系统根证书过期报错)"""
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
    print("\n" + "=" * 74)
    print("  🦅 Phoenix 智慧供热内网数据全网同步服务 (Win7 / Python 3.8)")
    print("=" * 74)
    target_tag = "【线上生产服务器】" if "platform.smartview.top" in cfg['phoenix_push_url'] else "【测试/自定义服务器】"
    print(f"  [1] Phoenix 接收端点: {cfg['phoenix_push_url']} {target_tag}")
    print(f"  [2] 轮询采集周期:     {cfg['poll_interval_seconds']} 秒")
    print(f"  [3] 内网平台地址:     {cfg['intranet_base_url']}")
    print(f"  [4] 采集覆盖范围:     电厂 {len(cfg.get('dc_list', []))} 座 | 首站 {len(cfg.get('sz_list', []))} 座 | 换热站 {len(cfg.get('yw_list', []))} 个中心 (全网)")
    print(f"  [5] 推送鉴权密钥:     {cfg['push_token']}")
    cookie_preview = cfg['intranet_cookie'][:45] + "..." if len(cfg.get('intranet_cookie', '')) > 45 else cfg.get('intranet_cookie', '')
    print(f"  [6] 内网 Session:     {cookie_preview}")
    print("-" * 74)
    print("【快捷操作】")
    print("  直接按 [回车键 Enter]  -> 立即以当前配置启动同步服务")
    print("  输入 [ 1 ]             -> 切换/修改 Phoenix 服务器地址 (支持一键切线上/本地/自定义)")
    print("  输入 [ 2 ]             -> 修改轮询采集间隔 (秒)")
    print("  输入 [ 3 ]             -> 修改内网平台 Session Cookie (更新会话凭据)")
    print("  输入 [ 4 ]             -> 逐项修改全部参数")
    print("=" * 74)

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
        "User-Agent": "Phoenix-Win7-SmartHeating-Relay/2.0",
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
    """执行单次完整的全网各分区数据同步周期"""
    log("▶ 开始采集内网各分区实时工况数据...")

    # 1. 采集电厂机组数据 (北海电厂、香海电厂)
    dc_list = cfg.get("dc_list", [2, 3])
    all_dc_data = []
    for dc_id in dc_list:
        dc_url = f"{cfg['intranet_base_url']}/get_dc_data/{dc_id}"
        category = DC_MAP.get(int(dc_id), f"电厂_{dc_id}")
        try:
            items = fetch_intranet_post(dc_url, None, cfg)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item["dc_id"] = dc_id
                        item["category"] = category
                        all_dc_data.append(item)
        except Exception as e:
            log(f"⚠️ {category}机组数据同步异常: {e}")

    # 2. 采集首站与主管网数据 (#1首站、#2首站、#3首站、香海首站)
    sz_list = cfg.get("sz_list", [2, 3, 4, 5])
    all_sz_data = []
    for sz_id in sz_list:
        sz_url = f"{cfg['intranet_base_url']}/get_sz_data/{sz_id}"
        category = SZ_MAP.get(int(sz_id), f"首站_{sz_id}")
        try:
            items = fetch_intranet_post(sz_url, {"sz_selected": str(sz_id)}, cfg)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item["sz_id"] = sz_id
                        item["category"] = category
                        all_sz_data.append(item)
        except Exception as e:
            log(f"⚠️ {category}工况同步异常: {e}")

    # 3. 采集换热站一次网数据 (9 大运营中心全覆盖)
    yw_list = cfg.get("yw_list", [60, 61, 62, 63, 64, 65, 66, 67, 68])
    all_yw_data = []
    for yw_id in yw_list:
        yw_url = f"{cfg['intranet_base_url']}/get_yw_data/{yw_id}"
        center_name = YW_MAP.get(int(yw_id), f"中心_{yw_id}")
        try:
            items = fetch_intranet_post(yw_url, {"yw_selected": str(yw_id)}, cfg)
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        item["center_id"] = yw_id
                        item["center_name"] = center_name
                        all_yw_data.append(item)
        except Exception as e:
            log(f"⚠️ {center_name}换热站数据同步异常: {e}")

    if not all_sz_data and not all_dc_data and not all_yw_data:
        log("❌ 本轮未能接收到有效工况数据，请检查网络连接或 Session 是否过期。")
        return

    log(
        f"✔ 全量采集完成: 电厂机组 {len(all_dc_data)} 项 ({len(dc_list)}座电厂), "
        f"首站测点 {len(all_sz_data)} 组 ({len(sz_list)}座首站), "
        f"换热站 {len(all_yw_data)} 座 ({len(yw_list)}个中心)"
    )

    # 4. 打包并推送到 Phoenix
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    push_payload = {
        "push_token": cfg["push_token"],
        "timestamp": now_str,
        "source": "192.168.1.206:6688",
        "sz_data": all_sz_data,
        "dc_data": all_dc_data,
        "yw_data": all_yw_data,
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
    log(f"采集范围: 电厂 {cfg.get('dc_list')} | 首站 {cfg.get('sz_list')} | 换热站 {cfg.get('yw_list')}")
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
