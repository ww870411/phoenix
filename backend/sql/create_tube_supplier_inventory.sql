-- =============================================================================
-- 表名: tube.tube_supplier_inventory
-- 说明: 供给主体（保温管生产厂家）厂区成品库存盘点表
-- 模式: 模式A 通用现货池（不绑定标段，section_1_id 默认为空字符串）
-- 模式: 按次实盘（通过 batch_no 隔离每次盘点快照，支持同日多次盘点不互相覆盖）
-- 创建时间: 2026-09-21
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS tube;

CREATE TABLE IF NOT EXISTS tube.tube_supplier_inventory (
    id BIGSERIAL PRIMARY KEY,
    batch_no VARCHAR(64) NOT NULL,                  -- 盘点批次编号 (如 INV_20260921_143000_123456_kaiyuan)
    report_date DATE NOT NULL,                      -- 盘点/业务日期 (YYYY-MM-DD)
    supply_entity_id VARCHAR(64) NOT NULL,          -- 供给主体标识 (如 wande, sanwei, beng 等)
    pipe_model_id VARCHAR(64) NOT NULL,             -- 保温管规格型号 (如 DN1100, DN1000)
    section_1_id VARCHAR(64) NOT NULL DEFAULT '',   -- 绑定标段标识 (模式A下默认为空字符串，代表通用现货池)
    stock_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,  -- 当前厂区实盘在库待发量 (米)
    remark TEXT,                                    -- 盘点说明或批注
    reported_by VARCHAR(128),                       -- 盘点填报人
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- 记录入库时间
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_supplier_inventory_qty_nonnegative 
        CHECK (stock_qty >= 0)
);

COMMENT ON TABLE tube.tube_supplier_inventory IS '供给主体保温管厂区成品库存盘点表';
COMMENT ON COLUMN tube.tube_supplier_inventory.id IS '自增主键';
COMMENT ON COLUMN tube.tube_supplier_inventory.batch_no IS '盘点批次号，每次提交生成唯一批次标识';
COMMENT ON COLUMN tube.tube_supplier_inventory.report_date IS '盘点/业务日期';
COMMENT ON COLUMN tube.tube_supplier_inventory.supply_entity_id IS '供给主体标识 (如 wande, sanwei, beng)';
COMMENT ON COLUMN tube.tube_supplier_inventory.pipe_model_id IS '保温管规格型号标识 (如 DN1100, DN1000)';
COMMENT ON COLUMN tube.tube_supplier_inventory.section_1_id IS '绑定标段标识 (通用现货池模式下为空字符串)';
COMMENT ON COLUMN tube.tube_supplier_inventory.stock_qty IS '当前厂区实盘在库待发量 (米)';
COMMENT ON COLUMN tube.tube_supplier_inventory.remark IS '盘点说明或批注';
COMMENT ON COLUMN tube.tube_supplier_inventory.reported_by IS '盘点填报人';
COMMENT ON COLUMN tube.tube_supplier_inventory.reported_at IS '初次填报时间';
COMMENT ON COLUMN tube.tube_supplier_inventory.updated_by IS '最后更新人';
COMMENT ON COLUMN tube.tube_supplier_inventory.updated_at IS '最后更新时间';

-- 联合唯一索引：同一盘点批次内、同一厂家、同一型号仅允许一条盘点记录（支持同日多次盘点共存）
CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_supplier_inventory_batch_entity_model
    ON tube.tube_supplier_inventory (batch_no, supply_entity_id, pipe_model_id);

-- 高频查询索引
CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_entity_time
    ON tube.tube_supplier_inventory (supply_entity_id, reported_at DESC);

CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_batch
    ON tube.tube_supplier_inventory (batch_no);

CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_entity_date
    ON tube.tube_supplier_inventory (supply_entity_id, report_date);

CREATE INDEX IF NOT EXISTS idx_tube_supplier_inventory_date
    ON tube.tube_supplier_inventory (report_date);
