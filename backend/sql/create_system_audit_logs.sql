-- ==========================================================
-- 凤凰平台全局系统操作与审计日志表 (System Audit Logs)
-- 模式: logs
-- 表名: system_audit_logs
-- ==========================================================

CREATE SCHEMA IF NOT EXISTS logs;

CREATE TABLE IF NOT EXISTS logs.system_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ts_east8 VARCHAR(64),
    project_key VARCHAR(64),
    category VARCHAR(64) NOT NULL DEFAULT 'default',
    action VARCHAR(64) NOT NULL DEFAULT 'action',
    status VARCHAR(32) NOT NULL DEFAULT 'success',
    duration_ms INTEGER,
    error_msg TEXT,
    resource_type VARCHAR(64),
    resource_id VARCHAR(128),
    page VARCHAR(512),
    target TEXT,
    request_id VARCHAR(64),
    username VARCHAR(64),
    user_group VARCHAR(64),
    unit VARCHAR(128),
    client_ip VARCHAR(64),
    user_agent TEXT,
    detail JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 高效索引构建：支撑时间倒序流、项目分权、对象追溯、用户检索、分类统计与 JSONB 倒排查询
CREATE INDEX IF NOT EXISTS idx_sys_audit_ts ON logs.system_audit_logs (ts DESC);
CREATE INDEX IF NOT EXISTS idx_sys_audit_proj ON logs.system_audit_logs (project_key);
CREATE INDEX IF NOT EXISTS idx_sys_audit_res ON logs.system_audit_logs (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_sys_audit_user ON logs.system_audit_logs (username);
CREATE INDEX IF NOT EXISTS idx_sys_audit_cat_act ON logs.system_audit_logs (category, action);
CREATE INDEX IF NOT EXISTS idx_sys_audit_status ON logs.system_audit_logs (status);
CREATE INDEX IF NOT EXISTS idx_sys_audit_page ON logs.system_audit_logs (page);
CREATE INDEX IF NOT EXISTS idx_sys_audit_detail_gin ON logs.system_audit_logs USING gin (detail);

COMMENT ON TABLE logs.system_audit_logs IS '系统全局操作与访问审计日志表';
COMMENT ON COLUMN logs.system_audit_logs.id IS '自增主键';
COMMENT ON COLUMN logs.system_audit_logs.ts IS '事件发生的标准 UTC 时间戳';
COMMENT ON COLUMN logs.system_audit_logs.ts_east8 IS '事件发生的东八区（北京时间）格式化时间文本';
COMMENT ON COLUMN logs.system_audit_logs.project_key IS '所属业务子项目标识（如 daily_report_25_26, insulation_pipe_supply_2026, admin_console 等）';
COMMENT ON COLUMN logs.system_audit_logs.category IS '操作分类（如 ui、navigation、submit、admin、auth、api 等）';
COMMENT ON COLUMN logs.system_audit_logs.action IS '具体动作名称（如 page_open、click、login、update_config、submit_entry 等）';
COMMENT ON COLUMN logs.system_audit_logs.status IS '操作/调用结果状态（success / failed / warning）';
COMMENT ON COLUMN logs.system_audit_logs.duration_ms IS '操作执行或接口耗时毫秒数';
COMMENT ON COLUMN logs.system_audit_logs.error_msg IS '失败时的异常错误摘要信息';
COMMENT ON COLUMN logs.system_audit_logs.resource_type IS '操作涉及的业务对象类型（如 sheet_entry, fitting_delivery, user_account, db_table 等）';
COMMENT ON COLUMN logs.system_audit_logs.resource_id IS '操作涉及的具体业务对象主键或唯一标识';
COMMENT ON COLUMN logs.system_audit_logs.page IS '操作发生的前端路由或页面 URL';
COMMENT ON COLUMN logs.system_audit_logs.target IS '操作的目标对象描述、按钮文案或具体业务目标';
COMMENT ON COLUMN logs.system_audit_logs.request_id IS '链路唯一追踪标识 ID';
COMMENT ON COLUMN logs.system_audit_logs.username IS '操作人账号';
COMMENT ON COLUMN logs.system_audit_logs.user_group IS '操作人系统角色组（如 Global_admin、Supply_entity 等）';
COMMENT ON COLUMN logs.system_audit_logs.unit IS '操作人归属单位/分公司名称';
COMMENT ON COLUMN logs.system_audit_logs.client_ip IS '操作人客户端 IP 地址';
COMMENT ON COLUMN logs.system_audit_logs.user_agent IS '客户端浏览器或设备 User-Agent 信息';
COMMENT ON COLUMN logs.system_audit_logs.detail IS '操作参数详情、数据前后快照(before/after)或补充数据的 JSONB 结构体';
COMMENT ON COLUMN logs.system_audit_logs.created_at IS '记录写入数据库的时间';

-- 存量历史库自愈修复：若历史表丢失自增序列或 DEFAULT nextval
CREATE SEQUENCE IF NOT EXISTS logs.system_audit_logs_id_seq;
ALTER TABLE logs.system_audit_logs ALTER COLUMN id SET DEFAULT nextval('logs.system_audit_logs_id_seq');
ALTER SEQUENCE logs.system_audit_logs_id_seq OWNED BY logs.system_audit_logs.id;
SELECT setval('logs.system_audit_logs_id_seq', COALESCE((SELECT MAX(id) FROM logs.system_audit_logs), 0) + 1, false);

