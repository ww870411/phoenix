"""在仓库内隔离目录验证区间缓存，不改动正式缓存文件。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from backend.services import dashboard_cache as cache


class CacheRangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "dashboard_cache_v2"
        mocked = patch.object(cache, "_resolve_cache_root", return_value=self.root)
        mocked.start()
        self.addCleanup(mocked.stop)
        # 先建立索引，阻止测试触发正式历史缓存迁移。
        cache._write_index("daily_report_25_26", cache._default_index("daily_report_25_26"))
        mocked = patch.object(cache, "_adopt_fallback_split_cache")
        mocked.start()
        self.addCleanup(mocked.stop)

    def put(self, day, value=1, key=None):
        from backend.services.heating_season_service import get_calculation_signature
        cache.update_cache_entry("daily_report_25_26", key or day, {
            "ok": True, "push_date": day, "show_date": day,
            "calculation_signature": get_calculation_signature(),
            "temperature_revision": cache.get_temperature_revision("daily_report_25_26"),
            "data": {"2.边际利润": {"测试值": value}, "单位字典": {"Group": "集团"}},
        })

    def test_disjoint_ranges_and_selective_delete_preserve_other_files(self):
        for day in ("2025-11-01", "2025-11-02", "2026-04-05", "2026-11-01", "2026-11-02"):
            self.put(day)
        before = {path.relative_to(self.root): path.read_bytes() for path in self.root.rglob("*.json") if path.name != "index.json"}
        result = cache.delete_cache_range("daily_report_25_26", "2025-11-02", "2026-04-05")
        self.assertEqual(result["deleted_dates"], ["2025-11-02", "2026-04-05"])
        self.assertEqual(result["available_dates"], ["2025-11-01", "2026-11-01", "2026-11-02"])
        for day in result["deleted_dates"]:
            self.assertFalse((self.root / day).exists())
        for relative, content in before.items():
            if relative.parts[0] not in result["deleted_dates"]:
                self.assertEqual((self.root / relative).read_bytes(), content)
        self.assertEqual(set(cache._load_index("daily_report_25_26")["entries"]), set(result["available_dates"]))

    def test_republish_overwrites_only_selected_day_and_deleted_day_can_be_rebuilt(self):
        self.put("2025-11-01", 10)
        self.put("2026-11-01", 20)
        retained = (self.root / "2026-11-01" / "summary.json").read_bytes()
        self.put("2025-11-01", 30)
        self.assertEqual(cache._load_json_dict(self.root / "2025-11-01" / "summary.json")["2.边际利润"]["测试值"], 30)
        self.assertEqual((self.root / "2026-11-01" / "summary.json").read_bytes(), retained)
        cache.delete_cache_range("daily_report_25_26", "2025-11-01", "2025-11-01")
        self.assertIsNone(cache.get_cached_payload("daily_report_25_26", "2025-11-01")[0])
        self.put("2025-11-01", 40)
        self.assertIn("2025-11-01", cache.get_cache_status("daily_report_25_26")["available_dates"])

    def test_default_alias_is_removed_with_its_actual_date(self):
        self.put("2025-11-01", key=cache.DEFAULT_CACHE_KEY)
        self.put("2026-11-01")
        self.assertEqual(cache.get_cache_status("daily_report_25_26")["available_dates"], ["2025-11-01", "2026-11-01"])
        self.assertEqual(cache.get_cached_payload("daily_report_25_26", "2025-11-01")[0]["push_date"], "2025-11-01")
        result = cache.delete_cache_range("daily_report_25_26", "2025-11-01", "2025-11-01")
        self.assertEqual(result["deleted_count"], 1)
        self.assertNotIn(cache.DEFAULT_CACHE_KEY, cache._load_index("daily_report_25_26")["entries"])
        self.assertFalse((self.root / cache.DEFAULT_CACHE_KEY).exists())

    def test_invalid_or_empty_intersection_does_not_mutate_cache(self):
        self.put("2025-11-01")
        before = (self.root / "index.json").read_bytes()
        for start, end in (("", "2026-11-01"), ("2026-02-30", "2026-03-01"), ("2026-11-02", "2026-11-01"), ("20261101", "2026-11-02")):
            with self.assertRaises(ValueError):
                cache.delete_cache_range("daily_report_25_26", start, end)
            with self.assertRaises(ValueError):
                cache.resolve_publish_schedule(start_date=start, end_date=end)
        self.assertEqual(cache.delete_cache_range("daily_report_25_26", "2026-11-01", "2026-11-02")["deleted_count"], 0)
        self.assertEqual((self.root / "index.json").read_bytes(), before)

    def test_inventory_excludes_incomplete_files(self):
        self.put("2025-11-01")
        (self.root / "2025-11-01" / "trend.json").unlink()
        self.assertEqual(cache.get_cache_status("daily_report_25_26")["available_dates"], [])
        self.assertIsNone(cache.get_cached_payload("daily_report_25_26", "2025-11-01")[0])

    def test_history_cache_with_old_formula_is_skipped_but_files_preserved(self):
        self.put("2025-11-01")
        meta_file = self.root / "2025-11-01" / "meta.json"
        meta = cache._load_json_dict(meta_file)
        meta["calculation_signature"] = "旧156天公式"
        cache._write_json_dict(meta_file, meta)
        payload, status = cache.get_cached_payload("daily_report_25_26", "2025-11-01")
        self.assertIsNone(payload)
        self.assertTrue(status["stale_settings"])
        self.assertTrue(meta_file.exists())
        self.assertIn("2025-11-01", cache.get_cache_status("daily_report_25_26")["available_dates"])

    def test_delete_rejects_paths_outside_cache_root_before_any_mutation(self):
        self.put("2025-11-01")
        index = cache._load_index("daily_report_25_26")
        index["entries"]["2025-11-02"] = {"dir_name": "../other_data"}
        cache._write_index("daily_report_25_26", index)
        with self.assertRaises(ValueError):
            cache.delete_cache_range("daily_report_25_26", "2025-11-01", "2025-11-02")
        self.assertTrue((self.root / "2025-11-01" / "meta.json").exists())

    def test_temperature_update_skips_old_snapshots_and_late_old_publish(self):
        """写气温前算出的结果即使延迟发布，也不能命中新气温版本。"""
        self.put("2026-11-01")
        old, _ = cache.get_cached_payload("daily_report_25_26", "2026-11-01")
        before = (self.root / "2026-11-01" / "summary.json").read_bytes()
        revision = cache.invalidate_temperature_cache("daily_report_25_26")
        payload, status = cache.get_cached_payload("daily_report_25_26", "2026-11-01")
        self.assertIsNone(payload)
        self.assertTrue(status["stale_temperature"])
        self.assertEqual((self.root / "2026-11-01" / "summary.json").read_bytes(), before)
        cache.update_cache_entry("daily_report_25_26", "2026-11-01", old)
        self.assertIsNone(cache.get_cached_payload("daily_report_25_26", "2026-11-01")[0])
        self.put("2026-11-01", 2)
        payload, _ = cache.get_cached_payload("daily_report_25_26", "2026-11-01")
        self.assertEqual(payload["temperature_revision"], revision)

    def test_cache_rebuild_does_not_reset_temperature_revision(self):
        revision = cache.invalidate_temperature_cache("daily_report_25_26")
        cache.replace_cache("daily_report_25_26", {})
        self.assertEqual(cache.get_temperature_revision("daily_report_25_26"), revision)

    def test_unversioned_snapshot_is_skipped_after_upgrade(self):
        self.put("2026-11-01")
        meta_file = self.root / "2026-11-01" / "meta.json"
        meta = cache._load_json_dict(meta_file)
        meta.pop("temperature_revision")
        cache._write_json_dict(meta_file, meta)
        payload, status = cache.get_cached_payload("daily_report_25_26", "2026-11-01")
        self.assertIsNone(payload)
        self.assertTrue(status["stale_temperature"])

    def test_parallel_publish_captures_temperature_version_before_computation(self):
        from backend.services import dashboard_cache_job as job
        revision = cache.invalidate_temperature_cache("daily_report_25_26")
        with patch.object(job, "load_dashboard_config", return_value={}):
            payload = job._build_base_payload("daily_report_25_26", "2026-11-01")
        cache.invalidate_temperature_cache("daily_report_25_26")
        self.assertEqual(payload["temperature_revision"], revision)


class WeatherCacheRevisionTests(unittest.TestCase):
    def test_successful_commit_invalidates_cache_but_failed_commit_does_not(self):
        """不连接数据库，验证正式气温写入函数的事务与换版顺序。"""
        from datetime import datetime
        from backend.services import weather_importer as weather
        moment = datetime(2026, 11, 1, 12, tzinfo=weather.EAST_8)
        session = MagicMock()
        with patch.object(weather, "_parse_hourly_for_compare", return_value=[1]), patch.object(weather, "_dedupe_by_hour", return_value={moment: 10.0}), patch.object(cache, "invalidate_temperature_cache") as invalidate:
            invalidate.side_effect = lambda *_: self.assertTrue(session.commit.called)
            weather.persist_hourly_temperatures(session, [{}])
            invalidate.assert_called_once_with("daily_report_25_26")
            invalidate.reset_mock()
            session.commit.side_effect = RuntimeError("模拟事务失败")
            with self.assertRaises(RuntimeError):
                weather.persist_hourly_temperatures(session, [{}])
            invalidate.assert_not_called()


class CacheRangeApiTests(unittest.TestCase):
    def test_default_view_reads_cache_using_actual_business_date(self):
        from backend.projects.daily_report_25_26.api import dashboard
        with patch.object(dashboard, "load_default_push_date", return_value="2025-11-01"), patch.object(cache, "get_cached_payload", return_value=({"ok": True, "push_date": "2025-11-01"}, {})) as read:
            result = dashboard.get_dashboard_data("")
        self.assertEqual(read.call_args.args[1], "2025-11-01")
        self.assertTrue(result["cache_hit"])

    def test_running_publish_blocks_delete(self):
        from backend.projects.daily_report_25_26.api import dashboard
        with patch.object(dashboard, "_ensure_cache_operator"), patch.object(dashboard.cache_publish_job_manager, "snapshot", return_value={"status": "running"}), patch.object(cache, "delete_cache_range") as delete:
            with self.assertRaises(HTTPException) as exc:
                dashboard.delete_dashboard_cache_range("2025-11-01", "2026-04-05", MagicMock())
        self.assertEqual(exc.exception.status_code, 409)
        delete.assert_not_called()

    def test_publish_passes_exact_inclusive_range_to_job(self):
        from backend.projects.daily_report_25_26.api import dashboard
        with patch.object(dashboard, "_ensure_cache_operator"), patch.object(dashboard.cache_publish_job_manager, "start", return_value=({"status": "running"}, True)) as start:
            result = dashboard.publish_dashboard_cache(MagicMock(), 7, None, "2026-11-01", "2026-11-02")
        self.assertEqual(start.call_args.args[1], ["2026-11-02", "2026-11-01"])
        self.assertEqual(result["days"], 2)


if __name__ == "__main__":
    unittest.main()
