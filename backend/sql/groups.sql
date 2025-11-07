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
group_sum_raw_zhangtun AS (
  SELECT
    'sum_consumption_amount_raw_coal_zhangtun'::text AS item,
    '原煤耗量汇总(张屯)'::text                      AS item_cn,
    COALESCE(MAX(unit), '吨')                        AS unit,
    biz_date,
    peer_date,
    SUM(value_biz_date)                              AS value_biz_date,
    SUM(value_peer_date)                             AS value_peer_date,
    SUM(sum_7d_biz)                                  AS sum_7d_biz,
    SUM(sum_7d_peer)                                 AS sum_7d_peer,
    SUM(sum_month_biz)                               AS sum_month_biz,
    SUM(sum_month_peer)                              AS sum_month_peer,
    SUM(sum_ytd_biz)                                 AS sum_ytd_biz,
    SUM(sum_ytd_peer)                                AS sum_ytd_peer
  FROM s
  WHERE
    (company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu') AND item='consumption_amount_raw_coal')
    OR (company='ZhuangHe' AND item='consumption_amount_raw_coal_zhangtun')
  GROUP BY biz_date, peer_date
),
group_sum_std_zhangtun AS (
  SELECT
    'sum_consumption_std_coal_zhangtun'::text AS item,
    '标煤耗量汇总(张屯)'::text                      AS item_cn,
    COALESCE(MAX(unit), '吨')                         AS unit,
    biz_date,
    peer_date,
    SUM(value_biz_date)                               AS value_biz_date,
    SUM(value_peer_date)                              AS value_peer_date,
    SUM(sum_7d_biz)                                   AS sum_7d_biz,
    SUM(sum_7d_peer)                                  AS sum_7d_peer,
    SUM(sum_month_biz)                                AS sum_month_biz,
    SUM(sum_month_peer)                               AS sum_month_peer,
    SUM(sum_ytd_biz)                                  AS sum_ytd_biz,
    SUM(sum_ytd_peer)                                 AS sum_ytd_peer
  FROM s
  WHERE
    (company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu') AND item='consumption_std_coal')
    OR (company='ZhuangHe' AND item='consumption_std_coal_zhangtun')
  GROUP BY biz_date, peer_date
),
denom_zc AS (
  SELECT
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS area_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS area_peer,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS fee_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe')) AS fee_peer
),
denom_grp AS (
  SELECT
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.biz_period  AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS area_biz,
    (SELECT SUM(c.value) FROM constant_data c, w WHERE c.period=w.peer_period AND c.item='amount_heating_fee_area'   AND c.company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinPu','ZhuangHe','YanJiuYuan')) AS area_peer,
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
  'rate_overall_efficiency',
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
-- 主城区：全厂热效率（小数四位）
SELECT
  'ZhuChengQu','主城区',
  'rate_overall_efficiency','全厂热效率','%',
  z.biz_date, z.peer_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.value_biz_date ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.value_biz_date ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.value_biz_date ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.value_biz_date ELSE 0 END), 0)
    ), 0
  ), 4) AS value_biz_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.value_peer_date ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.value_peer_date ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.value_peer_date ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.value_peer_date ELSE 0 END), 0)
    ), 0
  ), 4) AS value_peer_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_7d_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_7d_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_7d_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_7d_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_7d_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_7d_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_7d_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_7d_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_7d_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_7d_peer,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_month_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_month_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_month_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_month_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_month_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_month_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_month_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_month_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_month_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_month_peer,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_ytd_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_ytd_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_ytd_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_ytd_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_ytd_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_ytd_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_ytd_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_ytd_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_ytd_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_ytd_peer
FROM base_zc z
GROUP BY z.biz_date, z.peer_date
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
WHERE item NOT IN ('amount_daily_net_complaints_per_10k_m2','rate_std_coal_per_heat','rate_heat_per_10k_m2','rate_power_per_10k_m2','rate_water_per_10k_m2','rate_overall_efficiency','amount_heat_lose','eco_direct_income')
UNION ALL
-- 集团：原煤耗量汇总（张屯范围）
SELECT
  'Group','集团全口径',
  r.item, r.item_cn, r.unit,
  r.biz_date, r.peer_date,
  r.value_biz_date, r.value_peer_date,
  r.sum_7d_biz, r.sum_7d_peer,
  r.sum_month_biz, r.sum_month_peer,
  r.sum_ytd_biz, r.sum_ytd_peer
FROM group_sum_raw_zhangtun r
UNION ALL
-- 集团：标煤耗量汇总（张屯范围）
SELECT
  'Group','集团全口径',
  s.item, s.item_cn, s.unit,
  s.biz_date, s.peer_date,
  s.value_biz_date, s.value_peer_date,
  s.sum_7d_biz, s.sum_7d_peer,
  s.sum_month_biz, s.sum_month_peer,
  s.sum_ytd_biz, s.sum_ytd_peer
FROM group_sum_std_zhangtun s
UNION ALL
-- 集团：全厂热效率（小数四位）
SELECT
  'Group','集团全口径',
  'rate_overall_efficiency','全厂热效率','%',
  z.biz_date, z.peer_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.value_biz_date ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.value_biz_date ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.value_biz_date ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.value_biz_date ELSE 0 END), 0)
    ), 0
  ), 4) AS value_biz_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.value_peer_date ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.value_peer_date ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.value_peer_date ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.value_peer_date ELSE 0 END), 0)
    ), 0
  ), 4) AS value_peer_date,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_7d_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_7d_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_7d_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_7d_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_7d_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_7d_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_7d_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_7d_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_7d_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_7d_peer,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_month_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_month_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_month_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_month_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_month_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_month_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_month_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_month_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_month_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_month_peer,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_ytd_biz ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_ytd_biz ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_ytd_biz ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_ytd_biz ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_ytd_biz,
  ROUND(COALESCE(
    (
      (SUM(CASE WHEN z.item='amount_heat_supply' THEN z.sum_ytd_peer ELSE 0 END)
       + 36.0 * SUM(CASE WHEN z.item='amount_power_sales' THEN z.sum_ytd_peer ELSE 0 END)
       - SUM(CASE WHEN z.item='consumption_outer_purchased_heat' THEN z.sum_ytd_peer ELSE 0 END))
      / NULLIF(29.308 * SUM(CASE WHEN z.item='consumption_std_coal' THEN z.sum_ytd_peer ELSE 0 END), 0)
    ), 0
  ), 4) AS sum_ytd_peer
FROM base_grp z
GROUP BY z.biz_date, z.peer_date
UNION ALL
-- 集团：直接收入（仅售电/暖/售高温水/售汽，不含“内售热收入”）
SELECT
  'Group','集团全口径',
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
FROM base_grp z
GROUP BY z.biz_date, z.peer_date
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
