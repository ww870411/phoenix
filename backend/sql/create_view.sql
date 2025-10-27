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
  d.center,
  d.center_cn,
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
FROM gongre_branches_detail_data d
CROSS JOIN window_defs w
WHERE d.date BETWEEN w.peer_ytd_start AND w.biz_date
GROUP BY
  d.center, d.center_cn, d.sheet_name, d.item, d.item_cn, d.unit,
  w.biz_date, w.peer_date;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sum_gongre_branches_center_item_bizdate
  ON sum_gongre_branches_detail_data (center, item, biz_date);

-- calc_sum_basic_data 物化视图
-- 在一级视图基础上补充各公司计算指标

DROP MATERIALIZED VIEW IF EXISTS calc_sum_basic_data;

CREATE MATERIALIZED VIEW calc_sum_basic_data AS
WITH base AS (
  SELECT * FROM sum_basic_data
),
item_meta AS (
  SELECT company, item,
         MAX(item_cn) AS item_cn,
         MAX(unit) AS unit
  FROM base
  GROUP BY company, item
),
constants_company AS (
  SELECT
    company,
    MAX(value) FILTER (WHERE item = 'price_power_sales' AND period = '25-26') AS price_power_sales_biz,
    MAX(value) FILTER (WHERE item = 'price_power_sales' AND period = '24-25') AS price_power_sales_peer,
    MAX(value) FILTER (WHERE item = 'price_heat_sales' AND period = '25-26') AS price_heat_sales_biz,
    MAX(value) FILTER (WHERE item = 'price_heat_sales' AND period = '24-25') AS price_heat_sales_peer,
    MAX(value) FILTER (WHERE item = 'price_raw_coal' AND period = '25-26') AS price_raw_coal_biz,
    MAX(value) FILTER (WHERE item = 'price_raw_coal' AND period = '24-25') AS price_raw_coal_peer,
    MAX(value) FILTER (WHERE item = 'price_natural_gas' AND period = '25-26') AS price_natural_gas_biz,
    MAX(value) FILTER (WHERE item = 'price_natural_gas' AND period = '24-25') AS price_natural_gas_peer,
    MAX(value) FILTER (WHERE item = 'price_purchased_power' AND period = '25-26') AS price_purchased_power_biz,
    MAX(value) FILTER (WHERE item = 'price_purchased_power' AND period = '24-25') AS price_purchased_power_peer,
    MAX(value) FILTER (WHERE item = 'price_purchased_water' AND period = '25-26') AS price_purchased_water_biz,
    MAX(value) FILTER (WHERE item = 'price_purchased_water' AND period = '24-25') AS price_purchased_water_peer,
    MAX(value) FILTER (WHERE item = 'price_acid' AND period = '25-26') AS price_acid_biz,
    MAX(value) FILTER (WHERE item = 'price_acid' AND period = '24-25') AS price_acid_peer,
    MAX(value) FILTER (WHERE item = 'price_clkali' AND period = '25-26') AS price_clkali_biz,
    MAX(value) FILTER (WHERE item = 'price_clkali' AND period = '24-25') AS price_clkali_peer,
    MAX(value) FILTER (WHERE item = 'price_oil' AND period = '25-26') AS price_oil_biz,
    MAX(value) FILTER (WHERE item = 'price_oil' AND period = '24-25') AS price_oil_peer,
    MAX(value) FILTER (WHERE item = 'price_n_ammonia_water' AND period = '25-26') AS price_ammonia_water_biz,
    MAX(value) FILTER (WHERE item = 'price_n_ammonia_water' AND period = '24-25') AS price_ammonia_water_peer,
    MAX(value) FILTER (WHERE item = 'price_limestone_powder' AND period = '25-26') AS price_limestone_powder_biz,
    MAX(value) FILTER (WHERE item = 'price_limestone_powder' AND period = '24-25') AS price_limestone_powder_peer,
    MAX(value) FILTER (WHERE item = 'price_std_coal_comparable' AND period = '25-26') AS price_std_coal_comparable_biz,
    MAX(value) FILTER (WHERE item = 'price_std_coal_comparable' AND period = '24-25') AS price_std_coal_comparable_peer,
    MAX(value) FILTER (WHERE item = 'eco_season_heating_income' AND period = '25-26') AS season_heating_income_biz,
    MAX(value) FILTER (WHERE item = 'eco_season_heating_income' AND period = '24-25') AS season_heating_income_peer,
    MAX(value) FILTER (WHERE item = 'amount_whole_heating_area' AND period = '25-26') AS amount_whole_heating_area_biz,
    MAX(value) FILTER (WHERE item = 'amount_whole_heating_area' AND period = '24-25') AS amount_whole_heating_area_peer,
    MAX(value) FILTER (WHERE item = 'amount_heating_fee_area' AND period = '25-26') AS amount_heating_fee_area_biz,
    MAX(value) FILTER (WHERE item = 'amount_heating_fee_area' AND period = '24-25') AS amount_heating_fee_area_peer,
    MAX(value) FILTER (WHERE item = 'price_purchased_heat' AND period = '25-26') AS price_purchased_heat_biz,
    MAX(value) FILTER (WHERE item = 'price_purchased_heat' AND period = '24-25') AS price_purchased_heat_peer,
    MAX(value) FILTER (WHERE item = 'price_hot_water' AND period = '25-26') AS price_hot_water_biz,
    MAX(value) FILTER (WHERE item = 'price_hot_water' AND period = '24-25') AS price_hot_water_peer,
    MAX(value) FILTER (WHERE item = 'price_limestone' AND period = '25-26') AS price_limestone_biz,
    MAX(value) FILTER (WHERE item = 'price_limestone' AND period = '24-25') AS price_limestone_peer,
    MAX(value) FILTER (WHERE item = 'price_magnesium_oxide' AND period = '25-26') AS price_magnesium_oxide_biz,
    MAX(value) FILTER (WHERE item = 'price_magnesium_oxide' AND period = '24-25') AS price_magnesium_oxide_peer,
    MAX(value) FILTER (WHERE item = 'price_denitration_agent' AND period = '25-26') AS price_denitration_agent_biz,
    MAX(value) FILTER (WHERE item = 'price_denitration_agent' AND period = '24-25') AS price_denitration_agent_peer
  FROM constant_data
  WHERE center IS NULL
  GROUP BY company
),
group1_common AS (
  SELECT
    company,
    company_cn,
    biz_date,
    peer_date,
    MAX(value_biz_date) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'amount_power_sales') AS amount_power_sales_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'amount_heat_supply') AS amount_heat_supply_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'consumption_amount_raw_coal') AS consumption_raw_coal_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'consumption_natural_gas') AS consumption_natural_gas_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'consumption_plant_purchased_power') AS consumption_plant_purchased_power_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'consumption_plant_water') AS consumption_plant_water_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_month_biz,
    MAX(sum_month_peer) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_month_peer,
    MAX(sum_ytd_biz) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_ytd_biz,
    MAX(sum_ytd_peer) FILTER (WHERE item = 'consumption_acid') AS consumption_acid_ytd_peer,
    MAX(value_biz_date) FILTER (WHERE item = 'consumption_alkali') AS consumption_alkali_biz,
    MAX(value_peer_date) FILTER (WHERE item = 'consumption_alkali') AS consumption_alkali_peer,
    MAX(sum_7d_biz) FILTER (WHERE item = 'consumption_alkali') AS consumption_alkali_7d_biz,
    MAX(sum_7d_peer) FILTER (WHERE item = 'consumption_alkali') AS consumption_alkali_7d_peer,
    MAX(sum_month_biz) FILTER (WHERE item = 'consumption_alkali
