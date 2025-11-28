
"""SQLAlchemy session and ORM models for daily_report_25_26."""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/phoenix",
)

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40,
    pool_timeout=60,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


class DailyBasicData(Base):
    __tablename__ = "daily_basic_data"

    id = Column(Integer, primary_key=True)
    company = Column(Text, nullable=False)
    company_cn = Column(Text)
    sheet_name = Column(Text, nullable=False)
    item = Column(Text, nullable=False)
    item_cn = Column(Text)
    value = Column(Numeric(18, 4))
    unit = Column(Text)
    note = Column(Text)
    date = Column(Date, nullable=False)
    status = Column(Text)
    operation_time = Column(DateTime, nullable=False)


class ConstantData(Base):
    __tablename__ = "constant_data"

    id = Column(Integer, primary_key=True)
    company = Column(Text, nullable=False)
    company_cn = Column(Text)
    sheet_name = Column(Text, nullable=False)
    item = Column(Text, nullable=False)
    item_cn = Column(Text)
    value = Column(Numeric(18, 4))
    unit = Column(Text)
    period = Column(Text, nullable=False)
    operation_time = Column(DateTime, nullable=False)


class TemperatureData(Base):
    __tablename__ = "temperature_data"

    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime, nullable=False)
    value = Column(Numeric(18, 4))
    operation_time = Column(DateTime, nullable=False)


class CoalInventoryData(Base):
    __tablename__ = "coal_inventory_data"

    id = Column(Integer, primary_key=True)
    company = Column(Text, nullable=False)
    company_cn = Column(Text)
    coal_type = Column(Text, nullable=False)
    coal_type_cn = Column(Text)
    storage_type = Column(Text)
    storage_type_cn = Column(Text)
    value = Column(Numeric(18, 4))
    unit = Column(Text)
    note = Column(Text)
    # 数据库列名已更正为 'status'
    status = Column(Text)
    date = Column(Date, nullable=False)
    operation_time = Column(DateTime, nullable=False)


class PlanAndRealMonthData(Base):
    __tablename__ = "paln_and_real_month_data"

    id = Column(Integer, primary_key=True)
    company = Column(Text, nullable=False)
    company_cn = Column(Text)
    item = Column(Text, nullable=False)
    item_cn = Column(Text)
    unit = Column(Text)
    period = Column(Text, nullable=False)
    value = Column(Numeric(18, 4))
    type = Column(Text, nullable=False)
    operation_time = Column(DateTime, nullable=False)

def get_session() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
