-- ==============================================================================
-- 保温管物流供需管理系统 (Insulation Pipe Supply 2026) 数据库初始化脚本
-- 适用数据库：PostgreSQL 12+
-- Schema: tube, logs
-- 说明：
-- 1. 本脚本包含 tube schema 下全部 11 张业务表及 logs schema 审计日志表的完整定义；
-- 2. 包含完整的物理主键约束 (PRIMARY KEY)、自增序列 (BIGSERIAL/SERIAL)、CHECK 校验约束、UNIQUE 索引与常用检索索引；
-- 3. 包含完整的表级与字段级中文注释 (COMMENT) 以及 GIS 初始化种子数据。
-- ==============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 0. Schema 创建
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS tube;
COMMENT ON SCHEMA tube IS '保温管物流供需管理项目业务数据专用 schema';

CREATE SCHEMA IF NOT EXISTS logs;
COMMENT ON SCHEMA logs IS '保温管物流供需管理项目操作与审计日志专用 schema';


-- -----------------------------------------------------------------------------
-- 1. 保温直管每日计划表 (tube.tube_daily_plan)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_daily_plan (
    id BIGSERIAL PRIMARY KEY,
    plan_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
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

COMMENT ON TABLE tube.tube_daily_plan IS '保温直管每日计划长表';
COMMENT ON COLUMN tube.tube_daily_plan.id IS '自增主键';
COMMENT ON COLUMN tube.tube_daily_plan.plan_date IS '计划日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_plan.section_1_id IS '需求主体/标段标识 (如 low_lot_1, high_lot_1)';
COMMENT ON COLUMN tube.tube_daily_plan.pipe_model_id IS '直管型号规格 (如 Φ1120×13/Φ1260×16)';
COMMENT ON COLUMN tube.tube_daily_plan.plan_qty IS '计划使用量 (米)';
COMMENT ON COLUMN tube.tube_daily_plan.filled_by IS '填报人账号';
COMMENT ON COLUMN tube.tube_daily_plan.filled_at IS '填报提交时间戳';
COMMENT ON COLUMN tube.tube_daily_plan.remark IS '说明备注';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_plan_date_section_1_model
    ON tube.tube_daily_plan (plan_date, section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_section_1_date
    ON tube.tube_daily_plan (section_1_id, plan_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_pipe_model_date
    ON tube.tube_daily_plan (pipe_model_id, plan_date);


-- -----------------------------------------------------------------------------
-- 2. 保温直管发货、到货、施工接收与库管确认生命周期主表 (tube.tube_delivery)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_delivery (
    id BIGSERIAL PRIMARY KEY,
    supply_entity_id VARCHAR(64) NOT NULL,
    order_no VARCHAR(64),
    shipment_no VARCHAR(64),
    vehicle_plate_no VARCHAR(32),
    section_1_id VARCHAR(64) NOT NULL,
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
    diff_approve_by VARCHAR(128),
    diff_approve_at TIMESTAMPTZ,
    diff_approve_remark TEXT,
    is_timeout_receive BOOLEAN NOT NULL DEFAULT FALSE,
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
                'completed',
                'pending_diff_approve'
            )
        )
);

COMMENT ON TABLE tube.tube_delivery IS '直管发货、到货、施工接收、库管确认生命周期主表';
COMMENT ON COLUMN tube.tube_delivery.id IS '自增主键';
COMMENT ON COLUMN tube.tube_delivery.supply_entity_id IS '供给主体 ID，对应 tube_config.json 中 supply_entities';
COMMENT ON COLUMN tube.tube_delivery.order_no IS '订单号，由系统生成并落库，用于单条发货记录的展示、检索与统计';
COMMENT ON COLUMN tube.tube_delivery.shipment_no IS '运输车次号，由系统自动生成，用于同一车次发货记录的筛选与分组展示';
COMMENT ON COLUMN tube.tube_delivery.vehicle_plate_no IS '车牌号，按运输车次维度填报；同一 shipment_no 下保持一致';
COMMENT ON COLUMN tube.tube_delivery.section_1_id IS '需求主体/标段标识';
COMMENT ON COLUMN tube.tube_delivery.pipe_model_id IS '保温管规格型号 ID';
COMMENT ON COLUMN tube.tube_delivery.shipped_qty IS '发货数量 (米)';
COMMENT ON COLUMN tube.tube_delivery.arrived_qty IS '现场到货确认数量 (米)，允许小于等于发货数量';
COMMENT ON COLUMN tube.tube_delivery.received_qty IS '施工接收数量 (米)，允许小于等于到货确认数量';
COMMENT ON COLUMN tube.tube_delivery.status IS '单据生命周期状态：pending_arrival(待到货)/pending_receive(待接收)/pending_warehouse(待入库)/completed(已完成)/cancelled(已撤销)/pending_diff_approve(待审批)';
COMMENT ON COLUMN tube.tube_delivery.abnormal_flag IS '是否存在数量差异等异常标记';
COMMENT ON COLUMN tube.tube_delivery.cancel_reason IS '发货撤销原因，仅允许在已发货待到货状态使用';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_by IS '现场负责人（Site Manager）差异审批人账号';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_at IS '差异审批处理时间戳';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_remark IS '差异审批意见或驳回备注';
COMMENT ON COLUMN tube.tube_delivery.is_timeout_receive IS '是否因到货确认 12 小时施工未签收触发系统自动强制接收标记';

CREATE INDEX IF NOT EXISTS idx_tube_delivery_status
    ON tube.tube_delivery (status);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_supply_shipped
    ON tube.tube_delivery (supply_entity_id, shipped_at DESC);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_section_1
    ON tube.tube_delivery (section_1_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_supply_entity
    ON tube.tube_delivery (supply_entity_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_order_no
    ON tube.tube_delivery (order_no);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_shipment_no
    ON tube.tube_delivery (shipment_no);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_pipe_model
    ON tube.tube_delivery (pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_shipped_at
    ON tube.tube_delivery (shipped_at);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_section_1_status
    ON tube.tube_delivery (section_1_id, status);


-- -----------------------------------------------------------------------------
-- 3. 保温直管每日实际使用消耗表 (tube.tube_daily_usage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_daily_usage (
    id BIGSERIAL PRIMARY KEY,
    usage_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    usage_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    loss_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    filled_by VARCHAR(128),
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_daily_usage_usage_qty_nonnegative
        CHECK (usage_qty >= 0),
    CONSTRAINT chk_tube_daily_usage_loss_qty_nonnegative
        CHECK (loss_qty >= 0)
);

COMMENT ON TABLE tube.tube_daily_usage IS '保温直管每日实际使用与损耗长表';
COMMENT ON COLUMN tube.tube_daily_usage.id IS '自增主键';
COMMENT ON COLUMN tube.tube_daily_usage.usage_date IS '实际施工使用日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_usage.section_1_id IS '需求主体/标段标识';
COMMENT ON COLUMN tube.tube_daily_usage.pipe_model_id IS '保温管规格型号 ID';
COMMENT ON COLUMN tube.tube_daily_usage.usage_qty IS '实际使用消耗量 (米)';
COMMENT ON COLUMN tube.tube_daily_usage.loss_qty IS '施工损耗/废弃量 (米)';
COMMENT ON COLUMN tube.tube_daily_usage.filled_by IS '填报人账号';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_usage_date_section_1_model
    ON tube.tube_daily_usage (usage_date, section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_section_1_date
    ON tube.tube_daily_usage (section_1_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_pipe_model_date
    ON tube.tube_daily_usage (pipe_model_id, usage_date);


-- -----------------------------------------------------------------------------
-- 4. 管件发货明细与生命周期表 (tube.tube_fitting_delivery)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_fitting_delivery (
    id BIGSERIAL PRIMARY KEY,
    supply_entity_id VARCHAR(64) NOT NULL,
    shipment_no VARCHAR(64) NOT NULL,
    order_no VARCHAR(64) NOT NULL,
    vehicle_plate_no VARCHAR(32) NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
    fitting_type VARCHAR(64) NOT NULL,
    model_spec VARCHAR(128) NOT NULL,
    shipped_qty NUMERIC(18, 2) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT '个',
    shipped_at TIMESTAMPTZ NOT NULL,
    ship_contact_name VARCHAR(128),
    ship_contact_phone VARCHAR(64),
    ship_remark TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_arrival',
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    arrived_qty NUMERIC,
    arrived_confirm_at TIMESTAMPTZ,
    arrived_confirm_by TEXT,
    arrived_remark TEXT,
    received_confirm_at TIMESTAMPTZ,
    received_confirm_by TEXT,
    received_remark TEXT,
    warehouse_confirm_at TIMESTAMPTZ,
    warehouse_confirm_by TEXT,
    warehouse_remark TEXT,
    cancel_at TIMESTAMPTZ,
    cancel_by TEXT,
    cancel_reason TEXT,
    CONSTRAINT chk_tube_fitting_shipped_qty_positive
        CHECK (shipped_qty > 0),
    CONSTRAINT chk_tube_fitting_status
        CHECK (status IN ('pending_arrival', 'pending_receive', 'pending_warehouse', 'completed', 'cancelled')),
    CONSTRAINT chk_tube_fitting_state_evidence
        CHECK (
            (status = 'pending_arrival' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
            (status = 'pending_receive' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
            (status = 'pending_warehouse' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL) OR
            (status = 'completed' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NOT NULL AND cancel_at IS NULL) OR
            (status = 'cancelled' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NOT NULL)
        )
);

COMMENT ON TABLE tube.tube_fitting_delivery IS '管件及附件发货、到货、施工接收与库管确认生命周期表';
COMMENT ON COLUMN tube.tube_fitting_delivery.id IS '自增主键';
COMMENT ON COLUMN tube.tube_fitting_delivery.supply_entity_id IS '供给主体标识';
COMMENT ON COLUMN tube.tube_fitting_delivery.shipment_no IS '管件发货车次号 (如 SSB-260822-001)';
COMMENT ON COLUMN tube.tube_fitting_delivery.order_no IS '管件明细订单号 (如 OSB-L1-260822-001)';
COMMENT ON COLUMN tube.tube_fitting_delivery.vehicle_plate_no IS '发货车牌号';
COMMENT ON COLUMN tube.tube_fitting_delivery.section_1_id IS '需求主体/标段标识';
COMMENT ON COLUMN tube.tube_fitting_delivery.fitting_type IS '管件物理类别 (弯头、三通、球阀、异径管、补偿器等)';
COMMENT ON COLUMN tube.tube_fitting_delivery.model_spec IS '管件规格型号描述';
COMMENT ON COLUMN tube.tube_fitting_delivery.shipped_qty IS '发货数量';
COMMENT ON COLUMN tube.tube_fitting_delivery.unit IS '计量单位 (默认: 个)';
COMMENT ON COLUMN tube.tube_fitting_delivery.status IS '状态: pending_arrival(待到货)/pending_receive(待接收)/pending_warehouse(待入库)/completed(已完成)/cancelled(已撤销)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_delivery_order_no
    ON tube.tube_fitting_delivery (order_no);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipment_no
    ON tube.tube_fitting_delivery (shipment_no);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_section_1_status
    ON tube.tube_fitting_delivery (section_1_id, status);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipped_at
    ON tube.tube_fitting_delivery (shipped_at);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_supply_entity
    ON tube.tube_fitting_delivery (supply_entity_id);


-- -----------------------------------------------------------------------------
-- 5. 管件每日现场消耗记录表 (tube.tube_fitting_daily_usage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_fitting_daily_usage (
    id BIGSERIAL PRIMARY KEY,
    project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    section_1_id VARCHAR(64) NOT NULL,
    usage_date DATE NOT NULL,
    fitting_type VARCHAR(64) NOT NULL,
    model_spec VARCHAR(255) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT '个',
    usage_qty INTEGER NOT NULL,
    remark TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    cancel_reason TEXT,
    cancelled_by VARCHAR(64),
    cancelled_at TIMESTAMPTZ,
    filled_by VARCHAR(64) NOT NULL,
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(64),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_fitting_daily_usage_qty_positive
        CHECK (usage_qty > 0)
);

COMMENT ON TABLE tube.tube_fitting_daily_usage IS '管件每日现场安装使用消耗记录表';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.id IS '自增主键';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.section_1_id IS '需求主体/标段标识';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.usage_date IS '施工消耗日期';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.fitting_type IS '管件类型';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.model_spec IS '规格型号';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.usage_qty IS '消耗数量 (整数量)';
COMMENT ON COLUMN tube.tube_fitting_daily_usage.status IS '状态: active(有效)/cancelled(已撤销)';

CREATE INDEX IF NOT EXISTS idx_tube_fitting_daily_usage_sec_date
    ON tube.tube_fitting_daily_usage (section_1_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_daily_usage_status
    ON tube.tube_fitting_daily_usage (status);


-- -----------------------------------------------------------------------------
-- 6. 保温直管工程基准表 (tube.tube_pipe_baseline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_pipe_baseline (
    id BIGSERIAL PRIMARY KEY,
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(128) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT '米',
    design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    remark TEXT,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_pipe_baseline_qty_nonnegative 
        CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
);

COMMENT ON TABLE tube.tube_pipe_baseline IS '保温直管设计量与计划采购量基准表';
COMMENT ON COLUMN tube.tube_pipe_baseline.id IS '自增主键';
COMMENT ON COLUMN tube.tube_pipe_baseline.section_1_id IS '需求主体/标段标识 (如 high_lot_1, low_lot_2)';
COMMENT ON COLUMN tube.tube_pipe_baseline.pipe_model_id IS '直管型号规格 (如 Φ1120×13/Φ1260×16)';
COMMENT ON COLUMN tube.tube_pipe_baseline.unit IS '计量单位 (默认 米)';
COMMENT ON COLUMN tube.tube_pipe_baseline.design_qty IS '设计使用总量 (根据设计图纸核定)';
COMMENT ON COLUMN tube.tube_pipe_baseline.purchase_plan_qty IS '计划采购总量 (核准的采购/供货额度)';
COMMENT ON COLUMN tube.tube_pipe_baseline.remark IS '说明备注';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_pipe_baseline_sec_model 
    ON tube.tube_pipe_baseline (section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_pipe_baseline_sec 
    ON tube.tube_pipe_baseline (section_1_id);

CREATE INDEX IF NOT EXISTS idx_tube_pipe_baseline_model 
    ON tube.tube_pipe_baseline (pipe_model_id);


-- -----------------------------------------------------------------------------
-- 7. 管件与物料工程基准表 (tube.tube_fitting_baseline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_fitting_baseline (
    id BIGSERIAL PRIMARY KEY,
    section_1_id VARCHAR(64) NOT NULL,
    system_type VARCHAR(32) NOT NULL DEFAULT '高温水',
    category VARCHAR(64) NOT NULL DEFAULT '管件',
    standard_name VARCHAR(128) NOT NULL DEFAULT '',
    model_spec VARCHAR(255) NOT NULL,
    sub_model_spec VARCHAR(128) NOT NULL DEFAULT '',
    unit VARCHAR(32) NOT NULL DEFAULT '个',
    design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    main_dn NUMERIC(10, 2),
    sub_dn NUMERIC(10, 2),
    angle NUMERIC(10, 2),
    bending_radius_ratio NUMERIC(10, 2),
    bending_radius_m NUMERIC(10, 2),
    valve_model VARCHAR(128),
    outer_diameter NUMERIC(10, 2),
    wall_thickness NUMERIC(10, 2),
    length_m NUMERIC(10, 2),
    pressure_rating VARCHAR(64),
    compensation_mm NUMERIC(10, 2),
    flow_direction VARCHAR(64),
    raw_model_spec VARCHAR(255),
    raw_name VARCHAR(128),
    remark TEXT,
    extra_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_fitting_baseline_qty_nonnegative 
        CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
);

COMMENT ON TABLE tube.tube_fitting_baseline IS '管件与标准化物料设计量与计划采购量基准表';
COMMENT ON COLUMN tube.tube_fitting_baseline.id IS '自增主键';
COMMENT ON COLUMN tube.tube_fitting_baseline.section_1_id IS '需求主体/标段标识 (如 high_lot_1)';
COMMENT ON COLUMN tube.tube_fitting_baseline.system_type IS '系统类型 (如 高温水 / 低温水)';
COMMENT ON COLUMN tube.tube_fitting_baseline.category IS '物理类别 (如 弯头、三通、球阀、异径管、补偿器、钢管等)';
COMMENT ON COLUMN tube.tube_fitting_baseline.standard_name IS '标准名称 (如 塑套钢预制保温弯头、直埋焊接球阀)';
COMMENT ON COLUMN tube.tube_fitting_baseline.model_spec IS '原始型号规格 (如 90° DN1100 R=1.5DN、DN1100/DN600)';
COMMENT ON COLUMN tube.tube_fitting_baseline.sub_model_spec IS '子型号/细分规格 (如 90°、45°、顺水 等，无则为空字符串)';
COMMENT ON COLUMN tube.tube_fitting_baseline.unit IS '计量单位 (如 个、套、台、根、米)';
COMMENT ON COLUMN tube.tube_fitting_baseline.design_qty IS '设计使用总量 (根据设计图纸核定)';
COMMENT ON COLUMN tube.tube_fitting_baseline.purchase_plan_qty IS '计划采购总量 (核准的采购/供货额度)';
COMMENT ON COLUMN tube.tube_fitting_baseline.main_dn IS '主径DN (如 1100, 1000)';
COMMENT ON COLUMN tube.tube_fitting_baseline.sub_dn IS '次径DN (三通/变径支管口径)';
COMMENT ON COLUMN tube.tube_fitting_baseline.angle IS '角度(°) (弯头/弯管角度)';
COMMENT ON COLUMN tube.tube_fitting_baseline.bending_radius_ratio IS '弯曲半径倍数 (如 1.5, 3.0)';
COMMENT ON COLUMN tube.tube_fitting_baseline.bending_radius_m IS '弯曲半径(m) (如 138.7)';
COMMENT ON COLUMN tube.tube_fitting_baseline.valve_model IS '阀门型号 (如 Q61F-16C)';
COMMENT ON COLUMN tube.tube_fitting_baseline.outer_diameter IS '外径Φ(mm) (钢管/直管专用)';
COMMENT ON COLUMN tube.tube_fitting_baseline.wall_thickness IS '壁厚(mm) (钢管/直管专用)';
COMMENT ON COLUMN tube.tube_fitting_baseline.length_m IS '长度(m) (弯管专用)';
COMMENT ON COLUMN tube.tube_fitting_baseline.pressure_rating IS '公称压力/压力等级 (如 2.5MPa, PN1.6)';
COMMENT ON COLUMN tube.tube_fitting_baseline.compensation_mm IS '补偿量(mm) (补偿器专用)';
COMMENT ON COLUMN tube.tube_fitting_baseline.flow_direction IS '流向/方向 (如 单正, 单反, 双向)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_baseline_sec_sys_name_spec_sub 
    ON tube.tube_fitting_baseline (section_1_id, system_type, standard_name, model_spec, sub_model_spec);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_sec_sys 
    ON tube.tube_fitting_baseline (section_1_id, system_type);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_category 
    ON tube.tube_fitting_baseline (category);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_standard_name 
    ON tube.tube_fitting_baseline (standard_name);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_main_dn 
    ON tube.tube_fitting_baseline (main_dn);


-- -----------------------------------------------------------------------------
-- 8. 库存调整记录表 (tube.tube_inventory_adjustment)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_inventory_adjustment (
    id BIGSERIAL PRIMARY KEY,
    adjust_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
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

COMMENT ON TABLE tube.tube_inventory_adjustment IS '管材库存手工盘点与调整预留表';
COMMENT ON COLUMN tube.tube_inventory_adjustment.id IS '自增主键';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_qty IS '调整数量，正数增加，负数减少';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_type IS '调整类型，如盘盈、盘亏、退库、调剂、破损、纠错';
COMMENT ON COLUMN tube.tube_inventory_adjustment.reason IS '调整原因详细说明';

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_section_1_date
    ON tube.tube_inventory_adjustment (section_1_id, adjust_date);

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_pipe_model_date
    ON tube.tube_inventory_adjustment (pipe_model_id, adjust_date);


-- -----------------------------------------------------------------------------
-- 9. 大连主城区日级气象数据表 (tube.tube_weather_daily)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_weather_daily (
    id BIGSERIAL PRIMARY KEY,
    weather_date DATE NOT NULL,
    weather_code INTEGER NOT NULL DEFAULT 0,
    rain_sum NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    uv_index_max NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    temp_max NUMERIC(18, 2),
    temp_mean NUMERIC(18, 2),
    temp_min NUMERIC(18, 2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_weather_daily IS '大连主城区日级气象数据及施工决策聚合表';
COMMENT ON COLUMN tube.tube_weather_daily.weather_date IS '气象日期';
COMMENT ON COLUMN tube.tube_weather_daily.weather_code IS 'WMO 天气状态码';
COMMENT ON COLUMN tube.tube_weather_daily.rain_sum IS '日降水总量 (mm)';
COMMENT ON COLUMN tube.tube_weather_daily.uv_index_max IS '最大紫外线指数';
COMMENT ON COLUMN tube.tube_weather_daily.temp_max IS '日内最高气温 (℃)';
COMMENT ON COLUMN tube.tube_weather_daily.temp_mean IS '日内算术平均气温 (℃)';
COMMENT ON COLUMN tube.tube_weather_daily.temp_min IS '日内最低气温 (℃)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_daily_date
    ON tube.tube_weather_daily (weather_date);


-- -----------------------------------------------------------------------------
-- 10. 大连主城区逐小时气温原始数据表 (tube.tube_weather_hourly)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_weather_hourly (
    id BIGSERIAL PRIMARY KEY,
    weather_date_time TIMESTAMPTZ NOT NULL,
    temperature NUMERIC(18, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_weather_hourly IS '大连主城区逐小时气温原始数据表';
COMMENT ON COLUMN tube.tube_weather_hourly.weather_date_time IS '日期时间粒度 (带时区)';
COMMENT ON COLUMN tube.tube_weather_hourly.temperature IS '逐小时气温 (℃)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_hourly_datetime
    ON tube.tube_weather_hourly (weather_date_time);


-- -----------------------------------------------------------------------------
-- 11. GIS 地图标注点位存储表 (tube.tube_gis)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_gis (
    id BIGSERIAL PRIMARY KEY,
    project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    marker_type VARCHAR(32) NOT NULL DEFAULT 'weld',
    section_name VARCHAR(128),
    pipeline_name VARCHAR(128) NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    lng NUMERIC(12, 6) NOT NULL,
    lat NUMERIC(12, 6) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'passed',
    spec VARCHAR(128),
    remarks TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    parent_code VARCHAR(64),
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_gis IS '管网焊口、三通、补偿器、弯头、阀门与表计 GIS 地图标注点位存储表';
COMMENT ON COLUMN tube.tube_gis.project_key IS '项目标识';
COMMENT ON COLUMN tube.tube_gis.marker_type IS '标注点位类型: weld (焊口) / meter (表计) / tee (三通) / compensator (补偿器) / elbow (弯头) / valve (阀门)';
COMMENT ON COLUMN tube.tube_gis.section_name IS '工程施工标段名称 (如: 标段1, 标段2)';
COMMENT ON COLUMN tube.tube_gis.pipeline_name IS '管线名称/编号，同一名称管线自动连成轨迹';
COMMENT ON COLUMN tube.tube_gis.code IS '点位唯一编号/标识 (如 W-DL-001 或 T-DL-001)';
COMMENT ON COLUMN tube.tube_gis.name IS '点位名称或地理描述';
COMMENT ON COLUMN tube.tube_gis.lng IS '高德地图精准经度坐标 Lng (保留6位小数)';
COMMENT ON COLUMN tube.tube_gis.lat IS '高德地图精准纬度坐标 Lat (保留6位小数)';
COMMENT ON COLUMN tube.tube_gis.status IS '状态: passed(合格)/pending(待探伤)/failed(待复焊) 或 normal(正常)/warning(预警)/closed(关闭)/open(开启)';
COMMENT ON COLUMN tube.tube_gis.spec IS '关联保温管规格型号 (如 DN400 预制直埋保温管)';
COMMENT ON COLUMN tube.tube_gis.remarks IS '备注说明与质检记录';
COMMENT ON COLUMN tube.tube_gis.sort_order IS '连线/管线节点排序号';
COMMENT ON COLUMN tube.tube_gis.parent_code IS '上级节点编号 (仅焊口设定，指向上一焊口或三通节点；若多个焊口指向同一三通则自动分出多条路线)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_gis_project_code
    ON tube.tube_gis (project_key, code);

CREATE INDEX IF NOT EXISTS idx_tube_gis_section
    ON tube.tube_gis (project_key, section_name);

CREATE INDEX IF NOT EXISTS idx_tube_gis_pipeline
    ON tube.tube_gis (project_key, pipeline_name);

CREATE INDEX IF NOT EXISTS idx_tube_gis_marker_type
    ON tube.tube_gis (project_key, marker_type);

-- GIS 初始化种子数据 (大连香炉礁供暖管网示例)
INSERT INTO tube.tube_gis 
(project_key, marker_type, section_name, pipeline_name, code, name, lng, lat, status, spec, remarks, sort_order, parent_code)
VALUES
('insulation_pipe_supply_2026', 'meter', '标段1', '香炉礁供暖主干线', 'M-DL-001', '香炉礁热电厂出口主热表', 121.602771, 38.927491, 'normal', 'DN400 高精度热网流量计', '厂区主热源出口总监测表计', 1, NULL),
('insulation_pipe_supply_2026', 'valve', '标段1', '香炉礁供暖主干线', 'V-DL-001', '1号主供水切断阀门', 121.603771, 38.927891, 'open', 'DN400 蝶阀电动执行机构', '厂外主供水管网控制阀', 2, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-001', '香炉礁热电厂出厂1号焊口', 121.604771, 38.928491, 'passed', 'DN400 预制直埋保温管', '大连热力施工组：探伤100%合格签认', 3, NULL),
('insulation_pipe_supply_2026', 'elbow', '标段1', '香炉礁供暖主干线', 'E-DL-001', '香工街转角弯头节点', 121.606771, 38.929891, 'normal', 'DN400 90度无缝冲压弯头', '香工街拐弯转向管道节点', 4, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-002', '香工街沿线2号对接焊口', 121.608771, 38.931491, 'pending', 'DN400 预制直埋保温管', '氩弧打底完成，等待安监质检组探伤', 5, 'W-DL-001'),
('insulation_pipe_supply_2026', 'tee', '标段1', '香炉礁供暖主干线', 'T-DL-001', '香工街与香周路分叉三通', 121.610771, 38.933491, 'normal', 'DN400/DN300 异径无缝三通', '关键管网分叉节点，引出香周路分支', 6, 'W-DL-002'),
('insulation_pipe_supply_2026', 'compensator', '标段1', '香炉礁供暖主干线', 'C-DL-001', '主线轴向波纹管补偿器', 121.611771, 38.934491, 'normal', 'DN400 轴向外压波纹补偿器', '吸收管线热膨胀伸缩应力', 7, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-003', '东北路交汇末端合拢焊口', 121.613771, 38.936491, 'passed', 'DN400 预制直埋保温管', '主干线施工完工合拢焊口', 8, 'T-DL-001'),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-004', '香周路分支1号对接焊口', 121.613271, 38.931891, 'passed', 'DN300 预制直埋保温管', '三通分支引出首段焊口', 9, 'T-DL-001'),
('insulation_pipe_supply_2026', 'valve', '标段1', '香炉礁供暖主干线', 'V-DL-002', '香周路分支隔离切断阀', 121.614871, 38.930491, 'open', 'DN300 手动阀门', '分支网维保检修控制阀', 10, 'W-DL-004'),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-005', '香周路分支末端焊口', 121.616771, 38.929091, 'pending', 'DN300 预制直埋保温管', '等待末端换热站对接', 11, 'V-DL-002'),
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-001', '鞍山路管网起点对接焊口', 121.612771, 38.927491, 'pending', 'DN300 聚氨酯保温管', '标段2施工首段', 1, NULL),
('insulation_pipe_supply_2026', 'tee', '标段2', '鞍山路预制管线', 'T-AS-001', '鞍山路社区三通分流点', 121.614771, 38.929091, 'normal', 'DN300 等径三通', '社区二级供热网分流节点', 2, NULL),
('insulation_pipe_supply_2026', 'compensator', '标段2', '鞍山路预制管线', 'C-AS-001', '鞍山路中段波纹补偿器', 121.616771, 38.930091, 'normal', 'DN300 波纹管补偿器', '吸收管段位移', 3, NULL),
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-002', '鞍山路主线末端焊口', 121.618771, 38.931091, 'failed', 'DN300 聚氨酯保温管', '探伤微小瑕疵，安排复焊', 4, NULL),
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-003', '鞍山路社区小区分支焊口', 121.616771, 38.927091, 'passed', 'DN200 保温管', '从 T-AS-001 三通引出的小区分支焊口', 5, 'T-AS-001')
ON CONFLICT (project_key, code) DO NOTHING;


-- -----------------------------------------------------------------------------
-- 12. 系统操作审计日志表 (logs.tube_operation_logs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS logs.tube_operation_logs (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    operator VARCHAR(100) NOT NULL,
    operator_group VARCHAR(100),
    action_type VARCHAR(50) NOT NULL,
    action_desc TEXT NOT NULL,
    resource_id VARCHAR(100),
    before_value JSONB,
    after_value JSONB,
    client_ip VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE logs.tube_operation_logs IS '保温管供需管理系统操作审计日志表';
COMMENT ON COLUMN logs.tube_operation_logs.id IS '自增主键';
COMMENT ON COLUMN logs.tube_operation_logs.operator IS '操作人用户名';
COMMENT ON COLUMN logs.tube_operation_logs.operator_group IS '操作人所属主体/角色分组';
COMMENT ON COLUMN logs.tube_operation_logs.action_type IS '操作动作类型 (如 CREATE_DELIVERY, CANCEL_DELIVERY, CONFIRM_ARRIVED)';
COMMENT ON COLUMN logs.tube_operation_logs.action_desc IS '中文业务语义操作描述';
COMMENT ON COLUMN logs.tube_operation_logs.resource_id IS '关联业务资源主键 ID (如 delivery_id)';
COMMENT ON COLUMN logs.tube_operation_logs.before_value IS '变更前 JSON 快照';
COMMENT ON COLUMN logs.tube_operation_logs.after_value IS '变更后 JSON 快照';

CREATE INDEX IF NOT EXISTS idx_logs_tube_op_operator ON logs.tube_operation_logs(operator);
CREATE INDEX IF NOT EXISTS idx_logs_tube_op_action_type ON logs.tube_operation_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_logs_tube_op_created_at ON logs.tube_operation_logs(created_at DESC);

COMMIT;
