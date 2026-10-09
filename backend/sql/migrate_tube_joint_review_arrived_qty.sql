-- 已由用户在当前数据库执行；其他环境部署时在事务中同步同一规则。
-- 不修改已有业务数量，仅取消到货量相对于发货量的上界。
BEGIN;
ALTER TABLE tube.tube_delivery DROP CONSTRAINT IF EXISTS chk_tube_delivery_arrived_qty_range;
ALTER TABLE tube.tube_delivery ADD CONSTRAINT chk_tube_delivery_arrived_qty_range
    CHECK (arrived_qty IS NULL OR arrived_qty >= 0);
COMMIT;

-- 回滚前需查询 arrived_qty > shipped_qty 的记录；存在时不可直接恢复旧约束。
