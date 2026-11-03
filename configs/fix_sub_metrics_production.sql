-- ==============================================================================
-- 🦅 Phoenix 凤凰计划 · 25-26 供暖期两个“其中”指标补齐脚本（省平台=0，市平台=当日净投诉量）
-- 适用场景:
--   如果您在服务器上已经执行过历史归档和 4 项指标入库，只需要单独补齐这两个“其中”指标，
--   可直接执行本脚本。
-- 覆盖范围:
--   1. 总表 (GongRe_Sheet): 156天 * 2指标 = 312 条
--   2. 分中心表 (GongRe_branches_detail_Sheet): 10中心 * 156天 * 2指标 = 3120 条
--   合计新增: 3,432 条标准指标记录
-- ==============================================================================

BEGIN;

-- 【步骤 1】防重清理（若已存在则清理后重新插入，确保幂等）
DELETE FROM daily_basic_data
WHERE sheet_name IN ('GongRe_Sheet', 'GongRe_branches_detail_Sheet')
  AND date >= '2025-11-01' AND date <= '2026-04-05'
  AND item IN ('amount_daily_provincial_net_complaints', 'amount_daily_city_net_complaints');

-- 【步骤 2】总表 (GongRe_Sheet) 补齐
-- 2.1 省平台全赋 0 (156 条)
INSERT INTO daily_basic_data (
    company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
)
SELECT 
    company, company_cn, sheet_name, 
    'amount_daily_provincial_net_complaints', '其中：1.省平台净投诉量', 
    0.0000, '件', NULL, date, 'submit', NOW()
FROM daily_basic_data
WHERE sheet_name = 'GongRe_Sheet'
  AND item = 'amount_daily_net_complaints'
  AND date >= '2025-11-01' AND date <= '2026-04-05';

-- 2.2 市平台等于当日净投诉量 (156 条)
INSERT INTO daily_basic_data (
    company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
)
SELECT 
    company, company_cn, sheet_name, 
    'amount_daily_city_net_complaints', '其中：2.市平台净投诉量', 
    value, '件', NULL, date, 'submit', NOW()
FROM daily_basic_data
WHERE sheet_name = 'GongRe_Sheet'
  AND item = 'amount_daily_net_complaints'
  AND date >= '2025-11-01' AND date <= '2026-04-05';

-- 【步骤 3】分中心明细表 (GongRe_branches_detail_Sheet) 补齐
-- 3.1 10个中心省平台全赋 0 (1560 条)
INSERT INTO daily_basic_data (
    company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
)
SELECT 
    company, company_cn, sheet_name, 
    'amount_daily_provincial_net_complaints', '其中：1.省平台净投诉量', 
    0.0000, '件', NULL, date, 'submit', NOW()
FROM daily_basic_data
WHERE sheet_name = 'GongRe_branches_detail_Sheet'
  AND item = 'amount_daily_net_complaints'
  AND date >= '2025-11-01' AND date <= '2026-04-05';

-- 3.2 10个中心市平台等于该中心当日净投诉量 (1560 条)
INSERT INTO daily_basic_data (
    company, company_cn, sheet_name, item, item_cn, value, unit, note, date, status, operation_time
)
SELECT 
    company, company_cn, sheet_name, 
    'amount_daily_city_net_complaints', '其中：2.市平台净投诉量', 
    value, '件', NULL, date, 'submit', NOW()
FROM daily_basic_data
WHERE sheet_name = 'GongRe_branches_detail_Sheet'
  AND item = 'amount_daily_net_complaints'
  AND date >= '2025-11-01' AND date <= '2026-04-05';

-- 【步骤 4】核验查询（预期：GongRe_Sheet 为 312 条，GongRe_branches_detail_Sheet 为 3120 条）
-- SELECT sheet_name, COUNT(*) FROM daily_basic_data 
-- WHERE date >= '2025-11-01' AND date <= '2026-04-05' 
--   AND item IN ('amount_daily_provincial_net_complaints', 'amount_daily_city_net_complaints')
-- GROUP BY sheet_name;

COMMIT;
