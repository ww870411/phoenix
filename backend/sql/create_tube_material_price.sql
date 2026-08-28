-- ==============================================================================
-- 保温管与管件合同物料单价基准表 (tube.tube_material_price) 初始化脚本
-- 适用数据库：PostgreSQL 12+
-- Schema: tube
-- ==============================================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS tube;

-- 1. 创建物料单价基准表
CREATE TABLE IF NOT EXISTS tube.tube_material_price (
    id BIGSERIAL PRIMARY KEY,
    project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    material_kind VARCHAR(32) NOT NULL,                           -- 'pipe'(保温直管) / 'fitting'(管件与附件)
    supply_entity_id VARCHAR(64),                                 -- 供给主体缩写代码 (如 kaiyuan, xinruide, wosheng, kaersi, sanwei, huayang)
    supplier_name VARCHAR(128) NOT NULL,                          -- 供给方单位全称 (如 大连开元热力管道股份有限公司)
    category VARCHAR(64) NOT NULL,                                -- 物理类别 (保温管, 弯头, 三通, 球阀, 补偿器, 变径管, 封头, 密封节, 固定支架)
    material_name VARCHAR(128) NOT NULL,                          -- 材料标准名称 (如 塑套钢直埋预制保温管, 直埋焊接球阀)
    model_spec VARCHAR(255) NOT NULL,                             -- 标准化规格型号 (具有自解释唯一性)
    raw_model_spec VARCHAR(128),                                  -- 原始表格中的规格型号简写 (如 DN300, 90° DN1100 R=1.5DN)
    unit VARCHAR(32) NOT NULL DEFAULT '米',                       -- 计量单位 (米, 个, 套, 台)
    unit_price NUMERIC(18, 2) NOT NULL DEFAULT 0,                 -- 含税合同单价 (元)
    remark TEXT,                                                  -- 备注说明 (如甲供钢管加工等特殊说明)
    created_by VARCHAR(128) DEFAULT 'EXCEL_IMPORT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128) DEFAULT 'EXCEL_IMPORT',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_material_price_unit_price_nonnegative 
        CHECK (unit_price >= 0),
    CONSTRAINT chk_tube_material_price_material_kind 
        CHECK (material_kind IN ('pipe', 'fitting'))
);

-- 表级与字段级注释
COMMENT ON TABLE tube.tube_material_price IS '保温管与管件标准合同物料单价字典库';
COMMENT ON COLUMN tube.tube_material_price.id IS '自增主键';
COMMENT ON COLUMN tube.tube_material_price.project_key IS '项目代码';
COMMENT ON COLUMN tube.tube_material_price.material_kind IS '物料大类: pipe(保温直管) / fitting(管件与附件)';
COMMENT ON COLUMN tube.tube_material_price.supply_entity_id IS '供给主体标识代码';
COMMENT ON COLUMN tube.tube_material_price.supplier_name IS '供给方单位全称';
COMMENT ON COLUMN tube.tube_material_price.category IS '物理品类分类 (保温管, 弯头, 三通, 球阀, 补偿器, 变径管, 封头, 密封节, 固定支架)';
COMMENT ON COLUMN tube.tube_material_price.material_name IS '材料标准名称';
COMMENT ON COLUMN tube.tube_material_price.model_spec IS '标准化规格型号描述 (物料唯一标识)';
COMMENT ON COLUMN tube.tube_material_price.raw_model_spec IS '原始规格型号简写';
COMMENT ON COLUMN tube.tube_material_price.unit IS '计量单位 (米/个/套/台)';
COMMENT ON COLUMN tube.tube_material_price.unit_price IS '含税中标单价 (元)';
COMMENT ON COLUMN tube.tube_material_price.remark IS '备注说明';

-- 检索索引：支持供给方 + 规格型号快速匹配 (允许同名多行报价)
CREATE INDEX IF NOT EXISTS idx_tube_material_price_sup_spec
    ON tube.tube_material_price (supplier_name, model_spec);

-- 高频业务检索索引
CREATE INDEX IF NOT EXISTS idx_tube_material_price_kind_sup 
    ON tube.tube_material_price (material_kind, supplier_name);

CREATE INDEX IF NOT EXISTS idx_tube_material_price_category 
    ON tube.tube_material_price (category);

CREATE INDEX IF NOT EXISTS idx_tube_material_price_entity_id 
    ON tube.tube_material_price (supply_entity_id);

CREATE INDEX IF NOT EXISTS idx_tube_material_price_spec 
    ON tube.tube_material_price (model_spec);

-- 2. 直管与管件分类便捷视图
CREATE OR REPLACE VIEW tube.v_tube_pipe_price AS
SELECT * FROM tube.tube_material_price WHERE material_kind = 'pipe';

CREATE OR REPLACE VIEW tube.v_tube_fitting_price AS
SELECT * FROM tube.tube_material_price WHERE material_kind = 'fitting';

COMMIT;
