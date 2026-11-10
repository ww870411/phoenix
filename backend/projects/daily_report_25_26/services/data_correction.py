"""日报修正申请：以数据库事务保存申请、单元格占用及审批留痕。"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import json
from threading import Lock

from fastapi import HTTPException
from sqlalchemy import Column, Date, DateTime, Integer, JSON, String, Text
from sqlalchemy.exc import IntegrityError

from backend.db.database_daily_report_25_26 import (
    Base, DailyBasicData, CoalInventoryData, SessionLocal, engine,
)
from backend.services.auth_manager import EAST_8

PROJECT = "daily_report_25_26"
_table_lock = Lock()
_ready_engine = None


class DataCorrection(Base):
    __tablename__ = "daily_data_correction"
    id = Column(Integer, primary_key=True)
    sheet_key = Column(Text, nullable=False, index=True)
    sheet_name = Column(Text, nullable=False)
    unit_id = Column(Text, nullable=False)
    biz_date = Column(Date, nullable=False, index=True)
    applicant = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    changes = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(Text)
    resolution_note = Column(Text)


class CorrectionReservation(Base):
    """唯一键按真实业务单元格生成，同期列与历史本期列共享占用。"""
    __tablename__ = "daily_data_correction_cell"
    cell_key = Column(Text, primary_key=True)
    request_id = Column(Integer, nullable=False, index=True)


def ensure_tables():
    global _ready_engine
    with _table_lock:
        if _ready_engine is not engine:
            Base.metadata.create_all(engine, tables=[DataCorrection.__table__, CorrectionReservation.__table__])
            _ready_engine = engine


def ensure_access(actor, sheet_key=None, unit_id=None, submit=False):
    if not actor.has_project_access(PROJECT):
        raise HTTPException(403, "无权访问该项目")
    if actor.group == "Global_admin":
        return
    pages = actor.get_project_page_access(PROJECT)
    if "data_entry" not in pages and "*" not in pages:
        raise HTTPException(403, "无日报填报页面权限")
    if submit and not actor.get_project_action_flags(PROJECT).can_submit:
        raise HTTPException(403, "当前账号无修正申请权限")
    if sheet_key:
        rule = actor.resolve_project_permissions(PROJECT).sheet_rules.get("data_entry")
        allowed = bool(rule and (
            rule.mode == "all" or sheet_key in rule.sheets or
            (rule.mode == "by_unit" and unit_id in actor.resolve_allowed_units(PROJECT))
        ))
        if not allowed:
            raise HTTPException(403, "无权操作该单位表格")


def number(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = Decimal(str(raw).strip())
        if not value.is_finite() or abs(value) >= Decimal("100000000000000"):
            raise ValueError()
        rounded = value.quantize(Decimal("0.0001"))
        if rounded != value:
            raise ValueError()
        return format(rounded, "f")
    except (InvalidOperation, ValueError):
        raise HTTPException(422, "修正值须为有效数字（最多四位小数）或空值")


def preserve_audit_note(existing, incoming):
    """普通填报不得清除已确认的修正流水，保留原备注里的完整修正段。"""
    marker = "【数据修正申请 #"
    if existing and marker in existing:
        audit = existing[existing.index(marker):]
        if audit not in (incoming or ""):
            return f"{incoming}\n{audit}" if incoming else audit
    return incoming


def cell_query(db, cell):
    model = CoalInventoryData if cell["table"] == "coal" else DailyBasicData
    identity = dict(cell["identity"], date=date.fromisoformat(cell["date"]))
    return db.query(model).filter_by(**identity)


def build_cells(db, sheet_key, biz_date, actor):
    # 只信任服务端基本指标模板，客户端不能指定表、单位或实际数据日期。
    from backend.projects.daily_report_25_26.api import legacy_full as legacy
    template, _, _ = legacy._locate_sheet_payload(sheet_key, preferred_path=legacy.BASIC_TEMPLATE_PATH)
    if template is None:
        raise HTTPException(404, "基本指标表中不存在该表格")
    names = legacy._extract_names(template)
    ensure_access(actor, sheet_key, names["unit_id"])
    columns = list(legacy._extract_list(template, legacy.COLUMN_KEYS) or [])
    rows = list(legacy._extract_list(template, legacy.ROW_KEYS) or [])
    dictionaries = legacy._collect_all_dicts(template)
    reverse = lambda name: {str(v).strip(): k for k, v in dictionaries.get(name, {}).items()}
    items = reverse("item_dict")
    centers = reverse("center_dict") or reverse("company_dict")
    companies, coal_types = reverse("company_dict"), reverse("coal_dict") or items
    is_coal = legacy._is_coal_inventory_sheet(sheet_key, template)
    is_center = legacy._is_gongre_sheet(sheet_key)
    cells = []
    try:
        peer = biz_date.replace(year=biz_date.year - 1)
    except ValueError:
        peer = biz_date.replace(year=biz_date.year - 1, day=28)
    for ri, row in enumerate(rows):
        if not isinstance(row, list) or len(row) < 2:
            continue
        label = str(row[0]).strip()
        if is_coal:
            indexes = [i for i, c in enumerate(columns) if c in legacy.COAL_STORAGE_NAME_MAP]
        else:
            indexes = [i for i, c in enumerate(columns) if "本期" in str(c) or "同期" in str(c)]
        for ci in indexes:
            # 模板中的箭头、固定说明不是数据输入格，不能作为数值修正。
            if ci < len(row) and row[ci] not in (None, ""):
                try:
                    number(row[ci])
                except HTTPException:
                    continue
            target_date = peer if "同期" in str(columns[ci]) else biz_date
            if is_coal:
                identity = dict(company=companies.get(label, label),
                                coal_type=coal_types.get(str(row[1]).strip(), str(row[1]).strip()),
                                storage_type=legacy.COAL_STORAGE_NAME_MAP[columns[ci]][0])
                extra = dict(company_cn=label, coal_type_cn=str(row[1]), storage_type_cn=columns[ci])
            else:
                if label not in items:
                    continue
                company = centers.get(str(row[1]).strip()) if is_center else names["unit_id"]
                if not company:
                    continue
                identity = dict(company=company, sheet_name=sheet_key, item=items[label])
                extra = dict(company_cn=str(row[1]) if is_center else names["unit_name"], item_cn=label)
            cell = dict(row_index=ri, col_index=ci, table="coal" if is_coal else "daily",
                        identity=identity, date=target_date.isoformat(), label=" / ".join(map(str, row[:2])),
                        column=str(columns[ci]), unit=str(row[2] if is_coal or is_center else row[1]), extra=extra)
            cell["cell_key"] = json.dumps([cell["table"], identity, cell["date"]], sort_keys=True, ensure_ascii=False)
            cells.append(cell)
    # 整表一次读取，避免分中心表每次轮询产生数百次查询。
    model = CoalInventoryData if is_coal else DailyBasicData
    query = db.query(model).filter(
        model.date.in_({date.fromisoformat(c["date"]) for c in cells}),
        model.company.in_({c["identity"]["company"] for c in cells}),
    )
    if not is_coal:
        query = query.filter(DailyBasicData.sheet_name == sheet_key)
    stored = {}
    for record in query.all():
        identity = ({k: getattr(record, k) for k in ("company", "coal_type", "storage_type")} if is_coal else
                    {k: getattr(record, k) for k in ("company", "sheet_name", "item")})
        key = json.dumps(["coal" if is_coal else "daily", identity, record.date.isoformat()], sort_keys=True, ensure_ascii=False)
        if key in stored:
            raise HTTPException(409, "存在重复业务数据，请先核查后再修正")
        stored[key] = record
    for cell in cells:
        record = stored.get(cell["cell_key"])
        cell["old_value"] = number(record.value) if record else None
        cell["exists"] = record is not None
        cell["version"] = record.operation_time.isoformat() if record else None
    return names, cells


def serialize(record, actor):
    return {k: (getattr(record, k).isoformat() if isinstance(getattr(record, k), (date, datetime)) else getattr(record, k))
            for k in ("id", "sheet_key", "sheet_name", "unit_id", "biz_date", "applicant", "reason", "status",
                      "changes", "created_at", "resolved_at", "resolved_by", "resolution_note")} | {
        "can_cancel": record.status == "pending" and record.applicant == actor.username,
        "can_review": record.status == "pending" and actor.group == "Global_admin",
    }


def ordinary_readonly(actor, unit_id, biz_date):
    from backend.services.auth_manager import auth_manager
    from backend.services.workflow_status import workflow_status_manager
    if actor.group == "Global_admin":
        return False
    business_day = auth_manager.current_biz_date()
    when = datetime.combine(business_day, datetime.min.time()).replace(tzinfo=EAST_8)
    return biz_date != business_day or workflow_status_manager.is_unit_approved(PROJECT, when, unit_id)


def validate_regular_submission(actor, sheet_key, payload):
    """普通入口继续只允许未审批业务日本期值，修正模式不能绕过申请。"""
    if actor.group == "Global_admin":
        return payload
    from backend.projects.daily_report_25_26.api import legacy_full as legacy
    template, _, _ = legacy._locate_sheet_payload(sheet_key, preferred_path=legacy.BASIC_TEMPLATE_PATH)
    if template is None:
        return payload  # 常量等其他页面保留原有协议。
    names = legacy._extract_names(template)
    ensure_access(actor, sheet_key, names["unit_id"], submit=True)
    business_date = legacy._parse_date_value(payload.get("biz_date"))
    if business_date is None:
        raise HTTPException(422, "请提供业务日期")
    if ordinary_readonly(actor, names["unit_id"], business_date):
        raise HTTPException(403, "历史日期或已审批数据只能通过修正申请修改")
    template_rows = list(legacy._extract_list(template, legacy.ROW_KEYS) or [])
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != len(template_rows):
        raise HTTPException(422, "表格行结构与模板不一致，请重载模板")
    headers = list(legacy._extract_list(template, legacy.COLUMN_KEYS) or [])
    first_data = next(i for i, c in enumerate(headers) if "本期" in str(c) or c in legacy.COAL_STORAGE_NAME_MAP)
    for row, expected in zip(rows, template_rows):
        if not isinstance(row, list) or len(row) != len(headers) or row[:first_data] != expected[:first_data]:
            raise HTTPException(422, "表格单位、指标或列结构与模板不一致")
    with SessionLocal() as db:
        _, cells = build_cells(db, sheet_key, business_date, actor)
        for cell in cells:
            if "同期" in cell["column"] and number(rows[cell["row_index"]][cell["col_index"]]) != cell["old_value"]:
                raise HTTPException(403, "同期值只能通过修正申请修改")
    try:
        peer = business_date.replace(year=business_date.year - 1)
    except ValueError:
        peer = business_date.replace(year=business_date.year - 1, day=28)
    trusted = dict(payload, sheet_key=sheet_key, unit_id=names["unit_id"], unit_name=names["unit_name"],
                   columns=[peer.isoformat() if "同期" in str(c) else business_date.isoformat() if "本期" in str(c) else c for c in headers])
    # 清除客户端字典后回填模板字典，防止通过旧提交接口改写实际数据标识。
    for aliases in legacy.DICT_KEY_GROUPS.values():
        for key in aliases:
            trusted.pop(key, None)
    trusted.update(legacy._collect_all_dicts(template))
    return trusted


def snapshot(actor, sheet_key, biz_date):
    ensure_tables()
    with SessionLocal() as db:
        names, cells = build_cells(db, sheet_key, biz_date, actor)
        keys = [c["cell_key"] for c in cells]
        reserved = {r.cell_key: r.request_id for r in db.query(CorrectionReservation).filter(CorrectionReservation.cell_key.in_(keys)).all()}
        return {"cells": [dict(c, pending_request_id=reserved.get(c["cell_key"])) for c in cells],
                "ordinary_readonly": ordinary_readonly(actor, names["unit_id"], biz_date)}


def create_request(actor, payload):
    ensure_access(actor, submit=True)
    ensure_tables()
    try:
        with SessionLocal.begin() as db:
            names, cells = build_cells(db, payload.sheet_key, payload.biz_date, actor)
            lookup = {(c["row_index"], c["col_index"]): c for c in cells}
            changes, seen = [], set()
            for change in payload.changes:
                cell = lookup.get((change.row_index, change.col_index))
                if not cell or cell["cell_key"] in seen:
                    raise HTTPException(422, "单元格不存在、不可修正或重复")
                seen.add(cell["cell_key"])
                if number(change.old_value) != cell["old_value"] or change.version != cell["version"]:
                    raise HTTPException(409, "原数据已变化，请重新加载后申请")
                new_value = number(change.new_value)
                if new_value != cell["old_value"]:
                    changes.append(dict(cell, new_value=new_value))
            if not changes:
                raise HTTPException(422, "没有需要修正的单元格")
            record = DataCorrection(sheet_key=payload.sheet_key, sheet_name=names["sheet_name"] or payload.sheet_key,
                                    unit_id=names["unit_id"], biz_date=payload.biz_date, applicant=actor.username,
                                    reason=payload.reason.strip(), changes=changes, created_at=datetime.now(EAST_8).replace(tzinfo=None), status="pending")
            db.add(record)
            db.flush()
            for cell in changes:
                db.add(CorrectionReservation(cell_key=cell["cell_key"], request_id=record.id))
            db.flush()
            return serialize(record, actor)
    except IntegrityError:
        raise HTTPException(409, "部分单元格已有待审批申请，请刷新后重试")


def resolve_request(actor, request_id, action, note):
    ensure_access(actor)
    if action not in {"approve", "reject", "cancel"}:
        raise HTTPException(422, "无效的处理动作")
    ensure_tables()
    with SessionLocal.begin() as db:
        record = db.query(DataCorrection).filter_by(id=request_id).with_for_update().one_or_none()
        if not record:
            raise HTTPException(404, "修正申请不存在")
        if action == "cancel":
            if record.applicant != actor.username:
                raise HTTPException(403, "仅申请人可以取消")
        elif actor.group != "Global_admin":
            raise HTTPException(403, "仅 Global_admin 可以确认或驳回")
        if record.status != "pending":
            raise HTTPException(409, "该申请已关闭，请刷新记录")
        now = datetime.now(EAST_8).replace(tzinfo=None)
        if action == "approve":
            for cell in sorted(record.changes, key=lambda c: c["cell_key"]):
                target = cell_query(db, cell).with_for_update().one_or_none()
                version = target.operation_time.isoformat() if target else None
                if (target is not None) != cell["exists"] or version != cell["version"] or (number(target.value) if target else None) != cell["old_value"]:
                    raise HTTPException(409, "原数据在申请后发生变化，未写入任何修正；请驳回并重新申请")
                if target is None:
                    model = CoalInventoryData if cell["table"] == "coal" else DailyBasicData
                    target = model(**cell["identity"], **cell["extra"], date=date.fromisoformat(cell["date"]), unit=cell["unit"], status="submit")
                    db.add(target)
                audit = (f"【数据修正申请 #{record.id}】业务日：{record.biz_date}；数据日期：{cell['date']}；"
                         f"申请人：{record.applicant}；申请时间：{record.created_at.isoformat(sep=' ')}；原因：{record.reason}；"
                         f"{cell['old_value'] if cell['old_value'] is not None else '空值'} → {cell['new_value'] if cell['new_value'] is not None else '空值'}；"
                         f"确认人：{actor.username}；确认时间：{now.isoformat(sep=' ')}；审批说明：{note or '无'}")
                target.value = Decimal(cell["new_value"]) if cell["new_value"] is not None else None
                target.note = f"{target.note}\n{audit}" if target.note else audit
                target.operation_time = now
        record.status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[action]
        record.resolved_by, record.resolved_at, record.resolution_note = actor.username, now, note
        db.query(CorrectionReservation).filter_by(request_id=record.id).delete(synchronize_session=False)
        db.flush()
        return serialize(record, actor)


def list_requests(actor, status=None, offset=0, limit=50):
    ensure_access(actor)
    ensure_tables()
    with SessionLocal() as db:
        query = db.query(DataCorrection)
        if actor.group != "Global_admin":
            # 记录的可见范围复用表格权限，避免跨单位读取申请详情。
            visible = []
            from backend.projects.daily_report_25_26.api import legacy_full as legacy
            catalog = legacy._read_json(legacy.BASIC_TEMPLATE_PATH)
            for key, tpl in catalog.items():
                try:
                    ensure_access(actor, key, legacy._extract_names(tpl)["unit_id"])
                    visible.append(key)
                except HTTPException:
                    pass
            query = query.filter(DataCorrection.sheet_key.in_(visible))
        if status:
            query = query.filter_by(status=status)
        total = query.count()
        return {"total": total, "records": [serialize(r, actor) for r in query.order_by(DataCorrection.id.desc()).offset(offset).limit(limit).all()]}
