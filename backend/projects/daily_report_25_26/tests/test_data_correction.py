"""用隔离数据库验证修正完整生命周期；不读写实际业务数据。"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
from uuid import uuid4
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database_daily_report_25_26 import Base, DailyBasicData, CoalInventoryData
from backend.projects.daily_report_25_26.services import data_correction as service
from backend.projects.daily_report_25_26.api.data_correction import CorrectionPayload, router
from backend.services.auth_manager import get_current_session

SHEET = "BeiHai_co_generation_Sheet"
DAY = date(2026, 11, 9)


def actor(username="filler", group="unit_filler", unit="BeiHai", submit=True):
    return SimpleNamespace(username=username, group=group, has_project_access=lambda _: True,
                           get_project_page_access=lambda _: {"data_entry"},
                           get_project_action_flags=lambda _: SimpleNamespace(can_submit=submit),
                           resolve_allowed_units=lambda _: {unit},
                           resolve_project_permissions=lambda _: SimpleNamespace(
                               sheet_rules={"data_entry": SimpleNamespace(mode="by_unit", sheets=set())}))


class DataCorrectionTests(TestCase):
    def setUp(self):
        if os.getenv("PHOENIX_CORRECTION_TEST_POSTGRES") == "1":
            # 所有测试对象位于一个外层事务内的新 schema，结束时回滚，不写业务表。
            from backend.db.database_daily_report_25_26 import DATABASE_URL
            self.engine = create_engine(DATABASE_URL)
            connection = self.engine.connect()
            outer = connection.begin()
            schema = "correction_test_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            target = connection
            self.factory = sessionmaker(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
            self.addCleanup(self.engine.dispose)
            self.addCleanup(connection.close)
            self.addCleanup(outer.rollback)
        else:
            self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
            target = self.engine
            self.factory = sessionmaker(bind=self.engine, autoflush=False)
            self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(target, tables=[DailyBasicData.__table__, CoalInventoryData.__table__,
                                                     service.DataCorrection.__table__, service.CorrectionReservation.__table__])
        if self.engine.dialect.name == "postgresql":
            target.execute(text('CREATE UNIQUE INDEX test_daily_identity ON daily_basic_data(company, sheet_name, item, date)'))
        self.patches = [patch.object(service, "engine", target), patch.object(service, "SessionLocal", self.factory)]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)
        self.user = actor()
        self.admin = actor("global", "Global_admin")
        with self.factory.begin() as db:
            for when in (DAY, DAY.replace(year=2025)):
                db.add(DailyBasicData(company="BeiHai", company_cn="北海热电厂", sheet_name=SHEET,
                                      item="amount_power_generation", item_cn="发电量", unit="万kWh", date=when,
                                      value=Decimal("10"), note="原备注", status="submit", operation_time=datetime(2026, 11, 9)))

    def payload(self, sheet=SHEET, day=DAY, indexes=((0, 2),), user=None, new_value="12"):
        cells = service.snapshot(user or self.user, sheet, day)["cells"]
        changes = []
        for ri, ci in indexes:
            cell = next(c for c in cells if c["row_index"] == ri and c["col_index"] == ci)
            changes.append({k: cell[k] for k in ("row_index", "col_index", "old_value", "version")} | {"new_value": new_value})
        return CorrectionPayload(sheet_key=sheet, biz_date=day, reason="数据核对后申请修正", changes=changes)

    def create(self, **kwargs):
        return service.create_request(self.user, self.payload(**kwargs))

    def value(self, day=DAY):
        with self.factory() as db:
            return db.query(DailyBasicData).filter_by(sheet_name=SHEET, date=day, item="amount_power_generation").one().value

    def test_submit_does_not_write_and_approval_appends_full_audit(self):
        record = self.create(indexes=((0, 2), (0, 3)))
        self.assertEqual(self.value(), Decimal("10"))
        self.assertTrue(next(c for c in service.snapshot(self.user, SHEET, DAY)["cells"] if c["row_index"] == 0 and c["col_index"] == 2)["pending_request_id"])
        resolved = service.resolve_request(self.admin, record["id"], "approve", "核实无误")
        self.assertEqual(resolved["status"], "approved")
        for day in (DAY, DAY.replace(year=2025)):
            self.assertEqual(self.value(day), Decimal("12"))
        with self.factory() as db:
            for row in db.query(DailyBasicData).all():
                for fragment in ("原备注", "申请人：filler", "确认人：global", "10.0000 → 12.0000", "核实无误", "数据核对后申请修正"):
                    self.assertIn(fragment, row.note)
            self.assertEqual(db.query(service.CorrectionReservation).count(), 0)

    def test_reject_and_cancel_keep_original_and_release_cells(self):
        for action, reviewer, expected in (("reject", self.admin, "rejected"), ("cancel", self.user, "cancelled")):
            with self.subTest(action=action):
                request = self.create()
                result = service.resolve_request(reviewer, request["id"], action, "关闭原因")
                self.assertEqual(result["status"], expected)
                self.assertEqual(self.value(), Decimal("10"))
                self.assertTrue(all(not c["pending_request_id"] for c in service.snapshot(self.user, SHEET, DAY)["cells"]))

    def test_only_global_admin_reviews_and_only_author_cancels(self):
        request = self.create()
        for action, reviewer in (("approve", self.user), ("reject", actor(group="Unit_admin")), ("cancel", actor("other"))):
            with self.subTest(action=action), self.assertRaises(HTTPException) as error:
                service.resolve_request(reviewer, request["id"], action, "")
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(self.value(), Decimal("10"))

    def test_stale_snapshot_rejected_at_creation(self):
        payload = self.payload()
        with self.factory.begin() as db:
            db.query(DailyBasicData).filter_by(date=DAY).update({"value": Decimal("11")})
        with self.assertRaises(HTTPException) as error:
            service.create_request(self.user, payload)
        self.assertEqual(error.exception.status_code, 409)

    def test_conflicting_pending_requests_and_peer_alias(self):
        self.create(indexes=((0, 3),))
        with self.assertRaises(HTTPException) as error:
            self.create(day=DAY.replace(year=2025), indexes=((0, 2),))
        self.assertEqual(error.exception.status_code, 409)

    def test_approval_conflict_rolls_back_entire_request(self):
        request = self.create(indexes=((0, 2), (0, 3)))
        with self.factory.begin() as db:
            db.query(DailyBasicData).filter_by(date=DAY).update({"operation_time": datetime(2026, 11, 9, 12)})
        with self.assertRaises(HTTPException) as error:
            service.resolve_request(self.admin, request["id"], "approve", "")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(self.value(DAY.replace(year=2025)), Decimal("10"))
        with self.factory() as db:
            self.assertEqual(db.get(service.DataCorrection, request["id"]).status, "pending")
            self.assertEqual(db.query(service.CorrectionReservation).count(), 2)

    def test_closed_request_cannot_resolve_twice(self):
        request = self.create()
        service.resolve_request(self.admin, request["id"], "approve", "")
        with self.assertRaises(HTTPException) as error:
            service.resolve_request(self.admin, request["id"], "approve", "")
        self.assertEqual(error.exception.status_code, 409)

    def test_scope_viewer_and_record_visibility(self):
        request = self.create()
        for viewer in (actor(unit="GongRe"), actor(submit=False)):
            with self.assertRaises(HTTPException) as error:
                service.create_request(viewer, self.payload())
            self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(service.list_requests(actor(unit="GongRe"))["total"], 0)
        self.assertEqual(service.list_requests(self.admin)["total"], 1)
        self.assertEqual(service.list_requests(self.user)["records"][0]["id"], request["id"])

    def test_center_and_coal_identities_and_approvals(self):
        for sheet, indexes, unit, model in (("GongRe_branches_detail_Sheet", ((0, 3),), "GongRe", DailyBasicData),
                                            ("Coal_inventory_Sheet", ((0, 3),), "ShouDian", CoalInventoryData)):
            user = actor(unit=unit)
            payload = self.payload(sheet=sheet, indexes=indexes, user=user)
            record = service.create_request(user, payload)
            service.resolve_request(self.admin, record["id"], "approve", "")
            cell = record["changes"][0]
            self.assertNotEqual(cell["identity"]["company"], "GongRe")
            if model is CoalInventoryData:
                self.assertEqual(cell["identity"]["coal_type"], "bituminous_coal")
            with self.factory() as db:
                self.assertEqual(service.cell_query(db, cell).one().value, Decimal("12"))

    def test_leap_day_null_zero_and_invalid_values(self):
        cells = service.snapshot(self.user, SHEET, date(2024, 2, 29))["cells"]
        self.assertEqual(next(c for c in cells if c["col_index"] == 3)["date"], "2023-02-28")
        for raw in ("NaN", "Infinity", "0.12345", "abc", "1e1000"):
            with self.subTest(raw=raw), self.assertRaises(HTTPException):
                service.number(raw)
        self.assertEqual(service.number(0), "0.0000")
        request = self.create(new_value="")
        service.resolve_request(self.admin, request["id"], "approve", "清空错误值")
        self.assertIsNone(self.value())

    def test_api_lifecycle_and_validation(self):
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides[get_current_session] = lambda: self.user
        client = TestClient(app)
        response = client.get(f"/data-corrections/snapshot?sheet_key={SHEET}&biz_date={DAY}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ordinary_readonly", response.json())
        payload = self.payload().model_dump(mode="json")
        response = client.post("/data-corrections", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        request_id = response.json()["id"]
        denied = client.post(f"/data-corrections/{request_id}/resolve", json={"action": "approve"})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(client.get("/data-corrections?status=pending").json()["total"], 1)
        self.assertEqual(client.post("/data-corrections", json=dict(payload, reason=" ")).status_code, 422)
        self.assertEqual(client.post(f"/data-corrections/{request_id}/resolve", json={"action": "cancel"}).json()["status"], "cancelled")

    def test_regular_resubmission_preserves_correction_audit(self):
        if self.engine.dialect.name != "postgresql":
            self.skipTest("PostgreSQL 专用 UPSERT 由隔离 schema 测试验证")
        from backend.projects.daily_report_25_26.api import legacy_full as legacy
        request = self.create()
        service.resolve_request(self.admin, request["id"], "approve", "确认")
        cell = request["changes"][0]
        flattened = [dict(cell["identity"], date=cell["date"], value="12", note="后续填报说明")]
        with patch.object(legacy, "SessionLocal", self.factory):
            legacy._persist_daily_basic({}, {}, flattened)
            legacy._persist_daily_basic({}, {}, flattened)
        with self.factory() as db:
            note = service.cell_query(db, cell).one().note
            self.assertIn("后续填报说明", note)
            self.assertEqual(note.count("【数据修正申请 #"), 1)

    def test_noop_forged_duplicate_and_whitespace_requests_rejected(self):
        payload = self.payload(new_value="10.0000")
        with self.assertRaises(HTTPException):
            service.create_request(self.user, payload)
        payload = self.payload()
        payload.changes[0].col_index = 0
        with self.assertRaises(HTTPException):
            service.create_request(self.user, payload)
        payload = self.payload()
        payload.changes.append(payload.changes[0])
        with self.assertRaises(HTTPException):
            service.create_request(self.user, payload)

    def test_coal_regular_resubmission_preserves_audit(self):
        from backend.projects.daily_report_25_26.api import legacy_full as legacy
        user = actor(unit="ShouDian")
        request = service.create_request(user, self.payload(sheet="Coal_inventory_Sheet", indexes=((0, 3),), user=user))
        service.resolve_request(self.admin, request["id"], "approve", "确认")
        cell = request["changes"][0]
        data = [dict(cell["identity"], date=cell["date"], value="12", note="后续库存说明")]
        with patch.object(legacy, "SessionLocal", self.factory):
            legacy._persist_coal_inventory(data)
        with self.factory() as db:
            note = service.cell_query(db, cell).one().note
            self.assertIn("后续库存说明", note)
            self.assertIn("【数据修正申请 #", note)

    def test_permission_guards_missing_records_and_status_filter(self):
        outsider = actor()
        outsider.has_project_access = lambda _: False
        with self.assertRaises(HTTPException):
            service.list_requests(outsider)
        outsider = actor()
        outsider.get_project_page_access = lambda _: set()
        with self.assertRaises(HTTPException):
            service.list_requests(outsider)
        for action in ("invalid", "approve"):
            with self.assertRaises(HTTPException):
                service.resolve_request(self.admin, 9999, action, "")
        with self.assertRaises(HTTPException):
            service.snapshot(self.user, "not-a-sheet", DAY)
        request = self.create()
        self.assertEqual(service.list_requests(self.user, "pending", 0, 1)["total"], 1)
        self.assertEqual(service.list_requests(self.user, "approved")["total"], 0)
        note = "原说明\n【数据修正申请 #1】流水"
        self.assertEqual(service.preserve_audit_note(note, None), "【数据修正申请 #1】流水")
        self.assertEqual(service.preserve_audit_note(note, note), note)
        service.resolve_request(self.user, request["id"], "cancel", "")

    def test_all_basic_templates_supply_unique_canonical_cells(self):
        from backend.projects.daily_report_25_26.api import legacy_full as legacy
        templates = legacy._read_json(legacy.BASIC_TEMPLATE_PATH)
        for sheet in templates:
            if sheet.startswith("__"):
                continue
            with self.subTest(sheet=sheet):
                cells = service.snapshot(self.admin, sheet, DAY)["cells"]
                self.assertTrue(cells)
                self.assertEqual(len(cells), len({c["cell_key"] for c in cells}))

    def regular_payload(self, sheet=SHEET):
        from backend.projects.daily_report_25_26.api import legacy_full as legacy
        template, _, _ = legacy._locate_sheet_payload(sheet, preferred_path=legacy.BASIC_TEMPLATE_PATH)
        rows = [list(r) for r in legacy._extract_list(template, legacy.ROW_KEYS)]
        for cell in service.snapshot(self.admin, sheet, DAY)["cells"]:
            rows[cell["row_index"]][cell["col_index"]] = cell["old_value"] or ""
        return {"biz_date": DAY.isoformat(), "rows": rows, "columns": ["伪造列头"], "unit_id": "Other", "item_dict": {"wrong": "发电量"}}

    def test_ordinary_submission_enforces_date_approval_peer_and_trusted_identity(self):
        from backend.services.auth_manager import auth_manager
        from backend.services.workflow_status import workflow_status_manager
        with patch.object(auth_manager, "current_biz_date", return_value=DAY), patch.object(workflow_status_manager, "is_unit_approved", return_value=False) as approved:
            payload = self.regular_payload()
            trusted = service.validate_regular_submission(self.user, SHEET, payload)
            self.assertEqual(trusted["unit_id"], "BeiHai")
            self.assertEqual(trusted["columns"][2:4], [DAY.isoformat(), "2025-11-09"])
            self.assertEqual(trusted["item_dict"]["amount_power_generation"], "发电量")
            self.assertNotIn("wrong", trusted["item_dict"])
            payload["rows"][0][3] = "99"
            with self.assertRaises(HTTPException) as error:
                service.validate_regular_submission(self.user, SHEET, payload)
            self.assertEqual(error.exception.status_code, 403)
            payload = self.regular_payload()
            payload["biz_date"] = "2025-11-09"
            with self.assertRaises(HTTPException) as error:
                service.validate_regular_submission(self.user, SHEET, payload)
            self.assertEqual(error.exception.status_code, 403)
            approved.return_value = True
            with self.assertRaises(HTTPException) as error:
                service.validate_regular_submission(self.user, SHEET, self.regular_payload())
            self.assertEqual(error.exception.status_code, 403)
            # 修正申请不受普通填报的日期或审批锁定影响。
            self.assertEqual(self.create()["status"], "pending")
        self.assertIs(service.validate_regular_submission(self.admin, SHEET, payload), payload)

    def test_ordinary_submission_rejects_malformed_rows_and_preserves_other_pages(self):
        from backend.services.auth_manager import auth_manager
        from backend.services.workflow_status import workflow_status_manager
        with patch.object(auth_manager, "current_biz_date", return_value=DAY), patch.object(workflow_status_manager, "is_unit_approved", return_value=False):
            for mutate in (lambda p: p.update(biz_date="bad"), lambda p: p.update(rows=[]),
                           lambda p: p["rows"][0].__setitem__(0, "其他指标")):
                payload = self.regular_payload(); mutate(payload)
                with self.assertRaises(HTTPException) as error:
                    service.validate_regular_submission(self.user, SHEET, payload)
                self.assertEqual(error.exception.status_code, 422)
            payload = self.regular_payload("GongRe_branches_detail_Sheet")
            trusted = service.validate_regular_submission(actor(unit="GongRe"), "GongRe_branches_detail_Sheet", payload)
            self.assertEqual(trusted["columns"][3:5], [DAY.isoformat(), "2025-11-09"])
            payload = self.regular_payload("Coal_inventory_Sheet")
            trusted = service.validate_regular_submission(actor(unit="ShouDian"), "Coal_inventory_Sheet", payload)
            self.assertEqual(trusted["unit_id"], "ShouDian")
            payload = {"rows": []}
            self.assertIs(service.validate_regular_submission(self.user, "not-basic-sheet", payload), payload)

    def test_workflow_approval_lookup_is_readonly(self):
        from threading import RLock
        from backend.services.auth_manager import EAST_8
        from backend.services.workflow_status import WorkflowSnapshot, WorkflowStatusManager, UnitApprovalState
        manager = WorkflowStatusManager.__new__(WorkflowStatusManager)
        manager._lock = RLock()
        manager._storage = {}
        manager._ensure_loaded_locked = lambda: None
        day = datetime.combine(DAY, datetime.min.time()).replace(tzinfo=EAST_8)
        self.assertFalse(manager.is_unit_approved(service.PROJECT, day, "BeiHai"))
        self.assertEqual(manager._storage, {})
        manager._storage[(service.PROJECT, day)] = WorkflowSnapshot(units={"BeiHai": UnitApprovalState(unit="BeiHai", status="approved")})
        self.assertTrue(manager.is_unit_approved(service.PROJECT, day, "BeiHai"))
        self.assertFalse(manager.is_unit_approved(service.PROJECT, day, "GongRe"))
