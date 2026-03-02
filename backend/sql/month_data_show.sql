-- monthly_data_show 表建表脚本
-- 用于存储月报导入与查询模块（monthly_data_show）提取后的标准化数据
-- 可重复执行，若表已存在则不会重新创建

CREATE TABLE IF NOT EXISTS monthly_data_show (
    id              BIGSERIAL PRIMARY KEY,
    company         TEXT NOT NULL,
    item            TEXT NOT NULL,
    unit            TEXT,
    value           NUMERIC(18,8),
    date            DATE NOT NULL,
    period          TEXT NOT NULL,
    type            TEXT NOT NULL,
    report_month    DATE NOT NULL,
    operation_time  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 业务唯一性：同一日期+期间+类型+公司+指标仅保留一条记录
CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_data_show_unique
    ON monthly_data_show (company, item, date, period, type);

-- 常用查询索引：按业务日期与公司查询
CREATE INDEX IF NOT EXISTS idx_monthly_data_show_date_company
    ON monthly_data_show (date, company);
