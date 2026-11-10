-- 日报修正申请增量迁移；不修改现有业务数据。最后验证日期：2026-11-10。
-- 应用首次调用接口也会幂等建表；部署时可提前执行本文件。
BEGIN;
CREATE TABLE IF NOT EXISTS daily_data_correction (
    id SERIAL PRIMARY KEY,
    sheet_key TEXT NOT NULL,
    sheet_name TEXT NOT NULL,
    unit_id TEXT NOT NULL,
    biz_date DATE NOT NULL,
    applicant TEXT NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    changes JSON NOT NULL,
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    resolved_by TEXT,
    resolution_note TEXT
);
CREATE INDEX IF NOT EXISTS ix_daily_data_correction_sheet_key ON daily_data_correction(sheet_key);
CREATE INDEX IF NOT EXISTS ix_daily_data_correction_biz_date ON daily_data_correction(biz_date);
CREATE INDEX IF NOT EXISTS ix_daily_data_correction_status ON daily_data_correction(status);
CREATE TABLE IF NOT EXISTS daily_data_correction_cell (
    cell_key TEXT PRIMARY KEY,
    request_id INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_daily_data_correction_cell_request_id ON daily_data_correction_cell(request_id);
COMMIT;
