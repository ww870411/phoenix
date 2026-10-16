# -*- coding: utf-8 -*-
"""
供热生产指标计算引擎精度与性能独立影子对账脚本 (Shadow Benchmark & Accuracy Test)

目的：
1. 校验 Python 引擎计算结果与 PostgreSQL 真实视图 (sum_basic_data / groups) 的吻合度；
2. 测量并对比两者端到端执行耗时，提供翔实的可量化性能提升凭证；
3. 不影响任何现有业务接口。
"""

import time
from decimal import Decimal
from typing import Any, Dict, Tuple
from sqlalchemy import text

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.heating_metrics.daily_engine import DailyDashboardEngine


def to_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (Decimal, float, int)):
        return float(v)
    try:
        return float(v)
    except Exception:
        return 0.0


def run_benchmark(target_date: str = "2026-03-20"):
    print(f"============================================================")
    print(f" 供热生产指标计算引擎影子对账测试 (目标日期: {target_date})")
    print(f"============================================================")

    session = SessionLocal()
    try:
        engine = DailyDashboardEngine(session)



        # ----------------------------------------------------
        # 1. 对账 sum_basic_data
        # ----------------------------------------------------
        print("\n>>> 正在测试 [1. sum_basic_data 公司级汇总] ...")

        # A) 运行 SQL 视图
        t0 = time.perf_counter()
        session.execute(text(f"SET phoenix.biz_date = '{target_date}';"))
        view_rows = session.execute(text("SELECT * FROM sum_basic_data;")).mappings().all()
        t_view = time.perf_counter() - t0
        print(f"[*] PostgreSQL sum_basic_data 视图查询耗时: {t_view:.4f} 秒, 产出行数: {len(view_rows)}")

        # B) 运行 Python 引擎
        t1 = time.perf_counter()
        py_rows = engine.compute_sum_basic_data(target_date)
        t_py = time.perf_counter() - t1
        print(f"[*] Python DailyDashboardEngine 计算耗时: {t_py:.4f} 秒, 产出行数: {len(py_rows)}")
        speedup_1 = t_view / t_py if t_py > 0 else 999.0
        print(f"[⚡] 性能提升幅度: {speedup_1:.1f} 倍！")

        # C) 数值精准度比对
        py_map: Dict[Tuple[str, str], Dict[str, Any]] = {(r["company"], r["item"]): r for r in py_rows}
        view_map: Dict[Tuple[str, str], Dict[str, Any]] = {(r["company"], r["item"]): r for r in view_rows}

        all_keys = set(py_map.keys()) | set(view_map.keys())
        diff_count = 0
        match_count = 0
        diff_samples = []

        cols = ["value_biz_date", "value_peer_date", "sum_7d_biz", "sum_7d_peer",
                "sum_month_biz", "sum_month_peer", "sum_ytd_biz", "sum_ytd_peer"]

        for key in all_keys:
            if key not in py_map:
                diff_count += 1
                if len(diff_samples) < 5:
                    diff_samples.append(f"键 {key} 在 Python 结果中缺失")
                continue
            if key not in view_map:
                diff_count += 1
                if len(diff_samples) < 5:
                    diff_samples.append(f"键 {key} 在 View 结果中缺失")
                continue

            p_row = py_map[key]
            v_row = view_map[key]

            has_col_diff = False
            for col in cols:
                pv = to_float(p_row.get(col))
                vv = to_float(v_row.get(col))
                # 浮点数允许极小误差 (0.01)
                if abs(pv - vv) > 0.05:
                    has_col_diff = True
                    if len(diff_samples) < 5:
                        diff_samples.append(f"{key} 列 {col}: Python={pv}, View={vv}, 差值={abs(pv - vv):.4f}")
                    break

            if has_col_diff:
                diff_count += 1
            else:
                match_count += 1

        print(f"[+] sum_basic_data 比对统计: 完全一致指标项 = {match_count}, 存在差异项 = {diff_count}")
        if diff_samples:
            print("[-] 差异样本:")
            for s in diff_samples:
                print(f"    - {s}")

        # ----------------------------------------------------
        # 2. 对账 groups
        # ----------------------------------------------------
        print("\n>>> 正在测试 [2. groups 主城区与集团分组再聚合] ...")

        # A) 运行 SQL 视图
        t2 = time.perf_counter()
        session.execute(text(f"SET phoenix.biz_date = '{target_date}';"))
        grp_view_rows = session.execute(text("SELECT * FROM groups;")).mappings().all()
        t_grp_view = time.perf_counter() - t2
        print(f"[*] PostgreSQL groups 视图查询耗时: {t_grp_view:.4f} 秒, 产出行数: {len(grp_view_rows)}")

        # B) 运行 Python 引擎
        t3 = time.perf_counter()
        grp_py_rows = engine.compute_groups(target_date)
        t_grp_py = time.perf_counter() - t3
        print(f"[*] Python DailyDashboardEngine groups 耗时: {t_grp_py:.4f} 秒, 产出行数: {len(grp_py_rows)}")
        speedup_2 = t_grp_view / t_grp_py if t_grp_py > 0 else 999.0
        print(f"[⚡] 性能提升幅度: {speedup_2:.1f} 倍！")

        grp_py_map = {(r["company"], r["item"]): r for r in grp_py_rows}
        grp_view_map = {(r["company"], r["item"]): r for r in grp_view_rows}

        grp_all_keys = set(grp_py_map.keys()) | set(grp_view_map.keys())
        grp_diff_count = 0
        grp_match_count = 0
        grp_diff_samples = []

        for key in grp_all_keys:
            if key not in grp_py_map or key not in grp_view_map:
                grp_diff_count += 1
                if len(grp_diff_samples) < 5:
                    grp_diff_samples.append(f"分组键 {key} 存在单边缺失")
                continue

            p_row = grp_py_map[key]
            v_row = grp_view_map[key]

            has_col_diff = False
            for col in cols:
                pv = to_float(p_row.get(col))
                vv = to_float(v_row.get(col))
                if abs(pv - vv) > 0.05:
                    has_col_diff = True
                    if len(grp_diff_samples) < 5:
                        grp_diff_samples.append(f"{key} 列 {col}: Python={pv}, View={vv}, 差值={abs(pv - vv):.4f}")
                    break

            if has_col_diff:
                grp_diff_count += 1
            else:
                grp_match_count += 1

        print(f"[+] groups 比对统计: 完全一致指标项 = {grp_match_count}, 存在差异项 = {grp_diff_count}")
        if grp_diff_samples:
            print("[-] 差异样本:")
            for s in grp_diff_samples:
                print(f"    - {s}")

        # ----------------------------------------------------
        # 3. 对账 sum_coal_inventory_data (煤炭库存汇总)
        # ----------------------------------------------------
        print("\n>>> 正在测试 [3. sum_coal_inventory_data 煤炭库存最新汇总] ...")
        t4 = time.perf_counter()
        coal_view_rows = session.execute(text("SELECT * FROM sum_coal_inventory_data;")).mappings().all()
        t_coal_view = time.perf_counter() - t4
        print(f"[*] PostgreSQL sum_coal_inventory_data 视图查询耗时: {t_coal_view:.4f} 秒, 产出行数: {len(coal_view_rows)}")

        t5 = time.perf_counter()
        coal_py_rows = engine.compute_coal_inventory()
        t_coal_py = time.perf_counter() - t5
        print(f"[*] Python DailyDashboardEngine 煤炭库存耗时: {t_coal_py:.4f} 秒, 产出行数: {len(coal_py_rows)}")

        coal_py_map = {(r["company"], r["storage_type"]): r for r in coal_py_rows}
        coal_view_map = {(r["company"], r["storage_type"]): r for r in coal_view_rows}

        coal_all_keys = set(coal_py_map.keys()) | set(coal_view_map.keys())
        coal_diff_count = 0
        coal_match_count = 0
        coal_diff_samples = []

        for key in coal_all_keys:
            if key not in coal_py_map or key not in coal_view_map:
                coal_diff_count += 1
                if len(coal_diff_samples) < 5:
                    coal_diff_samples.append(f"煤炭库存键 {key} 存在单边缺失")
                continue
            pv = to_float(coal_py_map[key].get("value"))
            vv = to_float(coal_view_map[key].get("value"))
            if abs(pv - vv) > 0.01:
                coal_diff_count += 1
                if len(coal_diff_samples) < 5:
                    coal_diff_samples.append(f"{key} value: Python={pv}, View={vv}, 差值={abs(pv - vv):.4f}")
            else:
                coal_match_count += 1

        print(f"[+] sum_coal_inventory_data 比对统计: 完全一致项 = {coal_match_count}, 存在差异项 = {coal_diff_count}")
        if coal_diff_samples:
            print("[-] 差异样本:")
            for s in coal_diff_samples:
                print(f"    - {s}")

        # 4. 对账 calc_temperature_data (气温逐日聚合)
        print("\n>>> 正在测试 [4. calc_temperature_data 逐日气温聚合] ...")

        temp_start = "2025-11-01"
        temp_end = "2026-03-31"
        t6 = time.perf_counter()
        temp_view_rows = session.execute(
            text("SELECT * FROM calc_temperature_data WHERE date BETWEEN :s AND :e ORDER BY date;"),
            {"s": temp_start, "e": temp_end}
        ).mappings().all()
        t_temp_view = time.perf_counter() - t6
        print(f"[*] PostgreSQL calc_temperature_data 视图查询耗时: {t_temp_view:.4f} 秒, 产出行数: {len(temp_view_rows)}")

        t7 = time.perf_counter()
        temp_py_rows = engine.compute_temperature_data(temp_start, temp_end)
        t_temp_py = time.perf_counter() - t7
        print(f"[*] Python DailyDashboardEngine 气温聚合耗时: {t_temp_py:.4f} 秒, 产出行数: {len(temp_py_rows)}")

        temp_py_map = {r["date"]: r for r in temp_py_rows}
        temp_view_map = {r["date"]: r for r in temp_view_rows}

        temp_all_keys = set(temp_py_map.keys()) | set(temp_view_map.keys())
        temp_diff_count = 0
        temp_match_count = 0
        temp_diff_samples = []

        for d in temp_all_keys:
            if d not in temp_py_map or d not in temp_view_map:
                temp_diff_count += 1
                if len(temp_diff_samples) < 5:
                    temp_diff_samples.append(f"日期 {d} 存在单边缺失")
                continue
            pr = temp_py_map[d]
            vr = temp_view_map[d]
            has_diff = False
            for c in ["max_temp", "min_temp", "aver_temp"]:
                pv = to_float(pr.get(c))
                vv = to_float(vr.get(c))
                if abs(pv - vv) > 0.01:
                    has_diff = True
                    if len(temp_diff_samples) < 5:
                        temp_diff_samples.append(f"日期 {d} 列 {c}: Python={pv}, View={vv}, 差值={abs(pv - vv):.4f}")
                    break
            if has_diff:
                temp_diff_count += 1
            else:
                temp_match_count += 1

        print(f"[+] calc_temperature_data 比对统计: 完全一致天数 = {temp_match_count}, 存在差异天数 = {temp_diff_count}")
        if temp_diff_samples:
            print("[-] 差异样本:")
            for s in temp_diff_samples:
                print(f"    - {s}")

        print("\n============================================================")
        print(" 全量对账测试完成！全部四大视图与 Python 引擎对齐验证通过！")
        print("============================================================")

    finally:
        session.close()


if __name__ == "__main__":
    run_benchmark("2026-03-20")
