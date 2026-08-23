-- ==============================================================================
-- 修复脚本：tube.tube_delivery 历史单据恢复、重号重排、主键固化与自增序列对齐
-- 适用数据库：PostgreSQL
-- 说明：本脚本仅修复底层重号与主键机制，不替用户作废任何单据，保留为“待到货”供前端自主撤销
-- ==============================================================================

BEGIN;

-- 1. 恢复开元管道（kaiyuan）被误覆盖的历史记录原始单号与车牌号
UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260728-001', shipment_no = 'SSA-260728-001', vehicle_plate_no = '辽K2B150'
WHERE id = 30 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260730-001', shipment_no = 'SSA-260730-001', vehicle_plate_no = '辽ACU528'
WHERE id = 32 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260730-002', shipment_no = 'SSA-260730-002', vehicle_plate_no = '辽AFP018'
WHERE id = 34 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260801-001', shipment_no = 'SSA-260801-001', vehicle_plate_no = '辽ABP469'
WHERE id = 36 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260804-001', shipment_no = 'SSA-260804-001', vehicle_plate_no = '辽ABP469'
WHERE id = 37 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260805-001', shipment_no = 'SSA-260805-001', vehicle_plate_no = '辽AER078'
WHERE id = 38 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';

UPDATE tube.tube_delivery
SET order_no = 'OSA-L1-260805-002', shipment_no = 'SSA-260805-002', vehicle_plate_no = '辽ACZ719'
WHERE id = 39 AND supply_entity_id = 'kaiyuan' AND created_at < '2026-08-22';


-- 2. 将 8月22日/23日新瑞德（xinruide）的 10 条重号发货单重排为独立 ID（48~57），保持 pending_arrival 待到货状态
UPDATE tube.tube_delivery
SET id = 48, order_no = 'OSB-L2-260822-006', shipment_no = 'SSB-260822-002', vehicle_plate_no = '辽CG1914'
WHERE id = 30 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

-- 单号 OSB-L2-260822-031（原 id 31）：赋予独立 ID 49，车牌补齐，保持 pending_arrival 供用户前端撤销
UPDATE tube.tube_delivery
SET id = 49,
    order_no = 'OSB-L2-260822-031',
    shipment_no = 'SSB-260822-002',
    vehicle_plate_no = '辽CG1914',
    status = 'pending_arrival',
    cancel_by = NULL,
    cancel_at = NULL,
    cancel_reason = NULL
WHERE id = 31 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 50, order_no = 'OSB-L2-260822-007', shipment_no = 'SSB-260822-003', vehicle_plate_no = '辽CG1914'
WHERE id = 32 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

-- 同批次异常单号 OSB-L2-260822-032（原 id 33）：赋予独立 ID 51，保持 pending_arrival 供用户前端撤销
UPDATE tube.tube_delivery
SET id = 51,
    order_no = 'OSB-L2-260822-032',
    shipment_no = 'SSB-260822-003',
    vehicle_plate_no = '辽CG1914',
    status = 'pending_arrival',
    cancel_by = NULL,
    cancel_at = NULL,
    cancel_reason = NULL
WHERE id = 33 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 52, order_no = 'OSB-L2-260822-008', shipment_no = 'SSB-260822-004', vehicle_plate_no = '辽CG1914'
WHERE id = 34 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

-- 同批次异常单号 OSB-L2-260822-033（原 id 35）：赋予独立 ID 53，保持 pending_arrival 供用户前端撤销
UPDATE tube.tube_delivery
SET id = 53,
    order_no = 'OSB-L2-260822-033',
    shipment_no = 'SSB-260822-004',
    vehicle_plate_no = '辽CG1914',
    status = 'pending_arrival',
    cancel_by = NULL,
    cancel_at = NULL,
    cancel_reason = NULL
WHERE id = 35 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 54, order_no = 'OSB-L2-260822-009', shipment_no = 'SSB-260822-005', vehicle_plate_no = '辽CG1914'
WHERE id = 36 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 55, order_no = 'OSB-L2-260822-010', shipment_no = 'SSB-260822-006'
WHERE id = 37 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 56, order_no = 'OSB-L2-260822-011', shipment_no = 'SSB-260822-007', vehicle_plate_no = '辽CH7635'
WHERE id = 38 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';

UPDATE tube.tube_delivery
SET id = 57, order_no = 'OSB-L2-260823-001', shipment_no = 'SSB-260823-001', vehicle_plate_no = '吉JG1271'
WHERE id = 39 AND supply_entity_id = 'xinruide' AND created_at >= '2026-08-22';


-- 3. 对齐自增序列（确保下一笔发货自增 ID 从 58 开始）
SELECT setval('tube.tube_delivery_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_delivery), 1));

-- 4. 为 tube.tube_delivery 添加主键约束，彻底杜绝后续重号
ALTER TABLE tube.tube_delivery DROP CONSTRAINT IF EXISTS tube_delivery_pkey;
ALTER TABLE tube.tube_delivery ADD PRIMARY KEY (id);

-- 5. 添加常用查询索引提升检索性能
CREATE INDEX IF NOT EXISTS idx_tube_delivery_supply_shipped
    ON tube.tube_delivery (supply_entity_id, shipped_at DESC);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_status
    ON tube.tube_delivery (status);

COMMIT;
