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
            "enabled": False,
            "model": "gemini-3.5-flash-lite",
            "api_key": "AIzaSyTestApiKey123",
        }

        updated_payload = workspace._save_config_section("ocr_tool_config", data_to_save)

        self.assertIn("ocr_tool_config", updated_payload)
        cfg = updated_payload["ocr_tool_config"]
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["model"], "gemini-3.5-flash-lite")
        self.assertTrue(cfg["api_key"].startswith("enc_v1:"))
        self.assertIn("updated_at", cfg)

        # 校验解密与提示词
        decrypted = config_service.get_configured_ocr_tool_config(updated_payload)
        self.assertFalse(decrypted["enabled"])
        self.assertEqual(decrypted["model"], "gemini-3.5-flash-lite")
        self.assertEqual(decrypted["api_key"], "AIzaSyTestApiKey123")
        self.assertTrue(decrypted["has_custom_key"])
        self.assertFalse(decrypted["enable_fallback"])
        self.assertFalse(decrypted["retry_primary_on_error"])
        self.assertEqual(decrypted["primary_retry_count"], 0)
        self.assertIn("系统已知合法供给方", decrypted["system_prompt"])
        self.assertIn("文字容错纠偏规则", decrypted["system_prompt"])

    def test_supplier_name_levenshtein_1_char_correction(self):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _match_supplier_name
        test_payload = {
            "supply_entities": [
                {"entity_id": "kaiyuan", "entity_name": "大连开元热力管道股份有限公司"},
                {"entity_id": "xinruide", "entity_name": "河北鑫瑞得管道设备有限公司"},
                {"entity_id": "tiandilong", "entity_name": "天津天地龙管业股份有限公司"},
            ]
        }
        # 1. 精确匹配
        _, name, is_corr = _match_supplier_name("大连开元热力管道股份有限公司", test_payload)
        self.assertEqual(name, "大连开元热力管道股份有限公司")
        self.assertFalse(is_corr)

        # 2. 差1个字（鑫瑞德 -> 鑫瑞得）
        _, name_corr1, is_corr1 = _match_supplier_name("河北鑫瑞德管道设备有限公司", test_payload)
        self.assertEqual(name_corr1, "河北鑫瑞得管道设备有限公司")
        self.assertTrue(is_corr1)

        # 3. 差1个字（天津天地隆 -> 天津天地龙）
        _, name_corr2, is_corr2 = _match_supplier_name("天津天地隆管业股份有限公司", test_payload)
        self.assertEqual(name_corr2, "天津天地龙管业股份有限公司")
        self.assertTrue(is_corr2)

    def test_metadata_label_value_deconfusion_cleaning(self):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _build_normalized_ocr_result
        raw_extracted = {
            "document_title": "物资发货单",
            "metadata_fields": [
                {"label": "司机", "value": "姓名 满仓"},
                {"label": "车号", "value": "牌照 辽B88888"},
                {"label": "联系方式", "value": "电话 13912345678"},
            ],
            "table_columns": ["序号", "物资名称", "数量"],
            "table_rows": [{"序号": "1", "物资名称": "直管", "数量": "10"}],
        }
        res = _build_normalized_ocr_result(
            final_extracted=raw_extracted,
            actual_used_model="gemini-3.5-flash-lite",
            primary_norm="gemini-3.5-flash-lite",
            candidate_models=["gemini-3.5-flash-lite"],
            enable_fallback=False,
            retry_primary_on_error=False,
            primary_retry_count=0,
            model_fallback_triggered=False,
        )
        meta = res["extracted_data"]["metadata_fields"]
        meta_dict = {item["label"]: item["value"] for item in meta}
        self.assertEqual(meta_dict.get("司机姓名"), "满仓")
        self.assertEqual(meta_dict.get("车号"), "辽B88888")
        self.assertEqual(meta_dict.get("联系方式"), "13912345678")
        corrections = res["extracted_data"]["verification_report"]["corrections_made"]
        self.assertTrue(any("满仓" in c for c in corrections))

    def test_normalize_phi_symbol_in_ocr_result(self):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _normalize_phi_symbol, _build_normalized_ocr_result
        self.assertEqual(_normalize_phi_symbol("φ1020*10"), "Φ1020*10")
        self.assertEqual(_normalize_phi_symbol("90°φ1100 R=1.5DN"), "90°Φ1100 R=1.5DN")
        self.assertEqual(_normalize_phi_symbol("Ф325*8"), "Φ325*8")
        self.assertEqual(_normalize_phi_symbol("⌀1400/1600"), "Φ1400/1600")

        raw_extracted = {
            "document_title": "物资发货单",
            "metadata_fields": [{"label": "规格", "value": "φ1020*10"}],
            "table_columns": ["序号", "物资名称", "规格型号", "数量"],
            "table_rows": [{"序号": "1", "物资名称": "直管", "规格型号": "φ1400/1600", "数量": "10"}],
        }
        res = _build_normalized_ocr_result(
            final_extracted=raw_extracted,
            actual_used_model="gemini-3.5-flash-lite",
            primary_norm="gemini-3.5-flash-lite",
            candidate_models=["gemini-3.5-flash-lite"],
            enable_fallback=False,
            retry_primary_on_error=False,
            primary_retry_count=0,
            model_fallback_triggered=False,
        )
        self.assertEqual(res["extracted_data"]["metadata_fields"][0]["value"], "Φ1020*10")
        self.assertEqual(res["extracted_data"]["table_rows"][0]["规格型号"], "Φ1400/1600")

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
        self.assertIn("服务器繁忙", cm.exception.detail)

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
            prompt_text="prompt",
            enable_fallback=True,
        )

        self.assertIn("备选模型识别成功", raw_text)
        self.assertEqual(used_model, "gemini-2.5-flash-lite")
        self.assertTrue(fb_triggered)

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service._call_gemini_vision")
    def test_ocr_model_failure_does_not_fallback_when_disabled(self, mock_call):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _call_gemini_vision_with_fallbacks
        from fastapi import HTTPException

        mock_call.side_effect = HTTPException(status_code=403, detail="API Key 无权限")

        with self.assertRaises(HTTPException) as cm:
            _call_gemini_vision_with_fallbacks(
                active_key="test_key",
                candidate_models=["gemini-primary", "gemini-fallback"],
                mime_type="image/jpeg",
                clean_b64="dGVzdA==",
                prompt_text="prompt",
                enable_fallback=False,
            )

        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(mock_call.call_count, 1)

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service._call_gemini_vision")
    def test_ocr_primary_retry_happens_before_fallback(self, mock_call):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import _call_gemini_vision_with_fallbacks
        from fastapi import HTTPException

        mock_call.side_effect = [
            HTTPException(status_code=503, detail="服务器繁忙，请点击重试"),
            ('{"document_title": "主模型重试成功"}', {"totalTokenCount": 100}),
        ]

        raw_text, used_model, fallback_triggered = _call_gemini_vision_with_fallbacks(
            active_key="test_key",
            candidate_models=["gemini-primary", "gemini-fallback"],
            mime_type="image/jpeg",
            clean_b64="dGVzdA==",
            prompt_text="prompt",
            enable_fallback=True,
            retry_primary_on_error=True,
            primary_retry_count=1,
        )

        self.assertIn("主模型重试成功", raw_text)
        self.assertEqual(used_model, "gemini-primary")
        self.assertFalse(fallback_triggered)
        self.assertEqual(mock_call.call_count, 2)

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service.load_tube_config")
    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service._call_gemini_vision")
    def test_extract_delivery_bill_data_complete_structure(self, mock_call, mock_load_cfg):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import extract_delivery_bill_data
        mock_load_cfg.return_value = {
            "ocr_tool_config": {
                "enabled": True,
                "api_key": "enc_v1:dummy",
            }
        }
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

    @patch("backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service.load_tube_config")
    def test_extract_delivery_bill_data_raises_when_no_api_key_in_tube_config(self, mock_load_cfg):
        from backend.projects.insulation_pipe_supply_2026.services.ocr_tool_service import extract_delivery_bill_data
        from fastapi import HTTPException

        mock_load_cfg.return_value = {
            "ocr_tool_config": {
                "enabled": True,
                "api_key": "",
            }
        }

        with self.assertRaises(HTTPException) as ctx:
            extract_delivery_bill_data(
                image_base64="data:image/jpeg;base64,dGVzdA==",
                api_key="",
                model_name="gemini-3.5-flash-lite"
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("tube_config.json", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()

