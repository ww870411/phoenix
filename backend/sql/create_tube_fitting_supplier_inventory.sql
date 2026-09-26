-- =============================================================================
-- 表名: tube.tube_fitting_supplier_inventory
-- 说明: 供给主体（管件制造厂家）厂区成品管件待发库存盘点表
-- 模式: 模式A 通用现货池（不绑定标段，section_1_id 默认为空字符串，支持定制件专属绑定）
-- 模式: 按次实盘（通过 batch_no 隔离每次盘点快照，支持同日多次盘点不互相覆盖）
-- 创建时间: 2026-09-26
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS tube;

CREATE TABLE IF NOT EXISTS tube.tube_fitting_supplier_inventory (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(64) NOT NULL,                  -- 盘点批次编号 (如 FIT_INV_20260926_143000_123456_wande)
    report_date DATE NOT NULL,                      -- 盘点/业务日期 (YYYY-MM-DD)
    supply_entity_id VARCHAR(64) NOT NULL,          -- 供给主体标识 (如 wande, sanwei, beng 等)
    section_1_id VARCHAR(64) NOT NULL DEFAULT '',   -- 绑定标段标识 (模式A通用现货池默认为空字符串)
    fitting_type VARCHAR(64) NOT NULL,              -- 管件类别 (弯头、三通、变径管、球阀、补偿器、固定支架等)
    material_name VARCHAR(128) NOT NULL DEFAULT '', -- 标准物料名称 (如 90°预制保温弯头、预制保温跨越三通等)
    model_spec VARCHAR(128) NOT NULL,               -- 规格型号描述 (如 DN1100 90°、DN1000/DN800 等)
    unit VARCHAR(32) NOT NULL DEFAULT '个',         -- 计量单位 (个、套、台、件等)
    stock_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,    -- 当前厂区实盘在库待发量
    remark TEXT,                                    -- 盘点说明或批注
    reported_by VARCHAR(128),                       -- 盘点填报人
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 记录入库时间
    updated_by VARCHAR(128),                        -- 最后更新人
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- 最后更新时间
    CONSTRAINT chk_fitting_supplier_inventory_qty_nonnegative 
        CHECK (stock_qty >= 0)
);

COMMENT ON TABLE tube.tube_fitting_supplier_inventory IS '供给主体管件厂区成品库存盘点表';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.id IS '自增主键';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.batch_no IS '盘点批次号，每次提交生成唯一批次标识';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.report_date IS '盘点/业务日期';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.supply_entity_id IS '供给主体标识 (如 wande, sanwei, beng)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.section_1_id IS '绑定标段标识 (通用现货池模式下为空字符串)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.fitting_type IS '管件类别 (弯头、三通、变径管、球阀、补偿器、固定支架等)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.material_name IS '标准物料名称 (如 90°预制保温弯头、预制保温跨越三通)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.model_spec IS '管件规格型号描述 (如 DN1100 90°、DN1000/DN800)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.unit IS '计量单位 (默认: 个)';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.stock_qty IS '当前厂区实盘在库待发量';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.remark IS '盘点说明或批注';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.reported_by IS '盘点填报人';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.reported_at IS '初次填报时间';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.updated_by IS '最后更新人';
COMMENT ON COLUMN tube.tube_fitting_supplier_inventory.updated_at IS '最后更新时间';

-- 联合唯一索引：同一盘点批次内、同一厂家、同一标段、同一管件类别、物料名称及型号规格仅允许一条盘点记录
CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_supplier_inv_batch_item
    ON tube.tube_fitting_supplier_inventory (batch_no, supply_entity_id, section_1_id, fitting_type, material_name, model_spec, unit);

-- 高频查询索引
CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_entity_time
    ON tube.tube_fitting_supplier_inventory (supply_entity_id, reported_at DESC);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_batch
    ON tube.tube_fitting_supplier_inventory (batch_no);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_entity_date
    ON tube.tube_fitting_supplier_inventory (supply_entity_id, report_date);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_date
    ON tube.tube_fitting_supplier_inventory (report_date);

CREATE INDEX IF NOT EXISTS idx_tube_fitting_supplier_inv_type_spec
    ON tube.tube_fitting_supplier_inventory (fitting_type, model_spec);
