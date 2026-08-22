-- =========================================================================
-- 凤凰平台：生产环境全库主键自增序列 (id sequence) 自动排查与一键自愈脚本
-- =========================================================================
-- 作用：
--   1. 自动扫描 logs, tube, public 等业务模式下的所有数据表；
--   2. 检测是否存在名为 "id" 且未设置 DEFAULT 序列的主键字段；
--   3. 自动创建缺失序列、绑定 DEFAULT nextval(...)，并推进序列值至 MAX(id) + 1。
-- =========================================================================

DO $$
DECLARE
    r RECORD;
    v_seq_name TEXT;
    v_full_table TEXT;
    v_sql TEXT;
    v_count INT := 0;
BEGIN
    RAISE NOTICE '========== 开始全库主键自增序列排查与自愈 ==========';

    FOR r IN (
        SELECT 
            c.table_schema,
            c.table_name,
            c.column_name,
            c.data_type
        FROM information_schema.columns c
        JOIN information_schema.tables t 
            ON t.table_schema = c.table_schema 
            AND t.table_name = c.table_name
        WHERE t.table_type = 'BASE TABLE'
          AND c.table_schema NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
          AND c.column_name = 'id'
          AND c.column_default IS NULL
          AND c.data_type IN ('integer', 'bigint', 'smallint')
        ORDER BY c.table_schema, c.table_name
    ) LOOP
        v_seq_name := quote_ident(r.table_schema) || '.' || quote_ident(r.table_name || '_id_seq');
        v_full_table := quote_ident(r.table_schema) || '.' || quote_ident(r.table_name);
        
        RAISE NOTICE '发现缺失自增序列的数据表: % (字段: id, 类型: %)', v_full_table, r.data_type;
        
        -- 1. 创建序列
        v_sql := 'CREATE SEQUENCE IF NOT EXISTS ' || v_seq_name || ';';
        EXECUTE v_sql;
        
        -- 2. 绑定序列默认值
        v_sql := 'ALTER TABLE ' || v_full_table || ' ALTER COLUMN id SET DEFAULT nextval(''' || v_seq_name || '''::regclass);';
        EXECUTE v_sql;
        
        -- 3. 关联所属列
        v_sql := 'ALTER SEQUENCE ' || v_seq_name || ' OWNED BY ' || v_full_table || '.id;';
        EXECUTE v_sql;
        
        -- 4. 同步序列指针到当前最大值
        v_sql := 'SELECT setval(''' || v_seq_name || ''', COALESCE((SELECT MAX(id) FROM ' || v_full_table || '), 0) + 1, false);';
        EXECUTE v_sql;
        
        v_count := v_count + 1;
        RAISE NOTICE '--> 成功修复表 % 自增序列: %', v_full_table, v_seq_name;
    END LOOP;

    IF v_count = 0 THEN
        RAISE NOTICE '全库检查完成：所有数据表主键自增序列均正常，无需修复！';
    ELSE
        RAISE NOTICE '========== 全库修复完成，共自愈修复 % 张表的自增序列 ==========', v_count;
    END IF;
END $$;
