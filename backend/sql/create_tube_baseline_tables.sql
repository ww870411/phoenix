-- =============================================================================
-- Phoenix 凤凰计划 · 保温管及管件基准设计量与计划采购量数据表创建脚本
-- 适用数据库：PostgreSQL 14+
-- 包含：
--   1. tube.tube_pipe_baseline (直管设计与计划采购基准表)
--   2. tube.tube_fitting_baseline (管件设计与计划采购基准表，支持主型号+子型号)
-- =============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS tube;

-- -----------------------------------------------------------------------------
-- 1. 保温直管基准表 (tube.tube_pipe_baseline)
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

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_pipe_baseline_sec_model 
    ON tube.tube_pipe_baseline (section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_pipe_baseline_sec 
    ON tube.tube_pipe_baseline (section_1_id);

CREATE INDEX IF NOT EXISTS idx_tube_pipe_baseline_model 
    ON tube.tube_pipe_baseline (pipe_model_id);

COMMENT ON TABLE tube.tube_pipe_baseline IS '保温直管设计量与计划采购量基准表';
COMMENT ON COLUMN tube.tube_pipe_baseline.id IS '自增主键';
COMMENT ON COLUMN tube.tube_pipe_baseline.section_1_id IS '需求主体/标段标识 (如 high_lot_1)';
COMMENT ON COLUMN tube.tube_pipe_baseline.pipe_model_id IS '直管型号规格 (如 Φ1120×13/Φ1260×16)';
COMMENT ON COLUMN tube.tube_pipe_baseline.unit IS '计量单位 (默认 米)';
COMMENT ON COLUMN tube.tube_pipe_baseline.design_qty IS '设计使用总量 (根据设计图纸核定)';
COMMENT ON COLUMN tube.tube_pipe_baseline.purchase_plan_qty IS '计划采购总量 (核准的采购/供货额度)';
COMMENT ON COLUMN tube.tube_pipe_baseline.remark IS '说明备注';
COMMENT ON COLUMN tube.tube_pipe_baseline.created_by IS '初始创建人';
COMMENT ON COLUMN tube.tube_pipe_baseline.created_at IS '记录创建时间';
COMMENT ON COLUMN tube.tube_pipe_baseline.updated_by IS '最后更新人';
COMMENT ON COLUMN tube.tube_pipe_baseline.updated_at IS '最后更新时间';


-- -----------------------------------------------------------------------------
-- 2. 管件基准表 (tube.tube_fitting_baseline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_fitting_baseline (
    id BIGSERIAL PRIMARY KEY,
    section_1_id VARCHAR(64) NOT NULL,
    fitting_type VARCHAR(64) NOT NULL,
    model_spec VARCHAR(128) NOT NULL,
    sub_model_spec VARCHAR(128) NOT NULL DEFAULT '',
    unit VARCHAR(32) NOT NULL DEFAULT '个',
    design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    remark TEXT,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_fitting_baseline_qty_nonnegative 
        CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_baseline_sec_type_spec_sub 
    ON tube.tube_fitting_baseline (section_1_id, fitting_type, model_spec, sub_model_spec);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_sec 
    ON tube.tube_fitting_baseline (section_1_id);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_type 
    ON tube.tube_fitting_baseline (fitting_type);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_baseline_spec 
    ON tube.tube_fitting_baseline (model_spec);

COMMENT ON TABLE tube.tube_fitting_baseline IS '管件设计量与计划采购量基准表';
COMMENT ON COLUMN tube.tube_fitting_baseline.id IS '自增主键';
COMMENT ON COLUMN tube.tube_fitting_baseline.section_1_id IS '需求主体/标段标识 (如 high_lot_1)';
COMMENT ON COLUMN tube.tube_fitting_baseline.fitting_type IS '管件类型 (如 弯头、三通、补偿器、大小头 等)';
COMMENT ON COLUMN tube.tube_fitting_baseline.model_spec IS '管件主型号/主规格 (如 DN1000、DN300)';
COMMENT ON COLUMN tube.tube_fitting_baseline.sub_model_spec IS '管件子型号/细分规格 (如 90°、45°、顺水、轴向200mm 等，无则为空字符串)';
COMMENT ON COLUMN tube.tube_fitting_baseline.unit IS '计量单位 (如 个、套、件、组)';
COMMENT ON COLUMN tube.tube_fitting_baseline.design_qty IS '设计使用总量 (根据设计图纸核定)';
COMMENT ON COLUMN tube.tube_fitting_baseline.purchase_plan_qty IS '计划采购总量 (核准的采购/供货额度)';
COMMENT ON COLUMN tube.tube_fitting_baseline.remark IS '说明备注';
COMMENT ON COLUMN tube.tube_fitting_baseline.created_by IS '初始创建人';
COMMENT ON COLUMN tube.tube_fitting_baseline.created_at IS '记录创建时间';
COMMENT ON COLUMN tube.tube_fitting_baseline.updated_by IS '最后更新人';
COMMENT ON COLUMN tube.tube_fitting_baseline.updated_at IS '最后更新时间';

COMMIT;
