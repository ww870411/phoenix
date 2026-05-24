-- tube 项目第一阶段数据库初始化脚本
-- 适用数据库：PostgreSQL
-- 说明：
-- 1. 本脚本会创建独立 schema：tube
-- 2. 所有 tube 项目业务表均放置在 tube schema 下
-- 3. 本脚本以 V5.1 确认版流程计划为准

BEGIN;

CREATE SCHEMA IF NOT EXISTS tube;

COMMENT ON SCHEMA tube IS '保温管物流链管理项目专用 schema';


CREATE TABLE IF NOT EXISTS tube.tube_daily_plan (
    id BIGSERIAL PRIMARY KEY,
    plan_date DATE NOT NULL,
    station_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    filled_by VARCHAR(128),
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_daily_plan_plan_qty_nonnegative
        CHECK (plan_qty >= 0)
);

COMMENT ON TABLE tube.tube_daily_plan IS '每日计划长表';
COMMENT ON COLUMN tube.tube_daily_plan.plan_date IS '计划日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_plan.plan_qty IS '计划使用量';
COMMENT ON COLUMN tube.tube_daily_plan.filled_by IS '填报人，首版为现场负责人';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_plan_date_station_model
    ON tube.tube_daily_plan (plan_date, station_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_station_date
    ON tube.tube_daily_plan (station_id, plan_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_pipe_model_date
    ON tube.tube_daily_plan (pipe_model_id, plan_date);

CREATE TABLE IF NOT EXISTS tube.tube_delivery (
    id BIGSERIAL PRIMARY KEY,
    supply_entity_id VARCHAR(64) NOT NULL,
    station_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    shipped_qty NUMERIC(18, 2) NOT NULL,
    arrived_qty NUMERIC(18, 2),
    received_qty NUMERIC(18, 2),
    shipped_at TIMESTAMPTZ NOT NULL,
    ship_contact_name VARCHAR(128),
    ship_contact_phone VARCHAR(64),
    ship_remark TEXT,
    arrived_confirm_by VARCHAR(128),
    arrived_confirm_at TIMESTAMPTZ,
    arrived_remark TEXT,
    received_confirm_by VARCHAR(128),
    received_confirm_at TIMESTAMPTZ,
    received_remark TEXT,
    warehouse_confirm_by VARCHAR(128),
    warehouse_confirm_at TIMESTAMPTZ,
    warehouse_remark TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_arrival',
    abnormal_flag BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_by VARCHAR(128),
    cancel_at TIMESTAMPTZ,
    cancel_reason TEXT,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_delivery_shipped_qty_positive
        CHECK (shipped_qty > 0),
    CONSTRAINT chk_tube_delivery_arrived_qty_range
        CHECK (arrived_qty IS NULL OR (arrived_qty >= 0 AND arrived_qty <= shipped_qty)),
    CONSTRAINT chk_tube_delivery_received_qty_range
        CHECK (
            received_qty IS NULL OR (
                received_qty >= 0
                AND received_qty <= COALESCE(arrived_qty, shipped_qty)
            )
        ),
    CONSTRAINT chk_tube_delivery_status
        CHECK (
            status IN (
                'pending_arrival',
                'cancelled',
                'pending_receive',
                'pending_warehouse',
                'completed'
            )
        )
);

COMMENT ON TABLE tube.tube_delivery IS '发货、到货、施工接收、库管确认生命周期主表';
COMMENT ON COLUMN tube.tube_delivery.supply_entity_id IS '供给主体 ID，对应 tube_config.json 中 supply_entities';
COMMENT ON COLUMN tube.tube_delivery.station_id IS '换热站 ID';
COMMENT ON COLUMN tube.tube_delivery.pipe_model_id IS '保温管型号 ID';
COMMENT ON COLUMN tube.tube_delivery.shipped_qty IS '发货数量';
COMMENT ON COLUMN tube.tube_delivery.arrived_qty IS '到货确认数量，允许小于发货数量';
COMMENT ON COLUMN tube.tube_delivery.received_qty IS '施工接收数量，允许小于到货确认数量';
COMMENT ON COLUMN tube.tube_delivery.status IS '状态：pending_arrival/cancelled/pending_receive/pending_warehouse/completed';
COMMENT ON COLUMN tube.tube_delivery.abnormal_flag IS '是否异常';
COMMENT ON COLUMN tube.tube_delivery.cancel_reason IS '发货撤销原因，仅允许在已发货待到货状态使用';

CREATE INDEX IF NOT EXISTS idx_tube_delivery_status
    ON tube.tube_delivery (status);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_station
    ON tube.tube_delivery (station_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_supply_entity
    ON tube.tube_delivery (supply_entity_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_pipe_model
    ON tube.tube_delivery (pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_shipped_at
    ON tube.tube_delivery (shipped_at);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_station_status
    ON tube.tube_delivery (station_id, status);

CREATE TABLE IF NOT EXISTS tube.tube_daily_usage (
    id BIGSERIAL PRIMARY KEY,
    usage_date DATE NOT NULL,
    station_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    usage_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    filled_by VARCHAR(128),
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_daily_usage_usage_qty_nonnegative
        CHECK (usage_qty >= 0)
);

COMMENT ON TABLE tube.tube_daily_usage IS '每日实际使用长表';
COMMENT ON COLUMN tube.tube_daily_usage.usage_date IS '实际使用日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_usage.usage_qty IS '实际使用量';
COMMENT ON COLUMN tube.tube_daily_usage.filled_by IS '填报人，首版为现场负责人';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_usage_date_station_model
    ON tube.tube_daily_usage (usage_date, station_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_station_date
    ON tube.tube_daily_usage (station_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_pipe_model_date
    ON tube.tube_daily_usage (pipe_model_id, usage_date);

CREATE TABLE IF NOT EXISTS tube.tube_inventory_adjustment (
    id BIGSERIAL PRIMARY KEY,
    adjust_date DATE NOT NULL,
    station_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    adjust_qty NUMERIC(18, 2) NOT NULL,
    adjust_type VARCHAR(32) NOT NULL,
    reason TEXT NOT NULL,
    operated_by VARCHAR(128),
    operated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    CONSTRAINT chk_tube_inventory_adjustment_nonzero
        CHECK (adjust_qty <> 0)
);

COMMENT ON TABLE tube.tube_inventory_adjustment IS '库存调整预留表';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_qty IS '调整数量，正数增加，负数减少';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_type IS '调整类型，如盘盈、盘亏、退库、调剂、破损、纠错';
COMMENT ON COLUMN tube.tube_inventory_adjustment.reason IS '调整原因';

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_station_date
    ON tube.tube_inventory_adjustment (station_id, adjust_date);

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_pipe_model_date
    ON tube.tube_inventory_adjustment (pipe_model_id, adjust_date);

COMMIT;
