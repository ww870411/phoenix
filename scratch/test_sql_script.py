# -*- coding: utf-8 -*-
import os
import sys
from sqlalchemy import text

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.db.database_daily_report_25_26 import SessionLocal

sql_script = """
BEGIN;

-- 1. 直管需求基准表
UPDATE tube.tube_pipe_baseline
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g'),
    updated_at = NOW()
WHERE pipe_model_id ~ '[0-9]+\\.0+([^0-9]|$)';

-- 2. 价格表
UPDATE tube.tube_material_price
SET model_spec = regexp_replace(model_spec, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g'),
    updated_at = NOW()
WHERE (material_kind = 'pipe' OR category = '保温管')
  AND model_spec ~ '[0-9]+\\.0+([^0-9]|$)';

-- 3. 发货表
UPDATE tube.tube_delivery
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g'),
    updated_at = NOW()
WHERE pipe_model_id ~ '[0-9]+\\.0+([^0-9]|$)';

-- 4. 每日计划表（先合并重叠行，再更新剩余行）
WITH normalized_rows AS (
    SELECT 
        id,
        plan_date,
        section_1_id,
        regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g') AS norm_model,
        plan_qty,
        ROW_NUMBER() OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g') 
            ORDER BY (CASE WHEN pipe_model_id !~ '\\.0+' THEN 0 ELSE 1 END), id ASC
        ) AS rn,
        SUM(plan_qty) OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
        ) AS total_plan_qty,
        COUNT(*) OVER(
            PARTITION BY plan_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
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

UPDATE tube.tube_daily_plan
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
WHERE pipe_model_id ~ '[0-9]+\\.0+([^0-9]|$)';

-- 5. 每日消耗表（先合并重叠行，再更新剩余行）
WITH normalized_rows AS (
    SELECT 
        id,
        usage_date,
        section_1_id,
        regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g') AS norm_model,
        usage_qty,
        loss_qty,
        ROW_NUMBER() OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g') 
            ORDER BY (CASE WHEN pipe_model_id !~ '\\.0+' THEN 0 ELSE 1 END), id ASC
        ) AS rn,
        SUM(usage_qty) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
        ) AS total_usage_qty,
        SUM(loss_qty) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
        ) AS total_loss_qty,
        COUNT(*) OVER(
            PARTITION BY usage_date, section_1_id, regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
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

UPDATE tube.tube_daily_usage
SET pipe_model_id = regexp_replace(pipe_model_id, '([0-9]+)\\.0+([^0-9]|$)', '\\1\\2', 'g')
WHERE pipe_model_id ~ '[0-9]+\\.0+([^0-9]|$)';

ROLLBACK;
"""

def test():
    s = SessionLocal()
    try:
        s.execute(text(sql_script))
        print("✅ SQL script syntax test passed completely (ROLLBACK)!")
    except Exception as e:
        print("❌ Error:", e)
        raise
    finally:
        s.close()

if __name__ == "__main__":
    test()
