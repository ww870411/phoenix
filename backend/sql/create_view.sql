
DROP MATERIALIZED VIEW IF EXISTS sum_gongre_branches_detail_data;
DROP MATERIALIZED VIEW IF EXISTS sum_basic_data;


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
