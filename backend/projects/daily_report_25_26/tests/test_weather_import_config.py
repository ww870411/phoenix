"""在仓库内隔离配置，验证管理配置及导入调用链，不访问外网或业务数据库。"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services import weather_importer as weather
from backend.projects.daily_report_25_26.api import dashboard


class WeatherImportConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "weather_import_config.json"
        mocked = patch.object(weather, "_weather_config_path", return_value=self.path)
        mocked.start()
        self.addCleanup(mocked.stop)
        self.api_url = "https://example.com/forecast?latitude=39&hourly=temperature_2m"

    def test_missing_config_preserves_original_url_without_creating_file(self):
        self.assertEqual(weather.load_weather_import_config()["api_url"], weather.OPEN_METEO_API_URL)
        self.assertFalse(self.path.exists())

    def test_saved_config_survives_reload_and_trims_spaces(self):
        weather.save_weather_import_config(f"  {self.api_url}  ")
        self.assertEqual(weather.load_weather_import_config(), {"api_url": self.api_url})
        self.assertFalse(self.path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_url_does_not_overwrite_saved_config(self):
        weather.save_weather_import_config(self.api_url)
        for invalid in ("", "ftp://example.com", "https://", "https://example.com/has space", "http://host:bad"):
            with self.subTest(url=invalid), self.assertRaises(ValueError):
                weather.save_weather_import_config(invalid)
        self.assertEqual(weather.load_weather_import_config()["api_url"], self.api_url)

    def test_corrupt_config_is_reported_instead_of_silently_using_default(self):
        self.path.write_text("{}", encoding="utf-8")
        with self.assertRaises(weather.WeatherImporterError):
            weather.load_weather_import_config()

    def test_failed_replace_preserves_config_and_cleans_temporary_file(self):
        weather.save_weather_import_config(self.api_url)
        with patch.object(weather.os, "replace", side_effect=OSError("模拟写入失败")):
            with self.assertRaises(OSError):
                weather.save_weather_import_config("https://example.org/forecast")
        self.assertEqual(weather.load_weather_import_config()["api_url"], self.api_url)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_fetch_uses_latest_saved_url_and_reports_actual_source(self):
        response = MagicMock()
        response.json.return_value = {
            "timezone": "Asia/Singapore",
            "hourly": {"time": ["2026-11-06T12:00"], "temperature_2m": [9.5]},
        }
        with patch.object(weather.httpx, "Client") as client:
            client.return_value.__enter__.return_value.get.return_value = response
            for url in (self.api_url, "https://example.org/forecast?past_days=5"):
                weather.save_weather_import_config(url)
                result = weather.fetch_hourly_temperatures()
                client.return_value.__enter__.return_value.get.assert_called_with(url)
                self.assertEqual(result["source"]["url"], url)
                self.assertEqual(result["summary"]["total_hours"], 1)
                self.assertEqual(result["hourly"][0]["value"], 9.5)

    def test_incompatible_response_raises_business_error(self):
        for payload in ([], {}, {"hourly": {"time": [], "temperature_2m": [1]}}):
            with self.subTest(payload=payload), self.assertRaises(weather.WeatherImporterError):
                weather._validate_hourly_payload(payload)

    def client(self, group="Global_admin"):
        app = FastAPI()
        app.include_router(dashboard.router)
        app.dependency_overrides[dashboard.get_current_session] = lambda: SimpleNamespace(
            group=group, permissions=SimpleNamespace(actions=SimpleNamespace(can_access_admin_console=False))
        )
        return TestClient(app)

    def test_config_endpoints_read_save_and_validate(self):
        with self.client() as client:
            self.assertEqual(client.get("/dashboard/temperature/config").json()["data"]["api_url"], weather.OPEN_METEO_API_URL)
            result = client.put("/dashboard/temperature/config", json={"api_url": self.api_url})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(client.get("/dashboard/temperature/config").json()["data"]["api_url"], self.api_url)
            self.assertEqual(client.put("/dashboard/temperature/config", json={"api_url": ""}).status_code, 422)

    def test_config_endpoints_preserve_existing_admin_permissions(self):
        with self.client("Group_admin") as client:
            self.assertEqual(client.get("/dashboard/temperature/config").status_code, 403)
            self.assertEqual(client.put("/dashboard/temperature/config", json={"api_url": self.api_url}).status_code, 403)
        self.assertFalse(self.path.exists())

    def test_config_endpoints_report_storage_errors(self):
        with self.client() as client:
            with patch.object(dashboard, "save_weather_import_config", side_effect=OSError):
                self.assertEqual(client.put("/dashboard/temperature/config", json={"api_url": self.api_url}).status_code, 500)
            self.path.write_text("{}", encoding="utf-8")
            self.assertEqual(client.get("/dashboard/temperature/config").status_code, 500)

    def test_preview_and_commit_both_use_saved_source(self):
        weather.save_weather_import_config(self.api_url)
        response = MagicMock()
        response.json.return_value = {
            "hourly": {"time": ["2026-11-06T12:00"], "temperature_2m": [9.5]},
        }
        with self.client() as client, patch.object(weather.httpx, "Client") as remote, \
                patch.object(dashboard, "SessionLocal"), \
                patch.object(dashboard, "compare_with_existing", return_value={}), \
                patch.object(dashboard, "persist_hourly_temperatures", return_value={}) as persist:
            remote.return_value.__enter__.return_value.get.return_value = response
            for endpoint in ("/dashboard/temperature/import", "/dashboard/temperature/import/commit"):
                result = client.post(endpoint)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()["source"]["url"], self.api_url)
                remote.return_value.__enter__.return_value.get.assert_called_with(self.api_url)
            persist.assert_called_once()


if __name__ == "__main__":
    unittest.main()
