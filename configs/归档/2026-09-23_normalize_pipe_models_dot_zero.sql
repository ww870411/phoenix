-- =============================================================================
-- 凤凰计划 Phoenix: 保温管规格型号全面去".0"规范化清洗 SQL 脚本
-- 适用数据库: PostgreSQL 14+
-- 作用范围:
--   1. tube.tube_pipe_baseline (直管需求基准表)
--   2. tube.tube_material_price (物料采购单价表)
--   3. tube.tube_delivery (发货流转单据表)
--   4. tube.tube_daily_plan (三日滚动计划表，含重叠行合并求和与去重)
--   5. tube.tube_daily_usage (施工消耗填报表，含重叠行合并求和与去重)
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. 直管需求基准表 (tube.tube_pipe_baseline)
-- -----------------------------------------------------------------------------
UPDATE tube.tube_pipe_baseline
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g'),
    updated_at = NOW()
WHERE pipe_model_id ~ '[0-9]+\.0+([^0-9]|$)';


-- -----------------------------------------------------------------------------
-- 2. 物料采购单价表 (tube.tube_material_price - 仅限保温管类)
-- -----------------------------------------------------------------------------
UPDATE tube.tube_material_price
SET model_spec = regexp_replace(model_spec, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g'),
    updated_at = NOW()
WHERE (material_kind = 'pipe' OR category = '保温管')
  AND model_spec ~ '[0-9]+\.0+([^0-9]|$)';


-- -----------------------------------------------------------------------------
-- 3. 发货流转单据表 (tube.tube_delivery)
-- -----------------------------------------------------------------------------
UPDATE tube.tube_delivery
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g'),
    updated_at = NOW()
WHERE pipe_model_id ~ '[0-9]+\.0+([^0-9]|$)';


-- -----------------------------------------------------------------------------
-- 4. 未来三日计划表 (tube.tube_daily_plan)
--    特别处理: 同标段同日期去.0后重叠的记录，先求和合并计划量并清理多余记录，杜绝唯一键冲突
-- -----------------------------------------------------------------------------
WITH normalized_rows AS (
    SELECT 
        id,
        plan_date,
        section_1_id,
        regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g') AS norm_model,
        plan_qty,
        ROW_NUMBER() OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g') 
            ORDER BY (CASE WHEN pipe_model_id !~ '\.0+' THEN 0 ELSE 1 END), id ASC
        ) AS rn,
        SUM(plan_qty) OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
        ) AS total_plan_qty,
        COUNT(*) OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
        ) AS cnt
    FROM tube.tube_daily_plan
),
duplicates_to_delete AS (
    DELETE FROM tube.tube_daily_plan
    WHERE id IN (
        SELECT id FROM normalized_rows WHERE cnt > 1 AND rn > 1
    )
)
UPDATE tube.tube_daily_plan p
SET plan_qty = n.total_plan_qty,
    pipe_model_id = n.norm_model
FROM normalized_rows n
WHERE p.id = n.id AND n.cnt > 1 AND n.rn = 1;

-- 对剩下无重叠但带 .0 的记录执行常规规范化更新
UPDATE tube.tube_daily_plan
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
WHERE pipe_model_id ~ '[0-9]+\.0+([^0-9]|$)';


-- -----------------------------------------------------------------------------
-- 5. 每日施工消耗表 (tube.tube_daily_usage)
--    特别处理: 同标段同日期去.0后重叠的记录，先求和合并使用量/损耗量并清理多余记录
-- -----------------------------------------------------------------------------
WITH normalized_rows AS (
    SELECT 
        id,
        usage_date,
        section_1_id,
        regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g') AS norm_model,
        usage_qty,
        loss_qty,
        ROW_NUMBER() OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g') 
            ORDER BY (CASE WHEN pipe_model_id !~ '\.0+' THEN 0 ELSE 1 END), id ASC
        ) AS rn,
        SUM(usage_qty) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
        ) AS total_usage_qty,
        SUM(loss_qty) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
        ) AS total_loss_qty,
        COUNT(*) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
        ) AS cnt
    FROM tube.tube_daily_usage
),
duplicates_to_delete AS (
    DELETE FROM tube.tube_daily_usage
    WHERE id IN (
        SELECT id FROM normalized_rows WHERE cnt > 1 AND rn > 1
    )
)
UPDATE tube.tube_daily_usage u
SET usage_qty = n.total_usage_qty,
    loss_qty = n.total_loss_qty,
    pipe_model_id = n.norm_model
FROM normalized_rows n
WHERE u.id = n.id AND n.cnt > 1 AND n.rn = 1;

-- 对剩下无重叠但带 .0 的记录执行常规规范化更新
UPDATE tube.tube_daily_usage
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\.0+([^0-9]|$)', '\1\2', 'g')
WHERE pipe_model_id ~ '[0-9]+\.0+([^0-9]|$)';

COMMIT;
