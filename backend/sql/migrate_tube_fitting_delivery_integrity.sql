-- 管件物流完整性迁移（兼容路线 A：保留历史可见发货单号）。
-- 作用：修复重复主键、回正被重复 id 串改的状态、补齐内部批次键、状态约束与并发编号设施。

BEGIN;

LOCK TABLE tube.tube_fitting_delivery IN ACCESS EXCLUSIVE MODE;

CREATE SEQUENCE IF NOT EXISTS tube.tube_fitting_delivery_id_seq;
ALTER SEQUENCE tube.tube_fitting_delivery_id_seq OWNED BY tube.tube_fitting_delivery.id;
ALTER TABLE tube.tube_fitting_delivery
    ALTER COLUMN id SET DEFAULT nextval('tube.tube_fitting_delivery_id_seq');

ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS shipment_key VARCHAR(64);
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS identifiers_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS arrived_qty NUMERIC;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS arrived_at TIMESTAMPTZ;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS arrived_by TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS arrival_remark TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS construction_confirmed_at TIMESTAMPTZ;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS construction_confirmed_by TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS construction_remark TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS warehouse_confirmed_at TIMESTAMPTZ;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS warehouse_confirmed_by TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS warehouse_remark TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancelled_by TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancel_reason TEXT;

-- 保存重复 id 的受影响集合，稍后用审计日志回正串改单据。
CREATE TEMP TABLE tmp_fitting_duplicate_id_repair ON COMMIT DROP AS
WITH ranked AS (
    SELECT ctid AS row_ctid,
           id AS old_id,
           ROW_NUMBER() OVER (PARTITION BY id ORDER BY created_at, shipped_at, ctid) AS duplicate_rank
    FROM tube.tube_fitting_delivery
), base AS (
    SELECT COALESCE(MAX(id), 0) AS max_id
    FROM tube.tube_fitting_delivery
)
SELECT row_ctid,
       old_id,
       max_id + ROW_NUMBER() OVER (ORDER BY old_id, row_ctid) AS new_id
FROM ranked
CROSS JOIN base
WHERE duplicate_rank > 1;

UPDATE tube.tube_fitting_delivery AS target
SET id = repair.new_id
FROM tmp_fitting_duplicate_id_repair AS repair
WHERE target.ctid = repair.row_ctid;

-- 重复 id 造成的连带更新没有对应业务日志；只回正这些受影响 id 中无日志凭证的记录。
UPDATE tube.tube_fitting_delivery AS delivery
SET status = 'shipped',
    arrived_qty = NULL,
    arrived_at = NULL,
    arrived_by = NULL,
    arrival_remark = NULL,
    construction_confirmed_at = NULL,
    construction_confirmed_by = NULL,
    construction_remark = NULL,
    warehouse_confirmed_at = NULL,
    warehouse_confirmed_by = NULL,
    warehouse_remark = NULL,
    cancelled_at = NULL,
    cancelled_by = NULL,
    cancel_reason = NULL,
    updated_at = NOW(),
    updated_by = 'SYSTEM_INTEGRITY_MIGRATION'
WHERE delivery.id IN (
    SELECT old_id FROM tmp_fitting_duplicate_id_repair
    UNION
    SELECT new_id FROM tmp_fitting_duplicate_id_repair
)
AND NOT EXISTS (
    SELECT 1
    FROM logs.tube_operation_logs AS operation_log
    WHERE operation_log.action_type IN (
        'CONFIRM_FITTING_ARRIVAL',
        'CONFIRM_FITTING_CONSTRUCTION',
        'CONFIRM_FITTING_WAREHOUSE',
        'CANCEL_FITTING_DELIVERY'
    )
      AND POSITION(delivery.shipment_no IN COALESCE(operation_log.resource_id, '')) > 0
);

-- 为历史批次生成稳定内部键；不同车辆或发货时刻即使同号也不会再被显示层合并。
UPDATE tube.tube_fitting_delivery
SET shipment_key = 'legacy-' || MD5(CONCAT_WS(
    '|', shipment_no, supply_entity_id, section_1_id,
    vehicle_plate_no, shipped_at::TEXT
))
WHERE shipment_key IS NULL OR BTRIM(shipment_key) = '';

UPDATE tube.tube_fitting_delivery
SET identifiers_locked = FALSE
WHERE identifiers_locked IS NULL;

-- 规范历史状态，使每个状态都具有一致的数量与时间凭证。
UPDATE tube.tube_fitting_delivery
SET arrived_qty = NULL,
    arrived_at = NULL,
    arrived_by = NULL,
    arrival_remark = NULL,
    construction_confirmed_at = NULL,
    construction_confirmed_by = NULL,
    construction_remark = NULL,
    warehouse_confirmed_at = NULL,
    warehouse_confirmed_by = NULL,
    warehouse_remark = NULL
WHERE status = 'shipped';

UPDATE tube.tube_fitting_delivery
SET arrived_qty = LEAST(COALESCE(arrived_qty, shipped_qty), shipped_qty),
    arrived_at = COALESCE(arrived_at, updated_at, created_at),
    arrived_by = COALESCE(NULLIF(arrived_by, ''), updated_by, created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    construction_confirmed_at = NULL,
    construction_confirmed_by = NULL,
    construction_remark = NULL,
    warehouse_confirmed_at = NULL,
    warehouse_confirmed_by = NULL,
    warehouse_remark = NULL
WHERE status = 'arrived';

UPDATE tube.tube_fitting_delivery
SET arrived_qty = LEAST(COALESCE(arrived_qty, shipped_qty), shipped_qty),
    arrived_at = COALESCE(arrived_at, created_at),
    arrived_by = COALESCE(NULLIF(arrived_by, ''), created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    construction_confirmed_at = COALESCE(construction_confirmed_at, updated_at, created_at),
    construction_confirmed_by = COALESCE(NULLIF(construction_confirmed_by, ''), updated_by, created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    warehouse_confirmed_at = NULL,
    warehouse_confirmed_by = NULL,
    warehouse_remark = NULL
WHERE status = 'construction_confirmed';

UPDATE tube.tube_fitting_delivery
SET arrived_qty = LEAST(COALESCE(arrived_qty, shipped_qty), shipped_qty),
    arrived_at = COALESCE(arrived_at, created_at),
    arrived_by = COALESCE(NULLIF(arrived_by, ''), created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    construction_confirmed_at = COALESCE(construction_confirmed_at, arrived_at, created_at),
    construction_confirmed_by = COALESCE(NULLIF(construction_confirmed_by, ''), arrived_by, created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    warehouse_confirmed_at = COALESCE(warehouse_confirmed_at, updated_at, created_at),
    warehouse_confirmed_by = COALESCE(NULLIF(warehouse_confirmed_by, ''), updated_by, created_by, 'SYSTEM_INTEGRITY_MIGRATION')
WHERE status = 'warehouse_confirmed';

UPDATE tube.tube_fitting_delivery
SET cancelled_at = COALESCE(cancelled_at, updated_at, created_at),
    cancelled_by = COALESCE(NULLIF(cancelled_by, ''), updated_by, created_by, 'SYSTEM_INTEGRITY_MIGRATION'),
    cancel_reason = COALESCE(NULLIF(cancel_reason, ''), '历史撤销记录迁移补录'),
    arrived_qty = NULL,
    arrived_at = NULL,
    arrived_by = NULL,
    arrival_remark = NULL,
    construction_confirmed_at = NULL,
    construction_confirmed_by = NULL,
    construction_remark = NULL,
    warehouse_confirmed_at = NULL,
    warehouse_confirmed_by = NULL,
    warehouse_remark = NULL
WHERE status = 'cancelled';

ALTER TABLE tube.tube_fitting_delivery ALTER COLUMN shipment_key SET NOT NULL;
ALTER TABLE tube.tube_fitting_delivery ALTER COLUMN identifiers_locked SET DEFAULT TRUE;
ALTER TABLE tube.tube_fitting_delivery ALTER COLUMN identifiers_locked SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tube.tube_fitting_delivery'::regclass AND contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_fitting_delivery
            ADD CONSTRAINT tube_fitting_delivery_pkey PRIMARY KEY (id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tube_fitting_status') THEN
        ALTER TABLE tube.tube_fitting_delivery
            ADD CONSTRAINT chk_tube_fitting_status
            CHECK (status IN ('shipped', 'arrived', 'construction_confirmed', 'warehouse_confirmed', 'cancelled'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tube_fitting_arrived_qty_range') THEN
        ALTER TABLE tube.tube_fitting_delivery
            ADD CONSTRAINT chk_tube_fitting_arrived_qty_range
            CHECK (arrived_qty IS NULL OR (
                arrived_qty > 0 AND arrived_qty <= shipped_qty AND arrived_qty = TRUNC(arrived_qty)
            ));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tube_fitting_shipped_qty_integer') THEN
        ALTER TABLE tube.tube_fitting_delivery
            ADD CONSTRAINT chk_tube_fitting_shipped_qty_integer
            CHECK (shipped_qty > 0 AND shipped_qty = TRUNC(shipped_qty));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tube_fitting_state_evidence') THEN
        ALTER TABLE tube.tube_fitting_delivery
            ADD CONSTRAINT chk_tube_fitting_state_evidence
            CHECK (
                (status = 'shipped' AND arrived_at IS NULL AND construction_confirmed_at IS NULL AND warehouse_confirmed_at IS NULL AND cancelled_at IS NULL)
                OR (status = 'arrived' AND arrived_qty IS NOT NULL AND arrived_at IS NOT NULL AND construction_confirmed_at IS NULL AND warehouse_confirmed_at IS NULL AND cancelled_at IS NULL)
                OR (status = 'construction_confirmed' AND arrived_qty IS NOT NULL AND arrived_at IS NOT NULL AND construction_confirmed_at IS NOT NULL AND warehouse_confirmed_at IS NULL AND cancelled_at IS NULL)
                OR (status = 'warehouse_confirmed' AND arrived_qty IS NOT NULL AND arrived_at IS NOT NULL AND construction_confirmed_at IS NOT NULL AND warehouse_confirmed_at IS NOT NULL AND cancelled_at IS NULL)
                OR (status = 'cancelled' AND arrived_at IS NULL AND construction_confirmed_at IS NULL AND warehouse_confirmed_at IS NULL AND cancelled_at IS NOT NULL)
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipment_no
    ON tube.tube_fitting_delivery (shipment_no);
CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_section_1_shipped
    ON tube.tube_fitting_delivery (section_1_id, shipped_at);
CREATE INDEX IF NOT EXISTS idx_tube_fitting_delivery_shipment_key
    ON tube.tube_fitting_delivery (shipment_key);
CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_delivery_new_order_no
    ON tube.tube_fitting_delivery (order_no)
    WHERE identifiers_locked;

CREATE TABLE IF NOT EXISTS tube.tube_fitting_shipment_counter (
    supply_entity_id VARCHAR(64) NOT NULL,
    shipped_date DATE NOT NULL,
    last_value INTEGER NOT NULL CHECK (last_value > 0),
    PRIMARY KEY (supply_entity_id, shipped_date)
);

INSERT INTO tube.tube_fitting_shipment_counter (supply_entity_id, shipped_date, last_value)
SELECT supply_entity_id,
       (shipped_at AT TIME ZONE 'Asia/Shanghai')::DATE,
       MAX(CASE WHEN RIGHT(shipment_no, 3) ~ '^[0-9]{3}$' THEN RIGHT(shipment_no, 3)::INTEGER ELSE 0 END)
FROM tube.tube_fitting_delivery
GROUP BY supply_entity_id, (shipped_at AT TIME ZONE 'Asia/Shanghai')::DATE
ON CONFLICT (supply_entity_id, shipped_date)
DO UPDATE SET last_value = GREATEST(
    tube.tube_fitting_shipment_counter.last_value,
    EXCLUDED.last_value
);

CREATE TABLE IF NOT EXISTS tube.tube_fitting_shipment_registry (
    shipment_key VARCHAR(64) PRIMARY KEY,
    shipment_no VARCHAR(64) NOT NULL,
    is_legacy BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO tube.tube_fitting_shipment_registry (shipment_key, shipment_no, is_legacy, created_at)
SELECT shipment_key, MIN(shipment_no), TRUE, MIN(created_at)
FROM tube.tube_fitting_delivery
GROUP BY shipment_key
ON CONFLICT (shipment_key) DO NOTHING;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_fitting_new_shipment_no
    ON tube.tube_fitting_shipment_registry (shipment_no)
    WHERE is_legacy = FALSE;

SELECT setval(
    'tube.tube_fitting_delivery_id_seq',
    COALESCE(MAX(id), 1),
    MAX(id) IS NOT NULL
)
FROM tube.tube_fitting_delivery;

COMMIT;
