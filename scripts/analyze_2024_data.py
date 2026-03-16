
import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text

# 修正后的数据库连接串，数据库名为 phoenix
DB_URL = "postgresql://postgres:postgres@localhost:5432/phoenix"

def analyze_2024_data():
    engine = create_engine(DB_URL)
    
    query = text("""
        SELECT company, item, unit, value, date, type
        FROM monthly_data_show
        WHERE date >= '2024-01-01' AND date <= '2024-12-01'
    """)
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
            
        if df.empty:
            print("2024年没有任何数据。")
            return

        print(f"找到 2024 年数据 {len(df)} 行。")
        
        # 1. 检查利用率指标本身
        util_items = ["发电设备利用率", "供热设备利用率"]
        for item in util_items:
            subset = df[df['item'] == item]
            if not subset.empty:
                print(f"\n指标 [{item}] 的统计：")
                print(f"总记录数: {len(subset)}")
                print(f"非零值记录数: {len(subset[subset['value'] != 0])}")
                print(f"零值记录数: {len(subset[subset['value'] == 0])}")
            else:
                print(f"\n指标 [{item}] 在 2024 年数据中不存在。")

        # 2. 检查基础指标
        base_items = ["发电量", "发电设备容量", "供热量", "外购热量", "锅炉设备容量"]
        print("\n--- 基础指标检查 ---")
        for item in base_items:
            subset = df[df['item'] == item]
            print(f"指标 [{item}]: {len(subset)} 条记录, 平均值: {subset['value'].mean():.2f}")

    except Exception as e:
        print(f"执行查询失败: {e}")

if __name__ == "__main__":
    analyze_2024_data()
