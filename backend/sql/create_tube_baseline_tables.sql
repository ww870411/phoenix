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
-- 2. 管件与物料基准表 (tube.tube_fitting_baseline)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tube.tube_fitting_baseline (
    id BIGSERIAL PRIMARY KEY,
    -- 核心维度与归属
    section_1_id VARCHAR(64) NOT NULL,
    system_type VARCHAR(32) NOT NULL DEFAULT '高温水',
    category VARCHAR(64) NOT NULL DEFAULT '管件',
    standard_name VARCHAR(128) NOT NULL DEFAULT '',
    model_spec VARCHAR(255) NOT NULL,
    sub_model_spec VARCHAR(128) NOT NULL DEFAULT '',
    unit VARCHAR(32) NOT NULL DEFAULT '个',
    
    -- 基准工程量
    design_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    purchase_plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    
    -- 结构化工程参数
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
    
    -- 辅助与审计字段
    remark TEXT,
    extra_params JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_fitting_baseline_qty_nonnegative 
        CHECK (design_qty >= 0 AND purchase_plan_qty >= 0)
);

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
COMMENT ON COLUMN tube.tube_fitting_baseline.remark IS '说明备注';
COMMENT ON COLUMN tube.tube_fitting_baseline.extra_params IS '扩展工程参数 (JSONB)';
COMMENT ON COLUMN tube.tube_fitting_baseline.created_by IS '初始创建人';
COMMENT ON COLUMN tube.tube_fitting_baseline.created_at IS '记录创建时间';
COMMENT ON COLUMN tube.tube_fitting_baseline.updated_by IS '最后更新人';
COMMENT ON COLUMN tube.tube_fitting_baseline.updated_at IS '最后更新时间';

COMMIT;
