"""动态计划无损审查：仅 GET、只读事务与内存替身，不保存业务数据。"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.daily_report_25_26.api import dynamic_plan as api
from backend.services.dynamic_decomposition_service import decompose_single_series, _decompose_entity_company


def emit(check, **data):
    print(json.dumps({"check": check, **data}, ensure_ascii=False, default=str))


def audit_live():
    base = "http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/dynamic_plan"
    with httpx.Client(timeout=30) as client:
        meta = client.get(base + "/meta").json()
        emit("meta", months=meta["available_months"], units=len(meta["units"]))
        for unit in meta["units"]:
            company = unit["company"]
            monthly = client.get(base + "/plans", params={"company": company}).json()
            detail = client.get(base + "/daily_decomposition", params={"company": company, "year_month": "2026-11"}).json()
            monthly_map = {m["item"]: m for m in monthly["metrics"]}
            mismatches, conservation_errors, negatives = [], [], []
            for metric in detail.get("metrics", []):
                item = metric["item"]
                plan = metric["month_plan"]
                daily = metric["daily_plans"]
                reference = monthly_map.get(item, {}).get("values", {}).get("2026-11")
                if reference is not None and abs(reference - plan) > 0.011:
                    mismatches.append({"item": item, "monthly": reference, "decomposition_target": plan})
                if abs(sum(daily) - plan) > 0.0051:
                    conservation_errors.append(item)
                if any(v < 0 for v in daily):
                    negatives.append(item)
            emit("company", company=company, ok=monthly.get("ok") and detail.get("ok"),
                 full=detail.get("has_full_month"), metrics=len(detail.get("metrics", [])),
                 mismatches=mismatches, conservation_errors=conservation_errors, negatives=negatives)
        for ym in meta["available_months"]:
            result = client.get(base + "/daily_decomposition", params={"company": "Group", "year_month": ym}).json()
            emit("temperature_gate", month=ym, full=result.get("has_full_month"),
                 available=result.get("available_days", len(result.get("dates", []))),
                 missing=len(result.get("missing_dates", [])))


def audit_database():
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        rows = session.execute(text("""
            SELECT (date_time AT TIME ZONE 'Asia/Shanghai')::date AS local_date,
                   COUNT(*) AS n, MIN(date_time), MAX(date_time), AVG(value)
            FROM temperature_data
            WHERE (date_time AT TIME ZONE 'Asia/Shanghai')::date >= '2026-11-01'
              AND (date_time AT TIME ZONE 'Asia/Shanghai')::date < '2026-12-01'
            GROUP BY 1 HAVING COUNT(value) < 24 ORDER BY 1
        """)).all()
        emit("incomplete_local_days", rows=[list(row) for row in rows])
        rows = session.execute(text("""
            SELECT company, item, month, k_value FROM dynamic_month_plan_k
            WHERE item LIKE '%purchased_heat%' ORDER BY company, month
        """)).all()
        emit("purchased_heat_model_keys", rows=[list(row) for row in rows])
        session.rollback()


async def audit_save_branch():
    class FakeDatabase:
        def execute(self, *args, **kwargs):
            return SimpleNamespace(fetchone=lambda: None)

        def rollback(self):
            self.rolled_back = True

        def close(self):
            pass

        def commit(self):
            raise AssertionError("审查禁止提交")

    database = FakeDatabase()
    payload = api.UpdateKParametersPayload(updates=[{
        "company": "Group", "month": 11, "item": "consumption_water", "m_value": 1.1,
    }])
    admin = SimpleNamespace(group="Global_admin")
    with patch.object(api, "SessionLocal", return_value=database):
        try:
            await api.update_k_parameters_endpoint(payload, session=admin, authorization=None)
        except api.HTTPException as exc:
            emit("save_missing_parameter", status=exc.status_code, detail=exc.detail,
                 rollback=getattr(database, "rolled_back", False), database="内存替身")
    for value in [-1, 1e100]:
        item = api.UpdateKParameterItem(company="Group", month=11, item="amount_heat_supply", m_value=value)
        emit("m_validation", value=value, accepted=item.m_value)


def audit_rounding():
    for amount in [100.0, 0.2, -1.0]:
        values, _ = decompose_single_series(amount, 0.0, [10.0] * 31, 10.0)
        emit("rounding", month_plan=amount, daily_sum=round(sum(values), 6),
             min_daily=min(values), last_daily=values[-1])


def audit_purchased_heat_alias():
    # 12 月实际月计划与实际参数，气温采用明确标注的合成序列以隔离缺温门禁。
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        result = _decompose_entity_company("ZhuangHe", 12, "2026-12", [10.0] * 15 + [20.0] * 16, 470 / 31, session)
        for metric in result["metrics_list"]:
            if "purchased_heat" in metric["item"]:
                emit("purchased_heat_alias", item=metric["item"], month_plan=metric["month_plan"],
                     has_k=metric["has_k"], k=metric["k_value"], weights=sorted(set(metric["daily_weights"])),
                     temperature_source="合成序列；月计划和参数来自只读数据库")
        session.rollback()


if __name__ == "__main__":
    audit_live()
    audit_database()
    asyncio.run(audit_save_branch())
    audit_rounding()
    audit_purchased_heat_alias()
