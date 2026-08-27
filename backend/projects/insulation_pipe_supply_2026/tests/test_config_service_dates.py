# -*- coding: utf-8 -*-
from datetime import date, datetime
import unittest
from unittest.mock import MagicMock, patch

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


class GovernanceOverviewEndpointTest(unittest.TestCase):
    @patch("backend.projects.insulation_pipe_supply_2026.api.workspace.SessionLocal")
    @patch("backend.projects.insulation_pipe_supply_2026.api.workspace.load_tube_config")
    def test_governance_overview_executes_successfully(self, mock_load_config, mock_session_local):
        from backend.projects.insulation_pipe_supply_2026.api import workspace
        mock_load_config.return_value = {
            "demand_entities": [
                {
                    "section_1_id": "sec_01",
                    "section_1_name": "标段一",
                    "section_2_name": "辖区A",
                    "sort_order": 1,
                }
            ],
            "construction_units": [
                {
                    "unit_name": "施工单位甲",
                    "section_1_ids": ["sec_01"],
                    "contact_name": "张工",
                    "contact_phone": "13800000000",
                }
            ],
            "manager_assignments": [],
        }

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.execute.return_value.mappings.return_value.all.return_value = []

        mock_user_session = MagicMock()
        mock_user_session.username = "admin"
        mock_user_session.group = "global_admin"

        res = workspace.get_demand_management_governance_overview(session=mock_user_session)

        self.assertTrue(res.get("ok"))
        self.assertIn("dates", res)
        self.assertIn("summary", res)
        self.assertIn("sections", res)
        self.assertEqual(len(res["sections"]), 1)
        sec = res["sections"][0]
        self.assertEqual(sec["section_1_id"], "sec_01")
        self.assertEqual(sec["construction_unit_name"], "施工单位甲")


if __name__ == "__main__":
    unittest.main()
