# -*- coding: utf-8 -*-
from datetime import date, datetime
import unittest
from unittest.mock import patch

from backend.projects.insulation_pipe_supply_2026.services import config_service


class ConfigServiceDateAutomationTest(unittest.TestCase):
    def test_business_date_switches_at_beijing_0630(self):
        before_switch = datetime(2026, 8, 10, 6, 29, 59, tzinfo=config_service.BEIJING_TZ)
        at_switch = datetime(2026, 8, 10, 6, 30, 0, tzinfo=config_service.BEIJING_TZ)

        self.assertEqual(config_service._get_beijing_business_date(before_switch), date(2026, 8, 9))
        self.assertEqual(config_service._get_beijing_business_date(at_switch), date(2026, 8, 10))

    @patch.object(config_service, "_get_beijing_business_date", return_value=date(2026, 8, 10))
    def test_yes_keeps_show_date_manual(self, _mock_business_date):
        payload = {
            "show_date": "2026-08-08",
            "usage_collection_date": "2026-08-08",
            "plan_start_date": "2026-08-09",
            "auto_update_plan_start_date": True,
        }

        self.assertEqual(config_service.get_configured_show_date(payload), date(2026, 8, 8))
        self.assertEqual(config_service.get_usage_collection_date(payload), date(2026, 8, 9))
        self.assertEqual(config_service.get_configured_plan_start_date(payload), date(2026, 8, 10))

    @patch.object(config_service, "_get_beijing_business_date", return_value=date(2026, 8, 10))
    def test_all_updates_show_and_usage_to_previous_business_day(self, _mock_business_date):
        payload = {
            "show_date": "2026-08-08",
            "usage_collection_date": "2026-08-08",
            "plan_start_date": "2026-08-09",
            "auto_update_plan_start_date": "all",
        }

        self.assertEqual(config_service.get_configured_show_date(payload), date(2026, 8, 9))
        self.assertEqual(config_service.get_usage_collection_date(payload), date(2026, 8, 9))
        self.assertEqual(config_service.get_configured_plan_start_date(payload), date(2026, 8, 10))

    @patch.object(config_service, "_get_beijing_business_date", return_value=date(2026, 8, 10))
    def test_no_keeps_all_dates_manual(self, _mock_business_date):
        payload = {
            "show_date": "2026-08-08",
            "usage_collection_date": "2026-08-08",
            "plan_start_date": "2026-08-09",
            "auto_update_plan_start_date": False,
        }

        self.assertEqual(config_service.get_configured_show_date(payload), date(2026, 8, 8))
        self.assertEqual(config_service.get_usage_collection_date(payload), date(2026, 8, 8))
        self.assertEqual(config_service.get_configured_plan_start_date(payload), date(2026, 8, 9))


if __name__ == "__main__":
    unittest.main()
