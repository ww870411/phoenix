# -*- coding: utf-8 -*-
from datetime import date, datetime
import json
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


class OcrToolConfigSaveTest(unittest.TestCase):
    @patch("backend.projects.insulation_pipe_supply_2026.api.workspace.save_tube_config")
    @patch("backend.projects.insulation_pipe_supply_2026.api.workspace.load_tube_config")
    def test_save_ocr_tool_config_encrypts_and_updates(self, mock_load_config, mock_save_config):
        from backend.projects.insulation_pipe_supply_2026.api import workspace

        mock_load_config.return_value = {
            "ocr_tool_config": {
                "model": "gemini-1.5-flash",
                "api_key": "",
            }
        }

        data_to_save = {
            "model": "gemini-3.5-flash-lite",
            "api_key": "AIzaSyTestApiKey123",
        }

        updated_payload = workspace._save_config_section("ocr_tool_config", data_to_save)

        self.assertIn("ocr_tool_config", updated_payload)
        cfg = updated_payload["ocr_tool_config"]
        self.assertEqual(cfg["model"], "gemini-3.5-flash-lite")
        self.assertTrue(cfg["api_key"].startswith("enc_v1:"))
        self.assertIn("updated_at", cfg)

        # 校验解密
        decrypted = config_service.get_configured_ocr_tool_config(updated_payload)
        self.assertEqual(decrypted["model"], "gemini-3.5-flash-lite")
        self.assertEqual(decrypted["api_key"], "AIzaSyTestApiKey123")
        self.assertTrue(decrypted["has_custom_key"])

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service.extract_delivery_bill_data")
    @patch("backend.projects.insulation_pipe_supply_2026.api.workspace.save_operation_log")
    def test_handle_ocr_delivery_bill_logs_operation(self, mock_save_log, mock_extract):
        from unittest.mock import MagicMock
        from backend.projects.insulation_pipe_supply_2026.api.workspace import handle_ocr_delivery_bill, OcrDeliveryBillPayload
        from backend.api.v1.auth import AuthSession
        from backend.projects.insulation_pipe_supply_2026.services.audit_log_service import QUERY_SUBMISSION_ACTIONS

        self.assertIn("OCR_DELIVERY_BILL", QUERY_SUBMISSION_ACTIONS)

        mock_extract.return_value = {
            "document_title": "测试物资入库单",
            "metadata_fields": [{"label": "单号", "value": "RK-001"}],
            "table_columns": ["序号", "品名", "数量"],
            "table_rows": [{"序号": "1", "品名": "弯头", "数量": "10"}],
            "verification_report": {
                "status": "verified",
                "confidence_score": 99.5,
                "corrections_count": 0,
            }
        }

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}
        session = MagicMock()
        session.username = "test_admin"
        session.group = "Global_admin"
        payload = OcrDeliveryBillPayload(image_base64="data:image/jpeg;base64,dGVzdA==")

        res = handle_ocr_delivery_bill(request=mock_request, payload=payload, session=session)
        self.assertEqual(res["document_title"], "测试物资入库单")

        mock_save_log.assert_called_once()
        call_kwargs = mock_save_log.call_args[1]
        self.assertEqual(call_kwargs["operator"], "test_admin")
        self.assertEqual(call_kwargs["operator_group"], "Global_admin")
        self.assertEqual(call_kwargs["action_type"], "OCR_DELIVERY_BILL")
        self.assertIn("测试物资入库单", call_kwargs["action_desc"])
        self.assertEqual(call_kwargs["after_value"]["document_title"], "测试物资入库单")

    @patch("httpx.post")
    def test_call_gemini_vision_503_simplified_error(self, mock_post):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _call_gemini_vision
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later."
        mock_resp.json.return_value = {
            "error": {
                "message": "This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later."
            }
        }
        mock_post.return_value = mock_resp

        with self.assertRaises(HTTPException) as cm:
            _call_gemini_vision(
                url="https://example.com/api",
                mime_type="image/jpeg",
                clean_b64="dGVzdA==",
                prompt_text="test"
            )

        self.assertEqual(cm.exception.status_code, 503)
        self.assertEqual(cm.exception.detail, "服务器繁忙，请点击重试")

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service._call_gemini_vision")
    def test_call_gemini_vision_with_fallbacks_recovers(self, mock_call):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _call_gemini_vision_with_fallbacks
        from fastapi import HTTPException

        # 模拟主模型 503 繁忙，备选模型 1 成功返回
        def side_effect(url, **kwargs):
            if "gemini-3.5-flash-lite" in url:
                raise HTTPException(status_code=503, detail="服务器繁忙，请点击重试")
            return '{"document_title": "备选模型识别成功"}', {"totalTokenCount": 100}

        mock_call.side_effect = side_effect

        raw_text, used_model, fb_triggered = _call_gemini_vision_with_fallbacks(
            active_key="test_key",
            candidate_models=["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"],
            mime_type="image/jpeg",
            clean_b64="dGVzdA==",
            prompt_text="prompt"
        )

        self.assertIn("备选模型识别成功", raw_text)
        self.assertEqual(used_model, "gemini-2.5-flash-lite")
        self.assertTrue(fb_triggered)

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service._call_gemini_vision")
    def test_extract_delivery_bill_data_complete_structure(self, mock_call):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import extract_delivery_bill_data
        mock_call.return_value = (
            json.dumps({
                "document_title": "测试发货单",
                "metadata_fields": [{"label": "单据编号", "value": "FH-20260901"}],
                "table_columns": ["序号", "物资规格", "数量"],
                "table_rows": [{"序号": "1", "物资规格": "DN300", "数量": "20"}],
                "remarks": "合格"
            }),
            {"totalTokenCount": 150}
        )

        res = extract_delivery_bill_data(
            image_base64="data:image/jpeg;base64,dGVzdA==",
            api_key="AIzaSyDummyKey",
            model_name="gemini-3.5-flash-lite",
            enable_double_check=False
        )

        self.assertTrue(res["ok"])
        self.assertEqual(res["primary_model"], "gemini-3.5-flash-lite")
        self.assertEqual(res["model_used"], "gemini-3.5-flash-lite")
        self.assertIn("extracted_data", res)
        self.assertIn("api_logs", res)
        self.assertEqual(len(res["api_logs"]), 1)
        self.assertEqual(res["extracted_data"]["document_title"], "测试发货单")
        self.assertEqual(len(res["extracted_data"]["table_rows"]), 1)


if __name__ == "__main__":
    unittest.main()



