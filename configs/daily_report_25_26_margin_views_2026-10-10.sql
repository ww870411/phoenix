-- 核对日期：2026-10-10；来源：phoenix_db / phoenix / public，pg_get_viewdef。
-- 本文件仅保存实际定义快照，本轮未执行任何视图重建。

-- 视图：sum_basic_data
CREATE OR REPLACE VIEW public.sum_basic_data AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.biz_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS biz_date
        ), anchor_dates AS (
         SELECT p.biz_date,
            (p.biz_date - '1 year'::interval)::date AS peer_date
           FROM params p
        ), window_defs AS (
         SELECT anchor_dates.biz_date,
            anchor_dates.peer_date,
            anchor_dates.biz_date - '6 days'::interval AS biz_7d_start,
            anchor_dates.peer_date - '6 days'::interval AS peer_7d_start,
            date_trunc('month'::text, anchor_dates.biz_date::timestamp with time zone)::date AS biz_month_start,
            date_trunc('month'::text, anchor_dates.peer_date::timestamp with time zone)::date AS peer_month_start,
            '2025-11-01'::date AS biz_ytd_start,
            '2024-11-01'::date AS peer_ytd_start,
            EXTRACT(year FROM anchor_dates.biz_date)::integer AS biz_year,
            EXTRACT(year FROM anchor_dates.peer_date)::integer AS peer_year,
                CASE
                    WHEN anchor_dates.biz_date >= make_date(EXTRACT(year FROM anchor_dates.biz_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN anchor_dates.peer_date >= make_date(EXTRACT(year FROM anchor_dates.peer_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text)
                END AS peer_period,
            1 AS days_day_biz,
            1 AS days_day_peer,
            7 AS days_7_biz,
            7 AS days_7_peer,
            anchor_dates.biz_date - date_trunc('month'::text, anchor_dates.biz_date::timestamp with time zone)::date + 1 AS days_month_biz,
            anchor_dates.peer_date - date_trunc('month'::text, anchor_dates.peer_date::timestamp with time zone)::date + 1 AS days_month_peer,
            anchor_dates.biz_date - '2025-11-01'::date + 1 AS days_ytd_biz,
            anchor_dates.peer_date - '2024-11-01'::date + 1 AS days_ytd_peer
           FROM anchor_dates
        ), base AS (
         SELECT d.company,
            d.company_cn,
            d.item,
            d.item_cn,
            d.unit,
            w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.biz_7d_start AND d.date <= w.biz_date), 0::numeric) AS sum_7d_biz,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.peer_7d_start AND d.date <= w.peer_date), 0::numeric) AS sum_7d_peer,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.biz_month_start AND d.date <= w.biz_date), 0::numeric) AS sum_month_biz,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.peer_month_start AND d.date <= w.peer_date), 0::numeric) AS sum_month_peer,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.biz_ytd_start AND d.date <= w.biz_date), 0::numeric) AS sum_ytd_biz,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.peer_ytd_start AND d.date <= w.peer_date), 0::numeric) AS sum_ytd_peer
           FROM daily_basic_data d
             CROSS JOIN window_defs w
          WHERE d.date >= w.peer_ytd_start AND d.date <= w.biz_date
          GROUP BY d.company, d.company_cn, d.item, d.item_cn, d.unit, w.biz_date, w.peer_date
        ), const_biz AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.biz_period
          GROUP BY c.company, c.item
        ), const_peer AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.peer_period
          GROUP BY c.company, c.item
        ), calc_station_heat AS (
         SELECT b.company,
            b.company_cn,
            'consumption_station_heat'::text AS item,
            '站内耗热量'::text AS item_cn,
            'GJ'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_biz_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_peer_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_7d_biz,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_7d_peer,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_month_biz,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_month_peer,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_ytd_biz,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS sum_ytd_peer
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc_station_heat_selected AS (
         SELECT calc_station_heat.company,
            calc_station_heat.company_cn,
            calc_station_heat.item,
            calc_station_heat.item_cn,
            calc_station_heat.unit,
            calc_station_heat.biz_date,
            calc_station_heat.peer_date,
            calc_station_heat.value_biz_date,
            calc_station_heat.value_peer_date,
            calc_station_heat.sum_7d_biz,
            calc_station_heat.sum_7d_peer,
            calc_station_heat.sum_month_biz,
            calc_station_heat.sum_month_peer,
            calc_station_heat.sum_ytd_biz,
            calc_station_heat.sum_ytd_peer
           FROM calc_station_heat
          WHERE calc_station_heat.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
        ), calc_amount_daily_net_complaints_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'amount_daily_net_complaints_per_10k_m2'::text AS item,
            '万平方米省市净投诉量'::text AS item_cn,
            '件/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_area ON cb_area.company = b.company AND cb_area.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_area ON cp_area.company = b.company AND cp_area.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_area.value, cp_area.value
        ), calc_rate_std_coal_per_heat AS (
         SELECT b.company,
            b.company_cn,
            'rate_std_coal_per_heat'::text AS item,
            '供热标煤单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_heat_per_10k_m2 AS (
         SELECT sh.company,
            sh.company_cn,
            'rate_heat_per_10k_m2'::text AS item,
            '供暖热单耗'::text AS item_cn,
            'GJ/万㎡'::text AS unit,
            max(sh.biz_date) AS max,
            max(sh.peer_date) AS max,
            COALESCE(sh.value_biz_date, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.value_peer_date, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_7d_biz, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_7d_peer, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_month_biz, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_month_peer, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_ytd_biz, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.sum_ytd_peer, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM calc_station_heat sh
             LEFT JOIN const_biz cb_fee ON cb_fee.company = sh.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = sh.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY sh.company, sh.company_cn, sh.value_biz_date, sh.value_peer_date, sh.sum_7d_biz, sh.sum_7d_peer, sh.sum_month_biz, sh.sum_month_peer, sh.sum_ytd_biz, sh.sum_ytd_peer, cb_fee.value, cp_fee.value
        ), calc_rate_power_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_power_per_10k_m2'::text AS item,
            '供暖电单耗'::text AS item_cn,
            'kWh/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_water_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_water_per_10k_m2'::text AS item,
            '供暖水单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_amount_heat_lose AS (
         SELECT b.company,
            b.company_cn,
            'amount_heat_lose'::text AS item,
            '网损热量'::text AS item_cn,
            'GJ'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.value_biz_date), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.value_peer_date), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_7d_biz), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_7d_peer), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_month_biz), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_month_peer), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_ytd_biz), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) - 2.9518 * COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END), 0::numeric) - COALESCE(max(sh.sum_ytd_peer), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN calc_station_heat sh ON sh.company = b.company
          WHERE b.company = 'GongRe'::text
          GROUP BY b.company, b.company_cn
        ), calc_power AS (
         SELECT b.company,
            b.company_cn,
            'eco_power_supply_income'::text AS item,
            '其中：售电收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_ps ON cb_ps.company = b.company AND cb_ps.item = 'price_power_sales'::text
             LEFT JOIN const_peer cp_ps ON cp_ps.company = b.company AND cp_ps.item = 'price_power_sales'::text
          GROUP BY b.company, b.company_cn, cb_ps.value, cp_ps.value
        ), calc_inner_heat AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_heat_supply_income'::text AS item,
            '其中：内售热收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS "?column?",
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_hin ON cb_hin.company = b.company AND cb_hin.item = 'price_inner_heat_sales'::text
             LEFT JOIN const_peer cp_hin ON cp_hin.company = b.company AND cp_hin.item = 'price_inner_heat_sales'::text
          GROUP BY b.company, b.company_cn, cb_hin.value, cp_hin.value
        ), calc_heating_income AS (
         SELECT b.company,
            b.company_cn,
            'eco_heating_supply_income'::text AS item,
            '其中：暖收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_day_biz
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_day_peer
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_7_biz
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_7_peer
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_month_biz
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_month_peer
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_ytd_biz
                   FROM window_defs))::numeric / 156.0 AS "?column?",
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_ytd_peer
                   FROM window_defs))::numeric / 156.0 AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_sh ON cb_sh.company = b.company AND cb_sh.item = 'eco_season_heating_income'::text
             LEFT JOIN const_peer cp_sh ON cp_sh.company = b.company AND cp_sh.item = 'eco_season_heating_income'::text
          GROUP BY b.company, b.company_cn, cb_sh.value, cp_sh.value
        ), calc_hot_water AS (
         SELECT b.company,
            b.company_cn,
            'eco_hot_water_supply_income'::text AS item,
            '其中：售高温水收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS "case"
           FROM base b
             LEFT JOIN const_biz cb_hw ON cb_hw.company = b.company AND cb_hw.item = 'price_hot_water_sales'::text
             LEFT JOIN const_peer cp_hw ON cp_hw.company = b.company AND cp_hw.item = 'price_hot_water_sales'::text
          GROUP BY b.company, b.company_cn, cb_hw.value, cp_hw.value
        ), calc_steam AS (
         SELECT b.company,
            b.company_cn,
            'eco_steam_supply_income'::text AS item,
            '其中：售汽收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_7d_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_7d_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_month_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_month_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_ytd_biz
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS "case",
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.sum_ytd_peer
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS "case"
           FROM base b
             LEFT JOIN const_biz cb_ss ON cb_ss.company = b.company AND cb_ss.item = 'price_steam_sales'::text
             LEFT JOIN const_peer cp_ss ON cp_ss.company = b.company AND cp_ss.item = 'price_steam_sales'::text
          GROUP BY b.company, b.company_cn, cb_ss.value, cp_ss.value
        ), calc_coal_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_coal_cost'::text AS item,
            '煤成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal'::text
          GROUP BY b.company, b.company_cn, cb_sc.value, cp_sc.value
        ), calc_natural_gas_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_natural_gas_cost'::text AS item,
            '天然气成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_ng ON cb_ng.company = b.company AND cb_ng.item = 'price_natural_gas'::text
             LEFT JOIN const_peer cp_ng ON cp_ng.company = b.company AND cp_ng.item = 'price_natural_gas'::text
          GROUP BY b.company, b.company_cn, cb_ng.value, cp_ng.value
        ), calc_purchased_power_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_power_cost'::text AS item,
            '外购电成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_pp ON cb_pp.company = b.company AND cb_pp.item = 'price_purchased_power'::text
             LEFT JOIN const_peer cp_pp ON cp_pp.company = b.company AND cp_pp.item = 'price_purchased_power'::text
          GROUP BY b.company, b.company_cn, cb_pp.value, cp_pp.value
        ), calc_purchased_water_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_water_cost'::text AS item,
            '购水成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_pw ON cb_pw.company = b.company AND cb_pw.item = 'price_purchased_water'::text
             LEFT JOIN const_peer cp_pw ON cp_pw.company = b.company AND cp_pw.item = 'price_purchased_water'::text
          GROUP BY b.company, b.company_cn, cb_pw.value, cp_pw.value
        ), calc_aux_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_measurable_auxiliary_materials'::text AS item,
            '可计量辅材成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS value_biz_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS value_peer_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS sum_7d_biz,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS sum_7d_peer,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS sum_month_biz,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS sum_month_peer,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS sum_ytd_biz,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_ac ON cb_ac.company = b.company AND cb_ac.item = 'price_acid'::text
             LEFT JOIN const_peer cp_ac ON cp_ac.company = b.company AND cp_ac.item = 'price_acid'::text
             LEFT JOIN const_biz cb_al ON cb_al.company = b.company AND cb_al.item = 'price_alkali'::text
             LEFT JOIN const_peer cp_al ON cp_al.company = b.company AND cp_al.item = 'price_alkali'::text
             LEFT JOIN const_biz cb_ol ON cb_ol.company = b.company AND cb_ol.item = 'price_oil'::text
             LEFT JOIN const_peer cp_ol ON cp_ol.company = b.company AND cp_ol.item = 'price_oil'::text
             LEFT JOIN const_biz cb_aw ON cb_aw.company = b.company AND cb_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_peer cp_aw ON cp_aw.company = b.company AND cp_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_biz cb_ls ON cb_ls.company = b.company AND cb_ls.item = 'price_limestone'::text
             LEFT JOIN const_peer cp_ls ON cp_ls.company = b.company AND cp_ls.item = 'price_limestone'::text
             LEFT JOIN const_biz cb_lsp ON cb_lsp.company = b.company AND cb_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_peer cp_lsp ON cp_lsp.company = b.company AND cp_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_biz cb_mg ON cb_mg.company = b.company AND cb_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_peer cp_mg ON cp_mg.company = b.company AND cp_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_biz cb_dn ON cb_dn.company = b.company AND cb_dn.item = 'price_denitration_agent'::text
             LEFT JOIN const_peer cp_dn ON cp_dn.company = b.company AND cp_dn.item = 'price_denitration_agent'::text
          GROUP BY b.company, b.company_cn, cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value, cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value, cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
        ), calc_outer_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_outer_heat_cost'::text AS item,
            '外购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_oh ON cb_oh.company = b.company AND cb_oh.item = 'price_outer_purchased_heat'::text
             LEFT JOIN const_peer cp_oh ON cp_oh.company = b.company AND cp_oh.item = 'price_outer_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_oh.value, cp_oh.value
        ), calc_inner_purchased_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_purchased_heat_cost'::text AS item,
            '内购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS value_peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS sum_7d_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS sum_7d_peer,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS sum_month_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS sum_month_peer,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS sum_ytd_biz,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_ih ON cb_ih.company = b.company AND cb_ih.item = 'price_inner_purchased_heat'::text
             LEFT JOIN const_peer cp_ih ON cp_ih.company = b.company AND cp_ih.item = 'price_inner_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_ih.value, cp_ih.value
        ), calc_direct_income AS (
         SELECT c.company,
            c.company_cn,
            'eco_direct_income'::text AS item,
            '直接收入'::text AS item_cn,
            '万元'::text AS unit,
            max(c.biz_date) AS biz_date,
            max(c.peer_date) AS peer_date,
            sum(c.value_biz_date) AS value_biz_date,
            sum(c.value_peer_date) AS value_peer_date,
            sum(c.sum_7d_biz) AS sum_7d_biz,
            sum(c.sum_7d_peer) AS sum_7d_peer,
            sum(c.sum_month_biz) AS sum_month_biz,
            sum(c.sum_month_peer) AS sum_month_peer,
            sum(c.sum_ytd_biz) AS sum_ytd_biz,
            sum(c.sum_ytd_peer) AS sum_ytd_peer
           FROM ( SELECT calc_power.company,
                    calc_power.company_cn,
                    calc_power.item,
                    calc_power.item_cn,
                    calc_power.unit,
                    calc_power.biz_date,
                    calc_power.peer_date,
                    calc_power.value_biz_date,
                    calc_power.value_peer_date,
                    calc_power.sum_7d_biz,
                    calc_power.sum_7d_peer,
                    calc_power.sum_month_biz,
                    calc_power.sum_month_peer,
                    calc_power.sum_ytd_biz,
                    calc_power.sum_ytd_peer
                   FROM calc_power
                UNION ALL
                 SELECT calc_inner_heat.company,
                    calc_inner_heat.company_cn,
                    calc_inner_heat.item,
                    calc_inner_heat.item_cn,
                    calc_inner_heat.unit,
                    calc_inner_heat.max,
                    calc_inner_heat.max_1 AS max,
                    calc_inner_heat."?column?",
                    calc_inner_heat."?column?_1" AS "?column?",
                    calc_inner_heat."?column?_2" AS "?column?",
                    calc_inner_heat."?column?_3" AS "?column?",
                    calc_inner_heat."?column?_4" AS "?column?",
                    calc_inner_heat."?column?_5" AS "?column?",
                    calc_inner_heat."?column?_6" AS "?column?",
                    calc_inner_heat."?column?_7" AS "?column?"
                   FROM calc_inner_heat calc_inner_heat(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
                UNION ALL
                 SELECT calc_heating_income.company,
                    calc_heating_income.company_cn,
                    calc_heating_income.item,
                    calc_heating_income.item_cn,
                    calc_heating_income.unit,
                    calc_heating_income.max,
                    calc_heating_income.max_1 AS max,
                    calc_heating_income."?column?",
                    calc_heating_income."?column?_1" AS "?column?",
                    calc_heating_income."?column?_2" AS "?column?",
                    calc_heating_income."?column?_3" AS "?column?",
                    calc_heating_income."?column?_4" AS "?column?",
                    calc_heating_income."?column?_5" AS "?column?",
                    calc_heating_income."?column?_6" AS "?column?",
                    calc_heating_income."?column?_7" AS "?column?"
                   FROM calc_heating_income calc_heating_income(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
                UNION ALL
                 SELECT calc_hot_water.company,
                    calc_hot_water.company_cn,
                    calc_hot_water.item,
                    calc_hot_water.item_cn,
                    calc_hot_water.unit,
                    calc_hot_water.max,
                    calc_hot_water.max_1 AS max,
                    calc_hot_water."case",
                    calc_hot_water.case_1 AS "case",
                    calc_hot_water.case_2 AS "case",
                    calc_hot_water.case_3 AS "case",
                    calc_hot_water.case_4 AS "case",
                    calc_hot_water.case_5 AS "case",
                    calc_hot_water.case_6 AS "case",
                    calc_hot_water.case_7 AS "case"
                   FROM calc_hot_water calc_hot_water(company, company_cn, item, item_cn, unit, max, max_1, "case", case_1, case_2, case_3, case_4, case_5, case_6, case_7)
                UNION ALL
                 SELECT calc_steam.company,
                    calc_steam.company_cn,
                    calc_steam.item,
                    calc_steam.item_cn,
                    calc_steam.unit,
                    calc_steam.max,
                    calc_steam.max_1 AS max,
                    calc_steam."case",
                    calc_steam.case_1 AS "case",
                    calc_steam.case_2 AS "case",
                    calc_steam.case_3 AS "case",
                    calc_steam.case_4 AS "case",
                    calc_steam.case_5 AS "case",
                    calc_steam.case_6 AS "case",
                    calc_steam.case_7 AS "case"
                   FROM calc_steam calc_steam(company, company_cn, item, item_cn, unit, max, max_1, "case", case_1, case_2, case_3, case_4, case_5, case_6, case_7)) c
          GROUP BY c.company, c.company_cn
        ), calc_marginal_profit AS (
         SELECT di.company,
            di.company_cn,
            'eco_marginal_profit'::text AS item,
            '边际利润'::text AS item_cn,
            '万元'::text AS unit,
            di.biz_date,
            di.peer_date,
            di.value_biz_date - (COALESCE(ng.value_biz_date, 0::numeric) + COALESCE(pp.value_biz_date, 0::numeric) + COALESCE(pw.value_biz_date, 0::numeric) + COALESCE(am.value_biz_date, 0::numeric) + COALESCE(oh.value_biz_date, 0::numeric) + COALESCE(ih.value_biz_date, 0::numeric) + COALESCE(rc.value_biz_date, 0::numeric)) AS value_biz_date,
            di.value_peer_date - (COALESCE(ng.value_peer_date, 0::numeric) + COALESCE(pp.value_peer_date, 0::numeric) + COALESCE(pw.value_peer_date, 0::numeric) + COALESCE(am.value_peer_date, 0::numeric) + COALESCE(oh.value_peer_date, 0::numeric) + COALESCE(ih.value_peer_date, 0::numeric) + COALESCE(rc.value_peer_date, 0::numeric)) AS value_peer_date,
            di.sum_7d_biz - (COALESCE(ng.sum_7d_biz, 0::numeric) + COALESCE(pp.sum_7d_biz, 0::numeric) + COALESCE(pw.sum_7d_biz, 0::numeric) + COALESCE(am.sum_7d_biz, 0::numeric) + COALESCE(oh.sum_7d_biz, 0::numeric) + COALESCE(ih.sum_7d_biz, 0::numeric) + COALESCE(rc.sum_7d_biz, 0::numeric)) AS sum_7d_biz,
            di.sum_7d_peer - (COALESCE(ng.sum_7d_peer, 0::numeric) + COALESCE(pp.sum_7d_peer, 0::numeric) + COALESCE(pw.sum_7d_peer, 0::numeric) + COALESCE(am.sum_7d_peer, 0::numeric) + COALESCE(oh.sum_7d_peer, 0::numeric) + COALESCE(ih.sum_7d_peer, 0::numeric) + COALESCE(rc.sum_7d_peer, 0::numeric)) AS sum_7d_peer,
            di.sum_month_biz - (COALESCE(ng.sum_month_biz, 0::numeric) + COALESCE(pp.sum_month_biz, 0::numeric) + COALESCE(pw.sum_month_biz, 0::numeric) + COALESCE(am.sum_month_biz, 0::numeric) + COALESCE(oh.sum_month_biz, 0::numeric) + COALESCE(ih.sum_month_biz, 0::numeric) + COALESCE(rc.sum_month_biz, 0::numeric)) AS sum_month_biz,
            di.sum_month_peer - (COALESCE(ng.sum_month_peer, 0::numeric) + COALESCE(pp.sum_month_peer, 0::numeric) + COALESCE(pw.sum_month_peer, 0::numeric) + COALESCE(am.sum_month_peer, 0::numeric) + COALESCE(oh.sum_month_peer, 0::numeric) + COALESCE(ih.sum_month_peer, 0::numeric) + COALESCE(rc.sum_month_peer, 0::numeric)) AS sum_month_peer,
            di.sum_ytd_biz - (COALESCE(ng.sum_ytd_biz, 0::numeric) + COALESCE(pp.sum_ytd_biz, 0::numeric) + COALESCE(pw.sum_ytd_biz, 0::numeric) + COALESCE(am.sum_ytd_biz, 0::numeric) + COALESCE(oh.sum_ytd_biz, 0::numeric) + COALESCE(ih.sum_ytd_biz, 0::numeric) + COALESCE(rc.sum_ytd_biz, 0::numeric)) AS sum_ytd_biz,
            di.sum_ytd_peer - (COALESCE(ng.sum_ytd_peer, 0::numeric) + COALESCE(pp.sum_ytd_peer, 0::numeric) + COALESCE(pw.sum_ytd_peer, 0::numeric) + COALESCE(am.sum_ytd_peer, 0::numeric) + COALESCE(oh.sum_ytd_peer, 0::numeric) + COALESCE(ih.sum_ytd_peer, 0::numeric) + COALESCE(rc.sum_ytd_peer, 0::numeric)) AS sum_ytd_peer
           FROM calc_direct_income di
             LEFT JOIN calc_natural_gas_cost ng ON ng.company = di.company
             LEFT JOIN calc_purchased_power_cost pp ON pp.company = di.company
             LEFT JOIN calc_purchased_water_cost pw ON pw.company = di.company
             LEFT JOIN calc_aux_cost am ON am.company = di.company
             LEFT JOIN calc_outer_heat_cost oh ON oh.company = di.company
             LEFT JOIN calc_inner_purchased_heat_cost ih ON ih.company = di.company
             LEFT JOIN calc_coal_cost rc ON rc.company = di.company
        ), cost_non_coal AS (
         SELECT t.company,
            sum(t.value_biz_date) AS value_biz_date,
            sum(t.value_peer_date) AS value_peer_date,
            sum(t.sum_7d_biz) AS sum_7d_biz,
            sum(t.sum_7d_peer) AS sum_7d_peer,
            sum(t.sum_month_biz) AS sum_month_biz,
            sum(t.sum_month_peer) AS sum_month_peer,
            sum(t.sum_ytd_biz) AS sum_ytd_biz,
            sum(t.sum_ytd_peer) AS sum_ytd_peer
           FROM ( SELECT calc_natural_gas_cost.company,
                    calc_natural_gas_cost.value_biz_date,
                    calc_natural_gas_cost.value_peer_date,
                    calc_natural_gas_cost.sum_7d_biz,
                    calc_natural_gas_cost.sum_7d_peer,
                    calc_natural_gas_cost.sum_month_biz,
                    calc_natural_gas_cost.sum_month_peer,
                    calc_natural_gas_cost.sum_ytd_biz,
                    calc_natural_gas_cost.sum_ytd_peer
                   FROM calc_natural_gas_cost
                UNION ALL
                 SELECT calc_purchased_power_cost.company,
                    calc_purchased_power_cost.value_biz_date,
                    calc_purchased_power_cost.value_peer_date,
                    calc_purchased_power_cost.sum_7d_biz,
                    calc_purchased_power_cost.sum_7d_peer,
                    calc_purchased_power_cost.sum_month_biz,
                    calc_purchased_power_cost.sum_month_peer,
                    calc_purchased_power_cost.sum_ytd_biz,
                    calc_purchased_power_cost.sum_ytd_peer
                   FROM calc_purchased_power_cost
                UNION ALL
                 SELECT calc_purchased_water_cost.company,
                    calc_purchased_water_cost.value_biz_date,
                    calc_purchased_water_cost.value_peer_date,
                    calc_purchased_water_cost.sum_7d_biz,
                    calc_purchased_water_cost.sum_7d_peer,
                    calc_purchased_water_cost.sum_month_biz,
                    calc_purchased_water_cost.sum_month_peer,
                    calc_purchased_water_cost.sum_ytd_biz,
                    calc_purchased_water_cost.sum_ytd_peer
                   FROM calc_purchased_water_cost
                UNION ALL
                 SELECT calc_aux_cost.company,
                    calc_aux_cost.value_biz_date,
                    calc_aux_cost.value_peer_date,
                    calc_aux_cost.sum_7d_biz,
                    calc_aux_cost.sum_7d_peer,
                    calc_aux_cost.sum_month_biz,
                    calc_aux_cost.sum_month_peer,
                    calc_aux_cost.sum_ytd_biz,
                    calc_aux_cost.sum_ytd_peer
                   FROM calc_aux_cost
                UNION ALL
                 SELECT calc_outer_heat_cost.company,
                    calc_outer_heat_cost.value_biz_date,
                    calc_outer_heat_cost.value_peer_date,
                    calc_outer_heat_cost.sum_7d_biz,
                    calc_outer_heat_cost.sum_7d_peer,
                    calc_outer_heat_cost.sum_month_biz,
                    calc_outer_heat_cost.sum_month_peer,
                    calc_outer_heat_cost.sum_ytd_biz,
                    calc_outer_heat_cost.sum_ytd_peer
                   FROM calc_outer_heat_cost
                UNION ALL
                 SELECT calc_inner_purchased_heat_cost.company,
                    calc_inner_purchased_heat_cost.value_biz_date,
                    calc_inner_purchased_heat_cost.value_peer_date,
                    calc_inner_purchased_heat_cost.sum_7d_biz,
                    calc_inner_purchased_heat_cost.sum_7d_peer,
                    calc_inner_purchased_heat_cost.sum_month_biz,
                    calc_inner_purchased_heat_cost.sum_month_peer,
                    calc_inner_purchased_heat_cost.sum_ytd_biz,
                    calc_inner_purchased_heat_cost.sum_ytd_peer
                   FROM calc_inner_purchased_heat_cost) t
          GROUP BY t.company
        ), calc_comparable_marginal_profit AS (
         SELECT b.company,
            b.company_cn,
            'eco_comparable_marginal_profit'::text AS item,
            '可比煤价边际利润'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(max(di.value_biz_date), 0::numeric) - COALESCE(max(cnc.value_biz_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS value_biz_date,
            COALESCE(max(di.value_peer_date), 0::numeric) - COALESCE(max(cnc.value_peer_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS value_peer_date,
            COALESCE(max(di.sum_7d_biz), 0::numeric) - COALESCE(max(cnc.sum_7d_biz), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS sum_7d_biz,
            COALESCE(max(di.sum_7d_peer), 0::numeric) - COALESCE(max(cnc.sum_7d_peer), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS sum_7d_peer,
            COALESCE(max(di.sum_month_biz), 0::numeric) - COALESCE(max(cnc.sum_month_biz), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS sum_month_biz,
            COALESCE(max(di.sum_month_peer), 0::numeric) - COALESCE(max(cnc.sum_month_peer), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS sum_month_peer,
            COALESCE(max(di.sum_ytd_biz), 0::numeric) - COALESCE(max(cnc.sum_ytd_biz), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS sum_ytd_biz,
            COALESCE(max(di.sum_ytd_peer), 0::numeric) - COALESCE(max(cnc.sum_ytd_peer), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS sum_ytd_peer
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN calc_direct_income di ON di.company = b.company
             LEFT JOIN cost_non_coal cnc ON cnc.company = b.company
          GROUP BY b.company, b.company_cn
        ), calc_overall_efficiency AS (
         SELECT b.company,
            b.company_cn,
            'rate_overall_efficiency'::text AS item,
            '全厂热效率'::text AS item_cn,
            '%'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_7d_biz
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_7d_peer
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_month_biz
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_month_peer
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_ytd_biz
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.sum_ytd_peer
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS round
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc AS (
         SELECT calc_station_heat_selected.company,
            calc_station_heat_selected.company_cn,
            calc_station_heat_selected.item,
            calc_station_heat_selected.item_cn,
            calc_station_heat_selected.unit,
            calc_station_heat_selected.biz_date,
            calc_station_heat_selected.peer_date,
            calc_station_heat_selected.value_biz_date,
            calc_station_heat_selected.value_peer_date,
            calc_station_heat_selected.sum_7d_biz,
            calc_station_heat_selected.sum_7d_peer,
            calc_station_heat_selected.sum_month_biz,
            calc_station_heat_selected.sum_month_peer,
            calc_station_heat_selected.sum_ytd_biz,
            calc_station_heat_selected.sum_ytd_peer
           FROM calc_station_heat_selected
        UNION ALL
         SELECT calc_amount_daily_net_complaints_per_10k_m2.company,
            calc_amount_daily_net_complaints_per_10k_m2.company_cn,
            calc_amount_daily_net_complaints_per_10k_m2.item,
            calc_amount_daily_net_complaints_per_10k_m2.item_cn,
            calc_amount_daily_net_complaints_per_10k_m2.unit,
            calc_amount_daily_net_complaints_per_10k_m2.max,
            calc_amount_daily_net_complaints_per_10k_m2.max_1 AS max,
            calc_amount_daily_net_complaints_per_10k_m2."?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_1" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_2" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_3" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_4" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_5" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_6" AS "?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_7" AS "?column?"
           FROM calc_amount_daily_net_complaints_per_10k_m2 calc_amount_daily_net_complaints_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_rate_std_coal_per_heat.company,
            calc_rate_std_coal_per_heat.company_cn,
            calc_rate_std_coal_per_heat.item,
            calc_rate_std_coal_per_heat.item_cn,
            calc_rate_std_coal_per_heat.unit,
            calc_rate_std_coal_per_heat.max,
            calc_rate_std_coal_per_heat.max_1 AS max,
            calc_rate_std_coal_per_heat."?column?",
            calc_rate_std_coal_per_heat."?column?_1" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_2" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_3" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_4" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_5" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_6" AS "?column?",
            calc_rate_std_coal_per_heat."?column?_7" AS "?column?"
           FROM calc_rate_std_coal_per_heat calc_rate_std_coal_per_heat(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_rate_heat_per_10k_m2.company,
            calc_rate_heat_per_10k_m2.company_cn,
            calc_rate_heat_per_10k_m2.item,
            calc_rate_heat_per_10k_m2.item_cn,
            calc_rate_heat_per_10k_m2.unit,
            calc_rate_heat_per_10k_m2.max,
            calc_rate_heat_per_10k_m2.max_1 AS max,
            calc_rate_heat_per_10k_m2."?column?",
            calc_rate_heat_per_10k_m2."?column?_1" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_2" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_3" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_4" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_5" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_6" AS "?column?",
            calc_rate_heat_per_10k_m2."?column?_7" AS "?column?"
           FROM calc_rate_heat_per_10k_m2 calc_rate_heat_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_rate_power_per_10k_m2.company,
            calc_rate_power_per_10k_m2.company_cn,
            calc_rate_power_per_10k_m2.item,
            calc_rate_power_per_10k_m2.item_cn,
            calc_rate_power_per_10k_m2.unit,
            calc_rate_power_per_10k_m2.max,
            calc_rate_power_per_10k_m2.max_1 AS max,
            calc_rate_power_per_10k_m2."?column?",
            calc_rate_power_per_10k_m2."?column?_1" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_2" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_3" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_4" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_5" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_6" AS "?column?",
            calc_rate_power_per_10k_m2."?column?_7" AS "?column?"
           FROM calc_rate_power_per_10k_m2 calc_rate_power_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_rate_water_per_10k_m2.company,
            calc_rate_water_per_10k_m2.company_cn,
            calc_rate_water_per_10k_m2.item,
            calc_rate_water_per_10k_m2.item_cn,
            calc_rate_water_per_10k_m2.unit,
            calc_rate_water_per_10k_m2.max,
            calc_rate_water_per_10k_m2.max_1 AS max,
            calc_rate_water_per_10k_m2."?column?",
            calc_rate_water_per_10k_m2."?column?_1" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_2" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_3" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_4" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_5" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_6" AS "?column?",
            calc_rate_water_per_10k_m2."?column?_7" AS "?column?"
           FROM calc_rate_water_per_10k_m2 calc_rate_water_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_amount_heat_lose.company,
            calc_amount_heat_lose.company_cn,
            calc_amount_heat_lose.item,
            calc_amount_heat_lose.item_cn,
            calc_amount_heat_lose.unit,
            calc_amount_heat_lose.max,
            calc_amount_heat_lose.max_1 AS max,
            calc_amount_heat_lose."?column?",
            calc_amount_heat_lose."?column?_1" AS "?column?",
            calc_amount_heat_lose."?column?_2" AS "?column?",
            calc_amount_heat_lose."?column?_3" AS "?column?",
            calc_amount_heat_lose."?column?_4" AS "?column?",
            calc_amount_heat_lose."?column?_5" AS "?column?",
            calc_amount_heat_lose."?column?_6" AS "?column?",
            calc_amount_heat_lose."?column?_7" AS "?column?"
           FROM calc_amount_heat_lose calc_amount_heat_lose(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_power.company,
            calc_power.company_cn,
            calc_power.item,
            calc_power.item_cn,
            calc_power.unit,
            calc_power.biz_date,
            calc_power.peer_date,
            calc_power.value_biz_date,
            calc_power.value_peer_date,
            calc_power.sum_7d_biz,
            calc_power.sum_7d_peer,
            calc_power.sum_month_biz,
            calc_power.sum_month_peer,
            calc_power.sum_ytd_biz,
            calc_power.sum_ytd_peer
           FROM calc_power
        UNION ALL
         SELECT calc_inner_heat.company,
            calc_inner_heat.company_cn,
            calc_inner_heat.item,
            calc_inner_heat.item_cn,
            calc_inner_heat.unit,
            calc_inner_heat.max,
            calc_inner_heat.max_1 AS max,
            calc_inner_heat."?column?",
            calc_inner_heat."?column?_1" AS "?column?",
            calc_inner_heat."?column?_2" AS "?column?",
            calc_inner_heat."?column?_3" AS "?column?",
            calc_inner_heat."?column?_4" AS "?column?",
            calc_inner_heat."?column?_5" AS "?column?",
            calc_inner_heat."?column?_6" AS "?column?",
            calc_inner_heat."?column?_7" AS "?column?"
           FROM calc_inner_heat calc_inner_heat(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_heating_income.company,
            calc_heating_income.company_cn,
            calc_heating_income.item,
            calc_heating_income.item_cn,
            calc_heating_income.unit,
            calc_heating_income.max,
            calc_heating_income.max_1 AS max,
            calc_heating_income."?column?",
            calc_heating_income."?column?_1" AS "?column?",
            calc_heating_income."?column?_2" AS "?column?",
            calc_heating_income."?column?_3" AS "?column?",
            calc_heating_income."?column?_4" AS "?column?",
            calc_heating_income."?column?_5" AS "?column?",
            calc_heating_income."?column?_6" AS "?column?",
            calc_heating_income."?column?_7" AS "?column?"
           FROM calc_heating_income calc_heating_income(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1", "?column?_2", "?column?_3", "?column?_4", "?column?_5", "?column?_6", "?column?_7")
        UNION ALL
         SELECT calc_hot_water.company,
            calc_hot_water.company_cn,
            calc_hot_water.item,
            calc_hot_water.item_cn,
            calc_hot_water.unit,
            calc_hot_water.max,
            calc_hot_water.max_1 AS max,
            calc_hot_water."case",
            calc_hot_water.case_1 AS "case",
            calc_hot_water.case_2 AS "case",
            calc_hot_water.case_3 AS "case",
            calc_hot_water.case_4 AS "case",
            calc_hot_water.case_5 AS "case",
            calc_hot_water.case_6 AS "case",
            calc_hot_water.case_7 AS "case"
           FROM calc_hot_water calc_hot_water(company, company_cn, item, item_cn, unit, max, max_1, "case", case_1, case_2, case_3, case_4, case_5, case_6, case_7)
        UNION ALL
         SELECT calc_steam.company,
            calc_steam.company_cn,
            calc_steam.item,
            calc_steam.item_cn,
            calc_steam.unit,
            calc_steam.max,
            calc_steam.max_1 AS max,
            calc_steam."case",
            calc_steam.case_1 AS "case",
            calc_steam.case_2 AS "case",
            calc_steam.case_3 AS "case",
            calc_steam.case_4 AS "case",
            calc_steam.case_5 AS "case",
            calc_steam.case_6 AS "case",
            calc_steam.case_7 AS "case"
           FROM calc_steam calc_steam(company, company_cn, item, item_cn, unit, max, max_1, "case", case_1, case_2, case_3, case_4, case_5, case_6, case_7)
        UNION ALL
         SELECT calc_coal_cost.company,
            calc_coal_cost.company_cn,
            calc_coal_cost.item,
            calc_coal_cost.item_cn,
            calc_coal_cost.unit,
            calc_coal_cost.biz_date,
            calc_coal_cost.peer_date,
            calc_coal_cost.value_biz_date,
            calc_coal_cost.value_peer_date,
            calc_coal_cost.sum_7d_biz,
            calc_coal_cost.sum_7d_peer,
            calc_coal_cost.sum_month_biz,
            calc_coal_cost.sum_month_peer,
            calc_coal_cost.sum_ytd_biz,
            calc_coal_cost.sum_ytd_peer
           FROM calc_coal_cost
        UNION ALL
         SELECT calc_natural_gas_cost.company,
            calc_natural_gas_cost.company_cn,
            calc_natural_gas_cost.item,
            calc_natural_gas_cost.item_cn,
            calc_natural_gas_cost.unit,
            calc_natural_gas_cost.biz_date,
            calc_natural_gas_cost.peer_date,
            calc_natural_gas_cost.value_biz_date,
            calc_natural_gas_cost.value_peer_date,
            calc_natural_gas_cost.sum_7d_biz,
            calc_natural_gas_cost.sum_7d_peer,
            calc_natural_gas_cost.sum_month_biz,
            calc_natural_gas_cost.sum_month_peer,
            calc_natural_gas_cost.sum_ytd_biz,
            calc_natural_gas_cost.sum_ytd_peer
           FROM calc_natural_gas_cost
        UNION ALL
         SELECT calc_purchased_power_cost.company,
            calc_purchased_power_cost.company_cn,
            calc_purchased_power_cost.item,
            calc_purchased_power_cost.item_cn,
            calc_purchased_power_cost.unit,
            calc_purchased_power_cost.biz_date,
            calc_purchased_power_cost.peer_date,
            calc_purchased_power_cost.value_biz_date,
            calc_purchased_power_cost.value_peer_date,
            calc_purchased_power_cost.sum_7d_biz,
            calc_purchased_power_cost.sum_7d_peer,
            calc_purchased_power_cost.sum_month_biz,
            calc_purchased_power_cost.sum_month_peer,
            calc_purchased_power_cost.sum_ytd_biz,
            calc_purchased_power_cost.sum_ytd_peer
           FROM calc_purchased_power_cost
        UNION ALL
         SELECT calc_purchased_water_cost.company,
            calc_purchased_water_cost.company_cn,
            calc_purchased_water_cost.item,
            calc_purchased_water_cost.item_cn,
            calc_purchased_water_cost.unit,
            calc_purchased_water_cost.biz_date,
            calc_purchased_water_cost.peer_date,
            calc_purchased_water_cost.value_biz_date,
            calc_purchased_water_cost.value_peer_date,
            calc_purchased_water_cost.sum_7d_biz,
            calc_purchased_water_cost.sum_7d_peer,
            calc_purchased_water_cost.sum_month_biz,
            calc_purchased_water_cost.sum_month_peer,
            calc_purchased_water_cost.sum_ytd_biz,
            calc_purchased_water_cost.sum_ytd_peer
           FROM calc_purchased_water_cost
        UNION ALL
         SELECT calc_aux_cost.company,
            calc_aux_cost.company_cn,
            calc_aux_cost.item,
            calc_aux_cost.item_cn,
            calc_aux_cost.unit,
            calc_aux_cost.biz_date,
            calc_aux_cost.peer_date,
            calc_aux_cost.value_biz_date,
            calc_aux_cost.value_peer_date,
            calc_aux_cost.sum_7d_biz,
            calc_aux_cost.sum_7d_peer,
            calc_aux_cost.sum_month_biz,
            calc_aux_cost.sum_month_peer,
            calc_aux_cost.sum_ytd_biz,
            calc_aux_cost.sum_ytd_peer
           FROM calc_aux_cost
        UNION ALL
         SELECT calc_outer_heat_cost.company,
            calc_outer_heat_cost.company_cn,
            calc_outer_heat_cost.item,
            calc_outer_heat_cost.item_cn,
            calc_outer_heat_cost.unit,
            calc_outer_heat_cost.biz_date,
            calc_outer_heat_cost.peer_date,
            calc_outer_heat_cost.value_biz_date,
            calc_outer_heat_cost.value_peer_date,
            calc_outer_heat_cost.sum_7d_biz,
            calc_outer_heat_cost.sum_7d_peer,
            calc_outer_heat_cost.sum_month_biz,
            calc_outer_heat_cost.sum_month_peer,
            calc_outer_heat_cost.sum_ytd_biz,
            calc_outer_heat_cost.sum_ytd_peer
           FROM calc_outer_heat_cost
        UNION ALL
         SELECT calc_inner_purchased_heat_cost.company,
            calc_inner_purchased_heat_cost.company_cn,
            calc_inner_purchased_heat_cost.item,
            calc_inner_purchased_heat_cost.item_cn,
            calc_inner_purchased_heat_cost.unit,
            calc_inner_purchased_heat_cost.biz_date,
            calc_inner_purchased_heat_cost.peer_date,
            calc_inner_purchased_heat_cost.value_biz_date,
            calc_inner_purchased_heat_cost.value_peer_date,
            calc_inner_purchased_heat_cost.sum_7d_biz,
            calc_inner_purchased_heat_cost.sum_7d_peer,
            calc_inner_purchased_heat_cost.sum_month_biz,
            calc_inner_purchased_heat_cost.sum_month_peer,
            calc_inner_purchased_heat_cost.sum_ytd_biz,
            calc_inner_purchased_heat_cost.sum_ytd_peer
           FROM calc_inner_purchased_heat_cost
        UNION ALL
         SELECT calc_direct_income.company,
            calc_direct_income.company_cn,
            calc_direct_income.item,
            calc_direct_income.item_cn,
            calc_direct_income.unit,
            calc_direct_income.biz_date,
            calc_direct_income.peer_date,
            calc_direct_income.value_biz_date,
            calc_direct_income.value_peer_date,
            calc_direct_income.sum_7d_biz,
            calc_direct_income.sum_7d_peer,
            calc_direct_income.sum_month_biz,
            calc_direct_income.sum_month_peer,
            calc_direct_income.sum_ytd_biz,
            calc_direct_income.sum_ytd_peer
           FROM calc_direct_income
        UNION ALL
         SELECT calc_marginal_profit.company,
            calc_marginal_profit.company_cn,
            calc_marginal_profit.item,
            calc_marginal_profit.item_cn,
            calc_marginal_profit.unit,
            calc_marginal_profit.biz_date,
            calc_marginal_profit.peer_date,
            calc_marginal_profit.value_biz_date,
            calc_marginal_profit.value_peer_date,
            calc_marginal_profit.sum_7d_biz,
            calc_marginal_profit.sum_7d_peer,
            calc_marginal_profit.sum_month_biz,
            calc_marginal_profit.sum_month_peer,
            calc_marginal_profit.sum_ytd_biz,
            calc_marginal_profit.sum_ytd_peer
           FROM calc_marginal_profit
        UNION ALL
         SELECT calc_comparable_marginal_profit.company,
            calc_comparable_marginal_profit.company_cn,
            calc_comparable_marginal_profit.item,
            calc_comparable_marginal_profit.item_cn,
            calc_comparable_marginal_profit.unit,
            calc_comparable_marginal_profit.biz_date,
            calc_comparable_marginal_profit.peer_date,
            calc_comparable_marginal_profit.value_biz_date,
            calc_comparable_marginal_profit.value_peer_date,
            calc_comparable_marginal_profit.sum_7d_biz,
            calc_comparable_marginal_profit.sum_7d_peer,
            calc_comparable_marginal_profit.sum_month_biz,
            calc_comparable_marginal_profit.sum_month_peer,
            calc_comparable_marginal_profit.sum_ytd_biz,
            calc_comparable_marginal_profit.sum_ytd_peer
           FROM calc_comparable_marginal_profit
        UNION ALL
         SELECT calc_overall_efficiency.company,
            calc_overall_efficiency.company_cn,
            calc_overall_efficiency.item,
            calc_overall_efficiency.item_cn,
            calc_overall_efficiency.unit,
            calc_overall_efficiency.max,
            calc_overall_efficiency.max_1 AS max,
            calc_overall_efficiency.round,
            calc_overall_efficiency.round_1 AS round,
            calc_overall_efficiency.round_2 AS round,
            calc_overall_efficiency.round_3 AS round,
            calc_overall_efficiency.round_4 AS round,
            calc_overall_efficiency.round_5 AS round,
            calc_overall_efficiency.round_6 AS round,
            calc_overall_efficiency.round_7 AS round
           FROM calc_overall_efficiency calc_overall_efficiency(company, company_cn, item, item_cn, unit, max, max_1, round, round_1, round_2, round_3, round_4, round_5, round_6, round_7)
        )
 SELECT base.company,
    base.company_cn,
    base.item,
    base.item_cn,
    base.unit,
    base.biz_date,
    base.peer_date,
    base.value_biz_date,
    base.value_peer_date,
    base.sum_7d_biz,
    base.sum_7d_peer,
    base.sum_month_biz,
    base.sum_month_peer,
    base.sum_ytd_biz,
    base.sum_ytd_peer
   FROM base
  WHERE NOT (base.item = 'consumption_station_heat'::text AND (base.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AND NOT (base.company = 'GongRe'::text AND (base.item = ANY (ARRAY['eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text])))
UNION ALL
 SELECT calc.company,
    calc.company_cn,
    calc.item,
    calc.item_cn,
    calc.unit,
    calc.biz_date,
    calc.peer_date,
    calc.value_biz_date,
    calc.value_peer_date,
    calc.sum_7d_biz,
    calc.sum_7d_peer,
    calc.sum_month_biz,
    calc.sum_month_peer,
    calc.sum_ytd_biz,
    calc.sum_ytd_peer
   FROM calc;

-- 视图：groups
CREATE OR REPLACE VIEW public.groups AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.biz_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS biz_date
        ), anchor_dates AS (
         SELECT p.biz_date,
            (p.biz_date - '1 year'::interval)::date AS peer_date
           FROM params p
        ), w AS (
         SELECT anchor_dates.biz_date,
            anchor_dates.peer_date,
                CASE
                    WHEN anchor_dates.biz_date >= make_date(EXTRACT(year FROM anchor_dates.biz_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN anchor_dates.peer_date >= make_date(EXTRACT(year FROM anchor_dates.peer_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text)
                END AS peer_period
           FROM anchor_dates
        ), s AS (
         SELECT sum_basic_data.company,
            sum_basic_data.company_cn,
            sum_basic_data.item,
            sum_basic_data.item_cn,
            sum_basic_data.unit,
            sum_basic_data.biz_date,
            sum_basic_data.peer_date,
            sum_basic_data.value_biz_date,
            sum_basic_data.value_peer_date,
            sum_basic_data.sum_7d_biz,
            sum_basic_data.sum_7d_peer,
            sum_basic_data.sum_month_biz,
            sum_basic_data.sum_month_peer,
            sum_basic_data.sum_ytd_biz,
            sum_basic_data.sum_ytd_peer
           FROM sum_basic_data
        ), base_zc AS (
         SELECT s.item,
            s.item_cn,
            s.unit,
            s.biz_date,
            s.peer_date,
            sum(s.value_biz_date) AS value_biz_date,
            sum(s.value_peer_date) AS value_peer_date,
            sum(s.sum_7d_biz) AS sum_7d_biz,
            sum(s.sum_7d_peer) AS sum_7d_peer,
            sum(s.sum_month_biz) AS sum_month_biz,
            sum(s.sum_month_peer) AS sum_month_peer,
            sum(s.sum_ytd_biz) AS sum_ytd_biz,
            sum(s.sum_ytd_peer) AS sum_ytd_peer
           FROM s
          WHERE s.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text])
          GROUP BY s.item, s.item_cn, s.unit, s.biz_date, s.peer_date
        ), base_grp AS (
         SELECT s.item,
            s.item_cn,
            s.unit,
            s.biz_date,
            s.peer_date,
            sum(s.value_biz_date) AS value_biz_date,
            sum(s.value_peer_date) AS value_peer_date,
            sum(s.sum_7d_biz) AS sum_7d_biz,
            sum(s.sum_7d_peer) AS sum_7d_peer,
            sum(s.sum_month_biz) AS sum_month_biz,
            sum(s.sum_month_peer) AS sum_month_peer,
            sum(s.sum_ytd_biz) AS sum_ytd_biz,
            sum(s.sum_ytd_peer) AS sum_ytd_peer
           FROM s
          WHERE s.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
          GROUP BY s.item, s.item_cn, s.unit, s.biz_date, s.peer_date
        ), group_sum_raw_zhangtun AS (
         SELECT 'sum_consumption_amount_raw_coal_zhangtun'::text AS item,
            '原煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(s.unit), '吨'::text) AS unit,
            s.biz_date,
            s.peer_date,
            sum(s.value_biz_date) AS value_biz_date,
            sum(s.value_peer_date) AS value_peer_date,
            sum(s.sum_7d_biz) AS sum_7d_biz,
            sum(s.sum_7d_peer) AS sum_7d_peer,
            sum(s.sum_month_biz) AS sum_month_biz,
            sum(s.sum_month_peer) AS sum_month_peer,
            sum(s.sum_ytd_biz) AS sum_ytd_biz,
            sum(s.sum_ytd_peer) AS sum_ytd_peer
           FROM s
          WHERE (s.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND s.item = 'consumption_amount_raw_coal'::text OR s.company = 'ZhuangHe'::text AND s.item = 'consumption_amount_raw_coal_zhangtun'::text
          GROUP BY s.biz_date, s.peer_date
        ), group_sum_std_zhangtun AS (
         SELECT 'sum_consumption_std_coal_zhangtun'::text AS item,
            '标煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(s.unit), '吨'::text) AS unit,
            s.biz_date,
            s.peer_date,
            sum(s.value_biz_date) AS value_biz_date,
            sum(s.value_peer_date) AS value_peer_date,
            sum(s.sum_7d_biz) AS sum_7d_biz,
            sum(s.sum_7d_peer) AS sum_7d_peer,
            sum(s.sum_month_biz) AS sum_month_biz,
            sum(s.sum_month_peer) AS sum_month_peer,
            sum(s.sum_ytd_biz) AS sum_ytd_biz,
            sum(s.sum_ytd_peer) AS sum_ytd_peer
           FROM s
          WHERE (s.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND s.item = 'consumption_std_coal'::text OR s.company = 'ZhuangHe'::text AND s.item = 'consumption_std_coal_zhangtun'::text
          GROUP BY s.biz_date, s.peer_date
        ), denom_zc AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_peer
        ), denom_grp AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_peer
        ), yjy_power AS (
         SELECT s.biz_date,
            s.peer_date,
            sum(s.value_biz_date) AS value_biz_date,
            sum(s.value_peer_date) AS value_peer_date,
            sum(s.sum_7d_biz) AS sum_7d_biz,
            sum(s.sum_7d_peer) AS sum_7d_peer,
            sum(s.sum_month_biz) AS sum_month_biz,
            sum(s.sum_month_peer) AS sum_month_peer,
            sum(s.sum_ytd_biz) AS sum_ytd_biz,
            sum(s.sum_ytd_peer) AS sum_ytd_peer
           FROM s
          WHERE s.company = 'YanJiuYuan'::text AND s.item = 'consumption_station_purchased_power'::text
          GROUP BY s.biz_date, s.peer_date
        ), yjy_area AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_peer
        )
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    base_zc.item,
    base_zc.item_cn,
    base_zc.unit,
    base_zc.biz_date,
    base_zc.peer_date,
    base_zc.value_biz_date,
    base_zc.value_peer_date,
    base_zc.sum_7d_biz,
    base_zc.sum_7d_peer,
    base_zc.sum_month_biz,
    base_zc.sum_month_peer,
    base_zc.sum_ytd_biz,
    base_zc.sum_ytd_peer
   FROM base_zc
  WHERE base_zc.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'amount_heat_lose'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.area_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.area_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.area_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.area_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.area_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.area_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.area_peer, 0::numeric) AS sum_ytd_peer
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'amount_daily_net_complaints'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_7d_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_7d_peer,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_month_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_month_peer,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_ytd_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS sum_ytd_peer
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    a.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    a.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    a.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    a.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    a.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    a.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM ( SELECT base_zc.biz_date,
            base_zc.peer_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_7d_biz
                    ELSE 0::numeric
                END) AS sum_7d_biz,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_7d_peer
                    ELSE 0::numeric
                END) AS sum_7d_peer,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_month_biz
                    ELSE 0::numeric
                END) AS sum_month_biz,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_month_peer
                    ELSE 0::numeric
                END) AS sum_month_peer,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_ytd_biz
                    ELSE 0::numeric
                END) AS sum_ytd_biz,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.sum_ytd_peer
                    ELSE 0::numeric
                END) AS sum_ytd_peer
           FROM base_zc
          GROUP BY base_zc.biz_date, base_zc.peer_date) a,
    denom_zc d
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    base_grp.item,
    base_grp.item_cn,
    base_grp.unit,
    base_grp.biz_date,
    base_grp.peer_date,
    base_grp.value_biz_date,
    base_grp.value_peer_date,
    base_grp.sum_7d_biz,
    base_grp.sum_7d_peer,
    base_grp.sum_month_biz,
    base_grp.sum_month_peer,
    base_grp.sum_ytd_biz,
    base_grp.sum_ytd_peer
   FROM base_grp
  WHERE base_grp.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'amount_heat_lose'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    r.item,
    r.item_cn,
    r.unit,
    r.biz_date,
    r.peer_date,
    r.value_biz_date,
    r.value_peer_date,
    r.sum_7d_biz,
    r.sum_7d_peer,
    r.sum_month_biz,
    r.sum_month_peer,
    r.sum_ytd_biz,
    r.sum_ytd_peer
   FROM group_sum_raw_zhangtun r
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    s.item,
    s.item_cn,
    s.unit,
    s.biz_date,
    s.peer_date,
    s.value_biz_date,
    s.value_peer_date,
    s.sum_7d_biz,
    s.sum_7d_peer,
    s.sum_month_biz,
    s.sum_month_peer,
    s.sum_ytd_biz,
    s.sum_ytd_peer
   FROM group_sum_std_zhangtun s
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS value_peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_7d_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_7d_peer,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_month_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_month_peer,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_ytd_biz,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END)) / NULLIF(29.308 * sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END), 0::numeric), 0::numeric), 4) AS sum_ytd_peer
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_biz
            ELSE 0::numeric
        END) AS sum_7d_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_7d_peer
            ELSE 0::numeric
        END) AS sum_7d_peer,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_biz
            ELSE 0::numeric
        END) AS sum_month_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_month_peer
            ELSE 0::numeric
        END) AS sum_month_peer,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_biz
            ELSE 0::numeric
        END) AS sum_ytd_biz,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.sum_ytd_peer
            ELSE 0::numeric
        END) AS sum_ytd_peer
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.area_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.area_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.area_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.area_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.area_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.area_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.area_peer, 0::numeric) AS sum_ytd_peer
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'amount_daily_net_complaints'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    z.sum_7d_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    z.sum_7d_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    z.sum_month_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    z.sum_month_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    z.sum_ytd_biz * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    z.sum_ytd_peer * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2_YanJiuYuan'::text AS item,
    '供暖电单耗(-研究院)'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    (z.value_biz_date - COALESCE(y.value_biz_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS value_biz_date,
    (z.value_peer_date - COALESCE(y.value_peer_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS value_peer_date,
    (z.sum_7d_biz - COALESCE(y.sum_7d_biz, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS sum_7d_biz,
    (z.sum_7d_peer - COALESCE(y.sum_7d_peer, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS sum_7d_peer,
    (z.sum_month_biz - COALESCE(y.sum_month_biz, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS sum_month_biz,
    (z.sum_month_peer - COALESCE(y.sum_month_peer, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS sum_month_peer,
    (z.sum_ytd_biz - COALESCE(y.sum_ytd_biz, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS sum_ytd_biz,
    (z.sum_ytd_peer - COALESCE(y.sum_ytd_peer, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS sum_ytd_peer
   FROM base_grp z
     LEFT JOIN yjy_power y ON y.biz_date = z.biz_date AND y.peer_date = z.peer_date,
    denom_grp d,
    yjy_area a
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date,
    a.sum_7d_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_7d_biz,
    a.sum_7d_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_7d_peer,
    a.sum_month_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_month_biz,
    a.sum_month_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_month_peer,
    a.sum_ytd_biz / NULLIF(d.fee_biz, 0::numeric) AS sum_ytd_biz,
    a.sum_ytd_peer / NULLIF(d.fee_peer, 0::numeric) AS sum_ytd_peer
   FROM ( SELECT base_grp.biz_date,
            base_grp.peer_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_7d_biz
                    ELSE 0::numeric
                END) AS sum_7d_biz,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_7d_peer
                    ELSE 0::numeric
                END) AS sum_7d_peer,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_month_biz
                    ELSE 0::numeric
                END) AS sum_month_biz,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_month_peer
                    ELSE 0::numeric
                END) AS sum_month_peer,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_ytd_biz
                    ELSE 0::numeric
                END) AS sum_ytd_biz,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.sum_ytd_peer
                    ELSE 0::numeric
                END) AS sum_ytd_peer
           FROM base_grp
          GROUP BY base_grp.biz_date, base_grp.peer_date) a,
    denom_grp d;

-- 视图：analysis_company_daily
CREATE OR REPLACE VIEW public.analysis_company_daily AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.biz_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS biz_date
        ), anchor_dates AS (
         SELECT p.biz_date,
            (p.biz_date - '1 year'::interval)::date AS peer_date
           FROM params p
        ), window_defs AS (
         SELECT anchor_dates.biz_date,
            anchor_dates.peer_date,
                CASE
                    WHEN anchor_dates.biz_date >= make_date(EXTRACT(year FROM anchor_dates.biz_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN anchor_dates.peer_date >= make_date(EXTRACT(year FROM anchor_dates.peer_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text)
                END AS peer_period,
            1 AS days_day_biz,
            1 AS days_day_peer
           FROM anchor_dates
        ), base AS (
         SELECT d.company,
            d.company_cn,
            d.item,
            d.item_cn,
            d.unit,
            w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN window_defs w
          WHERE d.date = w.biz_date OR d.date = w.peer_date
          GROUP BY d.company, d.company_cn, d.item, d.item_cn, d.unit, w.biz_date, w.peer_date
        ), const_biz AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.biz_period
          GROUP BY c.company, c.item
        ), const_peer AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.peer_period
          GROUP BY c.company, c.item
        ), calc_station_heat AS (
         SELECT b.company,
            b.company_cn,
            'consumption_station_heat'::text AS item,
            '站内耗热量'::text AS item_cn,
            'GJ'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_biz_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_peer_date
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc_station_heat_selected AS (
         SELECT calc_station_heat.company,
            calc_station_heat.company_cn,
            calc_station_heat.item,
            calc_station_heat.item_cn,
            calc_station_heat.unit,
            calc_station_heat.biz_date,
            calc_station_heat.peer_date,
            calc_station_heat.value_biz_date,
            calc_station_heat.value_peer_date
           FROM calc_station_heat
          WHERE calc_station_heat.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
        ), calc_amount_daily_net_complaints_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'amount_daily_net_complaints_per_10k_m2'::text AS item,
            '万平方米省市净投诉量'::text AS item_cn,
            '件/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'amount_daily_net_complaints'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_area ON cb_area.company = b.company AND cb_area.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_area ON cp_area.company = b.company AND cp_area.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_area.value, cp_area.value
        ), calc_rate_std_coal_per_heat AS (
         SELECT b.company,
            b.company_cn,
            'rate_std_coal_per_heat'::text AS item,
            '供热标煤单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_heat_per_10k_m2 AS (
         SELECT sh.company,
            sh.company_cn,
            'rate_heat_per_10k_m2'::text AS item,
            '供暖热单耗'::text AS item_cn,
            'GJ/万㎡'::text AS unit,
            max(sh.biz_date) AS max,
            max(sh.peer_date) AS max,
            COALESCE(sh.value_biz_date, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.value_peer_date, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM calc_station_heat sh
             LEFT JOIN const_biz cb_fee ON cb_fee.company = sh.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = sh.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY sh.company, sh.company_cn, sh.value_biz_date, sh.value_peer_date, cb_fee.value, cp_fee.value
        ), calc_rate_power_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_power_per_10k_m2'::text AS item,
            '供暖电单耗'::text AS item_cn,
            'kWh/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_water_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_water_per_10k_m2'::text AS item,
            '供暖水单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_power AS (
         SELECT b.company,
            b.company_cn,
            'eco_power_supply_income'::text AS item,
            '供热供电收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ps ON cb_ps.company = b.company AND cb_ps.item = 'price_power_sales'::text
             LEFT JOIN const_peer cp_ps ON cp_ps.company = b.company AND cp_ps.item = 'price_power_sales'::text
          GROUP BY b.company, b.company_cn, cb_ps.value, cp_ps.value
        ), calc_inner_heat_supply_income AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_heat_supply_income'::text AS item,
            '其中：内售热收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hin ON cb_hin.company = b.company AND cb_hin.item = 'price_inner_heat_sales'::text
             LEFT JOIN const_peer cp_hin ON cp_hin.company = b.company AND cp_hin.item = 'price_inner_heat_sales'::text
          GROUP BY b.company, b.company_cn, cb_hin.value, cp_hin.value
        ), calc_heating_income AS (
         SELECT b.company,
            b.company_cn,
            'eco_heating_supply_income'::text AS item,
            '其中：暖收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_day_biz
                   FROM window_defs))::numeric / 156.0 AS value_biz_date,
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_day_peer
                   FROM window_defs))::numeric / 156.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sh ON cb_sh.company = b.company AND cb_sh.item = 'eco_season_heating_income'::text
             LEFT JOIN const_peer cp_sh ON cp_sh.company = b.company AND cp_sh.item = 'eco_season_heating_income'::text
          GROUP BY b.company, b.company_cn, cb_sh.value, cp_sh.value
        ), calc_hot_water AS (
         SELECT b.company,
            b.company_cn,
            'eco_hot_water_supply_income'::text AS item,
            '其中：售高温水收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS value_biz_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hw ON cb_hw.company = b.company AND cb_hw.item = 'price_hot_water_sales'::text
             LEFT JOIN const_peer cp_hw ON cp_hw.company = b.company AND cp_hw.item = 'price_hot_water_sales'::text
          GROUP BY b.company, b.company_cn, cb_hw.value, cp_hw.value
        ), calc_steam AS (
         SELECT b.company,
            b.company_cn,
            'eco_steam_supply_income'::text AS item,
            '其中：售汽收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS value_biz_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ss ON cb_ss.company = b.company AND cb_ss.item = 'price_steam_sales'::text
             LEFT JOIN const_peer cp_ss ON cp_ss.company = b.company AND cp_ss.item = 'price_steam_sales'::text
          GROUP BY b.company, b.company_cn, cb_ss.value, cp_ss.value
        ), calc_coal_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_coal_cost'::text AS item,
            '煤成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal'::text
          GROUP BY b.company, b.company_cn, cb_sc.value, cp_sc.value
        ), calc_natural_gas_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_natural_gas_cost'::text AS item,
            '天然气成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ng ON cb_ng.company = b.company AND cb_ng.item = 'price_natural_gas'::text
             LEFT JOIN const_peer cp_ng ON cp_ng.company = b.company AND cp_ng.item = 'price_natural_gas'::text
          GROUP BY b.company, b.company_cn, cb_ng.value, cp_ng.value
        ), calc_purchased_power_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_power_cost'::text AS item,
            '外购电成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pp ON cb_pp.company = b.company AND cb_pp.item = 'price_purchased_power'::text
             LEFT JOIN const_peer cp_pp ON cp_pp.company = b.company AND cp_pp.item = 'price_purchased_power'::text
          GROUP BY b.company, b.company_cn, cb_pp.value, cp_pp.value
        ), calc_purchased_water_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_water_cost'::text AS item,
            '购水成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pw ON cb_pw.company = b.company AND cb_pw.item = 'price_purchased_water'::text
             LEFT JOIN const_peer cp_pw ON cp_pw.company = b.company AND cp_pw.item = 'price_purchased_water'::text
          GROUP BY b.company, b.company_cn, cb_pw.value, cp_pw.value
        ), calc_aux_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_measurable_auxiliary_materials'::text AS item,
            '可计量辅材成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS value_biz_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ac ON cb_ac.company = b.company AND cb_ac.item = 'price_acid'::text
             LEFT JOIN const_peer cp_ac ON cp_ac.company = b.company AND cp_ac.item = 'price_acid'::text
             LEFT JOIN const_biz cb_al ON cb_al.company = b.company AND cb_al.item = 'price_alkali'::text
             LEFT JOIN const_peer cp_al ON cp_al.company = b.company AND cp_al.item = 'price_alkali'::text
             LEFT JOIN const_biz cb_ol ON cb_ol.company = b.company AND cb_ol.item = 'price_oil'::text
             LEFT JOIN const_peer cp_ol ON cp_ol.company = b.company AND cp_ol.item = 'price_oil'::text
             LEFT JOIN const_biz cb_aw ON cb_aw.company = b.company AND cb_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_peer cp_aw ON cp_aw.company = b.company AND cp_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_biz cb_ls ON cb_ls.company = b.company AND cb_ls.item = 'price_limestone'::text
             LEFT JOIN const_peer cp_ls ON cp_ls.company = b.company AND cp_ls.item = 'price_limestone'::text
             LEFT JOIN const_biz cb_lsp ON cb_lsp.company = b.company AND cb_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_peer cp_lsp ON cp_lsp.company = b.company AND cp_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_biz cb_mg ON cb_mg.company = b.company AND cb_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_peer cp_mg ON cp_mg.company = b.company AND cp_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_biz cb_dn ON cb_dn.company = b.company AND cb_dn.item = 'price_denitration_agent'::text
             LEFT JOIN const_peer cp_dn ON cp_dn.company = b.company AND cp_dn.item = 'price_denitration_agent'::text
          GROUP BY b.company, b.company_cn, cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value, cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value, cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
        ), calc_outer_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_outer_heat_cost'::text AS item,
            '外购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_oh ON cb_oh.company = b.company AND cb_oh.item = 'price_outer_purchased_heat'::text
             LEFT JOIN const_peer cp_oh ON cp_oh.company = b.company AND cp_oh.item = 'price_outer_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_oh.value, cp_oh.value
        ), calc_inner_purchased_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_purchased_heat_cost'::text AS item,
            '内购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ih ON cb_ih.company = b.company AND cb_ih.item = 'price_inner_purchased_heat'::text
             LEFT JOIN const_peer cp_ih ON cp_ih.company = b.company AND cp_ih.item = 'price_inner_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_ih.value, cp_ih.value
        ), calc_direct_income AS (
         SELECT c.company,
            c.company_cn,
            'eco_direct_income'::text AS item,
            '直接收入'::text AS item_cn,
            '万元'::text AS unit,
            max(c.biz_date) AS biz_date,
            max(c.peer_date) AS peer_date,
            sum(c.value_biz_date) AS value_biz_date,
            sum(c.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_power.company,
                    calc_power.company_cn,
                    calc_power.item,
                    calc_power.item_cn,
                    calc_power.unit,
                    calc_power.biz_date,
                    calc_power.peer_date,
                    calc_power.value_biz_date,
                    calc_power.value_peer_date
                   FROM calc_power
                UNION ALL
                 SELECT calc_inner_heat_supply_income.company,
                    calc_inner_heat_supply_income.company_cn,
                    calc_inner_heat_supply_income.item,
                    calc_inner_heat_supply_income.item_cn,
                    calc_inner_heat_supply_income.unit,
                    calc_inner_heat_supply_income.biz_date,
                    calc_inner_heat_supply_income.peer_date,
                    calc_inner_heat_supply_income.value_biz_date,
                    calc_inner_heat_supply_income.value_peer_date
                   FROM calc_inner_heat_supply_income
                UNION ALL
                 SELECT calc_heating_income.company,
                    calc_heating_income.company_cn,
                    calc_heating_income.item,
                    calc_heating_income.item_cn,
                    calc_heating_income.unit,
                    calc_heating_income.biz_date,
                    calc_heating_income.peer_date,
                    calc_heating_income.value_biz_date,
                    calc_heating_income.value_peer_date
                   FROM calc_heating_income
                UNION ALL
                 SELECT calc_hot_water.company,
                    calc_hot_water.company_cn,
                    calc_hot_water.item,
                    calc_hot_water.item_cn,
                    calc_hot_water.unit,
                    calc_hot_water.biz_date,
                    calc_hot_water.peer_date,
                    calc_hot_water.value_biz_date,
                    calc_hot_water.value_peer_date
                   FROM calc_hot_water
                UNION ALL
                 SELECT calc_steam.company,
                    calc_steam.company_cn,
                    calc_steam.item,
                    calc_steam.item_cn,
                    calc_steam.unit,
                    calc_steam.biz_date,
                    calc_steam.peer_date,
                    calc_steam.value_biz_date,
                    calc_steam.value_peer_date
                   FROM calc_steam) c
          GROUP BY c.company, c.company_cn
        ), calc_marginal_profit AS (
         SELECT di.company,
            di.company_cn,
            'eco_marginal_profit'::text AS item,
            '边际利润'::text AS item_cn,
            '万元'::text AS unit,
            di.biz_date,
            di.peer_date,
            di.value_biz_date - (COALESCE(ng.value_biz_date, 0::numeric) + COALESCE(pp.value_biz_date, 0::numeric) + COALESCE(pw.value_biz_date, 0::numeric) + COALESCE(am.value_biz_date, 0::numeric) + COALESCE(oh.value_biz_date, 0::numeric) + COALESCE(ih.value_biz_date, 0::numeric) + COALESCE(rc.value_biz_date, 0::numeric)) AS value_biz_date,
            di.value_peer_date - (COALESCE(ng.value_peer_date, 0::numeric) + COALESCE(pp.value_peer_date, 0::numeric) + COALESCE(pw.value_peer_date, 0::numeric) + COALESCE(am.value_peer_date, 0::numeric) + COALESCE(oh.value_peer_date, 0::numeric) + COALESCE(ih.value_peer_date, 0::numeric) + COALESCE(rc.value_peer_date, 0::numeric)) AS value_peer_date
           FROM calc_direct_income di
             LEFT JOIN calc_natural_gas_cost ng(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON ng.company = di.company
             LEFT JOIN calc_purchased_power_cost pp(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON pp.company = di.company
             LEFT JOIN calc_purchased_water_cost pw(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON pw.company = di.company
             LEFT JOIN calc_aux_cost am(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON am.company = di.company
             LEFT JOIN calc_outer_heat_cost oh(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON oh.company = di.company
             LEFT JOIN calc_inner_purchased_heat_cost ih(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON ih.company = di.company
             LEFT JOIN calc_coal_cost rc(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON rc.company = di.company
        ), cost_non_coal AS (
         SELECT t.company,
            sum(t.value_biz_date) AS value_biz_date,
            sum(t.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_natural_gas_cost.company,
                    calc_natural_gas_cost.value_biz_date,
                    calc_natural_gas_cost.value_peer_date
                   FROM calc_natural_gas_cost calc_natural_gas_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_purchased_power_cost.company,
                    calc_purchased_power_cost.value_biz_date,
                    calc_purchased_power_cost.value_peer_date
                   FROM calc_purchased_power_cost calc_purchased_power_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_purchased_water_cost.company,
                    calc_purchased_water_cost.value_biz_date,
                    calc_purchased_water_cost.value_peer_date
                   FROM calc_purchased_water_cost calc_purchased_water_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_aux_cost.company,
                    calc_aux_cost.value_biz_date,
                    calc_aux_cost.value_peer_date
                   FROM calc_aux_cost calc_aux_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_outer_heat_cost.company,
                    calc_outer_heat_cost.value_biz_date,
                    calc_outer_heat_cost.value_peer_date
                   FROM calc_outer_heat_cost calc_outer_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_inner_purchased_heat_cost.company,
                    calc_inner_purchased_heat_cost.value_biz_date,
                    calc_inner_purchased_heat_cost.value_peer_date
                   FROM calc_inner_purchased_heat_cost calc_inner_purchased_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)) t
          GROUP BY t.company
        ), calc_comparable_marginal_profit AS (
         SELECT b.company,
            b.company_cn,
            'eco_comparable_marginal_profit'::text AS item,
            '可比煤价边际利润'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(max(di.value_biz_date), 0::numeric) - COALESCE(max(cnc.value_biz_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS value_biz_date,
            COALESCE(max(di.value_peer_date), 0::numeric) - COALESCE(max(cnc.value_peer_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN calc_direct_income di ON di.company = b.company
             LEFT JOIN cost_non_coal cnc ON cnc.company = b.company
          GROUP BY b.company, b.company_cn
        ), calc_overall_efficiency AS (
         SELECT b.company,
            b.company_cn,
            'rate_overall_efficiency'::text AS item,
            '全厂热效率'::text AS item_cn,
            '%'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_peer_date
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc AS (
         SELECT calc_station_heat_selected.company,
            calc_station_heat_selected.company_cn,
            calc_station_heat_selected.item,
            calc_station_heat_selected.item_cn,
            calc_station_heat_selected.unit,
            calc_station_heat_selected.biz_date,
            calc_station_heat_selected.peer_date,
            calc_station_heat_selected.value_biz_date,
            calc_station_heat_selected.value_peer_date
           FROM calc_station_heat_selected
        UNION ALL
         SELECT calc_amount_daily_net_complaints_per_10k_m2.company,
            calc_amount_daily_net_complaints_per_10k_m2.company_cn,
            calc_amount_daily_net_complaints_per_10k_m2.item,
            calc_amount_daily_net_complaints_per_10k_m2.item_cn,
            calc_amount_daily_net_complaints_per_10k_m2.unit,
            calc_amount_daily_net_complaints_per_10k_m2.max,
            calc_amount_daily_net_complaints_per_10k_m2.max_1 AS max,
            calc_amount_daily_net_complaints_per_10k_m2."?column?",
            calc_amount_daily_net_complaints_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_amount_daily_net_complaints_per_10k_m2 calc_amount_daily_net_complaints_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_std_coal_per_heat.company,
            calc_rate_std_coal_per_heat.company_cn,
            calc_rate_std_coal_per_heat.item,
            calc_rate_std_coal_per_heat.item_cn,
            calc_rate_std_coal_per_heat.unit,
            calc_rate_std_coal_per_heat.max,
            calc_rate_std_coal_per_heat.max_1 AS max,
            calc_rate_std_coal_per_heat."?column?",
            calc_rate_std_coal_per_heat."?column?_1" AS "?column?"
           FROM calc_rate_std_coal_per_heat calc_rate_std_coal_per_heat(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_heat_per_10k_m2.company,
            calc_rate_heat_per_10k_m2.company_cn,
            calc_rate_heat_per_10k_m2.item,
            calc_rate_heat_per_10k_m2.item_cn,
            calc_rate_heat_per_10k_m2.unit,
            calc_rate_heat_per_10k_m2.max,
            calc_rate_heat_per_10k_m2.max_1 AS max,
            calc_rate_heat_per_10k_m2."?column?",
            calc_rate_heat_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_heat_per_10k_m2 calc_rate_heat_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_power_per_10k_m2.company,
            calc_rate_power_per_10k_m2.company_cn,
            calc_rate_power_per_10k_m2.item,
            calc_rate_power_per_10k_m2.item_cn,
            calc_rate_power_per_10k_m2.unit,
            calc_rate_power_per_10k_m2.max,
            calc_rate_power_per_10k_m2.max_1 AS max,
            calc_rate_power_per_10k_m2."?column?",
            calc_rate_power_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_power_per_10k_m2 calc_rate_power_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_water_per_10k_m2.company,
            calc_rate_water_per_10k_m2.company_cn,
            calc_rate_water_per_10k_m2.item,
            calc_rate_water_per_10k_m2.item_cn,
            calc_rate_water_per_10k_m2.unit,
            calc_rate_water_per_10k_m2.max,
            calc_rate_water_per_10k_m2.max_1 AS max,
            calc_rate_water_per_10k_m2."?column?",
            calc_rate_water_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_water_per_10k_m2 calc_rate_water_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_power.company,
            calc_power.company_cn,
            calc_power.item,
            calc_power.item_cn,
            calc_power.unit,
            calc_power.biz_date,
            calc_power.peer_date,
            calc_power.value_biz_date,
            calc_power.value_peer_date
           FROM calc_power
        UNION ALL
         SELECT calc_inner_heat_supply_income.company,
            calc_inner_heat_supply_income.company_cn,
            calc_inner_heat_supply_income.item,
            calc_inner_heat_supply_income.item_cn,
            calc_inner_heat_supply_income.unit,
            calc_inner_heat_supply_income.biz_date,
            calc_inner_heat_supply_income.peer_date,
            calc_inner_heat_supply_income.value_biz_date,
            calc_inner_heat_supply_income.value_peer_date
           FROM calc_inner_heat_supply_income
        UNION ALL
         SELECT calc_heating_income.company,
            calc_heating_income.company_cn,
            calc_heating_income.item,
            calc_heating_income.item_cn,
            calc_heating_income.unit,
            calc_heating_income.biz_date,
            calc_heating_income.peer_date,
            calc_heating_income.value_biz_date,
            calc_heating_income.value_peer_date
           FROM calc_heating_income
        UNION ALL
         SELECT calc_hot_water.company,
            calc_hot_water.company_cn,
            calc_hot_water.item,
            calc_hot_water.item_cn,
            calc_hot_water.unit,
            calc_hot_water.biz_date,
            calc_hot_water.peer_date,
            calc_hot_water.value_biz_date,
            calc_hot_water.value_peer_date
           FROM calc_hot_water
        UNION ALL
         SELECT calc_steam.company,
            calc_steam.company_cn,
            calc_steam.item,
            calc_steam.item_cn,
            calc_steam.unit,
            calc_steam.biz_date,
            calc_steam.peer_date,
            calc_steam.value_biz_date,
            calc_steam.value_peer_date
           FROM calc_steam
        UNION ALL
         SELECT calc_coal_cost.company,
            calc_coal_cost.company_cn,
            calc_coal_cost.item,
            calc_coal_cost.item_cn,
            calc_coal_cost.unit,
            calc_coal_cost.max,
            calc_coal_cost.max_1 AS max,
            calc_coal_cost.value_biz_date,
            calc_coal_cost.value_peer_date
           FROM calc_coal_cost calc_coal_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_natural_gas_cost.company,
            calc_natural_gas_cost.company_cn,
            calc_natural_gas_cost.item,
            calc_natural_gas_cost.item_cn,
            calc_natural_gas_cost.unit,
            calc_natural_gas_cost.max,
            calc_natural_gas_cost.max_1 AS max,
            calc_natural_gas_cost.value_biz_date,
            calc_natural_gas_cost.value_peer_date
           FROM calc_natural_gas_cost calc_natural_gas_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_purchased_power_cost.company,
            calc_purchased_power_cost.company_cn,
            calc_purchased_power_cost.item,
            calc_purchased_power_cost.item_cn,
            calc_purchased_power_cost.unit,
            calc_purchased_power_cost.max,
            calc_purchased_power_cost.max_1 AS max,
            calc_purchased_power_cost.value_biz_date,
            calc_purchased_power_cost.value_peer_date
           FROM calc_purchased_power_cost calc_purchased_power_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_purchased_water_cost.company,
            calc_purchased_water_cost.company_cn,
            calc_purchased_water_cost.item,
            calc_purchased_water_cost.item_cn,
            calc_purchased_water_cost.unit,
            calc_purchased_water_cost.max,
            calc_purchased_water_cost.max_1 AS max,
            calc_purchased_water_cost.value_biz_date,
            calc_purchased_water_cost.value_peer_date
           FROM calc_purchased_water_cost calc_purchased_water_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_aux_cost.company,
            calc_aux_cost.company_cn,
            calc_aux_cost.item,
            calc_aux_cost.item_cn,
            calc_aux_cost.unit,
            calc_aux_cost.max,
            calc_aux_cost.max_1 AS max,
            calc_aux_cost.value_biz_date,
            calc_aux_cost.value_peer_date
           FROM calc_aux_cost calc_aux_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_outer_heat_cost.company,
            calc_outer_heat_cost.company_cn,
            calc_outer_heat_cost.item,
            calc_outer_heat_cost.item_cn,
            calc_outer_heat_cost.unit,
            calc_outer_heat_cost.max,
            calc_outer_heat_cost.max_1 AS max,
            calc_outer_heat_cost.value_biz_date,
            calc_outer_heat_cost.value_peer_date
           FROM calc_outer_heat_cost calc_outer_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_inner_purchased_heat_cost.company,
            calc_inner_purchased_heat_cost.company_cn,
            calc_inner_purchased_heat_cost.item,
            calc_inner_purchased_heat_cost.item_cn,
            calc_inner_purchased_heat_cost.unit,
            calc_inner_purchased_heat_cost.max,
            calc_inner_purchased_heat_cost.max_1 AS max,
            calc_inner_purchased_heat_cost.value_biz_date,
            calc_inner_purchased_heat_cost.value_peer_date
           FROM calc_inner_purchased_heat_cost calc_inner_purchased_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_direct_income.company,
            calc_direct_income.company_cn,
            calc_direct_income.item,
            calc_direct_income.item_cn,
            calc_direct_income.unit,
            calc_direct_income.biz_date,
            calc_direct_income.peer_date,
            calc_direct_income.value_biz_date,
            calc_direct_income.value_peer_date
           FROM calc_direct_income
        UNION ALL
         SELECT calc_marginal_profit.company,
            calc_marginal_profit.company_cn,
            calc_marginal_profit.item,
            calc_marginal_profit.item_cn,
            calc_marginal_profit.unit,
            calc_marginal_profit.biz_date,
            calc_marginal_profit.peer_date,
            calc_marginal_profit.value_biz_date,
            calc_marginal_profit.value_peer_date
           FROM calc_marginal_profit
        UNION ALL
         SELECT calc_comparable_marginal_profit.company,
            calc_comparable_marginal_profit.company_cn,
            calc_comparable_marginal_profit.item,
            calc_comparable_marginal_profit.item_cn,
            calc_comparable_marginal_profit.unit,
            calc_comparable_marginal_profit.max,
            calc_comparable_marginal_profit.max_1 AS max,
            calc_comparable_marginal_profit.value_biz_date,
            calc_comparable_marginal_profit.value_peer_date
           FROM calc_comparable_marginal_profit calc_comparable_marginal_profit(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_overall_efficiency.company,
            calc_overall_efficiency.company_cn,
            calc_overall_efficiency.item,
            calc_overall_efficiency.item_cn,
            calc_overall_efficiency.unit,
            calc_overall_efficiency.max,
            calc_overall_efficiency.max_1 AS max,
            calc_overall_efficiency.value_biz_date,
            calc_overall_efficiency.value_peer_date
           FROM calc_overall_efficiency calc_overall_efficiency(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        )
 SELECT base.company,
    base.company_cn,
    base.item,
    base.item_cn,
    base.unit,
    base.biz_date,
    base.peer_date,
    base.value_biz_date,
    base.value_peer_date
   FROM base
  WHERE NOT (base.item = 'consumption_station_heat'::text AND (base.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AND NOT (base.company = 'GongRe'::text AND (base.item = ANY (ARRAY['eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text])))
UNION ALL
 SELECT calc.company,
    calc.company_cn,
    calc.item,
    calc.item_cn,
    calc.unit,
    calc.biz_date,
    calc.peer_date,
    calc.value_biz_date,
    calc.value_peer_date
   FROM calc;

-- 视图：analysis_company_sum
CREATE OR REPLACE VIEW public.analysis_company_sum AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.sum_start_date'::text, true)::date, '2025-11-01'::date) AS raw_start,
            COALESCE(current_setting('phoenix.sum_end_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS raw_end
        ), window_defs AS (
         SELECT LEAST(params.raw_start, params.raw_end) AS biz_start,
            GREATEST(params.raw_start, params.raw_end) AS biz_end,
            (LEAST(params.raw_start, params.raw_end) - '1 year'::interval)::date AS peer_start,
            (GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::date AS peer_end,
                CASE
                    WHEN GREATEST(params.raw_start, params.raw_end) >= make_date(EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer, 10, 1) THEN (lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN (GREATEST(params.raw_start, params.raw_end) - '1 year'::interval) >= make_date(EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer % 100)::text, 2, '0'::text)
                END AS peer_period,
            GREATEST(params.raw_start, params.raw_end) - LEAST(params.raw_start, params.raw_end) + 1 AS days_range_biz,
            GREATEST(params.raw_start, params.raw_end) - LEAST(params.raw_start, params.raw_end) + 1 AS days_range_peer
           FROM params
        ), base AS (
         SELECT d.company,
            d.company_cn,
            d.item,
            d.item_cn,
            d.unit,
            w.biz_end AS biz_date,
            w.peer_end AS peer_date,
            COALESCE(sum(d.value) FILTER (WHERE (d.item = ANY (ARRAY['sum_month_total_net_complaints'::text, 'sum_season_total_net_complaints'::text])) AND d.date = w.biz_end OR (d.item <> ALL (ARRAY['sum_month_total_net_complaints'::text, 'sum_season_total_net_complaints'::text])) AND d.date >= w.biz_start AND d.date <= w.biz_end), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE (d.item = ANY (ARRAY['sum_month_total_net_complaints'::text, 'sum_season_total_net_complaints'::text])) AND d.date = w.peer_end OR (d.item <> ALL (ARRAY['sum_month_total_net_complaints'::text, 'sum_season_total_net_complaints'::text])) AND d.date >= w.peer_start AND d.date <= w.peer_end), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN window_defs w
          WHERE d.date >= w.peer_start AND d.date <= w.biz_end
          GROUP BY d.company, d.company_cn, d.item, d.item_cn, d.unit, w.biz_end, w.peer_end
        ), const_biz AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.biz_period
          GROUP BY c.company, c.item
        ), const_peer AS (
         SELECT c.company,
            c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.period = w.peer_period
          GROUP BY c.company, c.item
        ), company_list AS (
         SELECT DISTINCT b.company,
            b.company_cn
           FROM base b
        ), season_total_net_complaints AS (
         SELECT d.company,
            d.company_cn,
            w.biz_end AS biz_date,
            w.peer_end AS peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_end), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_end), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN window_defs w
          WHERE d.item = 'sum_season_total_net_complaints'::text AND (d.date = w.biz_end OR d.date = w.peer_end)
          GROUP BY d.company, d.company_cn, w.biz_end, w.peer_end
        ), calc_station_heat AS (
         SELECT b.company,
            b.company_cn,
            'consumption_station_heat'::text AS item,
            '站内耗热量'::text AS item_cn,
            'GJ'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_biz_date,
            COALESCE(
                CASE
                    WHEN b.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]) THEN sum(
                    CASE
                        WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) - sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'consumption_station_heat'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END)
                END, 0::numeric) AS value_peer_date
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc_station_heat_selected AS (
         SELECT calc_station_heat.company,
            calc_station_heat.company_cn,
            calc_station_heat.item,
            calc_station_heat.item_cn,
            calc_station_heat.unit,
            calc_station_heat.biz_date,
            calc_station_heat.peer_date,
            calc_station_heat.value_biz_date,
            calc_station_heat.value_peer_date
           FROM calc_station_heat
          WHERE calc_station_heat.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
        ), calc_amount_daily_net_complaints_per_10k_m2 AS (
         SELECT cl.company,
            cl.company_cn,
            'amount_daily_net_complaints_per_10k_m2'::text AS item,
            '万平方米省市净投诉量'::text AS item_cn,
            '件/万㎡'::text AS unit,
            w.biz_end AS biz_date,
            w.peer_end AS peer_date,
            COALESCE(st.value_biz_date, 0::numeric) / NULLIF(COALESCE(cb_area.value, 0::numeric), 0::numeric) AS value_biz_date,
            COALESCE(st.value_peer_date, 0::numeric) / NULLIF(COALESCE(cp_area.value, 0::numeric), 0::numeric) AS value_peer_date
           FROM company_list cl
             CROSS JOIN window_defs w
             LEFT JOIN season_total_net_complaints st ON st.company = cl.company AND st.biz_date = w.biz_end AND st.peer_date = w.peer_end
             LEFT JOIN const_biz cb_area ON cb_area.company = cl.company AND cb_area.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_area ON cp_area.company = cl.company AND cp_area.item = 'amount_heating_fee_area'::text
        ), calc_rate_std_coal_per_heat AS (
         SELECT b.company,
            b.company_cn,
            'rate_std_coal_per_heat'::text AS item,
            '供热标煤单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_heat_per_10k_m2 AS (
         SELECT sh.company,
            sh.company_cn,
            'rate_heat_per_10k_m2'::text AS item,
            '供暖热单耗'::text AS item_cn,
            'GJ/万㎡'::text AS unit,
            max(sh.biz_date) AS max,
            max(sh.peer_date) AS max,
            COALESCE(sh.value_biz_date, 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sh.value_peer_date, 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM calc_station_heat sh
             LEFT JOIN const_biz cb_fee ON cb_fee.company = sh.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = sh.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY sh.company, sh.company_cn, sh.value_biz_date, sh.value_peer_date, cb_fee.value, cp_fee.value
        ), calc_rate_power_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_power_per_10k_m2'::text AS item,
            '供暖电单耗'::text AS item_cn,
            'kWh/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = 'consumption_station_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) * 10000.0 / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_rate_water_per_10k_m2 AS (
         SELECT b.company,
            b.company_cn,
            'rate_water_per_10k_m2'::text AS item,
            '供暖水单耗'::text AS item_cn,
            '吨/万㎡'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_biz_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cb_fee.value, 0::numeric), 0::numeric) AS "?column?",
            COALESCE(sum(
                CASE
                    WHEN b.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN b.value_peer_date
                    ELSE 0::numeric
                END), 0::numeric) / NULLIF(COALESCE(cp_fee.value, 0::numeric), 0::numeric) AS "?column?"
           FROM base b
             LEFT JOIN const_biz cb_fee ON cb_fee.company = b.company AND cb_fee.item = 'amount_heating_fee_area'::text
             LEFT JOIN const_peer cp_fee ON cp_fee.company = b.company AND cp_fee.item = 'amount_heating_fee_area'::text
          GROUP BY b.company, b.company_cn, cb_fee.value, cp_fee.value
        ), calc_power AS (
         SELECT b.company,
            b.company_cn,
            'eco_power_supply_income'::text AS item,
            '供热供电收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ps ON cb_ps.company = b.company AND cb_ps.item = 'price_power_sales'::text
             LEFT JOIN const_peer cp_ps ON cp_ps.company = b.company AND cp_ps.item = 'price_power_sales'::text
          GROUP BY b.company, b.company_cn, cb_ps.value, cp_ps.value
        ), calc_inner_heat_supply_income AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_heat_supply_income'::text AS item,
            '其中：内售热收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hin ON cb_hin.company = b.company AND cb_hin.item = 'price_inner_heat_sales'::text
             LEFT JOIN const_peer cp_hin ON cp_hin.company = b.company AND cp_hin.item = 'price_inner_heat_sales'::text
          GROUP BY b.company, b.company_cn, cb_hin.value, cp_hin.value
        ), calc_heating_income AS (
         SELECT b.company,
            b.company_cn,
            'eco_heating_supply_income'::text AS item,
            '其中：暖收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_range_biz
                   FROM window_defs))::numeric / 156.0 AS value_biz_date,
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_range_peer
                   FROM window_defs))::numeric / 156.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sh ON cb_sh.company = b.company AND cb_sh.item = 'eco_season_heating_income'::text
             LEFT JOIN const_peer cp_sh ON cp_sh.company = b.company AND cp_sh.item = 'eco_season_heating_income'::text
          GROUP BY b.company, b.company_cn, cb_sh.value, cp_sh.value
        ), calc_hot_water AS (
         SELECT b.company,
            b.company_cn,
            'eco_hot_water_supply_income'::text AS item,
            '其中：售高温水收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0
                END AS value_biz_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_hot_water_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0
                END AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hw ON cb_hw.company = b.company AND cb_hw.item = 'price_hot_water_sales'::text
             LEFT JOIN const_peer cp_hw ON cp_hw.company = b.company AND cp_hw.item = 'price_hot_water_sales'::text
          GROUP BY b.company, b.company_cn, cb_hw.value, cp_hw.value
        ), calc_steam AS (
         SELECT b.company,
            b.company_cn,
            'eco_steam_supply_income'::text AS item,
            '其中：售汽收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                        ELSE 0::numeric
                    END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0
                END AS value_biz_date,
                CASE
                    WHEN b.company = 'GongRe'::text THEN COALESCE(sum(
                    CASE
                        WHEN b.item = 'eco_steam_supply_income'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END), 0::numeric)
                    ELSE sum(
                    CASE
                        WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                        ELSE 0::numeric
                    END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0
                END AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ss ON cb_ss.company = b.company AND cb_ss.item = 'price_steam_sales'::text
             LEFT JOIN const_peer cp_ss ON cp_ss.company = b.company AND cp_ss.item = 'price_steam_sales'::text
          GROUP BY b.company, b.company_cn, cb_ss.value, cp_ss.value
        ), calc_coal_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_coal_cost'::text AS item,
            '煤成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal'::text
          GROUP BY b.company, b.company_cn, cb_sc.value, cp_sc.value
        ), calc_natural_gas_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_natural_gas_cost'::text AS item,
            '天然气成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ng ON cb_ng.company = b.company AND cb_ng.item = 'price_natural_gas'::text
             LEFT JOIN const_peer cp_ng ON cp_ng.company = b.company AND cp_ng.item = 'price_natural_gas'::text
          GROUP BY b.company, b.company_cn, cb_ng.value, cp_ng.value
        ), calc_purchased_power_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_power_cost'::text AS item,
            '外购电成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pp ON cb_pp.company = b.company AND cb_pp.item = 'price_purchased_power'::text
             LEFT JOIN const_peer cp_pp ON cp_pp.company = b.company AND cp_pp.item = 'price_purchased_power'::text
          GROUP BY b.company, b.company_cn, cb_pp.value, cp_pp.value
        ), calc_purchased_water_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_purchased_water_cost'::text AS item,
            '购水成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pw ON cb_pw.company = b.company AND cb_pw.item = 'price_purchased_water'::text
             LEFT JOIN const_peer cp_pw ON cp_pw.company = b.company AND cp_pw.item = 'price_purchased_water'::text
          GROUP BY b.company, b.company_cn, cb_pw.value, cp_pw.value
        ), calc_aux_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_measurable_auxiliary_materials'::text AS item,
            '可计量辅材成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS value_biz_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ac ON cb_ac.company = b.company AND cb_ac.item = 'price_acid'::text
             LEFT JOIN const_peer cp_ac ON cp_ac.company = b.company AND cp_ac.item = 'price_acid'::text
             LEFT JOIN const_biz cb_al ON cb_al.company = b.company AND cb_al.item = 'price_alkali'::text
             LEFT JOIN const_peer cp_al ON cp_al.company = b.company AND cp_al.item = 'price_alkali'::text
             LEFT JOIN const_biz cb_ol ON cb_ol.company = b.company AND cb_ol.item = 'price_oil'::text
             LEFT JOIN const_peer cp_ol ON cp_ol.company = b.company AND cp_ol.item = 'price_oil'::text
             LEFT JOIN const_biz cb_aw ON cb_aw.company = b.company AND cb_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_peer cp_aw ON cp_aw.company = b.company AND cp_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_biz cb_ls ON cb_ls.company = b.company AND cb_ls.item = 'price_limestone'::text
             LEFT JOIN const_peer cp_ls ON cp_ls.company = b.company AND cp_ls.item = 'price_limestone'::text
             LEFT JOIN const_biz cb_lsp ON cb_lsp.company = b.company AND cb_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_peer cp_lsp ON cp_lsp.company = b.company AND cp_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_biz cb_mg ON cb_mg.company = b.company AND cb_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_peer cp_mg ON cp_mg.company = b.company AND cp_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_biz cb_dn ON cb_dn.company = b.company AND cb_dn.item = 'price_denitration_agent'::text
             LEFT JOIN const_peer cp_dn ON cp_dn.company = b.company AND cp_dn.item = 'price_denitration_agent'::text
          GROUP BY b.company, b.company_cn, cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value, cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value, cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
        ), calc_outer_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_outer_heat_cost'::text AS item,
            '外购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_oh ON cb_oh.company = b.company AND cb_oh.item = 'price_outer_purchased_heat'::text
             LEFT JOIN const_peer cp_oh ON cp_oh.company = b.company AND cp_oh.item = 'price_outer_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_oh.value, cp_oh.value
        ), calc_inner_purchased_heat_cost AS (
         SELECT b.company,
            b.company_cn,
            'eco_inner_purchased_heat_cost'::text AS item,
            '内购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ih ON cb_ih.company = b.company AND cb_ih.item = 'price_inner_purchased_heat'::text
             LEFT JOIN const_peer cp_ih ON cp_ih.company = b.company AND cp_ih.item = 'price_inner_purchased_heat'::text
          GROUP BY b.company, b.company_cn, cb_ih.value, cp_ih.value
        ), calc_direct_income AS (
         SELECT c.company,
            c.company_cn,
            'eco_direct_income'::text AS item,
            '直接收入'::text AS item_cn,
            '万元'::text AS unit,
            max(c.biz_date) AS biz_date,
            max(c.peer_date) AS peer_date,
            sum(c.value_biz_date) AS value_biz_date,
            sum(c.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_power.company,
                    calc_power.company_cn,
                    calc_power.item,
                    calc_power.item_cn,
                    calc_power.unit,
                    calc_power.biz_date,
                    calc_power.peer_date,
                    calc_power.value_biz_date,
                    calc_power.value_peer_date
                   FROM calc_power
                UNION ALL
                 SELECT calc_inner_heat_supply_income.company,
                    calc_inner_heat_supply_income.company_cn,
                    calc_inner_heat_supply_income.item,
                    calc_inner_heat_supply_income.item_cn,
                    calc_inner_heat_supply_income.unit,
                    calc_inner_heat_supply_income.biz_date,
                    calc_inner_heat_supply_income.peer_date,
                    calc_inner_heat_supply_income.value_biz_date,
                    calc_inner_heat_supply_income.value_peer_date
                   FROM calc_inner_heat_supply_income
                UNION ALL
                 SELECT calc_heating_income.company,
                    calc_heating_income.company_cn,
                    calc_heating_income.item,
                    calc_heating_income.item_cn,
                    calc_heating_income.unit,
                    calc_heating_income.biz_date,
                    calc_heating_income.peer_date,
                    calc_heating_income.value_biz_date,
                    calc_heating_income.value_peer_date
                   FROM calc_heating_income
                UNION ALL
                 SELECT calc_hot_water.company,
                    calc_hot_water.company_cn,
                    calc_hot_water.item,
                    calc_hot_water.item_cn,
                    calc_hot_water.unit,
                    calc_hot_water.biz_date,
                    calc_hot_water.peer_date,
                    calc_hot_water.value_biz_date,
                    calc_hot_water.value_peer_date
                   FROM calc_hot_water
                UNION ALL
                 SELECT calc_steam.company,
                    calc_steam.company_cn,
                    calc_steam.item,
                    calc_steam.item_cn,
                    calc_steam.unit,
                    calc_steam.biz_date,
                    calc_steam.peer_date,
                    calc_steam.value_biz_date,
                    calc_steam.value_peer_date
                   FROM calc_steam) c
          GROUP BY c.company, c.company_cn
        ), calc_marginal_profit AS (
         SELECT di.company,
            di.company_cn,
            'eco_marginal_profit'::text AS item,
            '边际利润'::text AS item_cn,
            '万元'::text AS unit,
            di.biz_date,
            di.peer_date,
            di.value_biz_date - (COALESCE(ng.value_biz_date, 0::numeric) + COALESCE(pp.value_biz_date, 0::numeric) + COALESCE(pw.value_biz_date, 0::numeric) + COALESCE(am.value_biz_date, 0::numeric) + COALESCE(oh.value_biz_date, 0::numeric) + COALESCE(ih.value_biz_date, 0::numeric) + COALESCE(rc.value_biz_date, 0::numeric)) AS value_biz_date,
            di.value_peer_date - (COALESCE(ng.value_peer_date, 0::numeric) + COALESCE(pp.value_peer_date, 0::numeric) + COALESCE(pw.value_peer_date, 0::numeric) + COALESCE(am.value_peer_date, 0::numeric) + COALESCE(oh.value_peer_date, 0::numeric) + COALESCE(ih.value_peer_date, 0::numeric) + COALESCE(rc.value_peer_date, 0::numeric)) AS value_peer_date
           FROM calc_direct_income di
             LEFT JOIN calc_natural_gas_cost ng(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON ng.company = di.company
             LEFT JOIN calc_purchased_power_cost pp(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON pp.company = di.company
             LEFT JOIN calc_purchased_water_cost pw(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON pw.company = di.company
             LEFT JOIN calc_aux_cost am(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON am.company = di.company
             LEFT JOIN calc_outer_heat_cost oh(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON oh.company = di.company
             LEFT JOIN calc_inner_purchased_heat_cost ih(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON ih.company = di.company
             LEFT JOIN calc_coal_cost rc(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date) ON rc.company = di.company
        ), cost_non_coal AS (
         SELECT t.company,
            sum(t.value_biz_date) AS value_biz_date,
            sum(t.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_natural_gas_cost.company,
                    calc_natural_gas_cost.value_biz_date,
                    calc_natural_gas_cost.value_peer_date
                   FROM calc_natural_gas_cost calc_natural_gas_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_purchased_power_cost.company,
                    calc_purchased_power_cost.value_biz_date,
                    calc_purchased_power_cost.value_peer_date
                   FROM calc_purchased_power_cost calc_purchased_power_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_purchased_water_cost.company,
                    calc_purchased_water_cost.value_biz_date,
                    calc_purchased_water_cost.value_peer_date
                   FROM calc_purchased_water_cost calc_purchased_water_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_aux_cost.company,
                    calc_aux_cost.value_biz_date,
                    calc_aux_cost.value_peer_date
                   FROM calc_aux_cost calc_aux_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_outer_heat_cost.company,
                    calc_outer_heat_cost.value_biz_date,
                    calc_outer_heat_cost.value_peer_date
                   FROM calc_outer_heat_cost calc_outer_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
                UNION ALL
                 SELECT calc_inner_purchased_heat_cost.company,
                    calc_inner_purchased_heat_cost.value_biz_date,
                    calc_inner_purchased_heat_cost.value_peer_date
                   FROM calc_inner_purchased_heat_cost calc_inner_purchased_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)) t
          GROUP BY t.company
        ), calc_comparable_marginal_profit AS (
         SELECT b.company,
            b.company_cn,
            'eco_comparable_marginal_profit'::text AS item,
            '可比煤价边际利润'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(max(di.value_biz_date), 0::numeric) - COALESCE(max(cnc.value_biz_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS value_biz_date,
            COALESCE(max(di.value_peer_date), 0::numeric) - COALESCE(max(cnc.value_peer_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.company = b.company AND cb_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.company = b.company AND cp_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN calc_direct_income di ON di.company = b.company
             LEFT JOIN cost_non_coal cnc ON cnc.company = b.company
          GROUP BY b.company, b.company_cn
        ), calc_overall_efficiency AS (
         SELECT b.company,
            b.company_cn,
            'rate_overall_efficiency'::text AS item,
            '全厂热效率'::text AS item_cn,
            '%'::text AS unit,
            max(b.biz_date) AS max,
            max(b.peer_date) AS max,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_peer_date
           FROM base b
          GROUP BY b.company, b.company_cn
        ), calc AS (
         SELECT calc_station_heat_selected.company,
            calc_station_heat_selected.company_cn,
            calc_station_heat_selected.item,
            calc_station_heat_selected.item_cn,
            calc_station_heat_selected.unit,
            calc_station_heat_selected.biz_date,
            calc_station_heat_selected.peer_date,
            calc_station_heat_selected.value_biz_date,
            calc_station_heat_selected.value_peer_date
           FROM calc_station_heat_selected
        UNION ALL
         SELECT calc_amount_daily_net_complaints_per_10k_m2.company,
            calc_amount_daily_net_complaints_per_10k_m2.company_cn,
            calc_amount_daily_net_complaints_per_10k_m2.item,
            calc_amount_daily_net_complaints_per_10k_m2.item_cn,
            calc_amount_daily_net_complaints_per_10k_m2.unit,
            calc_amount_daily_net_complaints_per_10k_m2.biz_date,
            calc_amount_daily_net_complaints_per_10k_m2.peer_date,
            calc_amount_daily_net_complaints_per_10k_m2.value_biz_date,
            calc_amount_daily_net_complaints_per_10k_m2.value_peer_date
           FROM calc_amount_daily_net_complaints_per_10k_m2
        UNION ALL
         SELECT calc_rate_std_coal_per_heat.company,
            calc_rate_std_coal_per_heat.company_cn,
            calc_rate_std_coal_per_heat.item,
            calc_rate_std_coal_per_heat.item_cn,
            calc_rate_std_coal_per_heat.unit,
            calc_rate_std_coal_per_heat.max,
            calc_rate_std_coal_per_heat.max_1 AS max,
            calc_rate_std_coal_per_heat."?column?",
            calc_rate_std_coal_per_heat."?column?_1" AS "?column?"
           FROM calc_rate_std_coal_per_heat calc_rate_std_coal_per_heat(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_heat_per_10k_m2.company,
            calc_rate_heat_per_10k_m2.company_cn,
            calc_rate_heat_per_10k_m2.item,
            calc_rate_heat_per_10k_m2.item_cn,
            calc_rate_heat_per_10k_m2.unit,
            calc_rate_heat_per_10k_m2.max,
            calc_rate_heat_per_10k_m2.max_1 AS max,
            calc_rate_heat_per_10k_m2."?column?",
            calc_rate_heat_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_heat_per_10k_m2 calc_rate_heat_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_power_per_10k_m2.company,
            calc_rate_power_per_10k_m2.company_cn,
            calc_rate_power_per_10k_m2.item,
            calc_rate_power_per_10k_m2.item_cn,
            calc_rate_power_per_10k_m2.unit,
            calc_rate_power_per_10k_m2.max,
            calc_rate_power_per_10k_m2.max_1 AS max,
            calc_rate_power_per_10k_m2."?column?",
            calc_rate_power_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_power_per_10k_m2 calc_rate_power_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_rate_water_per_10k_m2.company,
            calc_rate_water_per_10k_m2.company_cn,
            calc_rate_water_per_10k_m2.item,
            calc_rate_water_per_10k_m2.item_cn,
            calc_rate_water_per_10k_m2.unit,
            calc_rate_water_per_10k_m2.max,
            calc_rate_water_per_10k_m2.max_1 AS max,
            calc_rate_water_per_10k_m2."?column?",
            calc_rate_water_per_10k_m2."?column?_1" AS "?column?"
           FROM calc_rate_water_per_10k_m2 calc_rate_water_per_10k_m2(company, company_cn, item, item_cn, unit, max, max_1, "?column?", "?column?_1")
        UNION ALL
         SELECT calc_power.company,
            calc_power.company_cn,
            calc_power.item,
            calc_power.item_cn,
            calc_power.unit,
            calc_power.biz_date,
            calc_power.peer_date,
            calc_power.value_biz_date,
            calc_power.value_peer_date
           FROM calc_power
        UNION ALL
         SELECT calc_inner_heat_supply_income.company,
            calc_inner_heat_supply_income.company_cn,
            calc_inner_heat_supply_income.item,
            calc_inner_heat_supply_income.item_cn,
            calc_inner_heat_supply_income.unit,
            calc_inner_heat_supply_income.biz_date,
            calc_inner_heat_supply_income.peer_date,
            calc_inner_heat_supply_income.value_biz_date,
            calc_inner_heat_supply_income.value_peer_date
           FROM calc_inner_heat_supply_income
        UNION ALL
         SELECT calc_heating_income.company,
            calc_heating_income.company_cn,
            calc_heating_income.item,
            calc_heating_income.item_cn,
            calc_heating_income.unit,
            calc_heating_income.biz_date,
            calc_heating_income.peer_date,
            calc_heating_income.value_biz_date,
            calc_heating_income.value_peer_date
           FROM calc_heating_income
        UNION ALL
         SELECT calc_hot_water.company,
            calc_hot_water.company_cn,
            calc_hot_water.item,
            calc_hot_water.item_cn,
            calc_hot_water.unit,
            calc_hot_water.biz_date,
            calc_hot_water.peer_date,
            calc_hot_water.value_biz_date,
            calc_hot_water.value_peer_date
           FROM calc_hot_water
        UNION ALL
         SELECT calc_steam.company,
            calc_steam.company_cn,
            calc_steam.item,
            calc_steam.item_cn,
            calc_steam.unit,
            calc_steam.biz_date,
            calc_steam.peer_date,
            calc_steam.value_biz_date,
            calc_steam.value_peer_date
           FROM calc_steam
        UNION ALL
         SELECT calc_coal_cost.company,
            calc_coal_cost.company_cn,
            calc_coal_cost.item,
            calc_coal_cost.item_cn,
            calc_coal_cost.unit,
            calc_coal_cost.max,
            calc_coal_cost.max_1 AS max,
            calc_coal_cost.value_biz_date,
            calc_coal_cost.value_peer_date
           FROM calc_coal_cost calc_coal_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_natural_gas_cost.company,
            calc_natural_gas_cost.company_cn,
            calc_natural_gas_cost.item,
            calc_natural_gas_cost.item_cn,
            calc_natural_gas_cost.unit,
            calc_natural_gas_cost.max,
            calc_natural_gas_cost.max_1 AS max,
            calc_natural_gas_cost.value_biz_date,
            calc_natural_gas_cost.value_peer_date
           FROM calc_natural_gas_cost calc_natural_gas_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_purchased_power_cost.company,
            calc_purchased_power_cost.company_cn,
            calc_purchased_power_cost.item,
            calc_purchased_power_cost.item_cn,
            calc_purchased_power_cost.unit,
            calc_purchased_power_cost.max,
            calc_purchased_power_cost.max_1 AS max,
            calc_purchased_power_cost.value_biz_date,
            calc_purchased_power_cost.value_peer_date
           FROM calc_purchased_power_cost calc_purchased_power_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_purchased_water_cost.company,
            calc_purchased_water_cost.company_cn,
            calc_purchased_water_cost.item,
            calc_purchased_water_cost.item_cn,
            calc_purchased_water_cost.unit,
            calc_purchased_water_cost.max,
            calc_purchased_water_cost.max_1 AS max,
            calc_purchased_water_cost.value_biz_date,
            calc_purchased_water_cost.value_peer_date
           FROM calc_purchased_water_cost calc_purchased_water_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_aux_cost.company,
            calc_aux_cost.company_cn,
            calc_aux_cost.item,
            calc_aux_cost.item_cn,
            calc_aux_cost.unit,
            calc_aux_cost.max,
            calc_aux_cost.max_1 AS max,
            calc_aux_cost.value_biz_date,
            calc_aux_cost.value_peer_date
           FROM calc_aux_cost calc_aux_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_outer_heat_cost.company,
            calc_outer_heat_cost.company_cn,
            calc_outer_heat_cost.item,
            calc_outer_heat_cost.item_cn,
            calc_outer_heat_cost.unit,
            calc_outer_heat_cost.max,
            calc_outer_heat_cost.max_1 AS max,
            calc_outer_heat_cost.value_biz_date,
            calc_outer_heat_cost.value_peer_date
           FROM calc_outer_heat_cost calc_outer_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_inner_purchased_heat_cost.company,
            calc_inner_purchased_heat_cost.company_cn,
            calc_inner_purchased_heat_cost.item,
            calc_inner_purchased_heat_cost.item_cn,
            calc_inner_purchased_heat_cost.unit,
            calc_inner_purchased_heat_cost.max,
            calc_inner_purchased_heat_cost.max_1 AS max,
            calc_inner_purchased_heat_cost.value_biz_date,
            calc_inner_purchased_heat_cost.value_peer_date
           FROM calc_inner_purchased_heat_cost calc_inner_purchased_heat_cost(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        UNION ALL
         SELECT calc_direct_income.company,
            calc_direct_income.company_cn,
            calc_direct_income.item,
            calc_direct_income.item_cn,
            calc_direct_income.unit,
            calc_direct_income.biz_date,
            calc_direct_income.peer_date,
            calc_direct_income.value_biz_date,
            calc_direct_income.value_peer_date
           FROM calc_direct_income
        UNION ALL
         SELECT calc_marginal_profit.company,
            calc_marginal_profit.company_cn,
            calc_marginal_profit.item,
            calc_marginal_profit.item_cn,
            calc_marginal_profit.unit,
            calc_marginal_profit.biz_date,
            calc_marginal_profit.peer_date,
            calc_marginal_profit.value_biz_date,
            calc_marginal_profit.value_peer_date
           FROM calc_marginal_profit
        UNION ALL
         SELECT calc_comparable_marginal_profit.company,
            calc_comparable_marginal_profit.company_cn,
            calc_comparable_marginal_profit.item,
            calc_comparable_marginal_profit.item_cn,
            calc_comparable_marginal_profit.unit,
            calc_comparable_marginal_profit.biz_date,
            calc_comparable_marginal_profit.peer_date,
            calc_comparable_marginal_profit.value_biz_date,
            calc_comparable_marginal_profit.value_peer_date
           FROM calc_comparable_marginal_profit
        UNION ALL
         SELECT calc_overall_efficiency.company,
            calc_overall_efficiency.company_cn,
            calc_overall_efficiency.item,
            calc_overall_efficiency.item_cn,
            calc_overall_efficiency.unit,
            calc_overall_efficiency.max,
            calc_overall_efficiency.max_1 AS max,
            calc_overall_efficiency.value_biz_date,
            calc_overall_efficiency.value_peer_date
           FROM calc_overall_efficiency calc_overall_efficiency(company, company_cn, item, item_cn, unit, max, max_1, value_biz_date, value_peer_date)
        )
 SELECT base.company,
    base.company_cn,
    base.item,
    base.item_cn,
    base.unit,
    base.biz_date,
    base.peer_date,
    base.value_biz_date,
    base.value_peer_date
   FROM base
  WHERE NOT (base.item = 'consumption_station_heat'::text AND (base.company = ANY (ARRAY['JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AND NOT (base.company = 'GongRe'::text AND (base.item = ANY (ARRAY['eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text])))
UNION ALL
 SELECT calc.company,
    calc.company_cn,
    calc.item,
    calc.item_cn,
    calc.unit,
    calc.biz_date,
    calc.peer_date,
    calc.value_biz_date,
    calc.value_peer_date
   FROM calc;

-- 视图：analysis_groups_daily
CREATE OR REPLACE VIEW public.analysis_groups_daily AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.biz_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS biz_date
        ), anchor_dates AS (
         SELECT p.biz_date,
            (p.biz_date - '1 year'::interval)::date AS peer_date
           FROM params p
        ), w AS (
         SELECT anchor_dates.biz_date,
            anchor_dates.peer_date,
                CASE
                    WHEN anchor_dates.biz_date >= make_date(EXTRACT(year FROM anchor_dates.biz_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN anchor_dates.peer_date >= make_date(EXTRACT(year FROM anchor_dates.peer_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text)
                END AS peer_period
           FROM anchor_dates
        ), company AS (
         SELECT analysis_company_daily.company,
            analysis_company_daily.company_cn,
            analysis_company_daily.item,
            analysis_company_daily.item_cn,
            analysis_company_daily.unit,
            analysis_company_daily.biz_date,
            analysis_company_daily.peer_date,
            analysis_company_daily.value_biz_date,
            analysis_company_daily.value_peer_date
           FROM analysis_company_daily
        ), base_zc AS (
         SELECT company.item,
            company.item_cn,
            company.unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text])
          GROUP BY company.item, company.item_cn, company.unit, company.biz_date, company.peer_date
        ), base_grp AS (
         SELECT company.item,
            company.item_cn,
            company.unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
          GROUP BY company.item, company.item_cn, company.unit, company.biz_date, company.peer_date
        ), group_sum_raw_zhangtun AS (
         SELECT 'sum_consumption_amount_raw_coal_zhangtun'::text AS item,
            '原煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(company.unit), '吨'::text) AS unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE (company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND company.item = 'consumption_amount_raw_coal'::text OR company.company = 'ZhuangHe'::text AND company.item = 'consumption_amount_raw_coal_zhangtun'::text
          GROUP BY company.biz_date, company.peer_date
        ), group_sum_std_zhangtun AS (
         SELECT 'sum_consumption_std_coal_zhangtun'::text AS item,
            '标煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(company.unit), '吨'::text) AS unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE (company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND company.item = 'consumption_std_coal'::text OR company.company = 'ZhuangHe'::text AND company.item = 'consumption_std_coal_zhangtun'::text
          GROUP BY company.biz_date, company.peer_date
        ), denom_zc AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_peer
        ), denom_grp AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_peer
        ), season_total_net_complaints_zc AS (
         SELECT w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN w
          WHERE d.item = 'sum_season_total_net_complaints'::text AND (d.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text])) AND (d.date = w.biz_date OR d.date = w.peer_date)
          GROUP BY w.biz_date, w.peer_date
        ), season_total_net_complaints_grp AS (
         SELECT w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN w
          WHERE d.item = 'sum_season_total_net_complaints'::text AND (d.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])) AND (d.date = w.biz_date OR d.date = w.peer_date)
          GROUP BY w.biz_date, w.peer_date
        ), yjy_power AS (
         SELECT company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = 'YanJiuYuan'::text AND company.item = 'consumption_station_purchased_power'::text
          GROUP BY company.biz_date, company.peer_date
        ), yjy_area AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_peer
        )
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    base_zc.item,
    base_zc.item_cn,
    base_zc.unit,
    base_zc.biz_date,
    base_zc.peer_date,
    base_zc.value_biz_date,
    base_zc.value_peer_date
   FROM base_zc
  WHERE base_zc.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    w.biz_date,
    w.peer_date,
    COALESCE(z.value_biz_date, 0::numeric) / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    COALESCE(z.value_peer_date, 0::numeric) / NULLIF(d.area_peer, 0::numeric) AS value_peer_date
   FROM denom_zc d
     CROSS JOIN w
     LEFT JOIN season_total_net_complaints_zc z ON z.biz_date = w.biz_date AND z.peer_date = w.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM ( SELECT base_zc.biz_date,
            base_zc.peer_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date
           FROM base_zc
          GROUP BY base_zc.biz_date, base_zc.peer_date) a,
    denom_zc d
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    base_grp.item,
    base_grp.item_cn,
    base_grp.unit,
    base_grp.biz_date,
    base_grp.peer_date,
    base_grp.value_biz_date,
    base_grp.value_peer_date
   FROM base_grp
  WHERE base_grp.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    r.item,
    r.item_cn,
    r.unit,
    r.biz_date,
    r.peer_date,
    r.value_biz_date,
    r.value_peer_date
   FROM group_sum_raw_zhangtun r
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    s.item,
    s.item_cn,
    s.unit,
    s.biz_date,
    s.peer_date,
    s.value_biz_date,
    s.value_peer_date
   FROM group_sum_std_zhangtun s
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.area_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'amount_daily_net_complaints'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2_YanJiuYuan'::text AS item,
    '供暖电单耗(-研究院)'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    (z.value_biz_date - COALESCE(y.value_biz_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS value_biz_date,
    (z.value_peer_date - COALESCE(y.value_peer_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS value_peer_date
   FROM base_grp z
     LEFT JOIN yjy_power y ON y.biz_date = z.biz_date AND y.peer_date = z.peer_date,
    denom_grp d,
    yjy_area a
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM ( SELECT base_grp.biz_date,
            base_grp.peer_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date
           FROM base_grp
          GROUP BY base_grp.biz_date, base_grp.peer_date) a,
    denom_grp d;

-- 视图：analysis_groups_sum
CREATE OR REPLACE VIEW public.analysis_groups_sum AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.sum_start_date'::text, true)::date, '2025-11-01'::date) AS sum_start,
            COALESCE(current_setting('phoenix.sum_end_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS sum_end
        ), anchor_dates AS (
         SELECT LEAST(params.sum_start, params.sum_end) AS biz_start,
            GREATEST(params.sum_start, params.sum_end) AS biz_end
           FROM params
        ), w AS (
         SELECT anchor_dates.biz_end AS biz_date,
            (anchor_dates.biz_end - '1 year'::interval)::date AS peer_date,
                CASE
                    WHEN anchor_dates.biz_end >= make_date(EXTRACT(year FROM anchor_dates.biz_end)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_end)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_end)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_end)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_end)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN (anchor_dates.biz_end - '1 year'::interval) >= make_date(EXTRACT(year FROM anchor_dates.biz_end - '1 year'::interval)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_end - '1 year'::interval)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_end - '1 year'::interval)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_end - '1 year'::interval)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_end - '1 year'::interval)::integer % 100)::text, 2, '0'::text)
                END AS peer_period
           FROM anchor_dates
        ), company AS (
         SELECT analysis_company_sum.company,
            analysis_company_sum.company_cn,
            analysis_company_sum.item,
            analysis_company_sum.item_cn,
            analysis_company_sum.unit,
            analysis_company_sum.biz_date,
            analysis_company_sum.peer_date,
            analysis_company_sum.value_biz_date,
            analysis_company_sum.value_peer_date
           FROM analysis_company_sum
        ), base_zc AS (
         SELECT company.item,
            company.item_cn,
            company.unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text])
          GROUP BY company.item, company.item_cn, company.unit, company.biz_date, company.peer_date
        ), base_grp AS (
         SELECT company.item,
            company.item_cn,
            company.unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text])
          GROUP BY company.item, company.item_cn, company.unit, company.biz_date, company.peer_date
        ), group_sum_raw_zhangtun AS (
         SELECT 'sum_consumption_amount_raw_coal_zhangtun'::text AS item,
            '原煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(company.unit), '吨'::text) AS unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE (company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND company.item = 'consumption_amount_raw_coal'::text OR company.company = 'ZhuangHe'::text AND company.item = 'consumption_amount_raw_coal_zhangtun'::text
          GROUP BY company.biz_date, company.peer_date
        ), group_sum_std_zhangtun AS (
         SELECT 'sum_consumption_std_coal_zhangtun'::text AS item,
            '标煤耗量汇总(张屯)'::text AS item_cn,
            COALESCE(max(company.unit), '吨'::text) AS unit,
            company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE (company.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text])) AND company.item = 'consumption_std_coal'::text OR company.company = 'ZhuangHe'::text AND company.item = 'consumption_std_coal_zhangtun'::text
          GROUP BY company.biz_date, company.peer_date
        ), denom_zc AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) AS fee_peer
        ), denom_grp AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS area_peer,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND (c.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) AS fee_peer
        ), season_total_net_complaints AS (
         SELECT d.company,
            d.company_cn,
            w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN w
          WHERE d.item = 'sum_season_total_net_complaints'::text AND (d.date = w.biz_date OR d.date = w.peer_date)
          GROUP BY d.company, d.company_cn, w.biz_date, w.peer_date
        ), yjy_power AS (
         SELECT company.biz_date,
            company.peer_date,
            sum(company.value_biz_date) AS value_biz_date,
            sum(company.value_peer_date) AS value_peer_date
           FROM company
          WHERE company.company = 'YanJiuYuan'::text AND company.item = 'consumption_station_purchased_power'::text
          GROUP BY company.biz_date, company.peer_date
        ), yjy_area AS (
         SELECT ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.biz_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_biz,
            ( SELECT sum(c.value) AS sum
                   FROM constant_data c,
                    w
                  WHERE c.period = w.peer_period AND c.item = 'amount_heating_fee_area'::text AND c.company = 'YanJiuYuan'::text) AS fee_peer
        )
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    base_zc.item,
    base_zc.item_cn,
    base_zc.unit,
    base_zc.biz_date,
    base_zc.peer_date,
    base_zc.value_biz_date,
    base_zc.value_peer_date
   FROM base_zc
  WHERE base_zc.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    w.biz_date,
    w.peer_date,
    (( SELECT sum(season_total_net_complaints.value_biz_date) AS sum
           FROM season_total_net_complaints
          WHERE season_total_net_complaints.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    (( SELECT sum(season_total_net_complaints.value_peer_date) AS sum
           FROM season_total_net_complaints
          WHERE season_total_net_complaints.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text]))) / NULLIF(d.area_peer, 0::numeric) AS value_peer_date
   FROM denom_zc d
     CROSS JOIN w
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_peer_date
   FROM base_zc z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_zc z,
    denom_zc d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'ZhuChengQu'::text AS company,
    '主城区'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM ( SELECT base_zc.biz_date,
            base_zc.peer_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_zc.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_zc.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date
           FROM base_zc
          GROUP BY base_zc.biz_date, base_zc.peer_date) a,
    denom_zc d
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    base_grp.item,
    base_grp.item_cn,
    base_grp.unit,
    base_grp.biz_date,
    base_grp.peer_date,
    base_grp.value_biz_date,
    base_grp.value_peer_date
   FROM base_grp
  WHERE base_grp.item <> ALL (ARRAY['amount_daily_net_complaints_per_10k_m2'::text, 'rate_std_coal_per_heat'::text, 'rate_heat_per_10k_m2'::text, 'rate_power_per_10k_m2'::text, 'rate_water_per_10k_m2'::text, 'rate_overall_efficiency'::text, 'eco_direct_income'::text, 'eco_marginal_profit'::text, 'eco_comparable_marginal_profit'::text])
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    r.item,
    r.item_cn,
    r.unit,
    r.biz_date,
    r.peer_date,
    r.value_biz_date,
    r.value_peer_date
   FROM group_sum_raw_zhangtun r
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    s.item,
    s.item_cn,
    s.unit,
    s.biz_date,
    s.peer_date,
    s.value_biz_date,
    s.value_peer_date
   FROM group_sum_std_zhangtun s
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_direct_income'::text AS item,
    '直接收入'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = ANY (ARRAY['eco_power_supply_income'::text, 'eco_heating_supply_income'::text, 'eco_hot_water_supply_income'::text, 'eco_steam_supply_income'::text]) THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_marginal_profit'::text AS item,
    '边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'eco_comparable_marginal_profit'::text AS item,
    '可比煤价边际利润'::text AS item_cn,
    '万元'::text AS unit,
    z.biz_date,
    z.peer_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) AS value_biz_date,
    sum(
        CASE
            WHEN z.item = 'eco_comparable_marginal_profit'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + sum(
        CASE
            WHEN z.item = 'eco_inner_purchased_heat_cost'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'eco_inner_heat_supply_income'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'amount_daily_net_complaints_per_10k_m2'::text AS item,
    '万平方米省市净投诉量'::text AS item_cn,
    '件/万㎡'::text AS unit,
    w.biz_date,
    w.peer_date,
    (( SELECT sum(season_total_net_complaints.value_biz_date) AS sum
           FROM season_total_net_complaints
          WHERE season_total_net_complaints.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) / NULLIF(d.area_biz, 0::numeric) AS value_biz_date,
    (( SELECT sum(season_total_net_complaints.value_peer_date) AS sum
           FROM season_total_net_complaints
          WHERE season_total_net_complaints.company = ANY (ARRAY['BeiHai'::text, 'XiangHai'::text, 'GongRe'::text, 'JinZhou'::text, 'BeiFang'::text, 'JinPu'::text, 'ZhuangHe'::text, 'YanJiuYuan'::text]))) / NULLIF(d.area_peer, 0::numeric) AS value_peer_date
   FROM denom_grp d
     CROSS JOIN w
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_std_coal_per_heat'::text AS item,
    '供热标煤单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_std_coal'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_heat_per_10k_m2'::text AS item,
    '供暖热单耗'::text AS item_cn,
    'GJ/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_heat'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2'::text AS item,
    '供暖电单耗'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    z.value_biz_date * 10000.0 / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    z.value_peer_date * 10000.0 / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM base_grp z,
    denom_grp d
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_power_per_10k_m2_YanJiuYuan'::text AS item,
    '供暖电单耗(-研究院)'::text AS item_cn,
    'kWh/万㎡'::text AS unit,
    z.biz_date,
    z.peer_date,
    (z.value_biz_date - COALESCE(y.value_biz_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_biz - COALESCE(a.fee_biz, 0::numeric), 0::numeric) AS value_biz_date,
    (z.value_peer_date - COALESCE(y.value_peer_date, 0::numeric)) * 10000.0 / NULLIF(d.fee_peer - COALESCE(a.fee_peer, 0::numeric), 0::numeric) AS value_peer_date
   FROM base_grp z
     LEFT JOIN yjy_power y ON y.biz_date = z.biz_date AND y.peer_date = z.peer_date,
    denom_grp d,
    yjy_area a
  WHERE z.item = 'consumption_station_purchased_power'::text
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_water_per_10k_m2'::text AS item,
    '供暖水单耗'::text AS item_cn,
    '吨/万㎡'::text AS unit,
    a.biz_date,
    a.peer_date,
    a.value_biz_date / NULLIF(d.fee_biz, 0::numeric) AS value_biz_date,
    a.value_peer_date / NULLIF(d.fee_peer, 0::numeric) AS value_peer_date
   FROM ( SELECT base_grp.biz_date,
            base_grp.peer_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_biz_date
                    ELSE 0::numeric
                END) AS value_biz_date,
            sum(
                CASE
                    WHEN base_grp.item = ANY (ARRAY['consumption_network_fill_water'::text, 'consumption_station_fill_water'::text, 'consumption_network_water'::text]) THEN base_grp.value_peer_date
                    ELSE 0::numeric
                END) AS value_peer_date
           FROM base_grp
          GROUP BY base_grp.biz_date, base_grp.peer_date) a,
    denom_grp d
UNION ALL
 SELECT 'Group'::text AS company,
    '集团全口径'::text AS company_cn,
    'rate_overall_efficiency'::text AS item,
    '全厂热效率'::text AS item_cn,
    '%'::text AS unit,
    z.biz_date,
    z.peer_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_biz_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_biz_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
    round(COALESCE((sum(
        CASE
            WHEN z.item = 'amount_heat_supply'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 36.0 * sum(
        CASE
            WHEN z.item = 'amount_power_sales'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) - sum(
        CASE
            WHEN z.item = 'consumption_outer_purchased_heat'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)) / NULLIF(29.308 * (sum(
        CASE
            WHEN z.item = 'consumption_std_coal'::text THEN z.value_peer_date
            ELSE 0::numeric
        END) + 1.4571 * sum(
        CASE
            WHEN z.item = 'consumption_oil'::text THEN z.value_peer_date
            ELSE 0::numeric
        END)), 0::numeric), 0::numeric), 4) AS value_peer_date
   FROM base_grp z
  GROUP BY z.biz_date, z.peer_date;

-- 视图：analysis_beihai_sub_daily
CREATE OR REPLACE VIEW public.analysis_beihai_sub_daily AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.biz_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS biz_date
        ), anchor_dates AS (
         SELECT p.biz_date,
            (p.biz_date - '1 year'::interval)::date AS peer_date
           FROM params p
        ), window_defs AS (
         SELECT anchor_dates.biz_date,
            anchor_dates.peer_date,
                CASE
                    WHEN anchor_dates.biz_date >= make_date(EXTRACT(year FROM anchor_dates.biz_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.biz_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.biz_date)::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN anchor_dates.peer_date >= make_date(EXTRACT(year FROM anchor_dates.peer_date)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM anchor_dates.peer_date)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM anchor_dates.peer_date)::integer % 100)::text, 2, '0'::text)
                END AS peer_period,
            1 AS days_day_biz,
            1 AS days_day_peer
           FROM anchor_dates
        ), base AS (
         SELECT d.sheet_name,
            d.company,
            d.company_cn,
            d.item,
            d.item_cn,
            d.unit,
            w.biz_date,
            w.peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.biz_date), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date = w.peer_date), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN window_defs w
          WHERE d.company = 'BeiHai'::text AND (d.sheet_name = ANY (ARRAY['BeiHai_co_generation_Sheet'::text, 'BeiHai_water_boiler_Sheet'::text])) AND (d.date = w.biz_date OR d.date = w.peer_date)
          GROUP BY d.sheet_name, d.company, d.company_cn, d.item, d.item_cn, d.unit, w.biz_date, w.peer_date
        ), const_biz AS (
         SELECT c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.company = 'BeiHai'::text AND c.period = w.biz_period
          GROUP BY c.item
        ), const_peer AS (
         SELECT c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN window_defs w
          WHERE c.company = 'BeiHai'::text AND c.period = w.peer_period
          GROUP BY c.item
        ), calc_power AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_power_supply_income'::text AS item,
            '其中：售电收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ps ON cb_ps.item = 'price_power_sales'::text
             LEFT JOIN const_peer cp_ps ON cp_ps.item = 'price_power_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ps.value, cp_ps.value
        ), calc_inner_heat_supply_income AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_inner_heat_supply_income'::text AS item,
            '其中：内售热收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hin ON cb_hin.item = 'price_inner_heat_sales'::text
             LEFT JOIN const_peer cp_hin ON cp_hin.item = 'price_inner_heat_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_hin.value, cp_hin.value
        ), calc_heating_income AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_heating_supply_income'::text AS item,
            '其中：暖收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT window_defs.days_day_biz
                   FROM window_defs))::numeric / 156.0 AS value_biz_date,
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT window_defs.days_day_peer
                   FROM window_defs))::numeric / 156.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sh ON cb_sh.item = 'eco_season_heating_income'::text
             LEFT JOIN const_peer cp_sh ON cp_sh.item = 'eco_season_heating_income'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_sh.value, cp_sh.value
        ), calc_hot_water AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_hot_water_supply_income'::text AS item,
            '其中：售高温水收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_hw ON cb_hw.item = 'price_hot_water_sales'::text
             LEFT JOIN const_peer cp_hw ON cp_hw.item = 'price_hot_water_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_hw.value, cp_hw.value
        ), calc_steam AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_steam_supply_income'::text AS item,
            '其中：售汽收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ss ON cb_ss.item = 'price_steam_sales'::text
             LEFT JOIN const_peer cp_ss ON cp_ss.item = 'price_steam_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ss.value, cp_ss.value
        ), calc_coal_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_coal_cost'::text AS item,
            '煤成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.item = 'price_std_coal'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.item = 'price_std_coal'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_sc.value, cp_sc.value
        ), calc_natural_gas_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_natural_gas_cost'::text AS item,
            '天然气成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ng ON cb_ng.item = 'price_natural_gas'::text
             LEFT JOIN const_peer cp_ng ON cp_ng.item = 'price_natural_gas'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ng.value, cp_ng.value
        ), calc_purchased_power_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_purchased_power_cost'::text AS item,
            '外购电成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pp ON cb_pp.item = 'price_purchased_power'::text
             LEFT JOIN const_peer cp_pp ON cp_pp.item = 'price_purchased_power'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_pp.value, cp_pp.value
        ), calc_purchased_water_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_purchased_water_cost'::text AS item,
            '购水成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_pw ON cb_pw.item = 'price_purchased_water'::text
             LEFT JOIN const_peer cp_pw ON cp_pw.item = 'price_purchased_water'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_pw.value, cp_pw.value
        ), calc_aux_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_measurable_auxiliary_materials'::text AS item,
            '可计量辅材成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS value_biz_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ac ON cb_ac.item = 'price_acid'::text
             LEFT JOIN const_peer cp_ac ON cp_ac.item = 'price_acid'::text
             LEFT JOIN const_biz cb_al ON cb_al.item = 'price_alkali'::text
             LEFT JOIN const_peer cp_al ON cp_al.item = 'price_alkali'::text
             LEFT JOIN const_biz cb_ol ON cb_ol.item = 'price_oil'::text
             LEFT JOIN const_peer cp_ol ON cp_ol.item = 'price_oil'::text
             LEFT JOIN const_biz cb_aw ON cb_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_peer cp_aw ON cp_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_biz cb_ls ON cb_ls.item = 'price_limestone'::text
             LEFT JOIN const_peer cp_ls ON cp_ls.item = 'price_limestone'::text
             LEFT JOIN const_biz cb_lsp ON cb_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_peer cp_lsp ON cp_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_biz cb_mg ON cb_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_peer cp_mg ON cp_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_biz cb_dn ON cb_dn.item = 'price_denitration_agent'::text
             LEFT JOIN const_peer cp_dn ON cp_dn.item = 'price_denitration_agent'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value, cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value, cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
        ), calc_outer_heat_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_outer_heat_cost'::text AS item,
            '外购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_oh ON cb_oh.item = 'price_outer_purchased_heat'::text
             LEFT JOIN const_peer cp_oh ON cp_oh.item = 'price_outer_purchased_heat'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_oh.value, cp_oh.value
        ), calc_inner_purchased_heat_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_inner_purchased_heat_cost'::text AS item,
            '内购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_ih ON cb_ih.item = 'price_inner_purchased_heat'::text
             LEFT JOIN const_peer cp_ih ON cp_ih.item = 'price_inner_purchased_heat'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ih.value, cp_ih.value
        ), calc_direct_income AS (
         SELECT c.sheet_name,
            c.company,
            c.company_cn,
            'eco_direct_income'::text AS item,
            '直接收入'::text AS item_cn,
            '万元'::text AS unit,
            max(c.biz_date) AS biz_date,
            max(c.peer_date) AS peer_date,
            sum(c.value_biz_date) AS value_biz_date,
            sum(c.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_power.sheet_name,
                    calc_power.company,
                    calc_power.company_cn,
                    calc_power.item,
                    calc_power.item_cn,
                    calc_power.unit,
                    calc_power.biz_date,
                    calc_power.peer_date,
                    calc_power.value_biz_date,
                    calc_power.value_peer_date
                   FROM calc_power
                UNION ALL
                 SELECT calc_inner_heat_supply_income.sheet_name,
                    calc_inner_heat_supply_income.company,
                    calc_inner_heat_supply_income.company_cn,
                    calc_inner_heat_supply_income.item,
                    calc_inner_heat_supply_income.item_cn,
                    calc_inner_heat_supply_income.unit,
                    calc_inner_heat_supply_income.biz_date,
                    calc_inner_heat_supply_income.peer_date,
                    calc_inner_heat_supply_income.value_biz_date,
                    calc_inner_heat_supply_income.value_peer_date
                   FROM calc_inner_heat_supply_income
                UNION ALL
                 SELECT calc_heating_income.sheet_name,
                    calc_heating_income.company,
                    calc_heating_income.company_cn,
                    calc_heating_income.item,
                    calc_heating_income.item_cn,
                    calc_heating_income.unit,
                    calc_heating_income.biz_date,
                    calc_heating_income.peer_date,
                    calc_heating_income.value_biz_date,
                    calc_heating_income.value_peer_date
                   FROM calc_heating_income
                UNION ALL
                 SELECT calc_hot_water.sheet_name,
                    calc_hot_water.company,
                    calc_hot_water.company_cn,
                    calc_hot_water.item,
                    calc_hot_water.item_cn,
                    calc_hot_water.unit,
                    calc_hot_water.biz_date,
                    calc_hot_water.peer_date,
                    calc_hot_water.value_biz_date,
                    calc_hot_water.value_peer_date
                   FROM calc_hot_water
                UNION ALL
                 SELECT calc_steam.sheet_name,
                    calc_steam.company,
                    calc_steam.company_cn,
                    calc_steam.item,
                    calc_steam.item_cn,
                    calc_steam.unit,
                    calc_steam.biz_date,
                    calc_steam.peer_date,
                    calc_steam.value_biz_date,
                    calc_steam.value_peer_date
                   FROM calc_steam) c
          GROUP BY c.sheet_name, c.company, c.company_cn
        ), calc_marginal_profit AS (
         SELECT di.sheet_name,
            di.company,
            di.company_cn,
            'eco_marginal_profit'::text AS item,
            '边际利润'::text AS item_cn,
            '万元'::text AS unit,
            di.biz_date,
            di.peer_date,
            di.value_biz_date - (COALESCE(ng.value_biz_date, 0::numeric) + COALESCE(pp.value_biz_date, 0::numeric) + COALESCE(pw.value_biz_date, 0::numeric) + COALESCE(am.value_biz_date, 0::numeric) + COALESCE(oh.value_biz_date, 0::numeric) + COALESCE(ih.value_biz_date, 0::numeric) + COALESCE(rc.value_biz_date, 0::numeric)) AS value_biz_date,
            di.value_peer_date - (COALESCE(ng.value_peer_date, 0::numeric) + COALESCE(pp.value_peer_date, 0::numeric) + COALESCE(pw.value_peer_date, 0::numeric) + COALESCE(am.value_peer_date, 0::numeric) + COALESCE(oh.value_peer_date, 0::numeric) + COALESCE(ih.value_peer_date, 0::numeric) + COALESCE(rc.value_peer_date, 0::numeric)) AS value_peer_date
           FROM calc_direct_income di
             LEFT JOIN calc_natural_gas_cost ng ON ng.sheet_name = di.sheet_name AND ng.company = di.company
             LEFT JOIN calc_purchased_power_cost pp ON pp.sheet_name = di.sheet_name AND pp.company = di.company
             LEFT JOIN calc_purchased_water_cost pw ON pw.sheet_name = di.sheet_name AND pw.company = di.company
             LEFT JOIN calc_aux_cost am ON am.sheet_name = di.sheet_name AND am.company = di.company
             LEFT JOIN calc_outer_heat_cost oh ON oh.sheet_name = di.sheet_name AND oh.company = di.company
             LEFT JOIN calc_inner_purchased_heat_cost ih ON ih.sheet_name = di.sheet_name AND ih.company = di.company
             LEFT JOIN calc_coal_cost rc ON rc.sheet_name = di.sheet_name AND rc.company = di.company
        ), cost_non_coal AS (
         SELECT t.sheet_name,
            t.company,
            sum(t.value_biz_date) AS value_biz_date,
            sum(t.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_natural_gas_cost.sheet_name,
                    calc_natural_gas_cost.company,
                    calc_natural_gas_cost.value_biz_date,
                    calc_natural_gas_cost.value_peer_date
                   FROM calc_natural_gas_cost
                UNION ALL
                 SELECT calc_purchased_power_cost.sheet_name,
                    calc_purchased_power_cost.company,
                    calc_purchased_power_cost.value_biz_date,
                    calc_purchased_power_cost.value_peer_date
                   FROM calc_purchased_power_cost
                UNION ALL
                 SELECT calc_purchased_water_cost.sheet_name,
                    calc_purchased_water_cost.company,
                    calc_purchased_water_cost.value_biz_date,
                    calc_purchased_water_cost.value_peer_date
                   FROM calc_purchased_water_cost
                UNION ALL
                 SELECT calc_aux_cost.sheet_name,
                    calc_aux_cost.company,
                    calc_aux_cost.value_biz_date,
                    calc_aux_cost.value_peer_date
                   FROM calc_aux_cost
                UNION ALL
                 SELECT calc_outer_heat_cost.sheet_name,
                    calc_outer_heat_cost.company,
                    calc_outer_heat_cost.value_biz_date,
                    calc_outer_heat_cost.value_peer_date
                   FROM calc_outer_heat_cost
                UNION ALL
                 SELECT calc_inner_purchased_heat_cost.sheet_name,
                    calc_inner_purchased_heat_cost.company,
                    calc_inner_purchased_heat_cost.value_biz_date,
                    calc_inner_purchased_heat_cost.value_peer_date
                   FROM calc_inner_purchased_heat_cost) t
          GROUP BY t.sheet_name, t.company
        ), calc_comparable_marginal_profit AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_comparable_marginal_profit'::text AS item,
            '可比煤价边际利润'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(max(di.value_biz_date), 0::numeric) - COALESCE(max(cnc.value_biz_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS value_biz_date,
            COALESCE(max(di.value_peer_date), 0::numeric) - COALESCE(max(cnc.value_peer_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS value_peer_date
           FROM base b
             LEFT JOIN const_biz cb_sc ON cb_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN const_peer cp_sc ON cp_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN calc_direct_income di ON di.sheet_name = b.sheet_name AND di.company = b.company
             LEFT JOIN cost_non_coal cnc ON cnc.sheet_name = b.sheet_name AND cnc.company = b.company
          GROUP BY b.sheet_name, b.company, b.company_cn
        ), calc_overall_efficiency AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'rate_overall_efficiency'::text AS item,
            '全厂热效率'::text AS item_cn,
            '%'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_peer_date
           FROM base b
          GROUP BY b.sheet_name, b.company, b.company_cn
        ), calc_selected AS (
         SELECT calc_power.sheet_name,
            calc_power.company,
            calc_power.company_cn,
            calc_power.item,
            calc_power.item_cn,
            calc_power.unit,
            calc_power.biz_date,
            calc_power.peer_date,
            calc_power.value_biz_date,
            calc_power.value_peer_date
           FROM calc_power
        UNION ALL
         SELECT calc_inner_heat_supply_income.sheet_name,
            calc_inner_heat_supply_income.company,
            calc_inner_heat_supply_income.company_cn,
            calc_inner_heat_supply_income.item,
            calc_inner_heat_supply_income.item_cn,
            calc_inner_heat_supply_income.unit,
            calc_inner_heat_supply_income.biz_date,
            calc_inner_heat_supply_income.peer_date,
            calc_inner_heat_supply_income.value_biz_date,
            calc_inner_heat_supply_income.value_peer_date
           FROM calc_inner_heat_supply_income
        UNION ALL
         SELECT calc_coal_cost.sheet_name,
            calc_coal_cost.company,
            calc_coal_cost.company_cn,
            calc_coal_cost.item,
            calc_coal_cost.item_cn,
            calc_coal_cost.unit,
            calc_coal_cost.biz_date,
            calc_coal_cost.peer_date,
            calc_coal_cost.value_biz_date,
            calc_coal_cost.value_peer_date
           FROM calc_coal_cost
        UNION ALL
         SELECT calc_purchased_power_cost.sheet_name,
            calc_purchased_power_cost.company,
            calc_purchased_power_cost.company_cn,
            calc_purchased_power_cost.item,
            calc_purchased_power_cost.item_cn,
            calc_purchased_power_cost.unit,
            calc_purchased_power_cost.biz_date,
            calc_purchased_power_cost.peer_date,
            calc_purchased_power_cost.value_biz_date,
            calc_purchased_power_cost.value_peer_date
           FROM calc_purchased_power_cost
        UNION ALL
         SELECT calc_purchased_water_cost.sheet_name,
            calc_purchased_water_cost.company,
            calc_purchased_water_cost.company_cn,
            calc_purchased_water_cost.item,
            calc_purchased_water_cost.item_cn,
            calc_purchased_water_cost.unit,
            calc_purchased_water_cost.biz_date,
            calc_purchased_water_cost.peer_date,
            calc_purchased_water_cost.value_biz_date,
            calc_purchased_water_cost.value_peer_date
           FROM calc_purchased_water_cost
        UNION ALL
         SELECT calc_aux_cost.sheet_name,
            calc_aux_cost.company,
            calc_aux_cost.company_cn,
            calc_aux_cost.item,
            calc_aux_cost.item_cn,
            calc_aux_cost.unit,
            calc_aux_cost.biz_date,
            calc_aux_cost.peer_date,
            calc_aux_cost.value_biz_date,
            calc_aux_cost.value_peer_date
           FROM calc_aux_cost
        UNION ALL
         SELECT calc_direct_income.sheet_name,
            calc_direct_income.company,
            calc_direct_income.company_cn,
            calc_direct_income.item,
            calc_direct_income.item_cn,
            calc_direct_income.unit,
            calc_direct_income.biz_date,
            calc_direct_income.peer_date,
            calc_direct_income.value_biz_date,
            calc_direct_income.value_peer_date
           FROM calc_direct_income
        UNION ALL
         SELECT calc_marginal_profit.sheet_name,
            calc_marginal_profit.company,
            calc_marginal_profit.company_cn,
            calc_marginal_profit.item,
            calc_marginal_profit.item_cn,
            calc_marginal_profit.unit,
            calc_marginal_profit.biz_date,
            calc_marginal_profit.peer_date,
            calc_marginal_profit.value_biz_date,
            calc_marginal_profit.value_peer_date
           FROM calc_marginal_profit
        UNION ALL
         SELECT calc_comparable_marginal_profit.sheet_name,
            calc_comparable_marginal_profit.company,
            calc_comparable_marginal_profit.company_cn,
            calc_comparable_marginal_profit.item,
            calc_comparable_marginal_profit.item_cn,
            calc_comparable_marginal_profit.unit,
            calc_comparable_marginal_profit.biz_date,
            calc_comparable_marginal_profit.peer_date,
            calc_comparable_marginal_profit.value_biz_date,
            calc_comparable_marginal_profit.value_peer_date
           FROM calc_comparable_marginal_profit
        UNION ALL
         SELECT calc_overall_efficiency.sheet_name,
            calc_overall_efficiency.company,
            calc_overall_efficiency.company_cn,
            calc_overall_efficiency.item,
            calc_overall_efficiency.item_cn,
            calc_overall_efficiency.unit,
            calc_overall_efficiency.biz_date,
            calc_overall_efficiency.peer_date,
            calc_overall_efficiency.value_biz_date,
            calc_overall_efficiency.value_peer_date
           FROM calc_overall_efficiency
        )
 SELECT base.sheet_name,
    base.company,
    base.company_cn,
    base.item,
    base.item_cn,
    base.unit,
    base.biz_date,
    base.peer_date,
    base.value_biz_date,
    base.value_peer_date
   FROM base
UNION ALL
 SELECT calc_selected.sheet_name,
    calc_selected.company,
    calc_selected.company_cn,
    calc_selected.item,
    calc_selected.item_cn,
    calc_selected.unit,
    calc_selected.biz_date,
    calc_selected.peer_date,
    calc_selected.value_biz_date,
    calc_selected.value_peer_date
   FROM calc_selected;

-- 视图：analysis_beihai_sub_sum
CREATE OR REPLACE VIEW public.analysis_beihai_sub_sum AS
 WITH params AS (
         SELECT COALESCE(current_setting('phoenix.sum_start_date'::text, true)::date, '2025-11-01'::date) AS raw_start,
            COALESCE(current_setting('phoenix.sum_end_date'::text, true)::date, (CURRENT_DATE - '1 day'::interval)::date) AS raw_end
        ), range_defs AS (
         SELECT LEAST(params.raw_start, params.raw_end) AS biz_start,
            GREATEST(params.raw_start, params.raw_end) AS biz_end,
            (LEAST(params.raw_start, params.raw_end) - '1 year'::interval)::date AS peer_start,
            (GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::date AS peer_end,
                CASE
                    WHEN GREATEST(params.raw_start, params.raw_end) >= make_date(EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer, 10, 1) THEN (lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end))::integer % 100)::text, 2, '0'::text)
                END AS biz_period,
                CASE
                    WHEN (GREATEST(params.raw_start, params.raw_end) - '1 year'::interval) >= make_date(EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer, 10, 1) THEN (lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer % 100)::text, 2, '0'::text) || '-'::text) || lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer + 1) % 100)::text, 2, '0'::text)
                    ELSE (lpad(((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer - 1) % 100)::text, 2, '0'::text) || '-'::text) || lpad((EXTRACT(year FROM GREATEST(params.raw_start, params.raw_end) - '1 year'::interval)::integer % 100)::text, 2, '0'::text)
                END AS peer_period,
            GREATEST(params.raw_start, params.raw_end) - LEAST(params.raw_start, params.raw_end) + 1 AS days_range_biz,
            GREATEST(params.raw_start, params.raw_end) - LEAST(params.raw_start, params.raw_end) + 1 AS days_range_peer
           FROM params
        ), base_sum AS (
         SELECT d.sheet_name,
            d.company,
            d.company_cn,
            d.item,
            d.item_cn,
            d.unit,
            w.biz_end AS biz_date,
            w.peer_end AS peer_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.biz_start AND d.date <= w.biz_end), 0::numeric) AS value_biz_date,
            COALESCE(sum(d.value) FILTER (WHERE d.date >= w.peer_start AND d.date <= w.peer_end), 0::numeric) AS value_peer_date
           FROM daily_basic_data d
             CROSS JOIN range_defs w
          WHERE d.company = 'BeiHai'::text AND (d.sheet_name = ANY (ARRAY['BeiHai_co_generation_Sheet'::text, 'BeiHai_water_boiler_Sheet'::text])) AND d.date >= w.peer_start AND d.date <= w.biz_end
          GROUP BY d.sheet_name, d.company, d.company_cn, d.item, d.item_cn, d.unit, w.biz_end, w.peer_end
        ), const_sum_biz AS (
         SELECT c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN range_defs w
          WHERE c.company = 'BeiHai'::text AND c.period = w.biz_period
          GROUP BY c.item
        ), const_sum_peer AS (
         SELECT c.item,
            max(c.value) AS value
           FROM constant_data c
             CROSS JOIN range_defs w
          WHERE c.company = 'BeiHai'::text AND c.period = w.peer_period
          GROUP BY c.item
        ), calc_sum_power AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_power_supply_income'::text AS item,
            '其中：售电收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ps.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ps.value, 0::numeric) AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_ps ON cb_ps.item = 'price_power_sales'::text
             LEFT JOIN const_sum_peer cp_ps ON cp_ps.item = 'price_power_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ps.value, cp_ps.value
        ), calc_sum_inner_heat_supply_income AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_inner_heat_supply_income'::text AS item,
            '其中：内售热收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hin.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hin.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_hin ON cb_hin.item = 'price_inner_heat_sales'::text
             LEFT JOIN const_sum_peer cp_hin ON cp_hin.item = 'price_inner_heat_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_hin.value, cp_hin.value
        ), calc_sum_heating_income AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_heating_supply_income'::text AS item,
            '其中：暖收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(cb_sh.value, 0::numeric) * (( SELECT range_defs.days_range_biz
                   FROM range_defs))::numeric / 156.0 AS value_biz_date,
            COALESCE(cp_sh.value, 0::numeric) * (( SELECT range_defs.days_range_peer
                   FROM range_defs))::numeric / 156.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_sh ON cb_sh.item = 'eco_season_heating_income'::text
             LEFT JOIN const_sum_peer cp_sh ON cp_sh.item = 'eco_season_heating_income'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_sh.value, cp_sh.value
        ), calc_sum_hot_water AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_hot_water_supply_income'::text AS item,
            '其中：售高温水收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_hw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_hot_water_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_hw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_hw ON cb_hw.item = 'price_hot_water_sales'::text
             LEFT JOIN const_sum_peer cp_hw ON cp_hw.item = 'price_hot_water_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_hw.value, cp_hw.value
        ), calc_sum_steam AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_steam_supply_income'::text AS item,
            '其中：售汽收入'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ss.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_steam_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ss.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_ss ON cb_ss.item = 'price_steam_sales'::text
             LEFT JOIN const_sum_peer cp_ss ON cp_ss.item = 'price_steam_sales'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ss.value, cp_ss.value
        ), calc_sum_coal_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_coal_cost'::text AS item,
            '煤成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_sc.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_sc.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_sc ON cb_sc.item = 'price_std_coal'::text
             LEFT JOIN const_sum_peer cp_sc ON cp_sc.item = 'price_std_coal'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_sc.value, cp_sc.value
        ), calc_sum_natural_gas_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_natural_gas_cost'::text AS item,
            '天然气成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ng.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_natural_gas'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ng.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_ng ON cb_ng.item = 'price_natural_gas'::text
             LEFT JOIN const_sum_peer cp_ng ON cp_ng.item = 'price_natural_gas'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ng.value, cp_ng.value
        ), calc_sum_purchased_power_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_purchased_power_cost'::text AS item,
            '外购电成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pp.value, 0::numeric) AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_purchased_power'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pp.value, 0::numeric) AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_pp ON cb_pp.item = 'price_purchased_power'::text
             LEFT JOIN const_sum_peer cp_pp ON cp_pp.item = 'price_purchased_power'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_pp.value, cp_pp.value
        ), calc_sum_purchased_water_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_purchased_water_cost'::text AS item,
            '购水成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_pw.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_pw.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_pw ON cb_pw.item = 'price_purchased_water'::text
             LEFT JOIN const_sum_peer cp_pw ON cp_pw.item = 'price_purchased_water'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_pw.value, cp_pw.value
        ), calc_sum_aux_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_measurable_auxiliary_materials'::text AS item,
            '可计量辅材成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_dn.value, 0::numeric)) / 10000.0 AS value_biz_date,
            (sum(
                CASE
                    WHEN b.item = 'consumption_acid'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ac.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_alkali'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_al.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ol.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_ammonia_water'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_aw.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ls.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_limestone_powder'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_lsp.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_magnesium_oxide'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_mg.value, 0::numeric) + sum(
                CASE
                    WHEN b.item = 'consumption_denitration_agent'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_dn.value, 0::numeric)) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_ac ON cb_ac.item = 'price_acid'::text
             LEFT JOIN const_sum_peer cp_ac ON cp_ac.item = 'price_acid'::text
             LEFT JOIN const_sum_biz cb_al ON cb_al.item = 'price_alkali'::text
             LEFT JOIN const_sum_peer cp_al ON cp_al.item = 'price_alkali'::text
             LEFT JOIN const_sum_biz cb_ol ON cb_ol.item = 'price_oil'::text
             LEFT JOIN const_sum_peer cp_ol ON cp_ol.item = 'price_oil'::text
             LEFT JOIN const_sum_biz cb_aw ON cb_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_sum_peer cp_aw ON cp_aw.item = 'price_n_ammonia_water'::text
             LEFT JOIN const_sum_biz cb_ls ON cb_ls.item = 'price_limestone'::text
             LEFT JOIN const_sum_peer cp_ls ON cp_ls.item = 'price_limestone'::text
             LEFT JOIN const_sum_biz cb_lsp ON cb_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_sum_peer cp_lsp ON cp_lsp.item = 'price_limestone_powder'::text
             LEFT JOIN const_sum_biz cb_mg ON cb_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_sum_peer cp_mg ON cp_mg.item = 'price_magnesium_oxide'::text
             LEFT JOIN const_sum_biz cb_dn ON cb_dn.item = 'price_denitration_agent'::text
             LEFT JOIN const_sum_peer cp_dn ON cp_dn.item = 'price_denitration_agent'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ac.value, cp_ac.value, cb_al.value, cp_al.value, cb_ol.value, cp_ol.value, cb_aw.value, cp_aw.value, cb_ls.value, cp_ls.value, cb_lsp.value, cp_lsp.value, cb_mg.value, cp_mg.value, cb_dn.value, cp_dn.value
        ), calc_sum_outer_heat_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_outer_heat_cost'::text AS item,
            '外购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_oh.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_oh.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_oh ON cb_oh.item = 'price_outer_purchased_heat'::text
             LEFT JOIN const_sum_peer cp_oh ON cp_oh.item = 'price_outer_purchased_heat'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_oh.value, cp_oh.value
        ), calc_sum_inner_purchased_heat_cost AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_inner_purchased_heat_cost'::text AS item,
            '内购热成本'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(cb_ih.value, 0::numeric) / 10000.0 AS value_biz_date,
            sum(
                CASE
                    WHEN b.item = 'amount_network_interface_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(cp_ih.value, 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_ih ON cb_ih.item = 'price_inner_purchased_heat'::text
             LEFT JOIN const_sum_peer cp_ih ON cp_ih.item = 'price_inner_purchased_heat'::text
          GROUP BY b.sheet_name, b.company, b.company_cn, cb_ih.value, cp_ih.value
        ), calc_sum_direct_income AS (
         SELECT c.sheet_name,
            c.company,
            c.company_cn,
            'eco_direct_income'::text AS item,
            '直接收入'::text AS item_cn,
            '万元'::text AS unit,
            max(c.biz_date) AS biz_date,
            max(c.peer_date) AS peer_date,
            sum(c.value_biz_date) AS value_biz_date,
            sum(c.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_sum_power.sheet_name,
                    calc_sum_power.company,
                    calc_sum_power.company_cn,
                    calc_sum_power.item,
                    calc_sum_power.item_cn,
                    calc_sum_power.unit,
                    calc_sum_power.biz_date,
                    calc_sum_power.peer_date,
                    calc_sum_power.value_biz_date,
                    calc_sum_power.value_peer_date
                   FROM calc_sum_power
                UNION ALL
                 SELECT calc_sum_inner_heat_supply_income.sheet_name,
                    calc_sum_inner_heat_supply_income.company,
                    calc_sum_inner_heat_supply_income.company_cn,
                    calc_sum_inner_heat_supply_income.item,
                    calc_sum_inner_heat_supply_income.item_cn,
                    calc_sum_inner_heat_supply_income.unit,
                    calc_sum_inner_heat_supply_income.biz_date,
                    calc_sum_inner_heat_supply_income.peer_date,
                    calc_sum_inner_heat_supply_income.value_biz_date,
                    calc_sum_inner_heat_supply_income.value_peer_date
                   FROM calc_sum_inner_heat_supply_income
                UNION ALL
                 SELECT calc_sum_heating_income.sheet_name,
                    calc_sum_heating_income.company,
                    calc_sum_heating_income.company_cn,
                    calc_sum_heating_income.item,
                    calc_sum_heating_income.item_cn,
                    calc_sum_heating_income.unit,
                    calc_sum_heating_income.biz_date,
                    calc_sum_heating_income.peer_date,
                    calc_sum_heating_income.value_biz_date,
                    calc_sum_heating_income.value_peer_date
                   FROM calc_sum_heating_income
                UNION ALL
                 SELECT calc_sum_hot_water.sheet_name,
                    calc_sum_hot_water.company,
                    calc_sum_hot_water.company_cn,
                    calc_sum_hot_water.item,
                    calc_sum_hot_water.item_cn,
                    calc_sum_hot_water.unit,
                    calc_sum_hot_water.biz_date,
                    calc_sum_hot_water.peer_date,
                    calc_sum_hot_water.value_biz_date,
                    calc_sum_hot_water.value_peer_date
                   FROM calc_sum_hot_water
                UNION ALL
                 SELECT calc_sum_steam.sheet_name,
                    calc_sum_steam.company,
                    calc_sum_steam.company_cn,
                    calc_sum_steam.item,
                    calc_sum_steam.item_cn,
                    calc_sum_steam.unit,
                    calc_sum_steam.biz_date,
                    calc_sum_steam.peer_date,
                    calc_sum_steam.value_biz_date,
                    calc_sum_steam.value_peer_date
                   FROM calc_sum_steam) c
          GROUP BY c.sheet_name, c.company, c.company_cn
        ), calc_sum_marginal_profit AS (
         SELECT di.sheet_name,
            di.company,
            di.company_cn,
            'eco_marginal_profit'::text AS item,
            '边际利润'::text AS item_cn,
            '万元'::text AS unit,
            di.biz_date,
            di.peer_date,
            di.value_biz_date - (COALESCE(ng.value_biz_date, 0::numeric) + COALESCE(pp.value_biz_date, 0::numeric) + COALESCE(pw.value_biz_date, 0::numeric) + COALESCE(am.value_biz_date, 0::numeric) + COALESCE(oh.value_biz_date, 0::numeric) + COALESCE(ih.value_biz_date, 0::numeric) + COALESCE(rc.value_biz_date, 0::numeric)) AS value_biz_date,
            di.value_peer_date - (COALESCE(ng.value_peer_date, 0::numeric) + COALESCE(pp.value_peer_date, 0::numeric) + COALESCE(pw.value_peer_date, 0::numeric) + COALESCE(am.value_peer_date, 0::numeric) + COALESCE(oh.value_peer_date, 0::numeric) + COALESCE(ih.value_peer_date, 0::numeric) + COALESCE(rc.value_peer_date, 0::numeric)) AS value_peer_date
           FROM calc_sum_direct_income di
             LEFT JOIN calc_sum_natural_gas_cost ng ON ng.sheet_name = di.sheet_name AND ng.company = di.company
             LEFT JOIN calc_sum_purchased_power_cost pp ON pp.sheet_name = di.sheet_name AND pp.company = di.company
             LEFT JOIN calc_sum_purchased_water_cost pw ON pw.sheet_name = di.sheet_name AND pw.company = di.company
             LEFT JOIN calc_sum_aux_cost am ON am.sheet_name = di.sheet_name AND am.company = di.company
             LEFT JOIN calc_sum_outer_heat_cost oh ON oh.sheet_name = di.sheet_name AND oh.company = di.company
             LEFT JOIN calc_sum_inner_purchased_heat_cost ih ON ih.sheet_name = di.sheet_name AND ih.company = di.company
             LEFT JOIN calc_sum_coal_cost rc ON rc.sheet_name = di.sheet_name AND rc.company = di.company
        ), cost_sum_non_coal AS (
         SELECT t.sheet_name,
            t.company,
            sum(t.value_biz_date) AS value_biz_date,
            sum(t.value_peer_date) AS value_peer_date
           FROM ( SELECT calc_sum_natural_gas_cost.sheet_name,
                    calc_sum_natural_gas_cost.company,
                    calc_sum_natural_gas_cost.value_biz_date,
                    calc_sum_natural_gas_cost.value_peer_date
                   FROM calc_sum_natural_gas_cost
                UNION ALL
                 SELECT calc_sum_purchased_power_cost.sheet_name,
                    calc_sum_purchased_power_cost.company,
                    calc_sum_purchased_power_cost.value_biz_date,
                    calc_sum_purchased_power_cost.value_peer_date
                   FROM calc_sum_purchased_power_cost
                UNION ALL
                 SELECT calc_sum_purchased_water_cost.sheet_name,
                    calc_sum_purchased_water_cost.company,
                    calc_sum_purchased_water_cost.value_biz_date,
                    calc_sum_purchased_water_cost.value_peer_date
                   FROM calc_sum_purchased_water_cost
                UNION ALL
                 SELECT calc_sum_aux_cost.sheet_name,
                    calc_sum_aux_cost.company,
                    calc_sum_aux_cost.value_biz_date,
                    calc_sum_aux_cost.value_peer_date
                   FROM calc_sum_aux_cost
                UNION ALL
                 SELECT calc_sum_outer_heat_cost.sheet_name,
                    calc_sum_outer_heat_cost.company,
                    calc_sum_outer_heat_cost.value_biz_date,
                    calc_sum_outer_heat_cost.value_peer_date
                   FROM calc_sum_outer_heat_cost
                UNION ALL
                 SELECT calc_sum_inner_purchased_heat_cost.sheet_name,
                    calc_sum_inner_purchased_heat_cost.company,
                    calc_sum_inner_purchased_heat_cost.value_biz_date,
                    calc_sum_inner_purchased_heat_cost.value_peer_date
                   FROM calc_sum_inner_purchased_heat_cost) t
          GROUP BY t.sheet_name, t.company
        ), calc_sum_comparable_marginal_profit AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'eco_comparable_marginal_profit'::text AS item,
            '可比煤价边际利润'::text AS item_cn,
            '万元'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            COALESCE(max(di.value_biz_date), 0::numeric) - COALESCE(max(cnc.value_biz_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) * COALESCE(max(cb_sc.value), 0::numeric) / 10000.0 AS value_biz_date,
            COALESCE(max(di.value_peer_date), 0::numeric) - COALESCE(max(cnc.value_peer_date), 0::numeric) - sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) * COALESCE(max(cp_sc.value), 0::numeric) / 10000.0 AS value_peer_date
           FROM base_sum b
             LEFT JOIN const_sum_biz cb_sc ON cb_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN const_sum_peer cp_sc ON cp_sc.item = 'price_std_coal_comparable'::text
             LEFT JOIN calc_sum_direct_income di ON di.sheet_name = b.sheet_name AND di.company = b.company
             LEFT JOIN cost_sum_non_coal cnc ON cnc.sheet_name = b.sheet_name AND cnc.company = b.company
          GROUP BY b.sheet_name, b.company, b.company_cn
        ), calc_sum_overall_efficiency AS (
         SELECT b.sheet_name,
            b.company,
            b.company_cn,
            'rate_overall_efficiency'::text AS item,
            '全厂热效率'::text AS item_cn,
            '%'::text AS unit,
            max(b.biz_date) AS biz_date,
            max(b.peer_date) AS peer_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_biz_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_biz_date,
            round(COALESCE((sum(
                CASE
                    WHEN b.item = 'amount_heat_supply'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 36.0 * sum(
                CASE
                    WHEN b.item = 'amount_power_sales'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) - sum(
                CASE
                    WHEN b.item = 'consumption_outer_purchased_heat'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)) / NULLIF(29.308 * (sum(
                CASE
                    WHEN b.item = 'consumption_std_coal'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END) + 1.4571 * sum(
                CASE
                    WHEN b.item = 'consumption_oil'::text THEN b.value_peer_date
                    ELSE 0::numeric
                END)), 0::numeric), 0::numeric), 4) AS value_peer_date
           FROM base_sum b
          GROUP BY b.sheet_name, b.company, b.company_cn
        ), calc_sum_selected AS (
         SELECT calc_sum_power.sheet_name,
            calc_sum_power.company,
            calc_sum_power.company_cn,
            calc_sum_power.item,
            calc_sum_power.item_cn,
            calc_sum_power.unit,
            calc_sum_power.biz_date,
            calc_sum_power.peer_date,
            calc_sum_power.value_biz_date,
            calc_sum_power.value_peer_date
           FROM calc_sum_power
        UNION ALL
         SELECT calc_sum_inner_heat_supply_income.sheet_name,
            calc_sum_inner_heat_supply_income.company,
            calc_sum_inner_heat_supply_income.company_cn,
            calc_sum_inner_heat_supply_income.item,
            calc_sum_inner_heat_supply_income.item_cn,
            calc_sum_inner_heat_supply_income.unit,
            calc_sum_inner_heat_supply_income.biz_date,
            calc_sum_inner_heat_supply_income.peer_date,
            calc_sum_inner_heat_supply_income.value_biz_date,
            calc_sum_inner_heat_supply_income.value_peer_date
           FROM calc_sum_inner_heat_supply_income
        UNION ALL
         SELECT calc_sum_coal_cost.sheet_name,
            calc_sum_coal_cost.company,
            calc_sum_coal_cost.company_cn,
            calc_sum_coal_cost.item,
            calc_sum_coal_cost.item_cn,
            calc_sum_coal_cost.unit,
            calc_sum_coal_cost.biz_date,
            calc_sum_coal_cost.peer_date,
            calc_sum_coal_cost.value_biz_date,
            calc_sum_coal_cost.value_peer_date
           FROM calc_sum_coal_cost
        UNION ALL
         SELECT calc_sum_purchased_power_cost.sheet_name,
            calc_sum_purchased_power_cost.company,
            calc_sum_purchased_power_cost.company_cn,
            calc_sum_purchased_power_cost.item,
            calc_sum_purchased_power_cost.item_cn,
            calc_sum_purchased_power_cost.unit,
            calc_sum_purchased_power_cost.biz_date,
            calc_sum_purchased_power_cost.peer_date,
            calc_sum_purchased_power_cost.value_biz_date,
            calc_sum_purchased_power_cost.value_peer_date
           FROM calc_sum_purchased_power_cost
        UNION ALL
         SELECT calc_sum_purchased_water_cost.sheet_name,
            calc_sum_purchased_water_cost.company,
            calc_sum_purchased_water_cost.company_cn,
            calc_sum_purchased_water_cost.item,
            calc_sum_purchased_water_cost.item_cn,
            calc_sum_purchased_water_cost.unit,
            calc_sum_purchased_water_cost.biz_date,
            calc_sum_purchased_water_cost.peer_date,
            calc_sum_purchased_water_cost.value_biz_date,
            calc_sum_purchased_water_cost.value_peer_date
           FROM calc_sum_purchased_water_cost
        UNION ALL
         SELECT calc_sum_aux_cost.sheet_name,
            calc_sum_aux_cost.company,
            calc_sum_aux_cost.company_cn,
            calc_sum_aux_cost.item,
            calc_sum_aux_cost.item_cn,
            calc_sum_aux_cost.unit,
            calc_sum_aux_cost.biz_date,
            calc_sum_aux_cost.peer_date,
            calc_sum_aux_cost.value_biz_date,
            calc_sum_aux_cost.value_peer_date
           FROM calc_sum_aux_cost
        UNION ALL
         SELECT calc_sum_direct_income.sheet_name,
            calc_sum_direct_income.company,
            calc_sum_direct_income.company_cn,
            calc_sum_direct_income.item,
            calc_sum_direct_income.item_cn,
            calc_sum_direct_income.unit,
            calc_sum_direct_income.biz_date,
            calc_sum_direct_income.peer_date,
            calc_sum_direct_income.value_biz_date,
            calc_sum_direct_income.value_peer_date
           FROM calc_sum_direct_income
        UNION ALL
         SELECT calc_sum_marginal_profit.sheet_name,
            calc_sum_marginal_profit.company,
            calc_sum_marginal_profit.company_cn,
            calc_sum_marginal_profit.item,
            calc_sum_marginal_profit.item_cn,
            calc_sum_marginal_profit.unit,
            calc_sum_marginal_profit.biz_date,
            calc_sum_marginal_profit.peer_date,
            calc_sum_marginal_profit.value_biz_date,
            calc_sum_marginal_profit.value_peer_date
           FROM calc_sum_marginal_profit
        UNION ALL
         SELECT calc_sum_comparable_marginal_profit.sheet_name,
            calc_sum_comparable_marginal_profit.company,
            calc_sum_comparable_marginal_profit.company_cn,
            calc_sum_comparable_marginal_profit.item,
            calc_sum_comparable_marginal_profit.item_cn,
            calc_sum_comparable_marginal_profit.unit,
            calc_sum_comparable_marginal_profit.biz_date,
            calc_sum_comparable_marginal_profit.peer_date,
            calc_sum_comparable_marginal_profit.value_biz_date,
            calc_sum_comparable_marginal_profit.value_peer_date
           FROM calc_sum_comparable_marginal_profit
        UNION ALL
         SELECT calc_sum_overall_efficiency.sheet_name,
            calc_sum_overall_efficiency.company,
            calc_sum_overall_efficiency.company_cn,
            calc_sum_overall_efficiency.item,
            calc_sum_overall_efficiency.item_cn,
            calc_sum_overall_efficiency.unit,
            calc_sum_overall_efficiency.biz_date,
            calc_sum_overall_efficiency.peer_date,
            calc_sum_overall_efficiency.value_biz_date,
            calc_sum_overall_efficiency.value_peer_date
           FROM calc_sum_overall_efficiency
        )
 SELECT base_sum.sheet_name,
    base_sum.company,
    base_sum.company_cn,
    base_sum.item,
    base_sum.item_cn,
    base_sum.unit,
    base_sum.biz_date,
    base_sum.peer_date,
    base_sum.value_biz_date,
    base_sum.value_peer_date
   FROM base_sum
UNION ALL
 SELECT calc_sum_selected.sheet_name,
    calc_sum_selected.company,
    calc_sum_selected.company_cn,
    calc_sum_selected.item,
    calc_sum_selected.item_cn,
    calc_sum_selected.unit,
    calc_sum_selected.biz_date,
    calc_sum_selected.peer_date,
    calc_sum_selected.value_biz_date,
    calc_sum_selected.value_peer_date
   FROM calc_sum_selected;

