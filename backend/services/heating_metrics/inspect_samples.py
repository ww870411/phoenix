# -*- coding: utf-8 -*-
import json
from sqlalchemy import text
from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.heating_metrics.daily_engine import DailyDashboardEngine

def dump_samples(target_date: str = "2026-01-15"):
    session = SessionLocal()
    try:
        engine = DailyDashboardEngine(session)
        # 查出北海原始底表数据
        raw_beihai = session.execute(
            text("SELECT item, item_cn, value FROM daily_basic_data WHERE company='BeiHai' AND date=:d "
                 "AND item IN ('amount_heat_supply', 'amount_power_sales', 'consumption_outer_purchased_heat', 'consumption_std_coal')"),
            {"d": target_date}
        ).mappings().all()
        print("=== BEIHAI RAW INPUTS (2026-01-15) ===")
        for r in raw_beihai:
            print(f"  {r['item']} ({r['item_cn']}): {r['value']}")

        rows = engine.compute_all_metrics(target_date)
        row_dict = {(r["company"], r["item"]): r for r in rows}

        sample_keys = [
            ("BeiHai", "rate_overall_efficiency"),
            ("Group", "rate_overall_efficiency"),
            ("XiangHai", "rate_std_coal_per_heat"),
            ("ZhuChengQu", "rate_std_coal_per_heat"),
            ("Group", "rate_power_per_10k_m2_YanJiuYuan"),
            ("ZhuChengQu", "eco_marginal_profit"),
            ("Group", "eco_marginal_profit"),
            ("ZhuChengQu", "eco_direct_income"),
            ("Group", "eco_direct_income"),
        ]

        out = {}
        for k in sample_keys:
            if k in row_dict:
                r = row_dict[k]
                out[f"{k[0]}:{k[1]}"] = {
                    "company_cn": r["company_cn"],
                    "item_cn": r["item_cn"],
                    "unit": r["unit"],
                    "value_biz_date": r["value_biz_date"],
                    "value_peer_date": r["value_peer_date"],
                    "sum_7d_biz": r["sum_7d_biz"],
                    "sum_month_biz": r["sum_month_biz"],
                    "sum_ytd_biz": r["sum_ytd_biz"],
                }

        print("=== METRICS_SAMPLE ===")
        print(json.dumps(out, ensure_ascii=False, indent=2))

        # 煤炭库存抽样
        coal_rows = engine.compute_coal_inventory()
        print("\n=== COAL_SAMPLE ===")
        for cr in coal_rows[:6]:
            print(f"{cr['company_cn']} - {cr['storage_type_cn']}: {cr['value']} {cr['unit']}")
        for cr in coal_rows:
            if cr["company"] in ["ZhuChengQu_sum", "Group_sum"]:
                print(f"*** {cr['company_cn']}: {cr['value']} {cr['unit']} ***")

        # 气温抽样
        temp_rows = engine.compute_temperature_data("2026-01-13", "2026-01-16")
        print("\n=== TEMP_SAMPLE ===")
        for tr in temp_rows:
            print(f"日期 {tr['date']}: 最高 {tr['max_temp']}℃, 最低 {tr['min_temp']}℃, 平均 {round(tr['aver_temp'], 2)}℃")

    finally:
        session.close()

if __name__ == "__main__":
    dump_samples("2026-01-15")
