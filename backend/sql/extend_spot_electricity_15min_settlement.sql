-- 扩展现货15分钟表：保存账单实时价及七台机组的省内中长期合约量价。
-- 适用数据库：PostgreSQL；目标表须已存在。
-- 可重复执行；已有数据不回填、不覆盖，新增字段保留NULL，不以0代替缺失。
-- 上传程序已迁移至15分钟表；末段核验旧表为空后删除旧表。

BEGIN;

ALTER TABLE public.spot_electricity_15min_data
    ADD COLUMN IF NOT EXISTS bill_real_time_price NUMERIC,

    ADD COLUMN IF NOT EXISTS beihai_unit1_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS beihai_unit1_contract_price NUMERIC,
    ADD COLUMN IF NOT EXISTS beihai_unit2_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS beihai_unit2_contract_price NUMERIC,
    ADD COLUMN IF NOT EXISTS beihai_unit3_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS beihai_unit3_contract_price NUMERIC,

    ADD COLUMN IF NOT EXISTS xianghai_unit1_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit1_contract_price NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit2_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit2_contract_price NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit3_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit3_contract_price NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit4_contract_quantity NUMERIC,
    ADD COLUMN IF NOT EXISTS xianghai_unit4_contract_price NUMERIC,

    ADD COLUMN IF NOT EXISTS beihai_bill_import_id UUID,
    ADD COLUMN IF NOT EXISTS xianghai_bill_import_id UUID;

COMMENT ON COLUMN public.spot_electricity_15min_data.bill_real_time_price IS
    '账单科目100600省内实时电价，元/MWh，保存源值；同一时段各机组核对一致后共用。独立于自动同步的real_time_price，不自动覆盖参考电价。';

COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit1_contract_quantity IS
    '北海1号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit1_contract_price IS
    '北海1号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit2_contract_quantity IS
    '北海2号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit2_contract_price IS
    '北海2号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit3_contract_quantity IS
    '北海3号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_unit3_contract_price IS
    '北海3号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';

COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit1_contract_quantity IS
    '香海1号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit1_contract_price IS
    '香海1号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit2_contract_quantity IS
    '香海2号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit2_contract_price IS
    '香海2号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit3_contract_quantity IS
    '香海3号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit3_contract_price IS
    '香海3号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit4_contract_quantity IS
    '香海4号机账单科目100401省内中长期合约电量，MWh，按15分钟时段保存原值';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_unit4_contract_price IS
    '香海4号机账单科目100401省内中长期合约电价，元/MWh，保存原值，不进行差价换算';

-- 批次ID关联持久化数据目录内的来源清单，不关联raw表。
COMMENT ON COLUMN public.spot_electricity_15min_data.beihai_bill_import_id IS
    '最近写入该时段北海账单数据的导入批次UUID，由上传程序填写，不关联raw表';
COMMENT ON COLUMN public.spot_electricity_15min_data.xianghai_bill_import_id IS
    '最近写入该时段香海账单数据的导入批次UUID，由上传程序填写，不关联raw表';

COMMIT;

-- 执行后核验新增字段。共17列：1个公共实时价、14个机组合约量价、2个厂站批次。
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'spot_electricity_15min_data'
  AND (column_name = 'bill_real_time_price'
       OR column_name ~ '^(beihai|xianghai)_unit[1-4]_contract_(quantity|price)$'
       OR column_name IN ('beihai_bill_import_id', 'xianghai_bill_import_id'))
ORDER BY ordinal_position;

-- ================================================================
-- 删除冗余字段（按用户要求追加，2026-10-31）
-- 警告：删除列会永久移除其中的数据，执行前请按需备份。
-- 查询接口、价格同步SQL和前端已同步移除物理列依赖，合计与价差按查询计算。
-- 不使用CASCADE；若有数据库对象依赖这些列，将报错并回滚本段事务。
-- 可重复执行；本段只删除下面明确列出的6列。
-- ================================================================
BEGIN;

ALTER TABLE public.spot_electricity_15min_data
    DROP COLUMN IF EXISTS estimated_revenue,
    DROP COLUMN IF EXISTS province_total_sales,
    DROP COLUMN IF EXISTS beihai_total_sales,
    DROP COLUMN IF EXISTS xianghai_total_sales,
    DROP COLUMN IF EXISTS total_power_sales,
    DROP COLUMN IF EXISTS price_spread;

COMMIT;

-- 核验：预期返回0行。
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'spot_electricity_15min_data'
  AND column_name IN (
      'estimated_revenue', 'province_total_sales',
      'beihai_total_sales', 'xianghai_total_sales',
      'total_power_sales', 'price_spread'
  );

-- 上传迁移完成后退役旧表；有数据则停止，避免遗漏尚未迁移的记录。
BEGIN;
DO $$
BEGIN
    IF to_regclass('public.spot_electricity_settlement_raw') IS NOT NULL THEN
        LOCK TABLE public.spot_electricity_settlement_raw IN ACCESS EXCLUSIVE MODE;
        IF EXISTS (SELECT 1 FROM public.spot_electricity_settlement_raw LIMIT 1) THEN
            RAISE EXCEPTION '旧账单表非空，请先迁移并核验数据，本次未删除';
        END IF;
        DROP TABLE public.spot_electricity_settlement_raw;
    END IF;
END $$;
COMMIT;

SELECT to_regclass('public.spot_electricity_settlement_raw') AS retired_table;
