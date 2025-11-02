-- ========= 煤炭库存聚合视图 =========
-- sum_coal_inventory_data：根据最新日期的煤炭库存数据，按公司与存储方式汇总，并追加公司级与集团汇总行
DROP VIEW IF EXISTS sum_coal_inventory_data;

CREATE VIEW sum_coal_inventory_data AS
WITH latest_date AS (
  SELECT MAX(date) AS max_date
  FROM coal_inventory_data
),

-- 1️⃣ 最新日期数据
filtered AS (
  SELECT
    c.company,
    c.company_cn,
    c.storage_type,
    c.storage_type_cn,
    c.unit,
    COALESCE(c.value, 0) AS value,
    c.date
  FROM coal_inventory_data c
  CROSS JOIN latest_date l
  WHERE c.date = l.max_date
),

-- 2️⃣ 基础层：公司 × 存储方式
base AS (
  SELECT
    f.company,
    MAX(f.company_cn) AS company_cn,
    f.storage_type,
    MAX(f.storage_type_cn) AS storage_type_cn,
    MAX(f.unit) AS unit,
    MAX(f.date) AS date,
    SUM(f.value) AS value
  FROM filtered f
  GROUP BY f.company, f.storage_type
),

-- 3️⃣ 每个公司自身汇总（改名为 *_sum）
company_rollup AS (
  SELECT
    b.company || '_sum' AS company,
    MAX(b.company_cn) || '合计' AS company_cn,
    'all_sites'::text AS storage_type,
    '全部地点'::text AS storage_type_cn,
    MAX(b.unit) AS unit,
    MAX(b.date) AS date,
    SUM(b.value) AS value
  FROM base b
  GROUP BY b.company
),

-- 4️⃣ 主城区汇总（BeiHai + XiangHai）
zhuchengqu_rollup AS (
  SELECT
    'ZhuChengQu_sum'::text AS company,
    '主城区'::text AS company_cn,
    'all_sites'::text AS storage_type,
    '全部地点'::text AS storage_type_cn,
    MAX(b.unit) AS unit,
    MAX(b.date) AS date,
    SUM(b.value) AS value
  FROM base b
  WHERE b.company IN ('BeiHai', 'XiangHai')
),

-- 5️⃣ 集团合计
grand_rollup AS (
  SELECT
    'Group_sum'::text AS company,
    '集团合计'::text AS company_cn,
    'all_sites'::text AS storage_type,
    '全部地点'::text AS storage_type_cn,
    MAX(b.unit) AS unit,
    MAX(b.date) AS date,
    SUM(b.value) AS value
  FROM base b
)
-- 最终输出
SELECT * FROM base
UNION ALL
SELECT * FROM company_rollup
UNION ALL
SELECT * FROM zhuchengqu_rollup
UNION ALL
SELECT * FROM grand_rollup;

-- 温度聚合视图：按天聚合 temperature_data 输出最高/最低/平均温度
CREATE OR REPLACE VIEW calc_temperature_data AS
SELECT
    DATE_TRUNC('day', date_time)::date AS date,
    MAX(value) AS max_temp,
    MIN(value) AS min_temp,
    AVG(value) AS aver_temp
FROM temperature_data
GROUP BY DATE_TRUNC('day', date_time)::date
ORDER BY date;
