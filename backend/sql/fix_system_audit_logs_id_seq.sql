-- ==========================================================
-- 生产环境专用：修复 logs.system_audit_logs 主键自增序列丢失
-- 适用场景：从备份还原或迁移后插入报错 "null value in column id"
-- ==========================================================

-- 1. 确保 logs 模式存在
CREATE SCHEMA IF NOT EXISTS logs;

-- 2. 确保序列存在
CREATE SEQUENCE IF NOT EXISTS logs.system_audit_logs_id_seq;

-- 3. 将序列所有权绑定到 logs.system_audit_logs 表的 id 列
ALTER SEQUENCE logs.system_audit_logs_id_seq OWNED BY logs.system_audit_logs.id;

-- 4. 设置 id 列的默认值为序列的 nextval
ALTER TABLE logs.system_audit_logs ALTER COLUMN id SET DEFAULT nextval('logs.system_audit_logs_id_seq');

-- 5. 将序列当前值同步至表中已有数据最大 id（防止主键冲突），若表为空则从 1 开始
SELECT setval('logs.system_audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM logs.system_audit_logs), 0) + 1, false);
