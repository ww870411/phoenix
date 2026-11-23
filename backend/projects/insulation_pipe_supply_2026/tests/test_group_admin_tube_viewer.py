# -*- coding: utf-8 -*-
"""验证 group_admin 兼职 tube_global_viewer 多用户组在项目中的只读同权访问与既有日报权限隔离。"""
from datetime import date, datetime
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.api.v1 import routes as v1_routes
from backend.projects.insulation_pipe_supply_2026.api import workspace
from backend.projects.insulation_pipe_supply_2026.services import config_service
from backend.services.auth_manager import auth_manager, get_session_groups


PROJECT_TUBE = "insulation_pipe_supply_2026"
PROJECT_DAILY = "daily_report_25_26"


def _build_real_session(username: str):
    auth_manager._ensure_loaded()
    record = auth_manager._users_by_name[username]
    return auth_manager._build_session(
        record=record,
        group_permissions=auth_manager._groups[record.group],
        token=f"unit-test-{username}",
        issued_at=auth_manager._now(),
        expires_at=None,
        persistent=False,
    )


class GroupAdminTubeViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.group_admin_session = _build_real_session("group_admin")
        cls.tube_viewer_session = _build_real_session("tube_viewer")
        cls.tube_config = config_service.load_tube_config()

    def test_account_keeps_primary_group_and_inherits_tube_viewer_permissions(self):
        self.assertEqual(self.group_admin_session.group, "Group_admin")
        self.assertEqual(get_session_groups(self.group_admin_session), ["Group_admin", "tube_global_viewer"])
        self.assertTrue(self.group_admin_session.has_project_access(PROJECT_TUBE))
        self.assertTrue(self.group_admin_session.has_project_access(PROJECT_DAILY))

        # insulation_pipe_supply_2026 权限应与 tube_viewer 完全一致
        self.assertEqual(
            self.group_admin_session.get_project_page_access(PROJECT_TUBE),
            self.tube_viewer_session.get_project_page_access(PROJECT_TUBE),
        )
        self.assertEqual(
            self.group_admin_session.get_project_action_flags(PROJECT_TUBE),
            self.tube_viewer_session.get_project_action_flags(PROJECT_TUBE),
        )
        self.assertFalse(self.group_admin_session.get_project_action_flags(PROJECT_TUBE).can_submit)
        self.assertFalse(self.group_admin_session.get_project_action_flags(PROJECT_TUBE).can_extract_xlsx)

        # daily_report_25_26 已取消 Group_admin 的提交权限，但审批/撤销/发布权限仍保留
        daily_flags = self.group_admin_session.get_project_action_flags(PROJECT_DAILY)
        self.assertFalse(daily_flags.can_submit)
        self.assertTrue(daily_flags.can_approve)
        self.assertTrue(daily_flags.can_revoke)
        self.assertTrue(daily_flags.can_publish)

    def test_project_and_page_visibility_match_tube_viewer(self):
        projects_res = v1_routes.list_projects(session=self.group_admin_session)
        project_ids = {item["project_id"] for item in projects_res["projects"]}
        self.assertIn(PROJECT_TUBE, project_ids)
        self.assertIn(PROJECT_DAILY, project_ids)

        ga_pages = [p["page_key"] for p in v1_routes.list_project_pages(PROJECT_TUBE, session=self.group_admin_session)["pages"]]
        tv_pages = [p["page_key"] for p in v1_routes.list_project_pages(PROJECT_TUBE, session=self.tube_viewer_session)["pages"]]
        self.assertEqual(ga_pages, tv_pages)
        self.assertIn("comprehensive_query", ga_pages)
        self.assertIn("supply_management", ga_pages)
        self.assertNotIn("global_management", ga_pages)

    def test_config_service_scopes_match_tube_viewer(self):
        ga_sections = config_service.resolve_accessible_section_1_ids(
            self.tube_config, self.group_admin_session.username, get_session_groups(self.group_admin_session)
        )
        tv_sections = config_service.resolve_accessible_section_1_ids(
            self.tube_config, self.tube_viewer_session.username, get_session_groups(self.tube_viewer_session)
        )
        self.assertTrue(len(ga_sections) > 0)
        self.assertEqual(ga_sections, tv_sections)

        ga_suppliers = config_service.resolve_accessible_supply_entity_ids(
            self.tube_config, self.group_admin_session.username, get_session_groups(self.group_admin_session)
        )
        tv_suppliers = config_service.resolve_accessible_supply_entity_ids(
            self.tube_config, self.tube_viewer_session.username, get_session_groups(self.tube_viewer_session)
        )
        self.assertTrue(len(ga_suppliers) > 0)
        self.assertEqual(ga_suppliers, tv_suppliers)

        # 单字符串旧调用方式向后兼容
        self.assertEqual(
            config_service.resolve_accessible_section_1_ids(self.tube_config, "anyone", "tube_global_viewer"),
            tv_sections,
        )

    def test_options_and_read_endpoints_match_tube_viewer(self):
        ga_demand_opts = workspace.get_demand_management_options(session=self.group_admin_session)
        tv_demand_opts = workspace.get_demand_management_options(session=self.tube_viewer_session)
        self.assertEqual(ga_demand_opts["section_1s"], tv_demand_opts["section_1s"])
        self.assertEqual(ga_demand_opts["user"]["group"], "Group_admin")
        self.assertEqual(ga_demand_opts["user"]["groups"], ["Group_admin", "tube_global_viewer"])

        ga_supply_opts = workspace.get_supply_management_options(session=self.group_admin_session)
        tv_supply_opts = workspace.get_supply_management_options(session=self.tube_viewer_session)
        self.assertEqual(ga_supply_opts["supply_entities"], tv_supply_opts["supply_entities"])
        self.assertEqual(ga_supply_opts["current_supply_entity_ids"], tv_supply_opts["current_supply_entity_ids"])

        ga_wh_opts = workspace.get_warehouse_management_options(session=self.group_admin_session)
        tv_wh_opts = workspace.get_warehouse_management_options(session=self.tube_viewer_session)
        self.assertEqual(ga_wh_opts["section_1s"], tv_wh_opts["section_1s"])

        with patch.object(workspace, "query_history_records", return_value=[]):
            ga_hist = workspace.get_global_management_history(
                start_date="2026-11-01",
                end_date="2026-11-02",
                section_1_id=None,
                session=self.group_admin_session,
            )
            self.assertTrue(ga_hist["ok"])

        with patch.object(workspace, "list_fitting_deliveries", return_value={"items": [], "total": 0}) as mock_list:
            workspace.handle_list_fitting_deliveries(
                section_1_id="",
                supply_entity_id="",
                status="",
                exclude_cancelled=True,
                start_date="",
                end_date="",
                search_keyword="",
                page=1,
                limit=50,
                public_view=False,
                session=self.group_admin_session,
            )
            self.assertIsNone(mock_list.call_args.kwargs["allowed_section_ids"])
            self.assertIsNone(mock_list.call_args.kwargs["allowed_supply_ids"])

        with patch.object(workspace, "save_operation_log"), patch.object(
            workspace, "query_supplier_inventory_history", return_value={"items": []}
        ) as mock_inv:
            workspace.handle_comprehensive_supplier_inventory(
                request=None,
                material_kind="pipe",
                view_mode="latest",
                start_date=None,
                end_date=None,
                supplier_ids="sup_a",
                pipe_model_ids=None,
                fitting_types=None,
                keyword=None,
                session=self.group_admin_session,
            )
            self.assertEqual(mock_inv.call_args.kwargs["supplier_ids"], ["sup_a"])

    def test_write_and_export_endpoints_blocked_for_group_admin_and_tube_viewer(self):
        sample_supplier_id = next(
            iter(config_service.resolve_accessible_supply_entity_ids(self.tube_config, "tube_viewer", "tube_global_viewer"))
        )
        sample_section_id = next(
            iter(config_service.resolve_accessible_section_1_ids(self.tube_config, "tube_viewer", "tube_global_viewer"))
        )

        for sess in (self.group_admin_session, self.tube_viewer_session):
            with self.subTest(username=sess.username):
                with self.assertRaises(HTTPException) as ctx1:
                    workspace.export_global_management_history(
                        start_date="2026-11-01", end_date="2026-11-02", section_1_id=None, session=sess
                    )
                self.assertEqual(ctx1.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx2:
                    workspace.create_supply_management_delivery(
                        payload=workspace.SupplyDeliveryCreatePayload(
                            supply_entity_id=sample_supplier_id,
                            section_1_id=sample_section_id,
                            pipe_model_id="DN100",
                            shipped_qty=10,
                            shipped_at=datetime(2026, 11, 20, 10, 0, 0),
                            vehicle_plate_no="辽A12345",
                        ),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx2.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx3:
                    workspace.confirm_warehouse_delivery_warehouse(
                        delivery_id=1,
                        payload=workspace.WarehouseConfirmPayload(remark="test"),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx3.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx4:
                    workspace.save_demand_management_plan_matrix(
                        payload=workspace.DemandPlanSavePayload(section_1_id=sample_section_id, records=[]),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx4.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx5:
                    workspace.save_demand_management_usage_sheet(
                        payload=workspace.DemandUsageSavePayload(
                            section_1_id=sample_section_id, usage_date=date(2026, 11, 20), records=[]
                        ),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx5.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx6:
                    workspace.submit_demand_management_section_1_status(
                        payload=workspace.DemandSection1SubmissionPayload(section_1_id=sample_section_id, remark="test"),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx6.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx7:
                    workspace.save_supplier_inventory_endpoint(
                        payload=workspace.SupplierInventorySavePayload(
                            supply_entity_id=sample_supplier_id, report_date="2026-11-20", items=[]
                        ),
                        request=None,
                        session=sess,
                    )
                self.assertEqual(ctx7.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx8:
                    workspace.save_supply_entity_contact_endpoint(
                        payload=workspace.SupplyContactSavePayload(
                            supply_entity_id=sample_supplier_id, contact_name="测试", contact_phone=""
                        ),
                        session=sess,
                    )
                self.assertEqual(ctx8.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx9:
                    workspace._ensure_fitting_role(sess, {"global_admin", "tube_supplier"}, "管件发货")
                self.assertEqual(ctx9.exception.status_code, 403)

                with self.assertRaises(HTTPException) as ctx10:
                    workspace._ensure_global_admin(sess)
                self.assertEqual(ctx10.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
