
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:postgres@localhost:5432/phoenix"

def check_companies_2024():
    engine = create_engine(DB_URL)
    query = text("""
        SELECT DISTINCT company 
        FROM monthly_data_show 
        WHERE date >= '2024-01-01' AND date <= '2024-12-31'
    """)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        print("2024 年数据中的所有口径：")
        print(df['company'].tolist())
    except Exception as e:
        print(f"查询失败: {e}")

if __name__ == "__main__":
    check_companies_2024()
