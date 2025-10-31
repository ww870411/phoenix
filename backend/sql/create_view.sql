
-- ========= 一级汇总视图（公司粒度，无分组口径） =========
-- sum_basic_data：仅保留“公司明细粒度”的 8 个口径聚合
-- 口径：按 company / item 汇总每日基础数据，对 biz_date（当前系统日前一天）及其同期日计算 8 个指标：
--   value_biz_date / value_peer_date / sum_7d_biz / sum_7d_peer / sum_month_biz / sum_month_peer / sum_ytd_biz / sum_ytd_peer
-- 注意：原先在本视图内内联输出的“主城区/集团”分组已移除，现迁移到独立视图 `groups`（依赖本视图进行再聚合）。
-- 使用前请确认 daily_basic_data 表结构与 value/date 字段命名一致，并在生产环境执行前先在测试库验证。
-- 默认创建在当前 search_path 指向的 schema（通常为 public），如需单独 schema 可在执行前 SET search_path。

DROP VIEW IF EXISTS sum_basic_data;

CREATE VIEW sum_basic_data AS

WITH params AS (
  SELECT COALESCE(current_setting('phoenix.biz_date', true)::date, (current_date - INTERVAL '1 day')::date) AS biz_date
),
anchor_dates AS (
  SELECT
    p.biz_date,
    (p.biz_date - INTERVAL '1 year')::date AS peer_date
  FROM params p
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
    DATE '2024-10-01' AS peer_ytd_start,
    -- heating-season period encoding, e.g. 25-26 / 24-25
    EXTRACT(YEAR FROM biz_date)::int AS biz_year,
    EXTRACT(YEAR FROM peer_date)::int AS peer_year,
    CASE
      WHEN biz_date >= make_date(EXTRACT(YEAR FROM biz_date)::int, 10, 1)
      THEN LPAD(((EXTRACT(YEAR FROM biz_date)::int) % 100)::text, 2, '0') || '-' ||
           LPAD((((EXTRACT(YEAR FROM biz_date)::int)+1) % 100)::text, 2, '0')
      ELSE LPAD((((EXTRACT(YEAR FROM biz_date)::int)-1) % 100)::text, 2, '0') || '-' ||
           LPAD(((EXTRACT(YEAR FROM biz_date)::int) % 100)::text, 2, '0')
    END AS biz_period,
    CASE
      WHEN peer_date >= make_date(EXTRACT(YEAR FROM peer_date)::int, 10, 1)
      THEN LPAD(((EXTRACT(YEAR FROM peer_date)::int) % 100)::text, 2, '0') || '-' ||
           LPAD((((EXTRACT(YEAR FROM peer_date)::int)+1) % 100)::text, 2, '0')
      ELSE LPAD((((EXTRACT(YEAR FROM peer_date)::int)-1) % 100)::text, 2, '0') || '-' ||
           LPAD(((EXTRACT(YEAR FROM peer_date)::int) % 100)::text, 2, '0')
    END AS peer_period,
    -- days_to_biz() per scope (inclusive)
    1::int AS days_day_biz,
    1::int AS days_day_peer,
    7::int AS days_7_biz,
    7::int AS days_7_peer,
    (biz_date - date_trunc('month', biz_date)::date + 1)::int AS days_month_biz,
    (peer_date - date_trunc('month', peer_date)::date + 1)::int AS days_month_peer,
    (biz_date - DATE '2025-10-01' + 1)::int AS days_ytd_biz,
    (peer_date - DATE '2024-10-01' + 1)::int AS days_ytd_peer
  FROM anchor_dates
),
-- base：原公司粒度的每日/同期值与各窗口累计（保持与原视图一致的输出列顺序）
base AS (
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
    w.biz_date, w.peer_date
),
const_biz AS (
  SELECT c.company, c.item, MAX(c.value) AS value
  FROM constant_data c
  CROSS JOIN window_defs w
  WHERE c.period = w.biz_period
  GROUP BY c.company, c.item
),
const_peer AS (
  SELECT c.company, c.item, MAX(c.value) AS value
  FROM constant_data c
  CROSS JOIN window_defs w
  WHERE c.period = w.peer_period
  GROUP BY c.company, c.item
),
calc_station_heat AS (
  -- 站内耗热量（GJ）：特殊公司用 供热量-高温水销售量，其它公司用底表同名项
  SELECT
    b.company,
    b.company_cn,
    'consumption_station_heat'::text AS item,
    '站内耗热量'::text               AS item_cn,
    'GJ'::text                       AS unit,
    MAX(b.biz_date)                  AS biz_date,
    MAX(b.peer_date)                 AS peer_date,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_biz_date ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_biz_date ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.value_biz_date ELSE 0 END)
      END
    ),0) AS value_biz_date,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_peer_date ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_peer_date ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.value_peer_date ELSE 0 END)
      END
    ),0) AS value_peer_date,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_biz ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_biz ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_7d_biz ELSE 0 END)
      END
    ),0) AS sum_7d_biz,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_peer ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_peer ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_7d_peer ELSE 0 END)
      END
    ),0) AS sum_7d_peer,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_biz ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_biz ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_month_biz ELSE 0 END)
      END
    ),0) AS sum_month_biz,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_peer ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_peer ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_month_peer ELSE 0 END)
      END
    ),0) AS sum_month_peer,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_biz ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_biz ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_ytd_biz ELSE 0 END)
      END
    ),0) AS sum_ytd_biz,
    COALESCE((
      CASE WHEN b.company IN ('JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
           THEN (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_peer ELSE 0 END)
                 - SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_peer ELSE 0 END))
           ELSE SUM(CASE WHEN b.item='consumption_station_heat' THEN b.sum_ytd_peer ELSE 0 END)
      END
    ),0) AS sum_ytd_peer
  FROM base b
  GROUP BY b.company, b.company_cn
),
calc_amount_daily_net_complaints_per_10k_m2 AS (
  -- 万平方米省市净投诉量 = 当日撤件后净投诉量 / c.挂网面积（单位：件/万㎡）
  SELECT
    b.company,
    b.company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text                   AS item_cn,
    '件/万㎡'::text                                 AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.value_biz_date ELSE 0 END),0) / NULLIF(COALESCE(cb_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.value_peer_date ELSE 0 END),0) / NULLIF(COALESCE(cp_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_7d_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_7d_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_month_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_month_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_ytd_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_area.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='amount_daily_net_complaints' THEN b.sum_ytd_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_area.value,0),0)
  FROM base b
  LEFT JOIN const_biz  cb_area ON cb_area.company=b.company AND cb_area.item='amount_whole_heating_area'
  LEFT JOIN const_peer cp_area ON cp_area.company=b.company AND cp_area.item='amount_whole_heating_area'
  GROUP BY b.company, b.company_cn, cb_area.value, cp_area.value
),
calc_rate_std_coal_per_heat AS (
  -- 供热标煤单耗 = 标煤耗量 / c.供暖收费面积（单位：吨/万㎡）
  SELECT
    b.company,
    b.company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text           AS item_cn,
    '吨/万㎡'::text                 AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_biz_date ELSE 0 END),0) / NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_peer_date ELSE 0 END),0) / NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_biz ELSE 0 END),0) / NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_peer ELSE 0 END),0) / NULLIF(COALESCE(cp_fee.value,0),0)
  FROM base b
  LEFT JOIN const_biz  cb_fee ON cb_fee.company=b.company AND cb_fee.item='amount_heating_fee_area'
  LEFT JOIN const_peer cp_fee ON cp_fee.company=b.company AND cp_fee.item='amount_heating_fee_area'
  GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
),
calc_rate_heat_per_10k_m2 AS (
  -- 供暖热单耗 = 站内耗热量 / c.供暖收费面积（单位：GJ/万㎡）
  SELECT
    sh.company,
    sh.company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text           AS item_cn,
    'GJ/万㎡'::text               AS unit,
    MAX(sh.biz_date),
    MAX(sh.peer_date),
    COALESCE(sh.value_biz_date,0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(sh.value_peer_date,0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(sh.sum_7d_biz,0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(sh.sum_7d_peer,0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(sh.sum_month_biz,0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(sh.sum_month_peer,0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(sh.sum_ytd_biz,0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(sh.sum_ytd_peer,0)/NULLIF(COALESCE(cp_fee.value,0),0)
  FROM calc_station_heat sh
  LEFT JOIN const_biz  cb_fee ON cb_fee.company=sh.company AND cb_fee.item='amount_heating_fee_area'
  LEFT JOIN const_peer cp_fee ON cp_fee.company=sh.company AND cp_fee.item='amount_heating_fee_area'
  GROUP BY sh.company, sh.company_cn, sh.value_biz_date, sh.value_peer_date, sh.sum_7d_biz, sh.sum_7d_peer, sh.sum_month_biz, sh.sum_month_peer, sh.sum_ytd_biz, sh.sum_ytd_peer,
           cb_fee.value, cp_fee.value
),
calc_rate_power_per_10k_m2 AS (
  -- 供暖电单耗 = （其中：换热站外购电量）×10000 / c.供暖收费面积（单位：kWh/万㎡）
  SELECT
    b.company,
    b.company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text            AS item_cn,
    'kWh/万㎡'::text               AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.value_biz_date ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cb_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.value_peer_date ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cp_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_7d_biz ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cb_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_7d_peer ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cp_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_month_biz ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cb_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_month_peer ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cp_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_ytd_biz ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cb_fee.value,0),0),
    (COALESCE(SUM(CASE WHEN b.item='consumption_station_purchased_power' THEN b.sum_ytd_peer ELSE 0 END),0)*10000.0)/NULLIF(COALESCE(cp_fee.value,0),0)
  FROM base b
  LEFT JOIN const_biz  cb_fee ON cb_fee.company=b.company AND cb_fee.item='amount_heating_fee_area'
  LEFT JOIN const_peer cp_fee ON cp_fee.company=b.company AND cp_fee.item='amount_heating_fee_area'
  GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
),
calc_rate_water_per_10k_m2 AS (
  -- 供暖水单耗 = （电厂一次网补水量 + 换热站补水量 + 热网补水量）/ c.供暖收费面积（单位：吨/万㎡）
  SELECT
    b.company,
    b.company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text            AS item_cn,
    '吨/万㎡'::text                AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.value_biz_date ELSE 0 END),0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.value_peer_date ELSE 0 END),0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_7d_biz ELSE 0 END),0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_7d_peer ELSE 0 END),0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_month_biz ELSE 0 END),0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_month_peer ELSE 0 END),0)/NULLIF(COALESCE(cp_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_ytd_biz ELSE 0 END),0)/NULLIF(COALESCE(cb_fee.value,0),0),
    COALESCE(SUM(CASE WHEN b.item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN b.sum_ytd_peer ELSE 0 END),0)/NULLIF(COALESCE(cp_fee.value,0),0)
  FROM base b
  LEFT JOIN const_biz  cb_fee ON cb_fee.company=b.company AND cb_fee.item='amount_heating_fee_area'
  LEFT JOIN const_peer cp_fee ON cp_fee.company=b.company AND cp_fee.item='amount_heating_fee_area'
  GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
),
calc_amount_heat_lose AS (
  -- 网损热量（仅 GongRe）：网口供热量 − 高温水销售量 − 售汽量*2.9518 − 站内耗热量（单位：GJ）
  SELECT
    b.company,
    b.company_cn,
    'amount_heat_lose'::text AS item,
    '网损热量'::text         AS item_cn,
    'GJ'::text               AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.value_biz_date ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_biz_date ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.value_biz_date ELSE 0 END),0)
      - COALESCE(MAX(sh.value_biz_date),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.value_peer_date ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_peer_date ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.value_peer_date ELSE 0 END),0)
      - COALESCE(MAX(sh.value_peer_date),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_7d_biz ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_biz ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_7d_biz ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_7d_biz),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_7d_peer ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_peer ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_7d_peer ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_7d_peer),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_month_biz ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_biz ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_month_biz ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_month_biz),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_month_peer ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_peer ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_month_peer ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_month_peer),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_ytd_biz ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_biz ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_ytd_biz ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_ytd_biz),0),
    COALESCE(SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_ytd_peer ELSE 0 END),0)
      - COALESCE(SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_peer ELSE 0 END),0)
      - 2.9518*COALESCE(SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_ytd_peer ELSE 0 END),0)
      - COALESCE(MAX(sh.sum_ytd_peer),0)
  FROM base b
  LEFT JOIN calc_station_heat sh ON sh.company=b.company
  WHERE b.company='GongRe'
  GROUP BY b.company, b.company_cn
),
calc_power AS (
  -- 其中：售电收入（万元）
  SELECT
    b.company,
    b.company_cn,
    'eco_power_supply_income'::text AS item,
    '其中：售电收入'::text        AS item_cn,
    '万元'::text                 AS unit,
    MAX(b.biz_date)              AS biz_date,
    MAX(b.peer_date)             AS peer_date,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ps.value,0)) AS value_biz_date,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ps.value,0)) AS value_peer_date,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ps.value,0)) AS sum_7d_biz,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ps.value,0)) AS sum_7d_peer,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ps.value,0)) AS sum_month_biz,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ps.value,0)) AS sum_month_peer,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ps.value,0)) AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ps.value,0)) AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_ps ON cb_ps.company=b.company AND cb_ps.item='price_power_sales'
  LEFT JOIN const_peer cp_ps ON cp_ps.company=b.company AND cp_ps.item='price_power_sales'
  GROUP BY b.company, b.company_cn, cb_ps.value, cp_ps.value
),
calc_inner_heat AS (
  -- 其中：内售热收入（万元）= 供热量 × 内售热单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_inner_heat_supply_income'::text AS item,
    '其中：内售热收入'::text              AS item_cn,
    '万元'::text                         AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_hin.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_hin.value,0))/10000.0
  FROM base b
  LEFT JOIN const_biz  cb_hin ON cb_hin.company=b.company AND cb_hin.item='price_inner_heat_sales'
  LEFT JOIN const_peer cp_hin ON cp_hin.company=b.company AND cp_hin.item='price_inner_heat_sales'
  GROUP BY b.company, b.company_cn, cb_hin.value, cp_hin.value
),
calc_heating_income AS (
  -- 其中：暖收入（万元）= c.采暖期供暖收入 × days_to_biz() / 157
  SELECT
    b.company,
    b.company_cn,
    'eco_heating_supply_income'::text AS item,
    '其中：暖收入'::text               AS item_cn,
    '万元'::text                      AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    COALESCE(cb_sh.value,0) * (SELECT days_day_biz    FROM window_defs) / 157.0,
    COALESCE(cp_sh.value,0) * (SELECT days_day_peer   FROM window_defs) / 157.0,
    COALESCE(cb_sh.value,0) * (SELECT days_7_biz      FROM window_defs) / 157.0,
    COALESCE(cp_sh.value,0) * (SELECT days_7_peer     FROM window_defs) / 157.0,
    COALESCE(cb_sh.value,0) * (SELECT days_month_biz  FROM window_defs) / 157.0,
    COALESCE(cp_sh.value,0) * (SELECT days_month_peer FROM window_defs) / 157.0,
    COALESCE(cb_sh.value,0) * (SELECT days_ytd_biz    FROM window_defs) / 157.0,
    COALESCE(cp_sh.value,0) * (SELECT days_ytd_peer   FROM window_defs) / 157.0
  FROM base b
  LEFT JOIN const_biz  cb_sh ON cb_sh.company=b.company AND cb_sh.item='eco_season_heating_income'
  LEFT JOIN const_peer cp_sh ON cp_sh.company=b.company AND cp_sh.item='eco_season_heating_income'
  GROUP BY b.company, b.company_cn, cb_sh.value, cp_sh.value
),
calc_hot_water AS (
  -- 其中：售高温水收入（万元）= 高温水销售量 × 售高温水单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_hot_water_supply_income'::text AS item,
    '其中：售高温水收入'::text           AS item_cn,
    '万元'::text                        AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_hw.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_hot_water_sales' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_hw.value,0))/10000.0
  FROM base b
  LEFT JOIN const_biz  cb_hw ON cb_hw.company=b.company AND cb_hw.item='price_hot_water_sales'
  LEFT JOIN const_peer cp_hw ON cp_hw.company=b.company AND cp_hw.item='price_hot_water_sales'
  GROUP BY b.company, b.company_cn, cb_hw.value, cp_hw.value
),
calc_steam AS (
  -- 其中：售汽收入（万元）= 售汽量 × 售汽单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_steam_supply_income'::text AS item,
    '其中：售汽收入'::text           AS item_cn,
    '万元'::text                    AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ss.value,0))/10000.0,
    (SUM(CASE WHEN b.item='amount_steam_sales' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ss.value,0))/10000.0
  FROM base b
  LEFT JOIN const_biz  cb_ss ON cb_ss.company=b.company AND cb_ss.item='price_steam_sales'
  LEFT JOIN const_peer cp_ss ON cp_ss.company=b.company AND cp_ss.item='price_steam_sales'
  GROUP BY b.company, b.company_cn, cb_ss.value, cp_ss.value
),
calc_coal_cost AS (
  -- 煤成本（万元）= 原煤耗量 × 原煤单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_coal_cost'::text AS item,
    '煤成本'::text        AS item_cn,
    '万元'::text          AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_rc.value,0))/10000.0 AS value_biz_date,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_rc.value,0))/10000.0 AS value_peer_date,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_rc.value,0))/10000.0 AS sum_7d_biz,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_rc.value,0))/10000.0 AS sum_7d_peer,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_rc.value,0))/10000.0 AS sum_month_biz,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_rc.value,0))/10000.0 AS sum_month_peer,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_rc.value,0))/10000.0 AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='consumption_amount_raw_coal' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_rc.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_rc ON cb_rc.company=b.company AND cb_rc.item='price_raw_coal'
  LEFT JOIN const_peer cp_rc ON cp_rc.company=b.company AND cp_rc.item='price_raw_coal'
  GROUP BY b.company, b.company_cn, cb_rc.value, cp_rc.value
),
calc_natural_gas_cost AS (
  -- 天然气成本（万元）= 耗天然气量 × 购天然气单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_natural_gas_cost'::text AS item,
    '天然气成本'::text            AS item_cn,
    '万元'::text                  AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ng.value,0))/10000.0 AS value_biz_date,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ng.value,0))/10000.0 AS value_peer_date,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ng.value,0))/10000.0 AS sum_7d_biz,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ng.value,0))/10000.0 AS sum_7d_peer,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ng.value,0))/10000.0 AS sum_month_biz,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ng.value,0))/10000.0 AS sum_month_peer,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ng.value,0))/10000.0 AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='consumption_natural_gas' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ng.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_ng ON cb_ng.company=b.company AND cb_ng.item='price_natural_gas'
  LEFT JOIN const_peer cp_ng ON cp_ng.company=b.company AND cp_ng.item='price_natural_gas'
  GROUP BY b.company, b.company_cn, cb_ng.value, cp_ng.value
),
calc_purchased_power_cost AS (
  -- 外购电成本（万元）= 外购电量 × 外购电单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_purchased_power_cost'::text AS item,
    '外购电成本'::text               AS item_cn,
    '万元'::text                     AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_pp.value,0)) AS value_biz_date,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_pp.value,0)) AS value_peer_date,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_pp.value,0)) AS sum_7d_biz,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_pp.value,0)) AS sum_7d_peer,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_pp.value,0)) AS sum_month_biz,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_pp.value,0)) AS sum_month_peer,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_pp.value,0)) AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='consumption_purchased_power' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_pp.value,0)) AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_pp ON cb_pp.company=b.company AND cb_pp.item='price_purchased_power'
  LEFT JOIN const_peer cp_pp ON cp_pp.company=b.company AND cp_pp.item='price_purchased_power'
  GROUP BY b.company, b.company_cn, cb_pp.value, cp_pp.value
),
calc_purchased_water_cost AS (
  -- 购水成本（万元）= 耗水量 × 购水单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_purchased_water_cost'::text AS item,
    '购水成本'::text                 AS item_cn,
    '万元'::text                     AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_pw.value,0))/10000.0 AS value_biz_date,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_pw.value,0))/10000.0 AS value_peer_date,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_pw.value,0))/10000.0 AS sum_7d_biz,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_pw.value,0))/10000.0 AS sum_7d_peer,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_pw.value,0))/10000.0 AS sum_month_biz,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_pw.value,0))/10000.0 AS sum_month_peer,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_pw.value,0))/10000.0 AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='consumption_water' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_pw.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_pw ON cb_pw.company=b.company AND cb_pw.item='price_purchased_water'
  LEFT JOIN const_peer cp_pw ON cp_pw.company=b.company AND cp_pw.item='price_purchased_water'
  GROUP BY b.company, b.company_cn, cb_pw.value, cp_pw.value
),
calc_aux_cost AS (
  -- 可计量辅材成本（万元）
  SELECT
    b.company,
    b.company_cn,
    'eco_measurable_auxiliary_materials'::text AS item,
    '可计量辅材成本'::text                      AS item_cn,
    '万元'::text                                AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_dn.value,0))
    )/10000.0 AS value_biz_date,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_dn.value,0))
    )/10000.0 AS value_peer_date,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_dn.value,0))
    )/10000.0 AS sum_7d_biz,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_dn.value,0))
    )/10000.0 AS sum_7d_peer,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_dn.value,0))
    )/10000.0 AS sum_month_biz,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_dn.value,0))
    )/10000.0 AS sum_month_peer,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_dn.value,0))
    )/10000.0 AS sum_ytd_biz,
    (
      (SUM(CASE WHEN b.item='consumption_acid'             THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ac.value,0)) +
      (SUM(CASE WHEN b.item='consumption_alkali'           THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_al.value,0)) +
      (SUM(CASE WHEN b.item='consumption_oil'              THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ol.value,0)) +
      (SUM(CASE WHEN b.item='consumption_ammonia_water'    THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_aw.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone'        THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ls.value,0)) +
      (SUM(CASE WHEN b.item='consumption_limestone_powder' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_lsp.value,0)) +
      (SUM(CASE WHEN b.item='consumption_magnesium_oxide'  THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_mg.value,0)) +
      (SUM(CASE WHEN b.item='consumption_denitration_agent' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_dn.value,0))
    )/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_ac  ON cb_ac.company=b.company  AND cb_ac.item='price_acid'
  LEFT JOIN const_peer cp_ac  ON cp_ac.company=b.company  AND cp_ac.item='price_acid'
  LEFT JOIN const_biz  cb_al  ON cb_al.company=b.company  AND cb_al.item='price_alkali'
  LEFT JOIN const_peer cp_al  ON cp_al.company=b.company  AND cp_al.item='price_alkali'
  LEFT JOIN const_biz  cb_ol  ON cb_ol.company=b.company  AND cb_ol.item='price_oil'
  LEFT JOIN const_peer cp_ol  ON cp_ol.company=b.company  AND cp_ol.item='price_oil'
  LEFT JOIN const_biz  cb_aw  ON cb_aw.company=b.company  AND cb_aw.item='price_n_ammonia_water'
  LEFT JOIN const_peer cp_aw  ON cp_aw.company=b.company  AND cp_aw.item='price_n_ammonia_water'
  LEFT JOIN const_biz  cb_ls  ON cb_ls.company=b.company  AND cb_ls.item='price_limestone'
  LEFT JOIN const_peer cp_ls  ON cp_ls.company=b.company  AND cp_ls.item='price_limestone'
  LEFT JOIN const_biz  cb_lsp ON cb_lsp.company=b.company AND cb_lsp.item='price_limestone_powder'
  LEFT JOIN const_peer cp_lsp ON cp_lsp.company=b.company AND cp_lsp.item='price_limestone_powder'
  LEFT JOIN const_biz  cb_mg  ON cb_mg.company=b.company  AND cb_mg.item='price_magnesium_oxide'
  LEFT JOIN const_peer cp_mg  ON cp_mg.company=b.company  AND cp_mg.item='price_magnesium_oxide'
  LEFT JOIN const_biz  cb_dn  ON cb_dn.company=b.company  AND cb_dn.item='price_denitration_agent'
  LEFT JOIN const_peer cp_dn  ON cp_dn.company=b.company  AND cp_dn.item='price_denitration_agent'
  GROUP BY b.company, b.company_cn,
           cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value,
           cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value,
           cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
),
calc_outer_heat_cost AS (
  -- 外购热成本（万元）= 外购热量 × 外购热单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_outer_heat_cost'::text AS item,
    '外购热成本'::text          AS item_cn,
    '万元'::text                AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_oh.value,0))/10000.0 AS value_biz_date,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_oh.value,0))/10000.0 AS value_peer_date,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_oh.value,0))/10000.0 AS sum_7d_biz,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_oh.value,0))/10000.0 AS sum_7d_peer,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_oh.value,0))/10000.0 AS sum_month_biz,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_oh.value,0))/10000.0 AS sum_month_peer,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_oh.value,0))/10000.0 AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_oh.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_oh ON cb_oh.company=b.company AND cb_oh.item='price_outer_purchased_heat'
  LEFT JOIN const_peer cp_oh ON cp_oh.company=b.company AND cp_oh.item='price_outer_purchased_heat'
  GROUP BY b.company, b.company_cn, cb_oh.value, cp_oh.value
),
calc_inner_purchased_heat_cost AS (
  -- 内购热成本（万元）= 网口供热量 × 内购热单价 / 10000
  SELECT
    b.company,
    b.company_cn,
    'eco_inner_purchased_heat_cost'::text AS item,
    '内购热成本'::text                     AS item_cn,
    '万元'::text                           AS unit,
    MAX(b.biz_date) AS biz_date,
    MAX(b.peer_date) AS peer_date,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_ih.value,0))/10000.0 AS value_biz_date,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_ih.value,0))/10000.0 AS value_peer_date,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_ih.value,0))/10000.0 AS sum_7d_biz,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_ih.value,0))/10000.0 AS sum_7d_peer,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_ih.value,0))/10000.0 AS sum_month_biz,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_ih.value,0))/10000.0 AS sum_month_peer,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_ih.value,0))/10000.0 AS sum_ytd_biz,
    (SUM(CASE WHEN b.item='amount_network_interface_heat_supply' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_ih.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_ih ON cb_ih.company=b.company AND cb_ih.item='price_inner_purchased_heat'
  LEFT JOIN const_peer cp_ih ON cp_ih.company=b.company AND cp_ih.item='price_inner_purchased_heat'
  GROUP BY b.company, b.company_cn, cb_ih.value, cp_ih.value
),
calc_direct_income AS (
  -- 直接收入（万元）= 售电 + 内售热 + 暖收入 + 售高温水 + 售汽
  SELECT
    c.company,
    c.company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text           AS item_cn,
    '万元'::text               AS unit,
    MAX(c.biz_date)            AS biz_date,
    MAX(c.peer_date)           AS peer_date,
    SUM(c.value_biz_date)      AS value_biz_date,
    SUM(c.value_peer_date)     AS value_peer_date,
    SUM(c.sum_7d_biz)          AS sum_7d_biz,
    SUM(c.sum_7d_peer)         AS sum_7d_peer,
    SUM(c.sum_month_biz)       AS sum_month_biz,
    SUM(c.sum_month_peer)      AS sum_month_peer,
    SUM(c.sum_ytd_biz)         AS sum_ytd_biz,
    SUM(c.sum_ytd_peer)        AS sum_ytd_peer
  FROM (
    SELECT * FROM calc_power
    UNION ALL SELECT * FROM calc_inner_heat
    UNION ALL SELECT * FROM calc_heating_income
    UNION ALL SELECT * FROM calc_hot_water
    UNION ALL SELECT * FROM calc_steam
  ) c
  GROUP BY c.company, c.company_cn
),
calc_marginal_profit AS (
  -- 边际利润（万元）= 直接收入 - 各类成本（煤/气/外购电/购水/辅材/外购热/内购热）
  SELECT
    di.company,
    di.company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text            AS item_cn,
    '万元'::text                AS unit,
    di.biz_date,
    di.peer_date,
    di.value_biz_date - (COALESCE(ng.value_biz_date,0)+COALESCE(pp.value_biz_date,0)+COALESCE(pw.value_biz_date,0)+COALESCE(am.value_biz_date,0)+COALESCE(oh.value_biz_date,0)+COALESCE(ih.value_biz_date,0)+COALESCE(rc.value_biz_date,0)) AS value_biz_date,
    di.value_peer_date - (COALESCE(ng.value_peer_date,0)+COALESCE(pp.value_peer_date,0)+COALESCE(pw.value_peer_date,0)+COALESCE(am.value_peer_date,0)+COALESCE(oh.value_peer_date,0)+COALESCE(ih.value_peer_date,0)+COALESCE(rc.value_peer_date,0)) AS value_peer_date,
    di.sum_7d_biz - (COALESCE(ng.sum_7d_biz,0)+COALESCE(pp.sum_7d_biz,0)+COALESCE(pw.sum_7d_biz,0)+COALESCE(am.sum_7d_biz,0)+COALESCE(oh.sum_7d_biz,0)+COALESCE(ih.sum_7d_biz,0)+COALESCE(rc.sum_7d_biz,0)) AS sum_7d_biz,
    di.sum_7d_peer - (COALESCE(ng.sum_7d_peer,0)+COALESCE(pp.sum_7d_peer,0)+COALESCE(pw.sum_7d_peer,0)+COALESCE(am.sum_7d_peer,0)+COALESCE(oh.sum_7d_peer,0)+COALESCE(ih.sum_7d_peer,0)+COALESCE(rc.sum_7d_peer,0)) AS sum_7d_peer,
    di.sum_month_biz - (COALESCE(ng.sum_month_biz,0)+COALESCE(pp.sum_month_biz,0)+COALESCE(pw.sum_month_biz,0)+COALESCE(am.sum_month_biz,0)+COALESCE(oh.sum_month_biz,0)+COALESCE(ih.sum_month_biz,0)+COALESCE(rc.sum_month_biz,0)) AS sum_month_biz,
    di.sum_month_peer - (COALESCE(ng.sum_month_peer,0)+COALESCE(pp.sum_month_peer,0)+COALESCE(pw.sum_month_peer,0)+COALESCE(am.sum_month_peer,0)+COALESCE(oh.sum_month_peer,0)+COALESCE(ih.sum_month_peer,0)+COALESCE(rc.sum_month_peer,0)) AS sum_month_peer,
    di.sum_ytd_biz - (COALESCE(ng.sum_ytd_biz,0)+COALESCE(pp.sum_ytd_biz,0)+COALESCE(pw.sum_ytd_biz,0)+COALESCE(am.sum_ytd_biz,0)+COALESCE(oh.sum_ytd_biz,0)+COALESCE(ih.sum_ytd_biz,0)+COALESCE(rc.sum_ytd_biz,0)) AS sum_ytd_biz,
    di.sum_ytd_peer - (COALESCE(ng.sum_ytd_peer,0)+COALESCE(pp.sum_ytd_peer,0)+COALESCE(pw.sum_ytd_peer,0)+COALESCE(am.sum_ytd_peer,0)+COALESCE(oh.sum_ytd_peer,0)+COALESCE(ih.sum_ytd_peer,0)+COALESCE(rc.sum_ytd_peer,0)) AS sum_ytd_peer
  FROM calc_direct_income di
  LEFT JOIN calc_natural_gas_cost       ng ON ng.company=di.company
  LEFT JOIN calc_purchased_power_cost   pp ON pp.company=di.company
  LEFT JOIN calc_purchased_water_cost   pw ON pw.company=di.company
  LEFT JOIN calc_aux_cost               am ON am.company=di.company
  LEFT JOIN calc_outer_heat_cost        oh ON oh.company=di.company
  LEFT JOIN calc_inner_purchased_heat_cost ih ON ih.company=di.company
  LEFT JOIN calc_coal_cost              rc ON rc.company=di.company
),
-- 汇总非煤成本（用于可比煤价边际利润）
cost_non_coal AS (
  SELECT company,
         SUM(value_biz_date)  AS value_biz_date,
         SUM(value_peer_date) AS value_peer_date,
         SUM(sum_7d_biz)      AS sum_7d_biz,
         SUM(sum_7d_peer)     AS sum_7d_peer,
         SUM(sum_month_biz)   AS sum_month_biz,
         SUM(sum_month_peer)  AS sum_month_peer,
         SUM(sum_ytd_biz)     AS sum_ytd_biz,
         SUM(sum_ytd_peer)    AS sum_ytd_peer
  FROM (
    SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_natural_gas_cost
    UNION ALL SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_purchased_power_cost
    UNION ALL SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_purchased_water_cost
    UNION ALL SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_aux_cost
    UNION ALL SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_outer_heat_cost
    UNION ALL SELECT company, value_biz_date, value_peer_date, sum_7d_biz, sum_7d_peer, sum_month_biz, sum_month_peer, sum_ytd_biz, sum_ytd_peer FROM calc_inner_purchased_heat_cost
  ) t
  GROUP BY company
),
calc_comparable_marginal_profit AS (
  -- 可比煤价边际利润（万元）= 直接收入 - 非煤成本 - 标煤耗量×可比标煤单价/10000
  SELECT
    b.company,
    b.company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text                AS item_cn,
    '万元'::text                            AS unit,
    MAX(b.biz_date)  AS biz_date,
    MAX(b.peer_date) AS peer_date,
    COALESCE(di.value_biz_date,0)
      - COALESCE(SUM(cnc.value_biz_date),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_biz_date ELSE 0 END) * COALESCE(cb_sc.value,0))/10000.0 AS value_biz_date,
    COALESCE(di.value_peer_date,0)
      - COALESCE(SUM(cnc.value_peer_date),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_peer_date ELSE 0 END) * COALESCE(cp_sc.value,0))/10000.0 AS value_peer_date,
    COALESCE(di.sum_7d_biz,0)
      - COALESCE(SUM(cnc.sum_7d_biz),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_biz ELSE 0 END) * COALESCE(cb_sc.value,0))/10000.0 AS sum_7d_biz,
    COALESCE(di.sum_7d_peer,0)
      - COALESCE(SUM(cnc.sum_7d_peer),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_peer ELSE 0 END) * COALESCE(cp_sc.value,0))/10000.0 AS sum_7d_peer,
    COALESCE(di.sum_month_biz,0)
      - COALESCE(SUM(cnc.sum_month_biz),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_biz ELSE 0 END) * COALESCE(cb_sc.value,0))/10000.0 AS sum_month_biz,
    COALESCE(di.sum_month_peer,0)
      - COALESCE(SUM(cnc.sum_month_peer),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_peer ELSE 0 END) * COALESCE(cp_sc.value,0))/10000.0 AS sum_month_peer,
    COALESCE(di.sum_ytd_biz,0)
      - COALESCE(SUM(cnc.sum_ytd_biz),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_biz ELSE 0 END) * COALESCE(cb_sc.value,0))/10000.0 AS sum_ytd_biz,
    COALESCE(di.sum_ytd_peer,0)
      - COALESCE(SUM(cnc.sum_ytd_peer),0)
      - (SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_peer ELSE 0 END) * COALESCE(cp_sc.value,0))/10000.0 AS sum_ytd_peer
  FROM base b
  LEFT JOIN const_biz  cb_sc ON cb_sc.company=b.company AND cb_sc.item='price_std_coal_comparable'
  LEFT JOIN const_peer cp_sc ON cp_sc.company=b.company AND cp_sc.item='price_std_coal_comparable'
  LEFT JOIN calc_direct_income di ON di.company=b.company
  LEFT JOIN cost_non_coal cnc      ON cnc.company=b.company
  GROUP BY b.company, b.company_cn, di.value_biz_date, di.value_peer_date, di.sum_7d_biz, di.sum_7d_peer, di.sum_month_biz, di.sum_month_peer, di.sum_ytd_biz, di.sum_ytd_peer,
           cb_sc.value, cp_sc.value
),
calc_overall_efficiency AS (
  -- 全厂热效率（%，两位小数）
  SELECT
    b.company,
    b.company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text              AS item_cn,
    '%'::text                       AS unit,
    MAX(b.biz_date),
    MAX(b.peer_date),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_biz_date ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.value_biz_date ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.value_biz_date ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_biz_date ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.value_peer_date ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.value_peer_date ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.value_peer_date ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.value_peer_date ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_biz ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_7d_biz ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_7d_biz ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_biz ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_7d_peer ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_7d_peer ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_7d_peer ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_7d_peer ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_biz ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_month_biz ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_month_biz ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_biz ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_month_peer ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_month_peer ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_month_peer ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_month_peer ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_biz ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_ytd_biz ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_ytd_biz ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_biz ELSE 0 END),0)
      ),0), 2),
    ROUND(100.0 * COALESCE(
      ( (SUM(CASE WHEN b.item='amount_heat_supply' THEN b.sum_ytd_peer ELSE 0 END)
        + 36.0*SUM(CASE WHEN b.item='amount_power_sales' THEN b.sum_ytd_peer ELSE 0 END)
        - SUM(CASE WHEN b.item='consumption_outer_purchased_heat' THEN b.sum_ytd_peer ELSE 0 END)
        )
        / NULLIF(29.308*SUM(CASE WHEN b.item='consumption_std_coal' THEN b.sum_ytd_peer ELSE 0 END),0)
      ),0), 2)
  FROM base b
  GROUP BY b.company, b.company_cn
),
calc AS (
  SELECT * FROM calc_station_heat
  UNION ALL
  SELECT * FROM calc_amount_daily_net_complaints_per_10k_m2
  UNION ALL
  SELECT * FROM calc_rate_std_coal_per_heat
  UNION ALL
  SELECT * FROM calc_rate_heat_per_10k_m2
  UNION ALL
  SELECT * FROM calc_rate_power_per_10k_m2
  UNION ALL
  SELECT * FROM calc_rate_water_per_10k_m2
  UNION ALL
  SELECT * FROM calc_amount_heat_lose
  UNION ALL
  SELECT * FROM calc_power
  UNION ALL
  SELECT * FROM calc_inner_heat
  UNION ALL
  SELECT * FROM calc_heating_income
  UNION ALL
  SELECT * FROM calc_hot_water
  UNION ALL
  SELECT * FROM calc_steam
  UNION ALL
  SELECT * FROM calc_coal_cost
  UNION ALL
  SELECT * FROM calc_natural_gas_cost
  UNION ALL
  SELECT * FROM calc_purchased_power_cost
  UNION ALL
  SELECT * FROM calc_purchased_water_cost
  UNION ALL
  SELECT * FROM calc_aux_cost
  UNION ALL
  SELECT * FROM calc_outer_heat_cost
  UNION ALL
  SELECT * FROM calc_inner_purchased_heat_cost
  UNION ALL
  SELECT * FROM calc_direct_income
  UNION ALL
  SELECT * FROM calc_marginal_profit
  UNION ALL
  SELECT * FROM calc_comparable_marginal_profit
  UNION ALL
  SELECT * FROM calc_overall_efficiency
)
SELECT * FROM base
UNION ALL
SELECT * FROM calc;

-- 注意：普通视图不可创建索引；如需性能优化，请在底表 daily_basic_data 上创建（或调整）索引。

-- ========= 分组再聚合视图（依赖 sum_basic_data） =========
-- 说明：
--   将原来 `sum_basic_data` 中的“主城区/集团”分组口径迁移到独立视图 `groups`，以便：
--   1) 在不影响公司明细口径的前提下单独消费分组结果；
--   2) 后续为“计算指标”提供统一的再聚合出口（视图依赖视图，简化维护）。
-- 分组规则：
--   ZhuChengQu = BeiHai + XiangHai + GongRe
--   Group      = ZhuChengQu + JinZhou + BeiFang + JinpPu + ZhuangHe + YanJiuYuan

DROP VIEW IF EXISTS groups;

CREATE VIEW groups AS
WITH params AS (
  SELECT COALESCE(current_setting('phoenix.biz_date', true)::date, (current_date - INTERVAL '1 day')::date) AS biz_date
),
anchor_dates AS (
  SELECT
    p.biz_date,
    (p.biz_date - INTERVAL '1 year')::date AS peer_date
  FROM params p
),
w AS (
  SELECT
    biz_date,
    peer_date,
    CASE
      WHEN biz_date >= make_date(EXTRACT(YEAR FROM biz_date)::int, 10, 1)
      THEN LPAD(((EXTRACT(YEAR FROM biz_date)::int) % 100)::text, 2, '0') || '-' ||
           LPAD((((EXTRACT(YEAR FROM biz_date)::int)+1) % 100)::text, 2, '0')
      ELSE LPAD((((EXTRACT(YEAR FROM biz_date)::int)-1) % 100)::text, 2, '0') || '-' ||
           LPAD(((EXTRACT(YEAR FROM biz_date)::int) % 100)::text, 2, '0')
    END AS biz_period,
    CASE
      WHEN peer_date >= make_date(EXTRACT(YEAR FROM peer_date)::int, 10, 1)
      THEN LPAD(((EXTRACT(YEAR FROM peer_date)::int) % 100)::text, 2, '0') || '-' ||
           LPAD((((EXTRACT(YEAR FROM peer_date)::int)+1) % 100)::text, 2, '0')
      ELSE LPAD((((EXTRACT(YEAR FROM peer_date)::int)-1) % 100)::text, 2, '0') || '-' ||
           LPAD(((EXTRACT(YEAR FROM peer_date)::int) % 100)::text, 2, '0')
    END AS peer_period
  FROM anchor_dates
),
s AS (
  SELECT * FROM sum_basic_data
),
base_zc AS (
  SELECT item, item_cn, unit, biz_date, peer_date,
         SUM(value_biz_date)  AS value_biz_date,
         SUM(value_peer_date) AS value_peer_date,
         SUM(sum_7d_biz)      AS sum_7d_biz,
         SUM(sum_7d_peer)     AS sum_7d_peer,
         SUM(sum_month_biz)   AS sum_month_biz,
         SUM(sum_month_peer)  AS sum_month_peer,
         SUM(sum_ytd_biz)     AS sum_ytd_biz,
         SUM(sum_ytd_peer)    AS sum_ytd_peer
  FROM s
  WHERE company IN ('BeiHai','XiangHai','GongRe')
  GROUP BY item, item_cn, unit, biz_date, peer_date
),
base_grp AS (
  SELECT item, item_cn, unit, biz_date, peer_date,
         SUM(value_biz_date)  AS value_biz_date,
         SUM(value_peer_date) AS value_peer_date,
         SUM(sum_7d_biz)      AS sum_7d_biz,
         SUM(sum_7d_peer)     AS sum_7d_peer,
         SUM(sum_month_biz)   AS sum_month_biz,
         SUM(sum_month_peer)  AS sum_month_peer,
         SUM(sum_ytd_biz)     AS sum_ytd_biz,
         SUM(sum_ytd_peer)    AS sum_ytd_peer
  FROM s
  WHERE company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')
  GROUP BY item, item_cn, unit, biz_date, peer_date
),
denom_zc AS (
  SELECT
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_whole_heating_area' AND c.company IN ('BeiHai','XiangHai','GongRe')) AS area_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_whole_heating_area' AND c.company IN ('BeiHai','XiangHai','GongRe')) AS area_peer,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS fee_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS fee_peer
),
denom_grp AS (
  SELECT
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_whole_heating_area' AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS area_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_whole_heating_area' AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS area_peer,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS fee_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS fee_peer
)
-- 1) 主城区：量/金额类直接汇总（排除比率与仅 GongRe 的网损热量）
SELECT
  'ZhuChengQu' AS company,
  '主城区'      AS company_cn,
  item, item_cn, unit,
  biz_date, peer_date,
  value_biz_date, value_peer_date,
  sum_7d_biz, sum_7d_peer,
  sum_month_biz, sum_month_peer,
  sum_ytd_biz, sum_ytd_peer
FROM base_zc
WHERE item NOT IN (
  'amount_daily_net_complaints_per_10k_m2',
  'rate_std_coal_per_heat',
  'rate_heat_per_10k_m2',
  'rate_power_per_10k_m2',
  'rate_water_per_10k_m2',
  'amount_heat_lose',
  'eco_direct_income' -- 主城区直接收入在下方以“售电+暖+售高温水+售汽”重算
)
UNION ALL
-- 主城区：直接收入（万元）= 售电收入 + 暖收入 + 售高温水收入 + 售汽收入（不含“内售热收入”）
SELECT
  'ZhuChengQu','主城区',
  'eco_direct_income','直接收入','万元',
  z.biz_date, z.peer_date,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.value_biz_date ELSE 0 END) AS value_biz_date,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.value_peer_date ELSE 0 END) AS value_peer_date,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_7d_biz ELSE 0 END)     AS sum_7d_biz,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_7d_peer ELSE 0 END)    AS sum_7d_peer,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_month_biz ELSE 0 END)  AS sum_month_biz,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_month_peer ELSE 0 END) AS sum_month_peer,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_ytd_biz ELSE 0 END)    AS sum_ytd_biz,
  SUM(CASE WHEN z.item IN ('eco_power_supply_income','eco_heating_supply_income','eco_hot_water_supply_income','eco_steam_supply_income') THEN z.sum_ytd_peer ELSE 0 END)   AS sum_ytd_peer
FROM base_zc z
GROUP BY z.biz_date, z.peer_date
UNION ALL
-- 主城区：万㎡净投诉量
SELECT
  'ZhuChengQu','主城区',
  'amount_daily_net_complaints_per_10k_m2','万平方米省市净投诉量','件/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.area_biz,0),
  z.value_peer_date / NULLIF(d.area_peer,0),
  z.sum_7d_biz / NULLIF(d.area_biz,0),
  z.sum_7d_peer / NULLIF(d.area_peer,0),
  z.sum_month_biz / NULLIF(d.area_biz,0),
  z.sum_month_peer / NULLIF(d.area_peer,0),
  z.sum_ytd_biz / NULLIF(d.area_biz,0),
  z.sum_ytd_peer / NULLIF(d.area_peer,0)
FROM base_zc z, denom_zc d
WHERE z.item='amount_daily_net_complaints'
UNION ALL
-- 主城区：供热标煤单耗
SELECT
  'ZhuChengQu','主城区',
  'rate_std_coal_per_heat','供热标煤单耗','吨/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.fee_biz,0),
  z.value_peer_date / NULLIF(d.fee_peer,0),
  z.sum_7d_biz / NULLIF(d.fee_biz,0),
  z.sum_7d_peer / NULLIF(d.fee_peer,0),
  z.sum_month_biz / NULLIF(d.fee_biz,0),
  z.sum_month_peer / NULLIF(d.fee_peer,0),
  z.sum_ytd_biz / NULLIF(d.fee_biz,0),
  z.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM base_zc z, denom_zc d
WHERE z.item='consumption_std_coal'
UNION ALL
-- 主城区：供暖热单耗（分子用站内耗热量）
SELECT
  'ZhuChengQu','主城区',
  'rate_heat_per_10k_m2','供暖热单耗','GJ/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.fee_biz,0),
  z.value_peer_date / NULLIF(d.fee_peer,0),
  z.sum_7d_biz / NULLIF(d.fee_biz,0),
  z.sum_7d_peer / NULLIF(d.fee_peer,0),
  z.sum_month_biz / NULLIF(d.fee_biz,0),
  z.sum_month_peer / NULLIF(d.fee_peer,0),
  z.sum_ytd_biz / NULLIF(d.fee_biz,0),
  z.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM base_zc z, denom_zc d
WHERE z.item='consumption_station_heat'
UNION ALL
-- 主城区：供暖电单耗（×10000）
SELECT
  'ZhuChengQu','主城区',
  'rate_power_per_10k_m2','供暖电单耗','kWh/万㎡',
  z.biz_date, z.peer_date,
  (z.value_biz_date*10000.0) / NULLIF(d.fee_biz,0),
  (z.value_peer_date*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_7d_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_7d_peer*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_month_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_month_peer*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_ytd_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_ytd_peer*10000.0) / NULLIF(d.fee_peer,0)
FROM base_zc z, denom_zc d
WHERE z.item='consumption_station_purchased_power'
UNION ALL
-- 主城区：供暖水单耗（一次网补水+换热站补水+热网补水）
SELECT
  'ZhuChengQu','主城区',
  'rate_water_per_10k_m2','供暖水单耗','吨/万㎡',
  a.biz_date, a.peer_date,
  a.value_biz_date / NULLIF(d.fee_biz,0),
  a.value_peer_date / NULLIF(d.fee_peer,0),
  a.sum_7d_biz / NULLIF(d.fee_biz,0),
  a.sum_7d_peer / NULLIF(d.fee_peer,0),
  a.sum_month_biz / NULLIF(d.fee_biz,0),
  a.sum_month_peer / NULLIF(d.fee_peer,0),
  a.sum_ytd_biz / NULLIF(d.fee_biz,0),
  a.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM (
  SELECT biz_date, peer_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN value_biz_date ELSE 0 END) AS value_biz_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN value_peer_date ELSE 0 END) AS value_peer_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_7d_biz ELSE 0 END) AS sum_7d_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_7d_peer ELSE 0 END) AS sum_7d_peer,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_month_biz ELSE 0 END) AS sum_month_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_month_peer ELSE 0 END) AS sum_month_peer,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_ytd_biz ELSE 0 END) AS sum_ytd_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_ytd_peer ELSE 0 END) AS sum_ytd_peer
  FROM base_zc
  GROUP BY biz_date, peer_date
) a, denom_zc d
UNION ALL
-- 2) 集团口径：量/金额类直接汇总（排除比率与仅 GongRe 的网损热量）
SELECT
  'Group' AS company,
  '集团全口径' AS company_cn,
  item, item_cn, unit,
  biz_date, peer_date,
  value_biz_date, value_peer_date,
  sum_7d_biz, sum_7d_peer,
  sum_month_biz, sum_month_peer,
  sum_ytd_biz, sum_ytd_peer
FROM base_grp
WHERE item NOT IN ('amount_daily_net_complaints_per_10k_m2','rate_std_coal_per_heat','rate_heat_per_10k_m2','rate_power_per_10k_m2','rate_water_per_10k_m2','amount_heat_lose')
UNION ALL
-- 集团：万㎡净投诉量
SELECT
  'Group','集团全口径',
  'amount_daily_net_complaints_per_10k_m2','万平方米省市净投诉量','件/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.area_biz,0),
  z.value_peer_date / NULLIF(d.area_peer,0),
  z.sum_7d_biz / NULLIF(d.area_biz,0),
  z.sum_7d_peer / NULLIF(d.area_peer,0),
  z.sum_month_biz / NULLIF(d.area_biz,0),
  z.sum_month_peer / NULLIF(d.area_peer,0),
  z.sum_ytd_biz / NULLIF(d.area_biz,0),
  z.sum_ytd_peer / NULLIF(d.area_peer,0)
FROM base_grp z, denom_grp d
WHERE z.item='amount_daily_net_complaints'
UNION ALL
-- 集团：供热标煤单耗
SELECT
  'Group','集团全口径',
  'rate_std_coal_per_heat','供热标煤单耗','吨/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.fee_biz,0),
  z.value_peer_date / NULLIF(d.fee_peer,0),
  z.sum_7d_biz / NULLIF(d.fee_biz,0),
  z.sum_7d_peer / NULLIF(d.fee_peer,0),
  z.sum_month_biz / NULLIF(d.fee_biz,0),
  z.sum_month_peer / NULLIF(d.fee_peer,0),
  z.sum_ytd_biz / NULLIF(d.fee_biz,0),
  z.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM base_grp z, denom_grp d
WHERE z.item='consumption_std_coal'
UNION ALL
-- 集团：供暖热单耗（分子用站内耗热量）
SELECT
  'Group','集团全口径',
  'rate_heat_per_10k_m2','供暖热单耗','GJ/万㎡',
  z.biz_date, z.peer_date,
  z.value_biz_date / NULLIF(d.fee_biz,0),
  z.value_peer_date / NULLIF(d.fee_peer,0),
  z.sum_7d_biz / NULLIF(d.fee_biz,0),
  z.sum_7d_peer / NULLIF(d.fee_peer,0),
  z.sum_month_biz / NULLIF(d.fee_biz,0),
  z.sum_month_peer / NULLIF(d.fee_peer,0),
  z.sum_ytd_biz / NULLIF(d.fee_biz,0),
  z.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM base_grp z, denom_grp d
WHERE z.item='consumption_station_heat'
UNION ALL
-- 集团：供暖电单耗（×10000）
SELECT
  'Group','集团全口径',
  'rate_power_per_10k_m2','供暖电单耗','kWh/万㎡',
  z.biz_date, z.peer_date,
  (z.value_biz_date*10000.0) / NULLIF(d.fee_biz,0),
  (z.value_peer_date*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_7d_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_7d_peer*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_month_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_month_peer*10000.0) / NULLIF(d.fee_peer,0),
  (z.sum_ytd_biz*10000.0) / NULLIF(d.fee_biz,0),
  (z.sum_ytd_peer*10000.0) / NULLIF(d.fee_peer,0)
FROM base_grp z, denom_grp d
WHERE z.item='consumption_station_purchased_power'
UNION ALL
-- 集团：供暖水单耗（一次网补水+换热站补水+热网补水）
SELECT
  'Group','集团全口径',
  'rate_water_per_10k_m2','供暖水单耗','吨/万㎡',
  a.biz_date, a.peer_date,
  a.value_biz_date / NULLIF(d.fee_biz,0),
  a.value_peer_date / NULLIF(d.fee_peer,0),
  a.sum_7d_biz / NULLIF(d.fee_biz,0),
  a.sum_7d_peer / NULLIF(d.fee_peer,0),
  a.sum_month_biz / NULLIF(d.fee_biz,0),
  a.sum_month_peer / NULLIF(d.fee_peer,0),
  a.sum_ytd_biz / NULLIF(d.fee_biz,0),
  a.sum_ytd_peer / NULLIF(d.fee_peer,0)
FROM (
  SELECT biz_date, peer_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN value_biz_date ELSE 0 END) AS value_biz_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN value_peer_date ELSE 0 END) AS value_peer_date,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_7d_biz ELSE 0 END) AS sum_7d_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_7d_peer ELSE 0 END) AS sum_7d_peer,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_month_biz ELSE 0 END) AS sum_month_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_month_peer ELSE 0 END) AS sum_month_peer,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_ytd_biz ELSE 0 END) AS sum_ytd_biz,
         SUM(CASE WHEN item IN ('consumption_network_fill_water','consumption_station_fill_water','consumption_network_water') THEN sum_ytd_peer ELSE 0 END) AS sum_ytd_peer
  FROM base_grp
  GROUP BY biz_date, peer_date
) a, denom_grp d;

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
