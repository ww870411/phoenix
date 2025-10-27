-- ========= 清理可能存在的旧对象（按依赖由上到下，避免命名/列结构冲突） =========
DROP VIEW IF EXISTS calc_sum_basic_trace;
DROP MATERIALIZED VIEW IF EXISTS calc_sum_gongre_branches_detail_data;
DROP MATERIALIZED VIEW IF EXISTS calc_sum_basic_data;
DROP VIEW IF EXISTS v_sum_gongre_branches_long;
DROP VIEW IF EXISTS v_sum_basic_long;
DROP MATERIALIZED VIEW IF EXISTS sum_gongre_branches_detail_data;
DROP MATERIALIZED VIEW IF EXISTS sum_basic_data;
DROP VIEW IF EXISTS v_constants_company_first_norm;
DROP VIEW IF EXISTS v_constants_center_first_norm;
DROP VIEW IF EXISTS v_constants_center_first;

-- ========= 先创建依赖视图与映射（确保后续对象可直接引用） =========

-- 常量（center/company 优先）与规范化键
CREATE OR REPLACE VIEW v_constants_center_first AS
SELECT
  COALESCE(NULLIF(TRIM(c.center), ''), NULLIF(TRIM(c.company), '')) AS key1,
  TRIM(c.item) AS item,
  TRIM(c.period) AS period,
  c.value
FROM constant_data c;

CREATE OR REPLACE VIEW v_constants_center_first_norm AS
SELECT
  TRIM(key1) AS key1,
  LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(item), '[\s\-]+', '_', 'g'), '__+', '_', 'g')) AS item_key,
  COALESCE(
    NULLIF(SUBSTRING(period FROM '(\d{2}-\d{2})'), ''),
    REGEXP_REPLACE(LOWER(TRIM(period)), '(?i)\s*period\s*', '', 'g')
  ) AS period_key,
  value
FROM v_constants_center_first;

CREATE OR REPLACE VIEW v_constants_company_first_norm AS
SELECT
  COALESCE(NULLIF(TRIM(c.company), ''), NULLIF(TRIM(c.center), '')) AS key1,
  LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(c.item), '[\s\-]+', '_', 'g'), '__+', '_', 'g')) AS item_key,
  COALESCE(
    NULLIF(SUBSTRING(c.period FROM '(\d{2}-\d{2})'), ''),
    REGEXP_REPLACE(LOWER(TRIM(c.period)), '(?i)\s*period\s*', '', 'g')
  ) AS period_key,
  c.value
FROM constant_data c;

-- 口径映射（scope→period），供后续 join
CREATE TABLE IF NOT EXISTS period_map (
  scope  TEXT PRIMARY KEY,
  period TEXT NOT NULL
);
INSERT INTO period_map(scope, period) VALUES
('value_biz_date','25-26'),
('sum_7d_biz','25-26'),
('sum_month_biz','25-26'),
('sum_ytd_biz','25-26'),
('value_peer_date','24-25'),
('sum_7d_peer','24-25'),
('sum_month_peer','24-25'),
('sum_ytd_peer','24-25')
ON CONFLICT (scope) DO NOTHING;

CREATE OR REPLACE VIEW v_scope_period AS
SELECT scope, period FROM period_map;

-- ========= 一级物化视图 =========
-- sum_basic_data 物化视图
-- 口径：按 company / item 汇总每日基础数据，对 biz_date（当前系统日前一天）及其同期日计算 6 个累计指标
-- 使用前请确认 daily_basic_data 表结构与 value/date 字段命名一致，并在生产环境执行前先在测试库验证
-- 默认创建在当前 search_path 指向的 schema（通常为 public），如需单独 schema 可在执行前 SET search_path

DROP MATERIALIZED VIEW IF EXISTS sum_basic_data;

CREATE MATERIALIZED VIEW sum_basic_data AS
WITH anchor_dates AS (
  SELECT
    (current_date - INTERVAL '1 day')::date AS biz_date,
    (current_date - INTERVAL '1 day' - INTERVAL '1 year')::date AS peer_date
),
window_defs AS (
  SELECT
    biz_date,
    peer_date,
    biz_date - INTERVAL '6 day' AS biz_7d_start,
    peer_date - INTERVAL '6 day' AS peer_7d_start,
    date_trunc('month', biz_date)::date AS biz_month_start,
    date_trunc('month', peer_date)::date AS peer_month_start,
    DATE '2025-10-01' AS biz_ytd_start,
    DATE '2024-10-01' AS peer_ytd_start
  FROM anchor_dates
)
SELECT
  d.company,
  d.company_cn,
  d.item,
  d.item_cn,
  d.unit,
  w.biz_date,
  w.peer_date,
  COALESCE(SUM(d.value) FILTER (WHERE d.date = w.biz_date), 0) AS value_biz_date,
  COALESCE(SUM(d.value) FILTER (WHERE d.date = w.peer_date), 0) AS value_peer_date,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_7d_start AND w.biz_date
  ), 0) AS sum_7d_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_7d_start AND w.peer_date
  ), 0) AS sum_7d_peer,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_month_start AND w.biz_date
  ), 0) AS sum_month_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_month_start AND w.peer_date
  ), 0) AS sum_month_peer,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_ytd_start AND w.biz_date
  ), 0) AS sum_ytd_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_ytd_start AND w.peer_date
  ), 0) AS sum_ytd_peer
FROM daily_basic_data d
CROSS JOIN window_defs w
WHERE d.date BETWEEN w.peer_ytd_start AND w.biz_date
GROUP BY
  d.company, d.company_cn, d.item, d.item_cn, d.unit,
  w.biz_date, w.peer_date;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sum_basic_data_company_item_bizdate
  ON sum_basic_data (company, item, biz_date);

-- sum_gongre_branches_detail_data 物化视图
-- 口径：按 center / item 汇总分中心明细数据，同步计算 biz_date（当前日前一天）及同期日的 6 个累计指标
-- 数据来源：gongre_branches_detail_data；如需独立 schema，请在执行前通过 SET search_path 调整

DROP MATERIALIZED VIEW IF EXISTS sum_gongre_branches_detail_data;

CREATE MATERIALIZED VIEW sum_gongre_branches_detail_data AS
WITH anchor_dates AS (
  SELECT
    (current_date - INTERVAL '1 day')::date AS biz_date,
    (current_date - INTERVAL '1 day' - INTERVAL '1 year')::date AS peer_date
),
window_defs AS (
  SELECT
    biz_date,
    peer_date,
    biz_date - INTERVAL '6 day' AS biz_7d_start,
    peer_date - INTERVAL '6 day' AS peer_7d_start,
    date_trunc('month', biz_date)::date AS biz_month_start,
    date_trunc('month', peer_date)::date AS peer_month_start,
    DATE '2025-10-01' AS biz_ytd_start,
    DATE '2024-10-01' AS peer_ytd_start
  FROM anchor_dates
)
SELECT
  d.company AS center,
  d.company_cn AS center_cn,
  d.sheet_name,
  d.item,
  d.item_cn,
  d.unit,
  w.biz_date,
  w.peer_date,
  COALESCE(SUM(d.value) FILTER (WHERE d.date = w.biz_date), 0) AS value_biz_date,
  COALESCE(SUM(d.value) FILTER (WHERE d.date = w.peer_date), 0) AS value_peer_date,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_7d_start AND w.biz_date
  ), 0) AS sum_7d_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_7d_start AND w.peer_date
  ), 0) AS sum_7d_peer,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_month_start AND w.biz_date
  ), 0) AS sum_month_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_month_start AND w.peer_date
  ), 0) AS sum_month_peer,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.biz_ytd_start AND w.biz_date
  ), 0) AS sum_ytd_biz,
  COALESCE(SUM(d.value) FILTER (
    WHERE d.date BETWEEN w.peer_ytd_start AND w.peer_date
  ), 0) AS sum_ytd_peer
FROM daily_basic_data d
CROSS JOIN window_defs w
WHERE d.date BETWEEN w.peer_ytd_start AND w.biz_date
  AND d.sheet_name = 'GongRe_branches_detail_Sheet'
GROUP BY
  d.company, d.company_cn, d.sheet_name, d.item, d.item_cn, d.unit,
  w.biz_date, w.peer_date;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sum_gongre_branches_center_item_bizdate
  ON sum_gongre_branches_detail_data (center, item, biz_date);

-- calc_sum_basic_data 物化视图
-- 在一级视图基础上补充各公司计算指标

CREATE TABLE IF NOT EXISTS period_map (
  scope  TEXT PRIMARY KEY,
  period TEXT NOT NULL
);
-- 与 constant_data.period 对齐：统一使用供暖期编码，如 '25-26'、'24-25'
INSERT INTO period_map(scope, period) VALUES
('value_biz_date','25-26'),
('sum_7d_biz','25-26'),
('sum_month_biz','25-26'),
('sum_ytd_biz','25-26'),
('value_peer_date','24-25'),
('sum_7d_peer','24-25'),
('sum_month_peer','24-25'),
('sum_ytd_peer','24-25')
ON CONFLICT (scope) DO NOTHING;

--行化视图
CREATE OR REPLACE VIEW v_sum_basic_long AS
SELECT company, company_cn, item, item_cn, unit, 'value_biz_date' AS scope, value_biz_date::numeric(18,4) AS val FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'value_peer_date', value_peer_date FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_7d_biz',     sum_7d_biz     FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_7d_peer',    sum_7d_peer    FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_month_biz',  sum_month_biz  FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_month_peer', sum_month_peer FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_ytd_biz',    sum_ytd_biz    FROM sum_basic_data
UNION ALL SELECT company, company_cn, item, item_cn, unit, 'sum_ytd_peer',   sum_ytd_peer   FROM sum_basic_data;

CREATE OR REPLACE VIEW v_sum_gongre_branches_long AS
SELECT center, center_cn, sheet_name, item, item_cn, unit, 'value_biz_date' AS scope, value_biz_date::numeric(18,4) AS val FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'value_peer_date', value_peer_date FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_7d_biz',     sum_7d_biz     FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_7d_peer',    sum_7d_peer    FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_month_biz',  sum_month_biz  FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_month_peer', sum_month_peer FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_ytd_biz',    sum_ytd_biz    FROM sum_gongre_branches_detail_data
UNION ALL SELECT center, center_cn, sheet_name, item, item_cn, unit, 'sum_ytd_peer',   sum_ytd_peer   FROM sum_gongre_branches_detail_data;


--常量查找视图
-- 统一键名：rate_sharing_ratio（如历史数据有“rate_sharing Ratio”，请在导入时改名）
CREATE OR REPLACE VIEW v_constants_center_first AS
SELECT
  COALESCE(NULLIF(TRIM(c.center), ''), NULLIF(TRIM(c.company), '')) AS key1,  -- center 优先
  TRIM(c.item) AS item,
  TRIM(c.period) AS period,
  c.value
FROM constant_data c;

-- 规范化常量项与 period、键名（小写、去空白、连字符转下划线、期别提取如 25-26）
CREATE OR REPLACE VIEW v_constants_center_first_norm AS
SELECT
  TRIM(key1) AS key1,
  LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(item), '[\s\-]+', '_', 'g'), '__+', '_', 'g')) AS item_key,
  COALESCE(
    NULLIF(SUBSTRING(period FROM '(\d{2}-\d{2})'), ''),
    REGEXP_REPLACE(LOWER(TRIM(period)), '(?i)\s*period\s*', '', 'g')
  ) AS period_key,
  value
FROM v_constants_center_first;

-- 公司优先版本（用于 company 维度的汇总计算）
CREATE OR REPLACE VIEW v_constants_company_first_norm AS
SELECT
  COALESCE(NULLIF(TRIM(c.company), ''), NULLIF(TRIM(c.center), '')) AS key1,
  LOWER(REGEXP_REPLACE(REGEXP_REPLACE(TRIM(c.item), '[\s\-]+', '_', 'g'), '__+', '_', 'g')) AS item_key,
  COALESCE(
    NULLIF(SUBSTRING(c.period FROM '(\d{2}-\d{2})'), ''),
    REGEXP_REPLACE(LOWER(TRIM(c.period)), '(?i)\s*period\s*', '', 'g')
  ) AS period_key,
  c.value
FROM constant_data c;

-- 口径映射封装（便于 JOIN）
CREATE OR REPLACE VIEW v_scope_period AS
SELECT scope, period FROM period_map;


--二级物化视图：company
DROP MATERIALIZED VIEW IF EXISTS calc_sum_basic_data;
CREATE MATERIALIZED VIEW calc_sum_basic_data AS
WITH b AS (
  SELECT company, company_cn, scope,
    -- 源项：按需继续补充（已覆盖你列出的核心项）
    SUM(CASE WHEN item='amount_power_sales' THEN val END) AS amount_power_sales,
    SUM(CASE WHEN item='amount_heat_supply' THEN val END) AS amount_heat_supply,
    SUM(CASE WHEN item='consumption_amount_raw_coal' THEN val END) AS coal,
    SUM(CASE WHEN item='consumption_std_coal' THEN val END) AS std_coal,
    SUM(CASE WHEN item='consumption_natural_gas' THEN val END) AS gas,
    SUM(CASE WHEN item='consumption_plant_purchased_power' THEN val END) AS plant_power,
    SUM(CASE WHEN item='consumption_plant_water' THEN val END) AS plant_water,
    SUM(CASE WHEN item='consumption_purchased_power' THEN val END) AS purchased_power,
    SUM(CASE WHEN item='consumption_purchased_heat' THEN val END) AS purchased_heat,
    SUM(CASE WHEN item='consumption_water' THEN val END) AS water,
    SUM(CASE WHEN item='consumption_acid' THEN val END) AS acid,
    SUM(CASE WHEN item='consumption_alkali' THEN val END) AS alkali,
    SUM(CASE WHEN item='consumption_oil' THEN val END) AS oil,
    SUM(CASE WHEN item='consumption_ammonia_water' THEN val END) AS ammo,
    SUM(CASE WHEN item='consumption_limestone' THEN val END) AS limestone,
    SUM(CASE WHEN item='consumption_limestone_powder' THEN val END) AS lime_pow,
    SUM(CASE WHEN item='consumption_magnesium_oxide' THEN val END) AS mag_oxide,
    SUM(CASE WHEN item='consumption_denitration_agent' THEN val END) AS den_agent,
    SUM(CASE WHEN item='consumption_station_purchased_power' THEN val END) AS station_power,
    SUM(CASE WHEN item='amount_network_interface_heat_supply' THEN val END) AS net_heat,
    SUM(CASE WHEN item='consumption_station_heat' THEN val END) AS station_heat,
    SUM(CASE WHEN item='amount_hot_water_sales' THEN val END) AS hot_water_sales,
    SUM(CASE WHEN item='amount_daily_net_complaints' THEN val END) AS daily_net_complaints,
    SUM(CASE WHEN item='amount_whole_heating_area' THEN val END) AS whole_area,
    SUM(CASE WHEN item='amount_heating_fee_area' THEN val END) AS fee_area
  FROM v_sum_basic_long
  GROUP BY company, company_cn, scope
),
c AS (
  SELECT
    b.*,
    MAX(CASE WHEN v.item_key='price_power_sales'         THEN v.value END) AS price_power_sales,
    MAX(CASE WHEN v.item_key='price_heat_sales'          THEN v.value END) AS price_heat_sales,
    MAX(CASE WHEN v.item_key='price_raw_coal'            THEN v.value END) AS price_raw_coal,
    MAX(CASE WHEN v.item_key='price_std_coal_comparable' THEN v.value END) AS price_std_coal_cmp,
    MAX(CASE WHEN v.item_key='price_purchased_power'     THEN v.value END) AS price_purch_power,
    MAX(CASE WHEN v.item_key='price_purchased_water'     THEN v.value END) AS price_water,
    MAX(CASE WHEN v.item_key='price_natural_gas'         THEN v.value END) AS price_gas,
    MAX(CASE WHEN v.item_key='price_acid'                THEN v.value END) AS price_acid,
    MAX(CASE WHEN v.item_key IN ('price_alkali','price_clkali') THEN v.value END) AS price_alkali,
    MAX(CASE WHEN v.item_key='price_oil'                 THEN v.value END) AS price_oil,
    MAX(CASE WHEN v.item_key IN ('price_ammonia_water','price_n_ammonia_water') THEN v.value END) AS price_ammo,
    MAX(CASE WHEN v.item_key='price_limestone'           THEN v.value END) AS price_limestone,
    MAX(CASE WHEN v.item_key='price_limestone_powder'    THEN v.value END) AS price_lime_pow,
    MAX(CASE WHEN v.item_key='price_magnesium_oxide'     THEN v.value END) AS price_mag_oxide,
    MAX(CASE WHEN v.item_key='price_denitration_agent'   THEN v.value END) AS price_den_agent,
    MAX(CASE WHEN v.item_key='price_purchased_heat'      THEN v.value END) AS price_purch_heat,
    MAX(CASE WHEN v.item_key='price_hot_water'           THEN v.value END) AS price_hot_water,
    MAX(CASE WHEN v.item_key IN ('eco_season_heating_income','season_heating_income') THEN v.value END) AS season_heating_income
  FROM b
  -- 仅保留按 scope 映射到具体 period 的连接
  JOIN v_scope_period sp2 ON sp2.scope = b.scope
  -- 常量表（公司优先）兼容公司英文/中文键名 + 键名与 period 规范化
  LEFT JOIN v_constants_company_first_norm v
         ON (v.key1 = b.company OR v.key1 = b.company_cn)
        AND v.period_key = sp2.period
  GROUP BY
    b.company, b.company_cn, b.scope,
    b.amount_power_sales, b.amount_heat_supply, b.coal, b.std_coal, b.gas, b.plant_power, b.plant_water,
    b.purchased_power, b.purchased_heat, b.water, b.acid, b.alkali, b.oil, b.ammo, b.limestone, b.lime_pow,
    b.mag_oxide, b.den_agent, b.station_power, b.net_heat, b.station_heat, b.hot_water_sales, b.daily_net_complaints,
    b.whole_area, b.fee_area
),
calc AS (
  SELECT
    company, company_cn, scope,

    -- ======== 通用收入/成本（万元） ========
    -- 售电收入：数量“万kWh” × 单价“元/kWh” = “万元”（无需再 /10000）
    (COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0)) AS eco_power_supply_income,
    -- 售热收入：GJ × 元/GJ → 元，再 /10000 转换为“万元”
    (COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0)) / 10000.0 AS eco_heat_supply_income,

    -- 直接收入（万元）= 售电收入（万元）+ 售热收入（万元）
    ( (COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0))
    + ((COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0)) / 10000.0) ) AS eco_direct_income,

    -- 煤成本、天然气成本、购电购水购热、辅材（万元）
    (COALESCE(coal,0) * COALESCE(price_raw_coal,0)) / 10000.0 AS eco_coal_cost,
    (COALESCE(gas,0) * COALESCE(price_gas,0)) / 10000.0 AS eco_natural_gas_cost,

    (COALESCE(plant_power,0) * COALESCE(price_purch_power,0)) / 10000.0 AS eco_purchased_power_cost,
    (COALESCE(plant_water,0) * COALESCE(price_water,0)) / 10000.0 AS eco_purchased_water_cost,

    (COALESCE(purchased_power,0) * COALESCE(price_purch_power,0)) / 10000.0 AS eco_purchased_power_cost_network,
    (COALESCE(water,0) * COALESCE(price_water,0)) / 10000.0 AS eco_purchased_water_cost_network,
    (COALESCE(purchased_heat,0) * COALESCE(price_purch_heat,0)) / 10000.0 AS eco_heat_cost,

    (COALESCE(acid,0)*COALESCE(price_acid,0)
    +COALESCE(alkali,0)*COALESCE(price_alkali,0)
    +COALESCE(oil,0)*COALESCE(price_oil,0)
    +COALESCE(ammo,0)*COALESCE(price_ammo,0)
    +COALESCE(limestone,0)*COALESCE(price_limestone,0)
    +COALESCE(lime_pow,0)*COALESCE(price_lime_pow,0)
    +COALESCE(mag_oxide,0)*COALESCE(price_mag_oxide,0)
    +COALESCE(den_agent,0)*COALESCE(price_den_agent,0)
    )/10000.0 AS eco_measurable_auxiliary_materials,

    -- 边际利润（公司组差异你可在前端显示时按公司过滤）
    (
      ((COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0))
      + (COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0))) 
      - (COALESCE(coal,0) * COALESCE(price_raw_coal,0))
      - (COALESCE(plant_power,0) * COALESCE(price_purch_power,0))
      - (COALESCE(plant_water,0) * COALESCE(price_water,0))
      - (COALESCE(acid,0)*COALESCE(price_acid,0) + COALESCE(alkali,0)*COALESCE(price_alkali,0)
         +COALESCE(oil,0)*COALESCE(price_oil,0) + COALESCE(ammo,0)*COALESCE(price_ammo,0)
         +COALESCE(limestone,0)*COALESCE(price_limestone,0) + COALESCE(lime_pow,0)*COALESCE(price_lime_pow,0)
         +COALESCE(mag_oxide,0)*COALESCE(price_mag_oxide,0) + COALESCE(den_agent,0)*COALESCE(price_den_agent,0))
    )/10000.0 AS eco_marginal_profit,

    -- 可比煤价边际（万元）
    (
      ((COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0))
      + (COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0)))
      - (COALESCE(purchased_power,0)*COALESCE(price_purch_power,0))
      - (COALESCE(water,0)*COALESCE(price_water,0))
      - (COALESCE(purchased_heat,0)*COALESCE(price_purch_heat,0))
      - (COALESCE(acid,0)*COALESCE(price_acid,0) + COALESCE(alkali,0)*COALESCE(price_alkali,0)
         +COALESCE(oil,0)*COALESCE(price_oil,0) + COALESCE(ammo,0)*COALESCE(price_ammo,0)
         +COALESCE(limestone,0)*COALESCE(price_limestone,0) + COALESCE(lime_pow,0)*COALESCE(price_lime_pow,0)
         +COALESCE(mag_oxide,0)*COALESCE(price_mag_oxide,0) + COALESCE(den_agent,0)*COALESCE(price_den_agent,0))
      - (COALESCE(std_coal,0)*COALESCE(price_std_coal_cmp,0))
    )/10000.0 AS eco_comparable_marginal_profit,

    -- 效率（无量纲）
    CASE WHEN COALESCE(std_coal,0) = 0 THEN NULL
      ELSE (COALESCE(amount_heat_supply,0) + COALESCE(amount_power_sales,0)*36.0) / (29.308*std_coal)
    END AS rate_overall_efficiency,

    -- GongRe 专用/泛用单耗
    CASE WHEN COALESCE(fee_area,0)=0 THEN NULL ELSE (COALESCE(station_heat,0)/fee_area) END AS rate_coal_per_10k_m2,
    CASE WHEN COALESCE(fee_area,0)=0 THEN NULL ELSE (COALESCE(purchased_power,0)/fee_area) END AS rate_power_per_10k_m2,
    CASE WHEN COALESCE(fee_area,0)=0 THEN NULL ELSE (COALESCE(water,0)/fee_area) END AS rate_water_per_10k_m2,

    -- 告警
    ARRAY_REMOVE(ARRAY[
      CASE WHEN price_power_sales IS NULL THEN 'price_power_sales' END,
      CASE WHEN price_heat_sales  IS NULL THEN 'price_heat_sales'  END
    ], NULL) AS missing_constants
  FROM c
)
SELECT
  company, company_cn, scope,
  -- 为了前端复用，这里把“新增计算项”也按 item 形式输出
  'eco_power_supply_income' AS item, '其中：售电收入' AS item_cn, '万元' AS unit, eco_power_supply_income AS value, missing_constants
FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_heat_supply_income','其中：售热收入','万元', eco_heat_supply_income, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_direct_income','直接收入','万元', eco_direct_income, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_coal_cost','煤成本','万元', eco_coal_cost, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_natural_gas_cost','天然气成本','万元', eco_natural_gas_cost, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_purchased_power_cost','外购电成本(厂)','万元', eco_purchased_power_cost, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_purchased_water_cost','购水成本(厂)','万元', eco_purchased_water_cost, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_measurable_auxiliary_materials','可计量辅材成本','万元', eco_measurable_auxiliary_materials, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_heat_cost','外购热成本','万元', eco_heat_cost, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_marginal_profit','边际利润','万元', eco_marginal_profit, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'eco_comparable_marginal_profit','可比煤价边际利润','万元', eco_comparable_marginal_profit, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'rate_overall_efficiency','全厂热效率','-', rate_overall_efficiency, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'rate_coal_per_10k_m2','供暖热单耗','GJ/万㎡', rate_coal_per_10k_m2, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'rate_power_per_10k_m2','供暖电单耗','万kWh/万㎡', rate_power_per_10k_m2, missing_constants FROM calc
UNION ALL SELECT company, company_cn, scope, 'rate_water_per_10k_m2','供暖水单耗','吨/万㎡', rate_water_per_10k_m2, missing_constants FROM calc
;
-- 为支持 REFRESH MATERIALIZED VIEW CONCURRENTLY，要求存在“无 WHERE 子句”的唯一索引
-- calc_sum_basic_data 行粒度：company + item + scope 唯一
CREATE UNIQUE INDEX IF NOT EXISTS ux_calc_sum_basic_company_item_scope
  ON calc_sum_basic_data (company, item, scope);


--二级物化视图：center
DROP MATERIALIZED VIEW IF EXISTS calc_sum_gongre_branches_detail_data;
CREATE MATERIALIZED VIEW calc_sum_gongre_branches_detail_data AS
WITH b AS (
  SELECT center, center_cn, scope,
    SUM(CASE WHEN item='rate_sharing_ratio' THEN val END) AS share_ratio,
    SUM(CASE WHEN item='consumption_water' THEN val END) AS water,
    SUM(CASE WHEN item='consumption_station_purchased_power' THEN val END) AS station_power,
    SUM(CASE WHEN item='amount_daily_net_complaints' THEN val END) AS daily_net_complaints
  FROM v_sum_gongre_branches_long
  GROUP BY center, center_cn, scope
),
-- 总公司（GongRe）用于分摊的两项
g AS (
  SELECT scope,
    SUM(CASE WHEN item='consumption_station_heat' THEN val END) AS gongre_station_heat,
    SUM(CASE WHEN item='amount_heat_lose' THEN val END) AS gongre_heat_lose
  FROM v_sum_basic_long
  WHERE company='GongRe'
  GROUP BY scope
),
c AS (
  SELECT
    b.center, b.center_cn, b.scope, b.share_ratio, b.water, b.station_power, b.daily_net_complaints,
    g.gongre_station_heat, g.gongre_heat_lose,
    MAX(CASE WHEN vc.item_key='amount_whole_heating_area' THEN vc.value END) AS whole_area,
    MAX(CASE WHEN vc.item_key IN ('eco_season_heating_income','season_heating_income') THEN vc.value END) AS season_heating_income,  -- 万元
    MAX(CASE WHEN vc.item_key='price_purchased_heat' THEN vc.value END) AS price_heat,                   -- 元/GJ
    MAX(CASE WHEN vc.item_key='price_purchased_water' THEN vc.value END) AS price_water,                 -- 元/吨
    MAX(CASE WHEN vc.item_key='price_purchased_power' THEN vc.value END) AS price_power                  -- 元/kWh
  FROM b
  LEFT JOIN g ON g.scope = b.scope
  JOIN v_scope_period sp ON sp.scope = b.scope
  LEFT JOIN v_constants_center_first_norm vc
    ON vc.period_key = sp.period AND (vc.key1 = b.center OR vc.key1='GongRe')
  GROUP BY b.center, b.center_cn, b.scope, b.share_ratio, b.water, b.station_power, b.daily_net_complaints,
           g.gongre_station_heat, g.gongre_heat_lose
),
calc AS (
  SELECT
    center, center_cn, scope,
    -- 分摊比按百分数
    (season_heating_income * COALESCE(share_ratio,0) / 100.0) AS eco_direct_income,                -- 万元
    (gongre_station_heat * price_heat * COALESCE(share_ratio,0) / 100.0) / 10000.0 AS eco_station_purchased_heat_cost, -- 万元
    (gongre_heat_lose * price_heat * COALESCE(share_ratio,0) / 100.0) / 10000.0 AS eco_heat_lose,  -- 万元
    (water * price_water) / 10000.0 AS eco_purchased_water_cost,                                   -- 万元
    (station_power * price_power) / 10000.0 AS eco_purchased_power_cost,                           -- 万元
    CASE WHEN COALESCE(whole_area,0)=0 THEN NULL ELSE (daily_net_complaints / whole_area) END AS amount_daily_net_complaints_per_10k_m2
  FROM c
)
SELECT center, center_cn, scope, 'eco_direct_income' AS item, '直接收入' AS item_cn, '万元' AS unit, eco_direct_income AS value FROM calc
UNION ALL SELECT center, center_cn, scope, 'eco_station_purchased_heat_cost','购热成本(分摊)','万元', eco_station_purchased_heat_cost FROM calc
UNION ALL SELECT center, center_cn, scope, 'eco_heat_lose','网损成本(分摊)','万元', eco_heat_lose FROM calc
UNION ALL SELECT center, center_cn, scope, 'eco_purchased_water_cost','购水成本','万元', eco_purchased_water_cost FROM calc
UNION ALL SELECT center, center_cn, scope, 'eco_purchased_power_cost','外购电成本','万元', eco_purchased_power_cost FROM calc
UNION ALL SELECT center, center_cn, scope, 'eco_marginal_profit','边际利润','万元',
  (eco_direct_income - eco_station_purchased_heat_cost - eco_heat_lose - eco_purchased_water_cost - eco_purchased_power_cost) FROM calc
UNION ALL SELECT center, center_cn, scope, 'amount_daily_net_complaints_per_10k_m2','万㎡净投诉','次/万㎡', amount_daily_net_complaints_per_10k_m2 FROM calc
;
-- 为支持 REFRESH MATERIALIZED VIEW CONCURRENTLY，要求存在“无 WHERE 子句”的唯一索引
-- calc_sum_gongre_branches_detail_data 行粒度：center + item + scope 唯一
CREATE UNIQUE INDEX IF NOT EXISTS ux_calc_sum_gongre_center_item_scope
  ON calc_sum_gongre_branches_detail_data (center, item, scope);


-- ======== 调试视图（仅用于排障，非物化） ========
-- 目的：暴露 calc_sum_basic_data 的中间输入与关键乘除过程，定位何处变 0
-- 使用：
--   SELECT * FROM calc_sum_basic_trace WHERE company='BeiHai' AND scope='sum_7d_biz';
--   或：WHERE company_cn='北海热电厂'
CREATE OR REPLACE VIEW calc_sum_basic_trace AS
WITH b AS (
  SELECT company, company_cn, scope,
    SUM(CASE WHEN item='amount_power_sales' THEN val END) AS amount_power_sales,
    SUM(CASE WHEN item='amount_heat_supply' THEN val END) AS amount_heat_supply
  FROM v_sum_basic_long
  GROUP BY company, company_cn, scope
),
sp2 AS (
  SELECT scope, period FROM v_scope_period
),
c AS (
  SELECT
    b.company, b.company_cn, b.scope, sp2.period,
    b.amount_power_sales, b.amount_heat_supply,
    MAX(CASE WHEN v.item_key='price_power_sales' THEN v.value END) AS price_power_sales,
    MAX(CASE WHEN v.item_key='price_heat_sales'  THEN v.value END) AS price_heat_sales
  FROM b
  JOIN sp2 ON sp2.scope = b.scope
  LEFT JOIN v_constants_company_first_norm v
         ON (v.key1 = b.company OR v.key1 = b.company_cn)
        AND v.period_key = sp2.period
  GROUP BY b.company, b.company_cn, b.scope, sp2.period,
           b.amount_power_sales, b.amount_heat_supply
)
SELECT
  company,
  company_cn,
  scope,
  period,
  amount_power_sales,
  price_power_sales,
  -- 乘积（售电）：按“万kWh × 元/kWh = 万元”，不再 /10000
  (COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0)) AS power_income_calc,
  amount_heat_supply,
  price_heat_sales,
  -- 乘积（售热）：GJ × 元/GJ → /10000 得万元
  (COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0)) / 10000.0 AS heat_income_calc,
  -- 汇总（万元）
  ( (COALESCE(amount_power_sales,0) * COALESCE(price_power_sales,0))
    + ((COALESCE(amount_heat_supply,0) * COALESCE(price_heat_sales,0)) / 10000.0) ) AS direct_income_calc,
  -- 缺失标记，便于一眼定位价格未命中情况
  (price_power_sales IS NULL) AS is_price_power_null,
  (price_heat_sales  IS NULL) AS is_price_heat_null
FROM c;
