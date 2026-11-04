#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧供热开发环境本地中继同步脚本 (Dev Relay Pull Client)
====================================================
用于在本地开发环境中主动从线上服务器拉取最新中继数据，解决服务器无法直接穿透 NAT 推送至 localhost 的问题。

使用方法:
  1. 单次同步:
     python dev_relay_pull_sync.py
  2. 周期自动轮询 (每 30 秒一次):
     python dev_relay_pull_sync.py --daemon
  3. 自定义远端服务器地址与 Token:
     python dev_relay_pull_sync.py --remote https://platform.smartview.top --token phoenix_smart_heating_secret_2026
"""

import argparse
import json
import logging
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("dev_relay_sync")

DEFAULT_REMOTE_BASE = "https://platform.smartview.top"
DEFAULT_TOKEN = "phoenix_smart_heating_secret_2026"
DEFAULT_LOCAL_RECEIVE_URL = (
    "http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/smart-heating/receive-relay"
)


def pull_and_sync(remote_base: str, local_receive_url: str, token: str) -> bool:
    feed_url = f"{remote_base.rstrip('/')}/api/v1/projects/daily_report_25_26/smart-heating/relay-feed"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    logger.info("正在从远端中继源获取工况: %s", feed_url)
    try:
        req = urllib.request.Request(
            feed_url,
            headers={
                "X-Push-Token": token,
                "User-Agent": "Phoenix-Dev-Sync-CLI/2.0",
            },
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            res_data = json.loads(raw)
            feed_payload = res_data.get("data", {})
            if not feed_payload:
                logger.warning("远端中继未返回有效数据: %s", res_data)
                return False

        sz_cnt = len(feed_payload.get("sz_data", []))
        dc_cnt = len(feed_payload.get("dc_data", []))
        yw_cnt = len(feed_payload.get("yw_data", []))
        logger.info("✔ 远端中继拉取成功 (首站: %d, 电厂: %d, 一次网: %d)", sz_cnt, dc_cnt, yw_cnt)

        # 转发至本地开发环境接收端
        forward_body = {
            "relay_token": token,
            "source": f"cli-sync:{remote_base}",
            "timestamp": feed_payload.get("timestamp"),
            "sz_data": feed_payload.get("sz_data", []),
            "dc_data": feed_payload.get("dc_data", []),
            "yw_data": feed_payload.get("yw_data", []),
            "gk_data": feed_payload.get("gk_data"),
            "gk_collected_epoch": feed_payload.get("gk_collected_epoch"),
            "received_epoch": feed_payload.get("received_epoch", 0),
        }

        req_local = urllib.request.Request(
            local_receive_url,
            data=json.dumps(forward_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Push-Token": token,
            },
            method="POST",
        )
        with urllib.request.urlopen(req_local, timeout=5) as local_resp:
            local_raw = local_resp.read().decode("utf-8")
            local_res = json.loads(local_raw)
            logger.info("✔ 本地开发环境入库成功: %s", local_res.get("message", "OK"))
            return True

    except urllib.error.HTTPError as he:
        logger.error("HTTP 异常 (%s): %s", he.code, he.reason)
        return False
    except Exception as e:
        logger.error("同步失败: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(description="智慧供热开发环境本地中继数据同步工具")
    parser.add_argument("--remote", default=DEFAULT_REMOTE_BASE, help="远程生产服务器地址")
    parser.add_argument("--local", default=DEFAULT_LOCAL_RECEIVE_URL, help="本地开发环境接收接口")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="中继安全通信密钥")
    parser.add_argument("--daemon", "-d", action="store_true", help="以守护进程模式循环同步")
    parser.add_argument("--interval", "-i", type=int, default=60, help="轮询间隔秒数 (默认 60s / 1m)")

    args = parser.parse_args()

    if not args.daemon:
        success = pull_and_sync(args.remote, args.local, args.token)
        sys.exit(0 if success else 1)

    logger.info("已启动中继轮询守护进程 (间隔: %ds)... 按 Ctrl+C 停止", args.interval)
    while True:
        try:
            pull_and_sync(args.remote, args.local, args.token)
        except Exception as e:
            logger.error("轮询异常: %s", e)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
