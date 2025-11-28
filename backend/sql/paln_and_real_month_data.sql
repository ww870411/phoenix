-- paln_and_real_month_data 表建表脚本
-- 独立执行时也可重复运行

CREATE TABLE IF NOT EXISTS paln_and_real_month_data (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    company_cn      TEXT,
    item            TEXT NOT NULL,
    item_cn         TEXT,
    unit            TEXT,
    period          TEXT NOT NULL,
    value           NUMERIC(18,4),
    type            TEXT NOT NULL,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_paln_and_real_month_unique
    ON paln_and_real_month_data (company, item, period, type);
