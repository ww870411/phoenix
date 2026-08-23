-- ==============================================================================
-- 脚本名称: fix_all_database_health_audit.sql
-- 功能描述: 全库健康体检与自愈脚本（自动对齐序列、重排重号ID、补齐主键与索引）
-- 适用范围: 覆盖 public, tube, logs 全库 21 张物理表
-- 运行原则: 纯幂等、无损业务数据、事务保护
-- ==============================================================================

BEGIN;

-- ------------------------------------------------------------------------------
-- 1. 修复 public.auth_sessions 主键
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'auth_sessions' AND n.nspname = 'public' AND c.contype = 'p'
    ) THEN
        ALTER TABLE public.auth_sessions ADD CONSTRAINT pk_auth_sessions PRIMARY KEY (token);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 2. 修复 public.paln_and_real_month_data 主键与自增序列
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS public.paln_and_real_month_data_id_seq;
    PERFORM setval('public.paln_and_real_month_data_id_seq', COALESCE((SELECT MAX(id) FROM public.paln_and_real_month_data), 0) + 1, false);
    ALTER TABLE public.paln_and_real_month_data ALTER COLUMN id SET DEFAULT nextval('public.paln_and_real_month_data_id_seq');
    ALTER SEQUENCE public.paln_and_real_month_data_id_seq OWNED BY public.paln_and_real_month_data.id;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'paln_and_real_month_data' AND n.nspname = 'public' AND c.contype = 'p'
    ) THEN
        ALTER TABLE public.paln_and_real_month_data ADD CONSTRAINT pk_paln_and_real_month_data PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 3. 修复 tube.tube_fitting_baseline 序列严重滞后问题
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_fitting_baseline_id_seq;
    PERFORM setval('tube.tube_fitting_baseline_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_fitting_baseline), 0) + 1, false);
    ALTER TABLE tube.tube_fitting_baseline ALTER COLUMN id SET DEFAULT nextval('tube.tube_fitting_baseline_id_seq');
    ALTER SEQUENCE tube.tube_fitting_baseline_id_seq OWNED BY tube.tube_fitting_baseline.id;
END $$;

-- ------------------------------------------------------------------------------
-- 4. 修复 tube.tube_pipe_baseline 序列滞后问题
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_pipe_baseline_id_seq;
    PERFORM setval('tube.tube_pipe_baseline_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_pipe_baseline), 0) + 1, false);
    ALTER TABLE tube.tube_pipe_baseline ALTER COLUMN id SET DEFAULT nextval('tube.tube_pipe_baseline_id_seq');
    ALTER SEQUENCE tube.tube_pipe_baseline_id_seq OWNED BY tube.tube_pipe_baseline.id;
END $$;

-- ------------------------------------------------------------------------------
-- 5. 修复 tube.tube_daily_usage 主键与序列
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_daily_usage_id_seq;
    PERFORM setval('tube.tube_daily_usage_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_daily_usage), 0) + 1, false);
    ALTER TABLE tube.tube_daily_usage ALTER COLUMN id SET DEFAULT nextval('tube.tube_daily_usage_id_seq');
    ALTER SEQUENCE tube.tube_daily_usage_id_seq OWNED BY tube.tube_daily_usage.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_daily_usage' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_daily_usage ADD CONSTRAINT pk_tube_daily_usage PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 6. 修复 tube.tube_gis 主键与序列
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_gis_id_seq;
    PERFORM setval('tube.tube_gis_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_gis), 0) + 1, false);
    ALTER TABLE tube.tube_gis ALTER COLUMN id SET DEFAULT nextval('tube.tube_gis_id_seq');
    ALTER SEQUENCE tube.tube_gis_id_seq OWNED BY tube.tube_gis.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_gis' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_gis ADD CONSTRAINT pk_tube_gis PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 7. 修复 tube.tube_weather_daily 主键、序列与唯一约束
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_weather_daily_id_seq;
    PERFORM setval('tube.tube_weather_daily_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_weather_daily), 0) + 1, false);
    ALTER TABLE tube.tube_weather_daily ALTER COLUMN id SET DEFAULT nextval('tube.tube_weather_daily_id_seq');
    ALTER SEQUENCE tube.tube_weather_daily_id_seq OWNED BY tube.tube_weather_daily.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_weather_daily' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_weather_daily ADD CONSTRAINT pk_tube_weather_daily PRIMARY KEY (id);
    END IF;

    CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_daily_date 
        ON tube.tube_weather_daily (weather_date);
END $$;

-- ------------------------------------------------------------------------------
-- 8. 修复 tube.tube_weather_hourly 主键、序列与唯一约束
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_weather_hourly_id_seq;
    PERFORM setval('tube.tube_weather_hourly_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_weather_hourly), 0) + 1, false);
    ALTER TABLE tube.tube_weather_hourly ALTER COLUMN id SET DEFAULT nextval('tube.tube_weather_hourly_id_seq');
    ALTER SEQUENCE tube.tube_weather_hourly_id_seq OWNED BY tube.tube_weather_hourly.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_weather_hourly' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_weather_hourly ADD CONSTRAINT pk_tube_weather_hourly PRIMARY KEY (id);
    END IF;

    CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_hourly_datetime 
        ON tube.tube_weather_hourly (weather_date_time);
END $$;

-- ------------------------------------------------------------------------------
-- 9. 修复 tube.tube_daily_plan（ID重排 -> 补齐主键与序列）
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    -- 为重号行重新分配单调递增的独立 id
    WITH numbered AS (
        SELECT ctid, ROW_NUMBER() OVER (ORDER BY plan_date, section_1_id, pipe_model_id, id) AS new_id
        FROM tube.tube_daily_plan
    )
    UPDATE tube.tube_daily_plan t
    SET id = n.new_id
    FROM numbered n
    WHERE t.ctid = n.ctid;

    CREATE SEQUENCE IF NOT EXISTS tube.tube_daily_plan_id_seq;
    PERFORM setval('tube.tube_daily_plan_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_daily_plan), 0) + 1, false);
    ALTER TABLE tube.tube_daily_plan ALTER COLUMN id SET DEFAULT nextval('tube.tube_daily_plan_id_seq');
    ALTER SEQUENCE tube.tube_daily_plan_id_seq OWNED BY tube.tube_daily_plan.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_daily_plan' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_daily_plan ADD CONSTRAINT pk_tube_daily_plan PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 10. 修复 logs.tube_operation_logs（ID重排 -> 补齐主键与序列）
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    WITH numbered AS (
        SELECT ctid, ROW_NUMBER() OVER (ORDER BY created_at, id) AS new_id
        FROM logs.tube_operation_logs
    )
    UPDATE logs.tube_operation_logs t
    SET id = n.new_id
    FROM numbered n
    WHERE t.ctid = n.ctid;

    CREATE SEQUENCE IF NOT EXISTS logs.tube_operation_logs_id_seq;
    PERFORM setval('logs.tube_operation_logs_id_seq', COALESCE((SELECT MAX(id) FROM logs.tube_operation_logs), 0) + 1, false);
    ALTER TABLE logs.tube_operation_logs ALTER COLUMN id SET DEFAULT nextval('logs.tube_operation_logs_id_seq');
    ALTER SEQUENCE logs.tube_operation_logs_id_seq OWNED BY logs.tube_operation_logs.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_operation_logs' AND n.nspname = 'logs' AND c.contype = 'p'
    ) THEN
        ALTER TABLE logs.tube_operation_logs ADD CONSTRAINT pk_tube_operation_logs PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 11. 修复 tube.tube_inventory_adjustment 主键与自增序列
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.tube_inventory_adjustment_id_seq;
    PERFORM setval('tube.tube_inventory_adjustment_id_seq', COALESCE((SELECT MAX(id) FROM tube.tube_inventory_adjustment), 0) + 1, false);
    ALTER TABLE tube.tube_inventory_adjustment ALTER COLUMN id SET DEFAULT nextval('tube.tube_inventory_adjustment_id_seq');
    ALTER SEQUENCE tube.tube_inventory_adjustment_id_seq OWNED BY tube.tube_inventory_adjustment.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'tube_inventory_adjustment' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.tube_inventory_adjustment ADD CONSTRAINT pk_tube_inventory_adjustment PRIMARY KEY (id);
    END IF;
END $$;

-- ------------------------------------------------------------------------------
-- 12. 修复 tube.operation_logs（旧日志空表）主键与自增序列
-- ------------------------------------------------------------------------------
DO $$
BEGIN
    CREATE SEQUENCE IF NOT EXISTS tube.operation_logs_id_seq;
    PERFORM setval('tube.operation_logs_id_seq', COALESCE((SELECT MAX(id) FROM tube.operation_logs), 0) + 1, false);
    ALTER TABLE tube.operation_logs ALTER COLUMN id SET DEFAULT nextval('tube.operation_logs_id_seq');
    ALTER SEQUENCE tube.operation_logs_id_seq OWNED BY tube.operation_logs.id;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE t.relname = 'operation_logs' AND n.nspname = 'tube' AND c.contype = 'p'
    ) THEN
        ALTER TABLE tube.operation_logs ADD CONSTRAINT pk_operation_logs PRIMARY KEY (id);
    END IF;
END $$;

COMMIT;
