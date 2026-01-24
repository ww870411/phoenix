
import os
import sys
from sqlalchemy import create_engine, text, or_, and_
from sqlalchemy.orm import sessionmaker
from backend.db.database_daily_report_25_26 import CoalInventoryData, DailyBasicData
from backend.services.auth_manager import auth_manager

# Setup DB connection
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/phoenix"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

def check_coal_data():
    biz_date = auth_manager.current_biz_date()
    print(f"Checking data for date: {biz_date}")

    # 1. Check raw data count
    total = session.query(CoalInventoryData).filter(CoalInventoryData.date == biz_date).count()
    print(f"Total raw records: {total}")

    # 2. Check null values
    null_val = session.query(CoalInventoryData).filter(
        CoalInventoryData.date == biz_date,
        CoalInventoryData.value.is_(None)
    ).count()
    print(f"Records with value IS NULL: {null_val}")

    # 3. Check records satisfying the filter
    valid_q = session.query(CoalInventoryData).filter(
        CoalInventoryData.date == biz_date,
        or_(
            CoalInventoryData.value.isnot(None),
            and_(CoalInventoryData.note.isnot(None), CoalInventoryData.note != "")
        )
    )
    valid_count = valid_q.count()
    print(f"Records passing filter: {valid_count}")

    # 4. Check distinct count
    distinct_count = session.query(
        CoalInventoryData.company,
        CoalInventoryData.coal_type
    ).filter(
        CoalInventoryData.date == biz_date,
        or_(
            CoalInventoryData.value.isnot(None),
            and_(CoalInventoryData.note.isnot(None), CoalInventoryData.note != "")
        )
    ).distinct().count()
    print(f"Distinct (company, coal_type) count: {distinct_count}")

    # 5. Sample distinct items
    if distinct_count > 0:
        print("Sample valid items:")
        rows = valid_q.limit(5).all()
        for r in rows:
            print(f"  - Comp: {r.company}, Coal: {r.coal_type}, Storage: {r.storage_type}, Val: {r.value}, Note: {r.note}")

if __name__ == "__main__":
    try:
        check_coal_data()
    finally:
        session.close()
