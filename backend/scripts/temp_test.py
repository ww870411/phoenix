# -*- coding: utf-8 -*-
"""
用于测试从 calc_temperature_data 视图中获取平均气温的脚本。
允许用户查询单个日期或日期范围。
新增调试功能，可同时查询原始数据和视图计算结果。
"""

import os
import sys
from datetime import datetime
from sqlalchemy import text

# --- 设置项目路径以允许从 'backend' 导入 ---
# 假设脚本在 phoenix/backend/scripts 中，我们需要上移两级到 phoenix/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
# ---

try:
    # 动态导入数据库会话
    from backend.db.database_daily_report_25_26 import SessionLocal
except ImportError as e:
    print(f"错误：无法从 'backend' 导入模块。请确保您的项目结构正确。\n")
    print(f"详细信息: {e}")
    sys.exit(1)

def fetch_single_date_debug(session, target_date):
    """为单个日期提供详细的调试信息，对比原始数据和视图结果。"""
    print(f"\n===== 开始调试日期: {target_date.strftime('%Y-%m-%d')} =====")

    # 1. 从原始表 'temperature_data' 获取当天的所有小时数据
    raw_stmt = text(
        """
        SELECT date_time, value
        FROM temperature_data
        WHERE DATE(date_time AT TIME ZONE 'Asia/Shanghai') = :target_date
        ORDER BY date_time
        """
    )
    raw_results = session.execute(raw_stmt, {"target_date": target_date}).all()

    # 2. 从视图 'calc_temperature_data' 获取聚合结果
    view_stmt = text(
        """
        SELECT date, aver_temp, min_temp, max_temp
        FROM calc_temperature_data
        WHERE date = :target_date
        """
    )
    view_result = session.execute(view_stmt, {"target_date": target_date}).first()

    # 3. 打印结果用于对比
    manual_avg = 0.0
    if raw_results:
        print(f"\n[1] 在 'temperature_data' 表中找到 {len(raw_results)} 条原始数据:")
        values = []
        for row in raw_results:
            print(f"  -> 时间戳: {row[0]}, 数值: {row[1]}")
            if row[1] is not None:
                values.append(float(row[1]))
        
        if values:
            manual_avg = sum(values) / len(values)
            print(f"\n[2] 手动计算这些原始数据的平均值 = {manual_avg:.4f}")
        else:
            print("\n[2] 原始数据中没有有效的数值，无法手动计算平均值。")

    else:
        print("\n[1] 在 'temperature_data' 表中未找到该日期的任何原始数据。")

    if view_result:
        print(f"\n[3] 从 'calc_temperature_data' 视图中查询到的计算结果:")
        print(f"  -> 日期: {view_result[0]}")
        print(f"  -> 视图计算的平均值 (aver_temp): {view_result[1]}")
        print(f"  -> 视图计算的最小值 (min_temp): {view_result[2]}")
        print(f"  -> 视图计算的最大值 (max_temp): {view_result[3]}")
        
        if manual_avg > 0:
            diff = float(view_result[1]) - manual_avg
            print(f"\n[4] 对比：视图计算结果与手动计算结果相差: {diff:.4f}")
    else:
        print("\n[3] 在 'calc_temperature_data' 视图中未找到该日期的聚合数据。")
    
    print(f"\n===== 调试结束: {target_date.strftime('%Y-%m-%d')} =====")


def main():
    """主函数，提示用户并获取数据。"""
    print("\n===== 平均气温数据查询及调试脚本 =====")
    
    date_str = input("请输入要调试的日期 (格式 YYYY-MM-DD): ").strip()
    
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("\n错误：日期格式不正确，请输入 YYYY-MM-DD 格式。\n")
        return

    # 创建数据库会话
    session = SessionLocal()
    try:
        fetch_single_date_debug(session, target_date)
    finally:
        # 确保无论如何都关闭会话
        session.close()
        print("\n数据库连接已关闭。\n")

if __name__ == "__main__":
    main()