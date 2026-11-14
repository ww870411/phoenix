# -*- coding: utf-8 -*-
"""
验证综合配置文件 config/project_settings.json 与 runtime/*_state.json 的拆分、
并发安全读写、跨服务业务日期联动，以及旧配置文件幂等迁移能力。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.projects.daily_report_25_26.services import kdocs_complaint_service
from backend.services import (
    auth_manager as auth_mod,
    dashboard_expression,
    ensemble_weather_service as ensemble_svc,
    heating_season_service as season_svc,
    project_settings,
    spot_electricity_sync_service as spot_mod,
    weather_auto_import_service as auto_mod,
    weather_importer as weather_svc,
)


class ProjectSettingsStoreTests(unittest.TestCase):
    """验证统一配置中心、运行态隔离与历史配置迁移。"""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config_dir = self.root / "projects" / "daily_report_25_26" / "config"
        self.runtime_dir = self.root / "projects" / "daily_report_25_26" / "runtime"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.config_dir / "project_settings.json"

        patches = [
            patch.object(project_settings, "DATA_DIRECTORY", self.root),
            patch.object(project_settings, "get_project_config_dir", side_effect=self._fake_config_dir),
            patch.object(project_settings, "get_project_runtime_dir", side_effect=self._fake_runtime_dir),
            patch.object(season_svc, "_resolve_runtime_dir", side_effect=self._fake_runtime_dir),
            patch.object(season_svc, "resolve_global_date_path", return_value=self.runtime_dir / "date.json"),
            patch.object(dashboard_expression, "_resolve_date_config_path", return_value=self.runtime_dir / "date.json"),
            patch.object(weather_svc, "_weather_config_path", return_value=self.runtime_dir / "weather_import_config.json"),
            patch.object(ensemble_svc, "_ensemble_config_path", return_value=self.runtime_dir / "ensemble_weather_import_config.json"),
            patch.object(auto_mod, "_auto_state_path", return_value=self.runtime_dir / "weather_auto_import_state.json"),
            patch.object(auto_mod, "_auto_config_path", return_value=self.runtime_dir / "weather_auto_import_config.json"),
            patch.object(auto_mod, "_ensemble_state_path", return_value=self.runtime_dir / "ensemble_weather_auto_import_state.json"),
            patch.object(auto_mod, "_ensemble_auto_config_path", return_value=self.runtime_dir / "ensemble_weather_auto_import_config.json"),
            patch.object(spot_mod, "CONFIG_FILE_PATH", self.config_dir / "spot_electricity_sync_config.json"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _fake_config_dir(self, project_key: str = "daily_report_25_26") -> Path:
        path = self.root / "projects" / project_key / "config"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _fake_runtime_dir(self, project_key: str = "daily_report_25_26") -> Path:
        path = self.root / "projects" / project_key / "runtime"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_all_six_sections_coexist_without_overwriting(self) -> None:
        """依次写入 6 个业务配置节点时应保留全部节点，且文件保持 UTF-8 无 BOM。"""
        season_svc.set_business_date("daily_report_25_26", "2026-11-14")
        season_svc.update_season_config("daily_report_25_26", active_period="26-27", description="测试26-27供暖期")
        weather_svc.save_weather_import_config("https://example.com/near")
        auto_mod.weather_auto_import_service.update_config(enabled=True, schedule_times=["08:00", "14:00"])
        ensemble_svc.save_ensemble_weather_import_config("https://example.com/ensemble")
        auto_mod.ensemble_weather_auto_import_service.update_config(enabled=False, schedule_times=["09:30"])
        kdocs_complaint_service.save_config(
            {
                "share_link": "https://www.kdocs.cn/l/testShare01",
                "share_id": "testShare01",
                "wps_sid": "dummy-session-token",
                "description": "测试底表",
                "auto_sync_enabled": True,
            }
        )
        spot_svc = spot_mod.SpotElectricitySyncService()
        spot_svc.update_config(
            {
                "enabled": True,
                "cron_time": "10:15",
                "retry_interval_minutes": 15,
                "max_retries_per_day": 4,
                "target_date_rule": "yesterday",
            }
        )

        raw_bytes = self.settings_path.read_bytes()
        self.assertFalse(raw_bytes.startswith(b"\xef\xbb\xbf"))
        doc = json.loads(raw_bytes.decode("utf-8"))

        self.assertTrue(
            {"biz_date", "season", "weather_near", "weather_ensemble", "kdocs_complaint", "spot_electricity"}.issubset(
                doc.keys()
            )
        )
        self.assertEqual(doc["biz_date"]["set_biz_date"], "2026-11-14")
        self.assertEqual(doc["season"]["active_period"], "26-27")
        self.assertEqual(doc["season"]["description"], "测试26-27供暖期")
        self.assertEqual(doc["weather_near"]["api_url"], "https://example.com/near")
        self.assertEqual(doc["weather_near"]["schedule_times"], ["08:00", "14:00"])
        self.assertTrue(doc["weather_near"]["enabled"])
        self.assertEqual(doc["weather_ensemble"]["api_url"], "https://example.com/ensemble")
        self.assertEqual(doc["weather_ensemble"]["schedule_times"], ["09:30"])
        self.assertFalse(doc["weather_ensemble"]["enabled"])
        self.assertEqual(doc["kdocs_complaint"]["share_id"], "testShare01")
        self.assertTrue(doc["kdocs_complaint"]["auto_sync_enabled"])
        self.assertEqual(doc["spot_electricity"]["cron_time"], "10:15")
        self.assertEqual(doc["spot_electricity"]["retry_interval_minutes"], 15)

    def test_runtime_state_updates_do_not_touch_project_settings(self) -> None:
        """更新金山文档/电力现货/自动气温导入的运行态字段时，绝不改写 project_settings.json。"""
        kdocs_complaint_service.save_config(
            {
                "share_link": "https://www.kdocs.cn/l/testShare02",
                "wps_sid": "dummy-token",
                "auto_sync_enabled": True,
            }
        )
        spot_svc = spot_mod.SpotElectricitySyncService()
        spot_svc.update_config({"enabled": True, "cron_time": "07:40"})
        auto_mod.weather_auto_import_service.update_config(enabled=True, schedule_times=["08:00"])

        settings_before = self.settings_path.read_bytes()

        # 仅写入 KDocs 运行态
        kdocs_complaint_service.save_config(
            {
                "last_test_status": "SUCCESS",
                "last_test_time": "2026-11-14 18:00:00",
                "last_test_message": "ok",
                "last_sync_time": "2026-11-14 18:01:00",
            }
        )
        kdocs_state = json.loads((self.runtime_dir / "kdocs_complaint_state.json").read_text(encoding="utf-8"))
        self.assertEqual(kdocs_state["last_test_status"], "SUCCESS")
        self.assertNotIn("wps_sid", kdocs_state)

        # 仅写入现货运行态（模拟定时执行失败记录）
        spot_svc._config["last_run_status"] = "failed"
        spot_svc._config["last_run_error"] = "mock error"
        spot_svc._persist_config(include_settings=False)
        spot_state = json.loads((self.runtime_dir / "spot_electricity_sync_state.json").read_text(encoding="utf-8"))
        self.assertEqual(spot_state["last_run_status"], "failed")
        self.assertNotIn("cron_time", spot_state)

        # 仅写入自动气温导入运行态
        with patch.object(auto_mod.WeatherAutoImportService, "_write_audit_log"):
            with patch.object(
                weather_svc,
                "fetch_hourly_temperatures",
                return_value={
                    "source": {"timezone": "Asia/Singapore"},
                    "hourly": [{"time": "2026-11-14T08:00", "value": 6.5}],
                    "dates": ["2026-11-14"],
                    "summary": {"total_hours": 1},
                },
            ), patch.object(auto_mod, "SessionLocal", return_value=MagicMock()), patch.object(
                weather_svc,
                "persist_hourly_temperatures",
                return_value={"inserted": 1, "replaced": 0, "start": "2026-11-14T08:00:00+08:00", "end": "2026-11-14T08:00:00+08:00"},
            ):
                auto_mod.weather_auto_import_service.run_import_once(trigger="manual")

        self.assertTrue((self.runtime_dir / "weather_auto_import_state.json").exists())
        self.assertEqual(self.settings_path.read_bytes(), settings_before)

    def test_biz_date_syncs_between_heating_season_auth_manager_and_dashboard(self) -> None:
        """业务日期写入 project_settings.json 后，heating_season、auth_manager 与看板默认日期联动一致。"""
        mgr = auth_mod.AuthManager()
        mgr._date_config_path = self.runtime_dir / "date.json"
        with patch.object(auth_mod, "auth_manager", mgr), patch.object(season_svc, "auth_manager", mgr):
            season_svc.set_business_date("daily_report_25_26", "2026-11-20")
            self.assertEqual(season_svc.read_current_biz_date("daily_report_25_26"), "2026-11-20")
            self.assertEqual(mgr.current_display_date(), date(2026, 11, 20))
            self.assertEqual(dashboard_expression.load_default_push_date("daily_report_25_26"), "2026-11-20")

            mgr.set_display_date(date(2026, 11, 22))
            self.assertEqual(season_svc.read_current_biz_date("daily_report_25_26"), "2026-11-22")
            self.assertEqual(dashboard_expression.load_default_push_date("daily_report_25_26"), "2026-11-22")

    def test_idempotent_legacy_migration_splits_config_state_and_archives_old_files(self) -> None:
        """验证历史分散文件可幂等拆分为综合配置 + runtime 状态文件并自动归档。"""
        (self.runtime_dir / "date.json").write_text(
            json.dumps({"set_biz_date": "2026-11-12"}, ensure_ascii=False), encoding="utf-8"
        )
        (self.runtime_dir / "season_config.json").write_text(
            json.dumps({"active_period": "25-26", "peer_period": "24-25", "start_date": "2025-11-01", "end_date": "2026-04-05"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.runtime_dir / "weather_import_config.json").write_text(
            json.dumps({"api_url": "https://example.com/near-legacy"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.runtime_dir / "weather_auto_import_config.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "schedule_times": ["07:00", "13:00"],
                    "last_success_time": "2026-11-12T07:00:05+08:00",
                    "history": [{"trigger": "schedule", "status": "success"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.runtime_dir / "ensemble_weather_auto_import_config.json").write_text(
            json.dumps(
                {
                    "enabled": False,
                    "schedule_times": ["10:00"],
                    "last_failure_message": "network timeout",
                    "history": [{"trigger": "manual", "status": "failed"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.config_dir / "kdocs_complaint_config.json").write_text(
            json.dumps(
                {
                    "share_link": "https://www.kdocs.cn/l/legacyShare",
                    "share_id": "legacyShare",
                    "wps_sid": "legacy-dummy-token",
                    "description": "旧底表",
                    "auto_sync_enabled": False,
                    "last_test_status": "SUCCESS",
                    "last_sync_time": "2026-11-11 09:00:00",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (self.config_dir / "spot_electricity_sync_config.json").write_text(
            json.dumps(
                {
                    "enabled": True,
                    "cron_time": "08:30",
                    "retry_interval_minutes": 20,
                    "max_retries_per_day": 5,
                    "target_date_rule": "yesterday",
                    "last_sync_date": "2026-11-11",
                    "last_run_status": "success",
                    "last_run_message": "sync ok",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        first = project_settings.migrate_legacy_project_settings("daily_report_25_26", archive_legacy=True)
        self.assertEqual(
            set(first["migrated_sections"]),
            {"biz_date", "season", "weather_near", "weather_ensemble", "kdocs_complaint", "spot_electricity"},
        )
        self.assertEqual(len(first["archived_files"]), 7)

        # 验证目标综合配置
        settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual(settings["biz_date"]["set_biz_date"], "2026-11-12")
        self.assertEqual(settings["season"]["active_period"], "25-26")
        self.assertEqual(settings["weather_near"]["api_url"], "https://example.com/near-legacy")
        self.assertEqual(settings["weather_near"]["schedule_times"], ["07:00", "13:00"])
        self.assertEqual(settings["weather_ensemble"]["schedule_times"], ["10:00"])
        self.assertEqual(settings["kdocs_complaint"]["share_id"], "legacyShare")
        self.assertNotIn("last_test_status", settings["kdocs_complaint"])
        self.assertEqual(settings["spot_electricity"]["cron_time"], "08:30")
        self.assertNotIn("last_sync_date", settings["spot_electricity"])

        # 验证拆分到 runtime/ 的状态文件
        near_state = json.loads((self.runtime_dir / "weather_auto_import_state.json").read_text(encoding="utf-8"))
        ens_state = json.loads((self.runtime_dir / "ensemble_weather_auto_import_state.json").read_text(encoding="utf-8"))
        kdocs_state = json.loads((self.runtime_dir / "kdocs_complaint_state.json").read_text(encoding="utf-8"))
        spot_state = json.loads((self.runtime_dir / "spot_electricity_sync_state.json").read_text(encoding="utf-8"))
        self.assertEqual(near_state["last_success_time"], "2026-11-12T07:00:05+08:00")
        self.assertEqual(ens_state["last_failure_message"], "network timeout")
        self.assertEqual(kdocs_state["last_test_status"], "SUCCESS")
        self.assertEqual(spot_state["last_sync_date"], "2026-11-11")
        self.assertEqual(spot_state["last_run_status"], "success")

        # 原旧文件应已归档清理
        for legacy_name in (
            self.runtime_dir / "date.json",
            self.runtime_dir / "season_config.json",
            self.runtime_dir / "weather_import_config.json",
            self.runtime_dir / "weather_auto_import_config.json",
            self.runtime_dir / "ensemble_weather_auto_import_config.json",
            self.config_dir / "kdocs_complaint_config.json",
            self.config_dir / "spot_electricity_sync_config.json",
        ):
            self.assertFalse(legacy_name.exists())

        # 二次执行必须幂等空操作
        second = project_settings.migrate_legacy_project_settings("daily_report_25_26", archive_legacy=True)
        self.assertEqual(second["migrated_sections"], [])
        self.assertEqual(second["migrated_states"], [])
        self.assertEqual(second["archived_files"], [])


if __name__ == "__main__":
    unittest.main()
