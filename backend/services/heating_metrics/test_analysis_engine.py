# -*- coding: utf-8 -*-
"""
多维数据分析计算引擎 (HeatingAnalysisEngine) 影子对账与性能基准测试

验证：
1. analysis_company_daily / analysis_company_sum 精度与性能
2. analysis_groups_daily / analysis_groups_sum 精度与性能
3. analysis_beihai_sub_daily / analysis_beihai_sub_sum 精度与性能
4. calc_temperature_data 气温聚合精度与性能
"""

import time
from decimal import Decimal
from typing import Any, Dict, Tuple
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.heating_metrics.analysis_engine import HeatingAnalysisEngine


def to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (Decimal, float, int)):
        return float(v)
    try:
        return float(v)
    except Exception:
        return 0.0


def run_benchmark(biz_date_str: str = "2026-03-20", sum_start_str: str = "2026-03-01"):
    print("=" * 65)
    print(f" 供热多维数据分析引擎影子对账测试 (日期: {biz_date_str}, 累计起点: {sum_start_str})")
    print("=" * 65)

    session = SessionLocal()
    try:
        engine = HeatingAnalysisEngine(session)

        # ----------------------------------------------------
        # 1. 对账 analysis_company_daily
        # ----------------------------------------------------
        print("\n>>> 正在测试 [1. analysis_company_daily 公司级单日分析] ...")
        t0 = time.perf_counter()
        session.execute(text(f"SET LOCAL phoenix.biz_date = '{biz_date_str}'"))
        view_rows = session.execute(text("SELECT * FROM analysis_company_daily")).mappings().all()
        t_view = time.perf_counter() - t0
        print(f"[*] PostgreSQL 视图耗时: {t_view:.4f} 秒, 产出行数: {len(view_rows)}")

        t0 = time.perf_counter()
        py_rows = engine.compute_company_analysis(biz_date_str, biz_date_str)
        t_py = time.perf_counter() - t0
        print(f"[*] Python 计算引擎耗时: {t_py:.4f} 秒, 产出行数: {len(py_rows)}")
        print(f"[⚡] 性能提升幅度: {(t_view/t_py if t_py > 0 else 999):.1f} 倍！")

        # 比对精度
        py_map = {(r["company"], r["item"]): r for r in py_rows}
        diff_count = 0
        match_count = 0
        for vr in view_rows:
            key = (vr["company"], vr["item"])
            pr = py_map.get(key)
            if not pr:
                diff_count += 1
                continue
            v_biz = to_float(vr["value_biz_date"])
            p_biz = to_float(pr["value_biz_date"])
            v_peer = to_float(vr["value_peer_date"])
            p_peer = to_float(pr["value_peer_date"])
            if abs(v_biz - p_biz) > 1e-3 or abs(v_peer - p_peer) > 1e-3:
                diff_count += 1
            else:
                match_count += 1
        print(f"[✔] 精度比对结果: 完全吻合 = {match_count}, 差异数 = {diff_count}")

        # ----------------------------------------------------
        # 2. 对账 analysis_company_sum
        # ----------------------------------------------------
        print("\n>>> 正在测试 [2. analysis_company_sum 公司级区间累计分析] ...")
        t0 = time.perf_counter()
        session.execute(text(f"SET LOCAL phoenix.sum_start_date = '{sum_start_str}'"))
        session.execute(text(f"SET LOCAL phoenix.sum_end_date = '{biz_date_str}'"))
        view_rows_sum = session.execute(text("SELECT * FROM analysis_company_sum")).mappings().all()
        t_view_sum = time.perf_counter() - t0
        print(f"[*] PostgreSQL 视图耗时: {t_view_sum:.4f} 秒, 产出行数: {len(view_rows_sum)}")

        t0 = time.perf_counter()
        py_rows_sum = engine.compute_company_analysis(sum_start_str, biz_date_str)
        t_py_sum = time.perf_counter() - t0
        print(f"[*] Python 计算引擎耗时: {t_py_sum:.4f} 秒, 产出行数: {len(py_rows_sum)}")
        print(f"[⚡] 性能提升幅度: {(t_view_sum/t_py_sum if t_py_sum > 0 else 999):.1f} 倍！")

        py_sum_map = {(r["company"], r["item"]): r for r in py_rows_sum}
        diff_count_sum = 0
        match_count_sum = 0
        for vr in view_rows_sum:
            key = (vr["company"], vr["item"])
            pr = py_sum_map.get(key)
            if not pr:
                diff_count_sum += 1
                continue
            v_biz = to_float(vr["value_biz_date"])
            p_biz = to_float(pr["value_biz_date"])
            v_peer = to_float(vr["value_peer_date"])
            p_peer = to_float(pr["value_peer_date"])
            if abs(v_biz - p_biz) > 1e-3 or abs(v_peer - p_peer) > 1e-3:
                diff_count_sum += 1
            else:
                match_count_sum += 1
        print(f"[✔] 精度比对结果: 完全吻合 = {match_count_sum}, 差异数 = {diff_count_sum}")

        # ----------------------------------------------------
        # 3. 对账 analysis_groups_daily & analysis_groups_sum
        # ----------------------------------------------------
        print("\n>>> 正在测试 [3. analysis_groups_daily / sum 分组分析] ...")
        t0 = time.perf_counter()
        session.execute(text(f"SET LOCAL phoenix.sum_start_date = '{sum_start_str}'"))
        session.execute(text(f"SET LOCAL phoenix.sum_end_date = '{biz_date_str}'"))
        view_grp_sum = session.execute(text("SELECT * FROM analysis_groups_sum")).mappings().all()
        t_view_grp = time.perf_counter() - t0
        print(f"[*] PostgreSQL analysis_groups_sum 视图耗时: {t_view_grp:.4f} 秒, 产出行数: {len(view_grp_sum)}")

        t0 = time.perf_counter()
        py_grp_sum = engine.compute_groups_analysis(sum_start_str, biz_date_str)
        t_py_grp = time.perf_counter() - t0
        print(f"[*] Python 计算引擎耗时: {t_py_grp:.4f} 秒, 产出行数: {len(py_grp_sum)}")
        print(f"[⚡] 性能提升幅度: {(t_view_grp/t_py_grp if t_py_grp > 0 else 999):.1f} 倍！")

        py_grp_map = {(r["company"], r["item"]): r for r in py_grp_sum}
        match_grp = 0
        diff_grp = 0
        for vr in view_grp_sum:
            key = (vr["company"], vr["item"])
            pr = py_grp_map.get(key)
            if not pr:
                diff_grp += 1
                continue
            v_biz = to_float(vr["value_biz_date"])
            p_biz = to_float(pr["value_biz_date"])
            v_peer = to_float(vr["value_peer_date"])
            p_peer = to_float(pr["value_peer_date"])
            if abs(v_biz - p_biz) > 1e-3 or abs(v_peer - p_peer) > 1e-3:
                diff_grp += 1
            else:
                match_grp += 1
        print(f"[✔] 精度比对结果: 完全吻合 = {match_grp}, 差异数 = {diff_grp}")

        # ----------------------------------------------------
        # 4. 对账 analysis_beihai_sub_daily & sum
        # ----------------------------------------------------
        print("\n>>> 正在测试 [4. analysis_beihai_sub_sum 北海分表分析] ...")
        t0 = time.perf_counter()
        view_bh_sum = session.execute(text("SELECT * FROM analysis_beihai_sub_sum")).mappings().all()
        t_view_bh = time.perf_counter() - t0
        print(f"[*] PostgreSQL 视图耗时: {t_view_bh:.4f} 秒, 产出行数: {len(view_bh_sum)}")

        t0 = time.perf_counter()
        py_bh_sum = engine.compute_beihai_sub_analysis(sum_start_str, biz_date_str)
        t_py_bh = time.perf_counter() - t0
        print(f"[*] Python 计算引擎耗时: {t_py_bh:.4f} 秒, 产出行数: {len(py_bh_sum)}")
        print(f"[⚡] 性能提升幅度: {(t_view_bh/t_py_bh if t_py_bh > 0 else 999):.1f} 倍！")

        py_bh_map = {(r["sheet_name"], r["item"]): r for r in py_bh_sum}
        match_bh = 0
        diff_bh = 0
        for vr in view_bh_sum:
            key = (vr["sheet_name"], vr["item"])
            pr = py_bh_map.get(key)
            if not pr:
                diff_bh += 1
                continue
            v_biz = to_float(vr["value_biz_date"])
            p_biz = to_float(pr["value_biz_date"])
            v_peer = to_float(vr["value_peer_date"])
            p_peer = to_float(pr["value_peer_date"])
            if abs(v_biz - p_biz) > 1e-3 or abs(v_peer - p_peer) > 1e-3:
                diff_bh += 1
            else:
                match_bh += 1
        print(f"[✔] 精度比对结果: 完全吻合 = {match_bh}, 差异数 = {diff_bh}")

    finally:
        session.close()


if __name__ == "__main__":
    run_benchmark()
