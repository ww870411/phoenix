"""用用户提供的 HAR 验证工况一览采集及中继，禁止写入正式运行数据。"""
import asyncio
import importlib.util
import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import BackgroundTasks

from backend.projects.daily_report_25_26.api import smart_heating as api
from backend.projects.daily_report_25_26 import dev_relay_pull_sync as cli

ROOT = Path(__file__).resolve().parents[4]
HAR = ROOT / "configs" / "192.168.1.206(工况一览).har"


def load_script(path):
    spec = importlib.util.spec_from_file_location("heating_relay_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entries = json.loads(HAR.read_text(encoding="utf-8-sig"))["log"]["entries"]
        cls.overview = json.loads(next(entry["response"]["content"]["text"] for entry in entries
                                      if entry["request"]["url"].endswith("/gk_get_data/")))

    def setUp(self):
        self.saved = []
        self.writer = patch.object(api, "_save_latest_data", side_effect=self.saved.append)
        self.writer.start()
        self.addCleanup(self.writer.stop)
        self.config = patch.object(api, "_load_relay_config", return_value={
            "forward_enabled": True, "forward_target_url": "http://relay.test/receive-relay",
            "push_token": api.DEFAULT_PUSH_TOKEN,
        })
        self.config.start()
        self.addCleanup(self.config.stop)
        # 历史摘要使用内存句柄，不触碰真实历史日志。
        import io
        self.history = patch("builtins.open", return_value=io.StringIO())

    def payload(self, **extra):
        return api.SmartHeatingPushPayload(
            gk_data=self.overview, gk_collected_epoch=time.time(), **extra)

    def test_push_forward_receive_and_feed_preserve_all_five_groups(self):
        tasks = BackgroundTasks()
        with self.history:
            result = asyncio.run(api.push_smart_heating_data(tasks, self.payload(), api.DEFAULT_PUSH_TOKEN))
        self.assertEqual(result["counts"]["gk_data"], 137)
        self.assertEqual(self.saved[-1]["gk_data"], self.overview)
        forwarded = tasks.tasks[0].args[0]
        self.assertEqual(forwarded["gk_data"], self.overview)
        asyncio.run(api.receive_relay_data(api.SmartHeatingPushPayload(**forwarded), api.DEFAULT_PUSH_TOKEN))
        self.assertEqual(self.saved[-1]["gk_collected_epoch"], forwarded["gk_collected_epoch"])
        self.assertEqual(self.saved[-1]["received_epoch"], forwarded["received_epoch"])
        with patch.object(api, "_read_latest_data", return_value=self.saved[-1]):
            feed = asyncio.run(api.get_relay_feed(None, api.DEFAULT_PUSH_TOKEN))
        self.assertEqual(feed["data"]["gk_data"], self.overview)

    def test_old_client_and_stale_relay_remain_compatible(self):
        old = api.SmartHeatingPushPayload(sz_data=[{"name": "东环供水", "WENDU": 0}])
        asyncio.run(api.receive_relay_data(old, api.DEFAULT_PUSH_TOKEN))
        self.assertIsNone(self.saved[-1]["gk_data"])
        stale = self.payload(received_epoch=time.time() - 400)
        asyncio.run(api.receive_relay_data(stale, api.DEFAULT_PUSH_TOKEN))
        with patch.object(api, "_read_latest_data", return_value=self.saved[-1]):
            latest = asyncio.run(api.get_latest_smart_heating_data(SimpleNamespace(group="Global_admin")))
        self.assertFalse(latest["is_online"])
        self.assertIsNone(latest["data"]["gk_data"])
        self.assertEqual(latest["data"]["sz_data"], [])

    def test_both_client_scripts_collect_overview_and_isolate_failures(self):
        paths = [ROOT / "backend/projects/daily_report_25_26/smart_heating_sync.py",
                 ROOT / "backend_data/projects/daily_report_25_26/smart_heating_relay_win7.py"]
        for path in paths:
            module = load_script(path)
            cfg = dict(module.DEFAULT_CONFIG, dc_list=[], sz_list=[], yw_list=[])
            with self.subTest(path=path), patch.object(module, "log"), \
                    patch.object(module, "fetch_intranet_post", return_value=self.overview) as fetch, \
                    patch.object(module, "push_to_phoenix", return_value={}) as push:
                module.run_single_cycle(cfg)
                self.assertTrue(fetch.call_args.args[0].endswith("/gk_get_data/"))
                self.assertIsNone(fetch.call_args.args[1])
                self.assertEqual(push.call_args.args[0]["gk_data"], self.overview)
            def fetch_with_failure(url, form, config):
                if url.endswith("/gk_get_data/"):
                    raise ValueError("模拟新接口失败")
                return [{"name": "北海#1机进气", "WENDU": 0}]
            with self.subTest(failure=path), patch.object(module, "log"), \
                    patch.object(module, "fetch_intranet_post", side_effect=fetch_with_failure), \
                    patch.object(module, "push_to_phoenix", return_value={}) as push:
                module.run_single_cycle(dict(cfg, dc_list=[2]))
                payload = push.call_args.args[0]
                self.assertIsNone(payload["gk_data"])
                self.assertIsNone(payload["gk_collected_epoch"])
                self.assertEqual(payload["dc_data"][0]["name"], "北海#1机进汽")

    def test_stale_overview_is_hidden_while_other_sources_are_online(self):
        record = {"ok": True, "is_live_push": True, "received_epoch": time.time(),
                  "gk_data": self.overview, "gk_collected_epoch": time.time() - 400,
                  "sz_data": [{"name": "东环供水", "WENDU": 0}]}
        with patch.object(api, "_read_latest_data", return_value=record):
            result = asyncio.run(api.get_latest_smart_heating_data(SimpleNamespace(group="Global_admin")))
            status = asyncio.run(api.get_smart_heating_status(SimpleNamespace(group="Global_admin")))
        self.assertTrue(result["is_online"])
        self.assertIsNone(result["data"]["gk_data"])
        self.assertEqual(result["data"]["sz_data"], record["sz_data"])
        self.assertEqual(status["counts"]["gk_data"], 0)
        self.assertEqual(record["gk_data"], self.overview)

    def test_remote_sync_and_cli_keep_original_freshness(self):
        import io
        original_epoch = time.time() - 400
        feed = {"ok": True, "gk_data": self.overview,
                "gk_collected_epoch": original_epoch, "received_epoch": original_epoch}
        raw = json.dumps({"data": feed}).encode("utf-8")
        with patch("urllib.request.urlopen", return_value=io.BytesIO(raw)):
            result = asyncio.run(api.sync_from_remote_server(
                api.RemoteSyncRequest(remote_url="http://upstream.test"), SimpleNamespace(group="Global_admin")))
        self.assertTrue(result["ok"])
        self.assertEqual(self.saved[-1]["received_epoch"], original_epoch)
        self.assertEqual(self.saved[-1]["gk_data"], self.overview)
        with patch("urllib.request.urlopen", side_effect=[io.BytesIO(raw), io.BytesIO(b'{"ok":true}')]) as request:
            self.assertTrue(cli.pull_and_sync("http://upstream.test", "http://local.test", "test-token"))
        forwarded = json.loads(request.call_args.args[0].data)
        self.assertEqual(forwarded["gk_data"], self.overview)
        self.assertEqual(forwarded["gk_collected_epoch"], original_epoch)
        self.assertEqual(forwarded["received_epoch"], original_epoch)


if __name__ == "__main__":
    unittest.main()
