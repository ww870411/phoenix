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


CREATE TABLE IF NOT EXISTS gongre_branches_detail_data (
    id              BIGSERIAL PRIMARY KEY,
    center          TEXT NOT NULL,
    center_cn       TEXT,
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

CREATE INDEX IF NOT EXISTS gongre_branches_detail_data_center_date_item
    ON gongre_branches_detail_data (date, center,item);


CREATE TABLE IF NOT EXISTS constant_data (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    company_cn      TEXT,
    sheet_name      TEXT NOT NULL,
    item            TEXT NOT NULL,
    item_cn         TEXT,
    value           NUMERIC(18,4),
    unit            TEXT,
    period          TEXT NOT NULL,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_constant_unique
    ON Constant_data (company, sheet_name, item, period);

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
    ON Coal_inventory_data (company, coal_type, date, storage_type);

