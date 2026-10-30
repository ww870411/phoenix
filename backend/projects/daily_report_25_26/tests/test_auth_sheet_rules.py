"""验证真实账号的项目表单范围及兼职规则合并，不登录、不连接业务数据库。"""
import unittest
from backend.services.auth_manager import AuthManager, SheetRule, auth_manager


PROJECT = "daily_report_25_26"


class AuthSheetRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        auth_manager._ensure_loaded()

    def test_each_single_role_preserves_its_project_rules(self):
        """覆盖现有单角色账号的各项目规则，保持动作授权不变。"""
        for record in auth_manager._users_by_name.values():
            if len(record.groups) != 1:
                continue
            configured = auth_manager._groups[record.groups[0]]
            effective = auth_manager._build_merged_permissions(record)
            for project_key, permissions in configured.projects.items():
                with self.subTest(username=record.username, project=project_key):
                    self.assertEqual(effective.projects[project_key].sheet_rules, permissions.sheet_rules)
                    self.assertEqual(effective.projects[project_key].actions, permissions.actions)

    def test_beihai_session_serializes_by_unit_rule_and_keeps_submit_enabled(self):
        record = auth_manager._users_by_name["beihai_filler"]
        session = auth_manager._build_session(
            record=record, group_permissions=auth_manager._groups[record.group],
            token="unit-test-not-persisted", issued_at=auth_manager._now(),
            expires_at=None, persistent=False,
        )
        project = session.to_permissions_payload()["projects"][PROJECT]
        self.assertEqual(project["sheet_rules"]["data_entry"], {"mode": "by_unit"})
        self.assertEqual(project["sheet_rules"]["data_show"], {"mode": "all"})
        self.assertEqual(session.resolve_allowed_units(PROJECT), {"BeiHai"})
        self.assertTrue(session.get_project_action_flags(PROJECT).can_submit)

    def test_all_unit_fillers_and_admins_keep_by_unit_entry(self):
        for record in auth_manager._users_by_name.values():
            if record.group not in {"unit_filler", "Unit_admin", "shoudian_filler"}:
                continue
            with self.subTest(username=record.username):
                permissions = auth_manager._build_merged_permissions(record).projects[PROJECT]
                self.assertEqual(permissions.sheet_rules["data_entry"].mode, "by_unit")

    def test_explicit_rules_union_independent_of_role_order(self):
        maps = [{"data_entry": SheetRule("explicit", {"A"})}, {"data_entry": SheetRule("explicit", {"B"})}]
        expected = {"data_entry": SheetRule("explicit", {"A", "B"})}
        self.assertEqual(AuthManager._merge_sheet_rule_maps(maps), expected)
        self.assertEqual(AuthManager._merge_sheet_rule_maps(reversed(maps)), expected)

    def test_by_unit_keeps_explicit_extra_sheets(self):
        maps = [{"data_entry": SheetRule("by_unit", {"Coal_inventory_Sheet"})}, {"data_entry": SheetRule("explicit", {"Extra_Sheet"})}]
        self.assertEqual(AuthManager._merge_sheet_rule_maps(maps)["data_entry"], SheetRule("by_unit", {"Coal_inventory_Sheet", "Extra_Sheet"}))

    def test_all_role_grants_all_but_view_only_role_does_not_expand_entry(self):
        unit = {"data_entry": SheetRule("by_unit")}
        viewer = {"data_show": SheetRule("all")}
        result = AuthManager._merge_sheet_rule_maps([unit, viewer])
        self.assertEqual(result["data_entry"].mode, "by_unit")
        self.assertEqual(AuthManager._merge_sheet_rule_maps([unit, {"data_entry": SheetRule("all")}])["data_entry"].mode, "all")


if __name__ == "__main__":
    unittest.main()
