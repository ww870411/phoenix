"""
辽宁电力现货15分钟数据及机组售电量填报模型。

对应数据库表：public.spot_electricity_15min_data
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    BigInteger,
    Numeric,
    Text,
    String,
    UniqueConstraint,
    func,
)
from backend.db.database_daily_report_25_26 import Base


class SpotElectricity15MinData(Base):
    """辽宁电力现货15分钟电价与机组售电量填报表 ORM 模型。"""

    __tablename__ = "spot_electricity_15min_data"
    __table_args__ = (
        UniqueConstraint("trade_date", "point_index", name="uq_spot_electricity_date_point"),
        {"schema": "public"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键")
    trade_date = Column(Date, nullable=False, index=True, comment="交易日期 (YYYY-MM-DD)")
    point_index = Column(Integer, nullable=False, comment="时点序号 (1-96)")
    time_label = Column(String(10), nullable=False, comment="官方时刻 (00:15-24:00)")
    period_start_time = Column(String(8), comment="时段起始时刻 (HH:MM:SS)")
    period_end_time = Column(String(8), comment="时段结束时刻 (HH:MM:SS)")

    # 现货市场电价 (单位：元/兆瓦时)
    day_ahead_price = Column(Numeric(10, 4), comment="日前电价 (元/兆瓦时)")
    real_time_price = Column(Numeric(10, 4), comment="实时电价 (元/兆瓦时)")
    price_spread = Column(Numeric(10, 4), comment="现货价差：实时电价 - 日前电价 (元/兆瓦时)")

    # 北海热电厂发电机组售电量 (1-3号机组，单位：兆瓦时 MWh)
    beihai_unit1_sales = Column(Numeric(12, 4), comment="北海热电厂 #1 机组售电量 (MWh)")
    beihai_unit2_sales = Column(Numeric(12, 4), comment="北海热电厂 #2 机组售电量 (MWh)")
    beihai_unit3_sales = Column(Numeric(12, 4), comment="北海热电厂 #3 机组售电量 (MWh)")
    beihai_total_sales = Column(Numeric(12, 4), comment="北海热电厂售电量合计 (MWh)")

    # 香海热电厂发电机组售电量 (1-4号机组，单位：兆瓦时 MWh)
    xianghai_unit1_sales = Column(Numeric(12, 4), comment="香海热电厂 #1 机组售电量 (MWh)")
    xianghai_unit2_sales = Column(Numeric(12, 4), comment="香海热电厂 #2 机组售电量 (MWh)")
    xianghai_unit3_sales = Column(Numeric(12, 4), comment="香海热电厂 #3 机组售电量 (MWh)")
    xianghai_unit4_sales = Column(Numeric(12, 4), comment="香海热电厂 #4 机组售电量 (MWh)")
    xianghai_total_sales = Column(Numeric(12, 4), comment="香海热电厂售电量合计 (MWh)")

    # 全省售电量、两厂总售电量与预估现货收益
    province_total_sales = Column(Numeric(14, 4), comment="全省该时段售电量 (MWh)")
    total_power_sales = Column(Numeric(12, 4), comment="两厂总售电量合计 (MWh)")
    estimated_revenue = Column(Numeric(14, 4), comment="预估现货售电收益 (元)")

    # 数据填报状态与审计字段
    status = Column(String(20), nullable=False, default="raw", comment="数据填报状态: raw/draft/submitted/locked")
    remarks = Column(Text, comment="填报备注或异常情况说明")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="记录创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="记录更新时间")
