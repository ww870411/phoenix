-- 保温管件发货明细表 (tube.tube_fitting_delivery) 字段名与状态枚举统一迁移脚本 (纯单表极简对齐防错版)
-- 说明：
-- 1. 物理重命名 8 个到货/施工/库管确认列为直管标准（按需要条件重命名）。
-- 2. 补齐 3 个撤销跟踪列（cancel_at, cancel_by, cancel_reason）。
-- 3. 清理移除非必要列（shipment_key, identifiers_locked）。
-- 4. 将历史 status 状态 'shipped' 映射更新为保温管标准状态 'pending_arrival'。
-- 5. 挂载全新标准的物理 CHECK 约束。
-- 6. 自动重置自增主键序列，防止自增 ID 冲突。

BEGIN;

LOCK TABLE tube.tube_fitting_delivery IN ACCESS EXCLUSIVE MODE;

-- 1. 条件物理重命名已有的 8 个到货/施工/库管确认列（如果尚存在旧列名）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='arrived_at') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN arrived_at TO arrived_confirm_at;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='arrived_by') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN arrived_by TO arrived_confirm_by;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='arrival_remark') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN arrival_remark TO arrived_remark;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='construction_confirmed_at') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN construction_confirmed_at TO received_confirm_at;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='construction_confirmed_by') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN construction_confirmed_by TO received_confirm_by;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='construction_remark') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN construction_remark TO received_remark;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='warehouse_confirmed_at') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN warehouse_confirmed_at TO warehouse_confirm_at;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='tube' AND table_name='tube_fitting_delivery' AND column_name='warehouse_confirmed_by') THEN
        ALTER TABLE tube.tube_fitting_delivery RENAME COLUMN warehouse_confirmed_by TO warehouse_confirm_by;
    END IF;
END $$;

-- 2. 补齐撤销关联列
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancel_at TIMESTAMPTZ;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancel_by TEXT;
ALTER TABLE tube.tube_fitting_delivery ADD COLUMN IF NOT EXISTS cancel_reason TEXT;

-- 3. 移除不必要的非物理直管对齐列 (若存在)
ALTER TABLE tube.tube_fitting_delivery DROP COLUMN IF EXISTS shipment_key;
ALTER TABLE tube.tube_fitting_delivery DROP COLUMN IF EXISTS identifiers_locked;

-- 4. 平滑更新状态字符串：把历史状态 shipped 物理更新为标准状态 pending_arrival
UPDATE tube.tube_fitting_delivery SET status = 'pending_arrival' WHERE status = 'shipped';
UPDATE tube.tube_fitting_delivery SET status = 'pending_receive' WHERE status = 'arrived';
UPDATE tube.tube_fitting_delivery SET status = 'pending_warehouse' WHERE status = 'construction_confirmed';
UPDATE tube.tube_fitting_delivery SET status = 'completed' WHERE status = 'warehouse_confirmed';

-- 5. 挂载全新标准的物理 CHECK 约束
ALTER TABLE tube.tube_fitting_delivery DROP CONSTRAINT IF EXISTS chk_tube_fitting_status;
ALTER TABLE tube.tube_fitting_delivery
    ADD CONSTRAINT chk_tube_fitting_status
    CHECK (status IN (
        'pending_arrival',
        'pending_receive',
        'pending_warehouse',
        'completed',
        'cancelled'
    ));

ALTER TABLE tube.tube_fitting_delivery DROP CONSTRAINT IF EXISTS chk_tube_fitting_state_evidence;
ALTER TABLE tube.tube_fitting_delivery
    ADD CONSTRAINT chk_tube_fitting_state_evidence
    CHECK (
        (status = 'pending_arrival' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL)
        OR (status = 'pending_receive' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL)
        OR (status = 'pending_warehouse' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL)
        OR (status = 'completed' AND arrived_qty IS NOT NULL AND arrived_confirm_at IS NOT NULL AND received_confirm_at IS NOT NULL AND warehouse_confirm_at IS NOT NULL AND cancel_at IS NULL)
        OR (status = 'cancelled' AND arrived_confirm_at IS NULL AND received_confirm_at IS NULL AND warehouse_confirm_at IS NULL AND cancel_at IS NULL)
    );

-- 6. 重新校准自增 ID 序列，防止序列冲突
SELECT setval('tube.tube_fitting_delivery_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_fitting_delivery), 1));

COMMIT;
