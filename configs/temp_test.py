# -*- coding: utf-8 -*-
"""
用于测试从 calc_temperature_data 视图中获取平均气温的脚本。
允许用户查询单个日期或日期范围。
"""

import os
import sys
from datetime import datetime
from sqlalchemy import text

# --- 设置项目路径以允许从 'backend' 导入 ---
# 假设脚本在 phoenix/configs 中，我们需要上移一级到 phoenix/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# ---

try:
    # 动态导入数据库会话
    from backend.db.database_daily_report_25_26 import SessionLocal
except ImportError as e:
    print(f"错误：无法从 'backend' 导入模块。请确保您的项目结构正确。")
    print(f"详细信息: {e}")
    sys.exit(1)

def fetch_single_date(session, target_date):
    """获取单个日期的平均气温。"""
    print(f"\n正在查询日期: {target_date.strftime('%Y-%m-%d')}...")
    stmt = text(
        """
        SELECT date, aver_temp
          FROM calc_temperature_data
         WHERE date = :target_date
        """
    )
    result = session.execute(stmt, {"target_date": target_date}).first()
    if result:
        print("-" * 30)
        print(f"查询成功！")
        print(f"  -> 日期: {result[0]}, 平均气温: {result[1]}")
        print("-" * 30)
    else:
        print(f"未找到日期 {target_date.strftime('%Y-%m-%d')} 的数据。")

def fetch_date_range(session, start_date, end_date):
    """获取日期范围内的平均气温。"""
    print(f"\n正在查询范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}...")
    stmt = text(
        """
        SELECT date, aver_temp
          FROM calc_temperature_data
         WHERE date BETWEEN :start_date AND :end_date
         ORDER BY date
        """
    )
    results = session.execute(stmt, {"start_date": start_date, "end_date": end_date}).all()
    if results:
        print("-" * 30)
        print(f"查询成功！共找到 {len(results)} 条记录:")
        for row in results:
            print(f"  -> 日期: {row[0]}, 平均气温: {row[1]}")
        print("-" * 30)
    else:
        print(f"在范围 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 内未找到数据。")

def main():
    """主函数，提示用户并获取数据。"""
    print("\n===== 平均气温数据查询测试脚本 =====")
    
    choice = input("请选择查询类型：\n  (s) 查询单个日期\n  (r) 查询日期范围\n请输入 [s/r]: ").lower().strip()

    # 创建数据库会话
    session = SessionLocal()
    try:
        if choice == 's':
            date_str = input("请输入要查询的日期 (格式 YYYY-MM-DD): ").strip()
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                fetch_single_date(session, target_date)
            except ValueError:
                print("\n错误：日期格式不正确，请输入 YYYY-MM-DD 格式。")
        
        elif choice == 'r':
            start_str = input("请输入开始日期 (格式 YYYY-MM-DD): ").strip()
            end_str = input("请输入结束日期 (格式 YYYY-MM-DD): ").strip()
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                if start_date > end_date:
                    print("\n错误：开始日期不能晚于结束日期。")
                else:
                    fetch_date_range(session, start_date, end_date)
            except ValueError:
                print("\n错误：日期格式不正确，请输入 YYYY-MM-DD 格式。")
        
        else:
            print("\n错误：无效的选项，请输入 's' 或 'r'。")

    finally:
        # 确保无论如何都关闭会话
        session.close()
        print("\n数据库连接已关闭。")

if __name__ == "__main__":
    main()
