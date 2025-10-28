
-- ========= 一级汇总视图（含主城区口径） =========
-- sum_basic_data 普通视图（含原公司粒度 + 主城区聚合）
-- 口径：按 company / item 汇总每日基础数据，对 biz_date（当前系统日前一天）及其同期日计算 6 个累计指标
-- 使用前请确认 daily_basic_data 表结构与 value/date 字段命名一致，并在生产环境执行前先在测试库验证
-- 默认创建在当前 search_path 指向的 schema（通常为 public），如需单独 schema 可在执行前 SET search_path

DROP VIEW IF EXISTS sum_basic_data;

CREATE VIEW sum_basic_data AS
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
)
-- 输出：原公司粒度 + “主城区(BeiHai+XiangHai+GongRe)”聚合口径
SELECT * FROM base
UNION ALL
SELECT
  'ZhuChengQu' AS company,
  '主城区'      AS company_cn,
  item, item_cn, unit,
  biz_date, peer_date,
  SUM(value_biz_date)  AS value_biz_date,
  SUM(value_peer_date) AS value_peer_date,
  SUM(sum_7d_biz)      AS sum_7d_biz,
  SUM(sum_7d_peer)     AS sum_7d_peer,
  SUM(sum_month_biz)   AS sum_month_biz,
  SUM(sum_month_peer)  AS sum_month_peer,
  SUM(sum_ytd_biz)     AS sum_ytd_biz,
  SUM(sum_ytd_peer)    AS sum_ytd_peer
FROM base
WHERE company IN ('BeiHai','XiangHai','GongRe')
GROUP BY item, item_cn, unit, biz_date, peer_date
UNION ALL
-- 集团全口径：ZhuChengQu（= BeiHai+XiangHai+GongRe）+ JinZhou + BeiFang + JinpPu + ZhuangHe + YanJiuYuan
-- 注：为避免依赖“ZhuChengQu”是否已存在于视图结果中，这里直接从 base 按公司明细汇总等价实现
SELECT
  'Group'       AS company,
  '集团全口径'   AS company_cn,
  item, item_cn, unit,
  biz_date, peer_date,
  SUM(value_biz_date)  AS value_biz_date,
  SUM(value_peer_date) AS value_peer_date,
  SUM(sum_7d_biz)      AS sum_7d_biz,
  SUM(sum_7d_peer)     AS sum_7d_peer,
  SUM(sum_month_biz)   AS sum_month_biz,
  SUM(sum_month_peer)  AS sum_month_peer,
  SUM(sum_ytd_biz)     AS sum_ytd_biz,
  SUM(sum_ytd_peer)    AS sum_ytd_peer
FROM base
WHERE company IN ('BeiHai','XiangHai','GongRe','JinZhou','BeiFang','JinpPu','ZhuangHe','YanJiuYuan')
GROUP BY item, item_cn, unit, biz_date, peer_date;

-- 注意：普通视图不可创建索引；如需性能优化，请在底表 daily_basic_data 上创建（或调整）索引。
