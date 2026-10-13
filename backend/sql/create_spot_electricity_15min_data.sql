-- ==============================================================================
-- 辽宁电力现货15分钟数据表 (public.spot_electricity_15min_data)
-- 适用场景：
-- 1. 存储辽宁省电力现货市场 15 分钟“日前电价”与“实时电价” (2026年及后续年份)
-- 2. 支持电厂每日每 15 分钟填报发电机组售电量数据：
--    - 北海热电厂 (1#、2#、3#机组及合计)
--    - 香海热电厂 (1#、2#、3#、4#机组及合计)
-- 3. 预留价差、总售电量、现货预估收益、填报状态与审计留痕字段
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.spot_electricity_15min_data (
    -- 1. 主键与时间序列标识
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,                                       -- 交易日期 (如 2026-01-01)
    point_index INTEGER NOT NULL,                                   -- 时点序号 (1 至 96)
    time_label VARCHAR(10) NOT NULL,                                -- 官方时刻标签 (00:15 至 24:00)
    period_start_time VARCHAR(8),                                   -- 时段起始时刻 (如 00:00:00)
    period_end_time VARCHAR(8),                                     -- 时段结束时刻 (如 00:15:00)

    -- 2. 现货市场电价指标 (单位：元/兆瓦时，支持负电价与浮点精度)
    day_ahead_price NUMERIC(10, 4),                                 -- 日前电价 (元/兆瓦时)
    real_time_price NUMERIC(10, 4),                                 -- 实时电价 (元/兆瓦时)
    price_spread NUMERIC(10, 4),                                    -- 现货价差 (实时电价 - 日前电价，元/兆瓦时)

    -- 3. 北海热电厂售电量 (1-3号机组，单位：兆瓦时 MWh)
    beihai_unit1_sales NUMERIC(12, 4),                              -- 北海热电厂 #1 机组售电量
    beihai_unit2_sales NUMERIC(12, 4),                              -- 北海热电厂 #2 机组售电量
    beihai_unit3_sales NUMERIC(12, 4),                              -- 北海热电厂 #3 机组售电量
    beihai_total_sales NUMERIC(12, 4),                              -- 北海热电厂售电量合计

    -- 4. 香海热电厂售电量 (1-4号机组，单位：兆瓦时 MWh)
    xianghai_unit1_sales NUMERIC(12, 4),                            -- 香海热电厂 #1 机组售电量
    xianghai_unit2_sales NUMERIC(12, 4),                            -- 香海热电厂 #2 机组售电量
    xianghai_unit3_sales NUMERIC(12, 4),                            -- 香海热电厂 #3 机组售电量
    xianghai_unit4_sales NUMERIC(12, 4),                            -- 香海热电厂 #4 机组售电量
    xianghai_total_sales NUMERIC(12, 4),                            -- 香海热电厂售电量合计

    -- 5. 全省与两厂售电量及财务收益预估
    province_total_sales NUMERIC(14, 4),                            -- 全省该时段售电量 (MWh)
    total_power_sales NUMERIC(12, 4),                               -- 两电厂总售电量合计 (MWh)
    estimated_revenue NUMERIC(14, 4),                               -- 预估现货售电收益 (元)

    -- 6. 填报状态与审计追踪
    status VARCHAR(20) NOT NULL DEFAULT 'raw',                      -- 状态: raw(仅电价), draft(填报中), submitted(已提交), locked(已封存)
    remarks TEXT,                                                   -- 填报备注或异常情况说明
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 数据创建时间
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 数据最后更新时间

    -- 唯一约束：确保每个交易日期的 96 个时点唯一
    CONSTRAINT uq_spot_electricity_date_point UNIQUE (trade_date, point_index)
);

-- 表与字段中文注释 (便于数据库运维与 BI 分析)
COMMENT ON TABLE public.spot_electricity_15min_data IS '辽宁省电力现货市场15分钟电价与电厂机组售电量填报数据表';
COMMENT ON COLUMN public.spot_electricity_15min_data.id IS '自增主键';
COMMENT ON COLUMN public.spot_electricity_15min_data.trade_date IS '交易日期';
COMMENT ON COLUMN public.spot_electricity_15min_data.point_index IS '时点序号 (1-96)';
COMMENT ON COLUMN public.spot_electricity_15min_data.time_label IS '官方时刻 (00:15-24:00)';
COMMENT ON COLUMN public.spot_electricity_15min_data.period_start_time IS '时段起始时刻 (HH:MM:SS)';
COMMENT ON COLUMN public.spot_electricity_15min_data.period_end_time IS '时段结束时刻 (HH:MM:SS)';
COMMENT ON COLUMN public.spot_electricity_15min_data.day_ahead_price IS '日前电价 (元/兆瓦时)';
COMMENT ON COLUMN public.spot_electricity_15min_data.real_time_price IS '实时电价 (元/兆瓦时)';
COMMENT ON COLUMN public.spot_electricity_15min_data.price_spread IS '现货价差：实时电价 - 日前电价 (元/兆瓦时)';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit1_sales IS '北海热电厂 #1 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit2_sales IS '北海热电厂 #2 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit3_sales IS '北海热电厂 #3 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_total_sales IS '北海热电厂售电量合计 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit1_sales IS '香海热电厂 #1 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit2_sales IS '香海热电厂 #2 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit3_sales IS '香海热电厂 #3 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit4_sales IS '香海热电厂 #4 机组售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_total_sales IS '香海热电厂售电量合计 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.province_total_sales IS '全省该时段售电量 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.total_power_sales IS '两厂总售电量合计 (MWh)';
COMMENT ON COLUMN public.spot_electricity_15min_data.estimated_revenue IS '预估现货售电收益 (元)';
COMMENT ON COLUMN public.spot_electricity_15min_data.status IS '数据填报状态: raw(初始导入), draft(填报中), submitted(已提交), locked(已封存)';
COMMENT ON COLUMN public.spot_electricity_15min_data.remarks IS '填报备注或异常情况说明';
COMMENT ON COLUMN public.spot_electricity_15min_data.created_at IS '记录创建时间';
COMMENT ON COLUMN public.spot_electricity_15min_data.updated_at IS '记录更新时间';

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_spot_elec_trade_date ON public.spot_electricity_15min_data (trade_date);
CREATE INDEX IF NOT EXISTS idx_spot_elec_date_point ON public.spot_electricity_15min_data (trade_date, point_index);
CREATE INDEX IF NOT EXISTS idx_spot_elec_status ON public.spot_electricity_15min_data (status);
