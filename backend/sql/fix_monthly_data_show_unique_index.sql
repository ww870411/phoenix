-- ==============================================================================
-- 脚本名称: fix_monthly_data_show_unique_index.sql
-- 功能描述: 修复 monthly_data_show 表缺失自增序列、主键及 ON CONFLICT 5维复合唯一索引
-- 适用场景: 生产/测试环境在导入 CSV 更新已有记录报错时执行
-- 特别说明: 自动探测表所在 schema，避免跨 schema 绑定 sequence 导致的报错
-- ==============================================================================

DO $$
DECLARE
    v_schema text;
BEGIN
    -- 1. 动态获取 monthly_data_show 表所在的实际 schema（通常为 public）
    SELECT table_schema INTO v_schema
    FROM information_schema.tables
    WHERE table_name = 'monthly_data_show'
    LIMIT 1;

    IF v_schema IS NULL THEN
        RAISE EXCEPTION '未在当前数据库中找到表 monthly_data_show，请检查连接！';
    END IF;

    RAISE NOTICE '正在为 schema [%] 下的 monthly_data_show 表修复索引与自增序列...', v_schema;

    -- 2. 在表所在的同 schema 下创建自增序列并绑定（避免跨 schema 报错）
    EXECUTE format('CREATE SEQUENCE IF NOT EXISTS %I.monthly_data_show_id_seq;', v_schema);
    EXECUTE format('SELECT setval(''%I.monthly_data_show_id_seq'', COALESCE((SELECT MAX(id) FROM %I.monthly_data_show), 0) + 1, false);', v_schema, v_schema);
    EXECUTE format('ALTER TABLE %I.monthly_data_show ALTER COLUMN id SET DEFAULT nextval(''%I.monthly_data_show_id_seq'');', v_schema, v_schema);
    EXECUTE format('ALTER SEQUENCE %I.monthly_data_show_id_seq OWNED BY %I.monthly_data_show.id;', v_schema, v_schema);

    -- 3. 补齐主键约束（若尚无）
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'monthly_data_show' AND n.nspname = v_schema AND c.contype = 'p'
    ) THEN
        EXECUTE format('ALTER TABLE %I.monthly_data_show ADD CONSTRAINT pk_monthly_data_show PRIMARY KEY (id);', v_schema);
    END IF;

    -- 4. 清理潜在历史重复数据（保留 id 最大的最新一条）
    EXECUTE format('
        DELETE FROM %I.monthly_data_show a USING %I.monthly_data_show b
        WHERE a.id < b.id
          AND a.company = b.company
          AND a.item = b.item
          AND a.date = b.date
          AND a.period = b.period
          AND a.type = b.type;
    ', v_schema, v_schema);

    -- 5. 【核心】创建 5 维复合唯一索引（解决 ON CONFLICT 报错）
    EXECUTE format('
        CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_data_show_unique
            ON %I.monthly_data_show (company, item, date, period, type);
    ', v_schema);

    -- 6. 创建常用查询加速索引
    EXECUTE format('
        CREATE INDEX IF NOT EXISTS idx_monthly_data_show_date_company
            ON %I.monthly_data_show (date, company);
    ', v_schema);

    RAISE NOTICE 'monthly_data_show 表索引与自增主键已全部修复成功！';

END $$;
