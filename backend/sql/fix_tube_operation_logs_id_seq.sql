-- 修复 logs.tube_operation_logs 数据表 id 主键自增序列丢失问题
CREATE SEQUENCE IF NOT EXISTS logs.tube_operation_logs_id_seq;

ALTER TABLE logs.tube_operation_logs 
    ALTER COLUMN id SET DEFAULT nextval('logs.tube_operation_logs_id_seq');

SELECT setval('logs.tube_operation_logs_id_seq', COALESCE((SELECT MAX(id) FROM logs.tube_operation_logs), 0) + 1, false);
