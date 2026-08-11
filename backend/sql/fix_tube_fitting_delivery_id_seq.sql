-- 修复 tube.tube_fitting_delivery 数据表 id 主键自增序列丢失问题
CREATE SEQUENCE IF NOT EXISTS tube.tube_fitting_delivery_id_seq;

ALTER TABLE tube.tube_fitting_delivery 
    ALTER COLUMN id SET DEFAULT nextval('tube.tube_fitting_delivery_id_seq');

SELECT setval('tube.tube_fitting_delivery_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_fitting_delivery), 0) + 1, false);
