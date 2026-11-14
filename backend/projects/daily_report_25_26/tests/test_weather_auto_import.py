# -*- coding: utf-8 -*-
"""在隔离临时目录内验证气温自动定时获取调度、状态记录与管理接口，不访问外网或真实数据库。"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.projects.daily_report_25_26.api import dashboard, dynamic_plan
from backend.services import ensemble_weather_service as ensemble_svc
from backend.services import project_settings
from backend.services import weather_auto_import_service as auto_mod
from backend.services import weather_importer as weather
from backend.services.auth_manager import EAST_8


class WeatherAutoImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.settings_path = Path(self.temp.name) / "project_settings.json"
        self.config_path = Path(self.temp.name) / "weather_import_config.json"
        self.auto_path = Path(self.temp.name) / "weather_auto_import_state.json"
        self.legacy_auto_path = Path(self.temp.name) / "weather_auto_import_config.json"

        patch_settings = patch.object(project_settings, "get_project_settings_path", return_value=self.settings_path)
        patch_cfg = patch.object(weather, "_weather_config_path", return_value=self.config_path)
        patch_state = patch.object(auto_mod, "_auto_state_path", return_value=self.auto_path)
        patch_auto = patch.object(auto_mod, "_auto_config_path", return_value=self.legacy_auto_path)
        patch_audit = patch.object(auto_mod.WeatherAutoImportService, "_write_audit_log")
        for p in (patch_settings, patch_cfg, patch_state, patch_auto, patch_audit):
            p.start()
            self.addCleanup(p.stop)

        self.service = auto_mod.WeatherAutoImportService()

    def test_normalize_schedule_times_sorts_dedupes_and_validates(self):
        self.assertEqual(
            auto_mod.normalize_schedule_times(["18:00", "06:30", "06:30", " 12:05 "]),
            ["06:30", "12:05", "18:00"],
        )
        for invalid in (["24:00"], ["12:60"], ["abc"], ["8:00:00"]):
            with self.subTest(raw=invalid), self.assertRaises(ValueError):
                auto_mod.normalize_schedule_times(invalid)

    def test_update_config_marks_past_slots_skipped_and_computes_next_run(self):
        now = datetime(2026, 11, 14, 10, 15, 0, tzinfo=EAST_8)
        status = self.service.update_config(
            enabled=True,
            schedule_times=["08:00", "12:30", "18:00"],
            now=now,
        )
        self.assertTrue(status["enabled"])
        self.assertEqual(status["schedule_times"], ["08:00", "12:30", "18:00"])
        self.assertIn("08:00", status["executed_slots_today"])
        self.assertNotIn("12:30", status["executed_slots_today"])
        self.assertEqual(status["next_run_time"], "2026-11-14 12:30:00")
        self.assertFalse(self.auto_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertFalse(self.settings_path.read_bytes().startswith(b"\xef\xbb\xbf"))

        # 关闭开关后不计算下一次时间
        paused = self.service.update_config(enabled=False, now=now)
        self.assertFalse(paused["enabled"])
        self.assertIsNone(paused["next_run_time"])

    def test_scheduler_step_triggers_once_per_slot_and_records_success_and_failure(self):
        t_setup = datetime(2026, 11, 14, 7, 0, 0, tzinfo=EAST_8)
        self.service.update_config(enabled=True, schedule_times=["08:00", "12:00", "18:00"], now=t_setup)

        # 未到 08:00 不触发
        res_before = self.service._scheduler_step(now=datetime(2026, 11, 14, 7, 59, 45, tzinfo=EAST_8))
        self.assertEqual(res_before, [])

        # 08:00 触发成功
        with patch.object(
            weather,
            "fetch_hourly_temperatures",
            return_value={
                "source": {"timezone": "Asia/Singapore"},
                "hourly": [{"time": "2026-11-14T08:00", "value": 6.5}],
                "dates": ["2026-11-14"],
                "summary": {"total_hours": 1},
            },
        ), patch.object(auto_mod, "SessionLocal", return_value=MagicMock()), patch.object(
            weather,
            "persist_hourly_temperatures",
            return_value={"inserted": 1, "replaced": 0, "start": "2026-11-14T08:00:00+08:00", "end": "2026-11-14T08:00:00+08:00"},
        ):
            res_0800 = self.service._scheduler_step(now=datetime(2026, 11, 14, 8, 0, 15, tzinfo=EAST_8))
            # 同一分钟内再次巡检不重复触发
            res_0800_dup = self.service._scheduler_step(now=datetime(2026, 11, 14, 8, 0, 35, tzinfo=EAST_8))

        self.assertEqual(len(res_0800), 1)
        self.assertTrue(res_0800[0]["ok"])
        self.assertEqual(res_0800_dup, [])

        snap_after_success = self.service.get_status(now=datetime(2026, 11, 14, 8, 1, 0, tzinfo=EAST_8))
        self.assertIsNotNone(snap_after_success["last_success_time"])
        self.assertEqual(snap_after_success["last_attempt_status"], "SUCCESS")
        self.assertIsNone(snap_after_success["last_failure_time"])
        self.assertEqual(snap_after_success["next_run_time"], "2026-11-14 12:00:00")

        # 12:00 触发时模拟 API 连接失败：记录失败时间，同时保留上次成功时间
        with patch.object(
            weather,
            "fetch_hourly_temperatures",
            side_effect=weather.WeatherImporterError("连接 Open-Meteo 超时"),
        ):
            res_1200 = self.service._scheduler_step(now=datetime(2026, 11, 14, 12, 0, 10, tzinfo=EAST_8))

        self.assertEqual(len(res_1200), 1)
        self.assertFalse(res_1200[0]["ok"])
        snap_after_fail = self.service.get_status(now=datetime(2026, 11, 14, 12, 1, 0, tzinfo=EAST_8))
        self.assertEqual(snap_after_fail["last_attempt_status"], "FAILED")
        self.assertEqual(snap_after_fail["last_success_time"], snap_after_success["last_success_time"])
        self.assertIsNotNone(snap_after_fail["last_failure_time"])
        self.assertIn("连接 Open-Meteo 超时", snap_after_fail["last_failure_message"])
        self.assertEqual(len(snap_after_fail["history"]), 2)
        self.assertEqual(snap_after_fail["history"][0]["status"], "FAILED")
        self.assertEqual(snap_after_fail["history"][1]["status"], "SUCCESS")
        self.assertEqual(snap_after_fail["next_run_time"], "2026-11-14 18:00:00")

        # 跨自然日后清空当日执行标记，允许次日再次执行
        with patch.object(
            weather,
            "fetch_hourly_temperatures",
            side_effect=weather.WeatherImporterError("次日短暂波动"),
        ):
            res_next_day = self.service._scheduler_step(now=datetime(2026, 11, 15, 8, 0, 5, tzinfo=EAST_8))
        self.assertEqual(len(res_next_day), 1)

    def _client(self, group="Global_admin"):
        app = FastAPI()
        app.include_router(dashboard.router)
        app.dependency_overrides[dashboard.get_current_session] = lambda: SimpleNamespace(
            username="admin_test",
            group=group,
            permissions=SimpleNamespace(actions=SimpleNamespace(can_access_admin_console=False)),
        )
        return TestClient(app)

    def test_auto_import_api_endpoints_and_permissions(self):
        with self._client("Group_admin") as forbidden_client:
            self.assertEqual(forbidden_client.get("/dashboard/temperature/auto-import/status").status_code, 403)
            self.assertEqual(
                forbidden_client.put("/dashboard/temperature/auto-import/config", json={"enabled": True, "schedule_times": ["08:00"]}).status_code,
                403,
            )
            self.assertEqual(forbidden_client.post("/dashboard/temperature/auto-import/run").status_code, 403)

        with self._client("Global_admin") as client:
            resp = client.put(
                "/dashboard/temperature/auto-import/config",
                json={"enabled": True, "schedule_times": ["20:00", "07:30", "20:00"]},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["data"]["schedule_times"], ["07:30", "20:00"])

            bad = client.put(
                "/dashboard/temperature/auto-import/config",
                json={"enabled": True, "schedule_times": ["99:00"]},
            )
            self.assertEqual(bad.status_code, 422)

            with patch.object(
                weather,
                "fetch_hourly_temperatures",
                return_value={
                    "source": {"provider": "open-meteo", "timezone": "Asia/Singapore"},
                    "hourly": [{"time": "2026-11-14T10:00", "value": 8.0}],
                    "dates": ["2026-11-14"],
                    "summary": {"total_hours": 1},
                },
            ), patch.object(auto_mod, "SessionLocal", return_value=MagicMock()), patch.object(
                weather,
                "persist_hourly_temperatures",
                return_value={"inserted": 1, "replaced": 1, "start": "2026-11-14T10:00:00+08:00", "end": "2026-11-14T10:00:00+08:00"},
            ):
                run_resp = client.post("/dashboard/temperature/auto-import/run")
                self.assertEqual(run_resp.status_code, 200)
                body = run_resp.json()
                self.assertTrue(body["ok"])
                self.assertIsNotNone(body["data"]["last_success_time"])
                self.assertEqual(body["data"]["history"][0]["trigger"], "manual_admin")

            status_resp = client.get("/dashboard/temperature/auto-import/status")
            self.assertEqual(status_resp.status_code, 200)
            self.assertEqual(status_resp.json()["data"]["last_attempt_status"], "SUCCESS")

    def test_dashboard_commit_also_updates_last_success_and_failure_time(self):
        weather.save_weather_import_config("https://example.com/forecast")
        response = MagicMock()
        response.json.return_value = {"hourly": {"time": ["2026-11-14T10:00"], "temperature_2m": [8.2]}}

        with self._client("Global_admin") as client:
            with patch.object(weather.httpx, "Client") as remote, \
                    patch.object(dashboard, "SessionLocal"), \
                    patch.object(dashboard, "persist_hourly_temperatures", return_value={"inserted": 1, "replaced": 0}):
                remote.return_value.__enter__.return_value.get.return_value = response
                ok_res = client.post("/dashboard/temperature/import/commit")
                self.assertEqual(ok_res.status_code, 200)

            status_ok = client.get("/dashboard/temperature/auto-import/status").json()["data"]
            self.assertIsNotNone(status_ok["last_success_time"])
            self.assertEqual(status_ok["last_success_trigger"], "数据看板手动")

            with patch.object(weather.httpx, "Client") as remote, \
                    patch.object(dashboard, "SessionLocal"):
                remote.return_value.__enter__.return_value.get.side_effect = weather.httpx.ConnectTimeout("timeout")
                fail_res = client.post("/dashboard/temperature/import/commit")
                self.assertEqual(fail_res.status_code, 502)

            status_fail = client.get("/dashboard/temperature/auto-import/status").json()["data"]
            self.assertIsNotNone(status_fail["last_failure_time"])
            self.assertEqual(status_fail["last_failure_trigger"], "数据看板手动")
            self.assertIsNotNone(status_fail["last_success_time"])


class EnsembleWeatherAutoImportTests(unittest.TestCase):
    """验证 35 天集合气温预报独立模块的配置、定时调度与页面联动。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.settings_path = Path(self.temp.name) / "project_settings.json"
        self.near_cfg = Path(self.temp.name) / "weather_import_config.json"
        self.near_state = Path(self.temp.name) / "weather_auto_import_state.json"
        self.near_auto = Path(self.temp.name) / "weather_auto_import_config.json"
        self.ensemble_cfg = Path(self.temp.name) / "ensemble_weather_import_config.json"
        self.ensemble_state = Path(self.temp.name) / "ensemble_weather_auto_import_state.json"
        self.ensemble_auto = Path(self.temp.name) / "ensemble_weather_auto_import_config.json"

        patches = [
            patch.object(project_settings, "get_project_settings_path", return_value=self.settings_path),
            patch.object(weather, "_weather_config_path", return_value=self.near_cfg),
            patch.object(auto_mod, "_auto_state_path", return_value=self.near_state),
            patch.object(auto_mod, "_auto_config_path", return_value=self.near_auto),
            patch.object(ensemble_svc, "_ensemble_config_path", return_value=self.ensemble_cfg),
            patch.object(auto_mod, "_ensemble_state_path", return_value=self.ensemble_state),
            patch.object(auto_mod, "_ensemble_auto_config_path", return_value=self.ensemble_auto),
            patch.object(auto_mod.WeatherAutoImportService, "_write_audit_log"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _client(self, group="Global_admin"):
        app = FastAPI()
        app.include_router(dashboard.router)
        app.include_router(dynamic_plan.public_router)
        app.dependency_overrides[dashboard.get_current_session] = lambda: SimpleNamespace(
            username="admin_test",
            group=group,
            permissions=SimpleNamespace(actions=SimpleNamespace(can_access_admin_console=False)),
        )
        return TestClient(app)

    def test_ensemble_config_load_save_and_validation(self):
        loaded_default = ensemble_svc.load_ensemble_weather_import_config()
        self.assertEqual(loaded_default["api_url"], ensemble_svc.DEFAULT_ENSEMBLE_API_URL)

        with self.assertRaises(ValueError):
            ensemble_svc.save_ensemble_weather_import_config("ftp://invalid-scheme.example.com")

        custom_url = "https://ensemble-api.open-meteo.com/v1/ensemble?latitude=39.0&longitude=121.6&forecast_days=35"
        saved = ensemble_svc.save_ensemble_weather_import_config(custom_url)
        self.assertEqual(saved["api_url"], custom_url)
        self.assertFalse(self.settings_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(ensemble_svc.load_ensemble_weather_import_config()["api_url"], custom_url)

    def test_ensemble_service_isolates_from_near_and_tracks_success_failure(self):
        # 修改 35 天集合预报配置与执行不应污染近端气温状态文件
        near_before = auto_mod.weather_auto_import_service.update_config(
            enabled=True,
            schedule_times=["06:00"],
            now=datetime(2026, 11, 14, 5, 0, 0, tzinfo=EAST_8),
        )
        ensemble_status = auto_mod.ensemble_weather_auto_import_service.update_config(
            enabled=True,
            schedule_times=["07:30", "19:30"],
            now=datetime(2026, 11, 14, 7, 0, 0, tzinfo=EAST_8),
        )
        self.assertEqual(ensemble_status["schedule_times"], ["07:30", "19:30"])
        self.assertEqual(near_before["schedule_times"], ["06:00"])

        with patch.object(
            ensemble_svc,
            "fetch_and_import_ensemble_weather",
            return_value={
                "ok": True,
                "message": "成功同步35天集合气温预报（720 条数据）",
                "inserted_or_updated": 720,
                "skipped_near": 12,
                "members_count": 51,
                "start_time": "2026-11-14 00:00:00",
                "end_time": "2026-12-19 23:00:00",
            },
        ):
            step_ok = auto_mod.ensemble_weather_auto_import_service._scheduler_step(
                now=datetime(2026, 11, 14, 7, 30, 8, tzinfo=EAST_8)
            )
        self.assertEqual(len(step_ok), 1)
        self.assertTrue(step_ok[0]["ok"])

        with patch.object(
            ensemble_svc,
            "fetch_and_import_ensemble_weather",
            side_effect=ensemble_svc.EnsembleWeatherError("连接 Ensemble API 超时"),
        ):
            step_err = auto_mod.ensemble_weather_auto_import_service._scheduler_step(
                now=datetime(2026, 11, 14, 19, 30, 5, tzinfo=EAST_8)
            )
        self.assertEqual(len(step_err), 1)
        self.assertFalse(step_err[0]["ok"])

        snap = step_err[0]["data"]
        self.assertIsNotNone(snap["last_success_time"])
        self.assertIsNotNone(snap["last_failure_time"])
        self.assertEqual(snap["last_attempt_status"], "FAILED")
        self.assertEqual(snap["history"][0]["trigger"], "auto")
        self.assertEqual(snap["history"][1]["status"], "SUCCESS")

        # 确认近端气温模块完全保持未受影响
        near_snap = auto_mod.weather_auto_import_service.get_status(
            now=datetime(2026, 11, 14, 20, 0, 0, tzinfo=EAST_8)
        )
        self.assertIsNone(near_snap["last_success_time"])
        self.assertIsNone(near_snap["last_failure_time"])
        self.assertEqual(near_snap["schedule_times"], ["06:00"])

    def test_ensemble_dashboard_endpoints_and_dynamic_plan_sync(self):
        with self._client("Group_admin") as forbidden_client:
            self.assertEqual(forbidden_client.get("/dashboard/temperature/ensemble/config").status_code, 403)
            self.assertEqual(
                forbidden_client.put("/dashboard/temperature/ensemble/config", json={"api_url": "https://example.com"}).status_code,
                403,
            )
            self.assertEqual(forbidden_client.get("/dashboard/temperature/ensemble/auto-import/status").status_code, 403)
            self.assertEqual(
                forbidden_client.put("/dashboard/temperature/ensemble/auto-import/config", json={"enabled": True, "schedule_times": ["07:30"]}).status_code,
                403,
            )
            self.assertEqual(forbidden_client.post("/dashboard/temperature/ensemble/auto-import/run").status_code, 403)

        with self._client("Global_admin") as client:
            cfg_put = client.put(
                "/dashboard/temperature/ensemble/config",
                json={"api_url": "https://ensemble-api.open-meteo.com/v1/ensemble?latitude=38.9&longitude=121.6&forecast_days=35"},
            )
            self.assertEqual(cfg_put.status_code, 200)
            self.assertIn("forecast_days=35", cfg_put.json()["data"]["api_url"])

            bad_cfg = client.put("/dashboard/temperature/ensemble/config", json={"api_url": "not-a-url"})
            self.assertEqual(bad_cfg.status_code, 422)

            auto_put = client.put(
                "/dashboard/temperature/ensemble/auto-import/config",
                json={"enabled": True, "schedule_times": ["19:00", "07:30", "19:00"]},
            )
            self.assertEqual(auto_put.status_code, 200)
            self.assertEqual(auto_put.json()["data"]["schedule_times"], ["07:30", "19:00"])

            bad_auto = client.put(
                "/dashboard/temperature/ensemble/auto-import/config",
                json={"enabled": True, "schedule_times": ["25:99"]},
            )
            self.assertEqual(bad_auto.status_code, 422)

            with patch.object(
                ensemble_svc,
                "fetch_and_import_ensemble_weather",
                return_value={"ok": True, "message": "管理中心立即同步35天预报成功", "imported_count": 840},
            ):
                run_resp = client.post("/dashboard/temperature/ensemble/auto-import/run")
                self.assertEqual(run_resp.status_code, 200)
                self.assertTrue(run_resp.json()["ok"])
                self.assertEqual(run_resp.json()["data"]["history"][0]["trigger"], "manual_admin")

            # 计划情景分解页面原有手动按钮调用同样同步状态
            with patch.object(
                ensemble_svc,
                "fetch_and_import_ensemble_weather",
                return_value={"ok": True, "message": "页面按钮同步35天预报成功", "imported_count": 840},
            ):
                dp_ok = client.post("/dynamic_plan/import_ensemble_temperature")
                self.assertEqual(dp_ok.status_code, 200)
                self.assertTrue(dp_ok.json()["ok"])

            status_after_dp = client.get("/dashboard/temperature/ensemble/auto-import/status").json()["data"]
            self.assertEqual(status_after_dp["last_success_trigger"], "计划情景页面手动")

            with patch.object(
                ensemble_svc,
                "fetch_and_import_ensemble_weather",
                side_effect=ensemble_svc.EnsembleWeatherError("远端连接重置"),
            ):
                dp_fail = client.post("/dynamic_plan/import_ensemble_temperature")
                self.assertEqual(dp_fail.status_code, 200)
                self.assertFalse(dp_fail.json()["ok"])

            status_after_fail = client.get("/dashboard/temperature/ensemble/auto-import/status").json()["data"]
            self.assertIsNotNone(status_after_fail["last_failure_time"])
            self.assertEqual(status_after_fail["last_failure_trigger"], "计划情景页面手动")
            self.assertIn("远端连接重置", status_after_fail["last_failure_message"])


if __name__ == "__main__":
    unittest.main()
