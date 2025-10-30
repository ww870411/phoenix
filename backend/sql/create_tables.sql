-- Phoenix 项目数据库建表脚本
-- 可重复执行，若表已存在则不会重新创建。

CREATE TABLE IF NOT EXISTS daily_basic_data (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    company_cn      TEXT,
    sheet_name      TEXT NOT NULL,
    item            TEXT NOT NULL,
    item_cn         TEXT,
    value           NUMERIC(18,4),
    unit            TEXT,
    note            TEXT,
    date            DATE NOT NULL,
    status          VARCHAR(32) ,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_basic_date_company
    ON Daily_basic_data (date, company,sheet_name,item,item_cn);

-- 为幂等与并发写入安全增加唯一约束：同一 (company, sheet_name, item, date) 仅保留一条记录
-- 注意：如库中已存在重复数据，请先按 operation_time 保留最新一条并清理旧数据，再执行本索引创建
CREATE UNIQUE INDEX IF NOT EXISTS ux_daily_basic_unique
    ON daily_basic_data (company, sheet_name, item, date);


CREATE TABLE IF NOT EXISTS constant_data (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    company_cn      TEXT,
    center          TEXT,
    center_cn       TEXT,
    sheet_name      TEXT NOT NULL,
    item            TEXT NOT NULL,
    item_cn         TEXT,
    value           NUMERIC(18,4),
    unit            TEXT,
    period          TEXT NOT NULL,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_constant_unique
    ON Constant_data (company, center, sheet_name, item, period);

CREATE TABLE IF NOT EXISTS temperature_data (
    id              BIGSERIAL PRIMARY KEY,
    date_time       TIMESTAMPTZ NOT NULL,
    value           NUMERIC(18,4),
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_temperature_datetime
    ON Temperature_data (date_time);

CREATE TABLE IF NOT EXISTS coal_inventory_data (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    company_cn      TEXT,
    coal_type       TEXT NOT NULL,
    coal_type_cn    TEXT,
    storage_type    TEXT,
    storage_type_cn TEXT,
    value           NUMERIC(18,4),
    unit            TEXT,
    date            DATE NOT NULL,
    status          TEXT,
    note            TEXT,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_coal_inventory_unique
    ON Coal_inventory_data (date, company, coal_type,  storage_type);
