-- 登录会话持久化表
-- 说明：
--   - 统一存储所有 Bearer Token，保证服务重启或多副本部署时会话不丢失；
--   - permissions/allowed_units 以 JSONB 形式保存，以便快速还原到 AuthSession；
--   - last_accessed 用于记录最近一次校验，便于统计与过期清理。
CREATE TABLE IF NOT EXISTS auth_sessions (
    token         TEXT PRIMARY KEY,
    username      TEXT        NOT NULL,
    user_group    TEXT        NOT NULL,
    unit          TEXT,
    hierarchy     INTEGER     NOT NULL,
    permissions   JSONB       NOT NULL,
    allowed_units JSONB       NOT NULL,
    issued_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL,
    last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_username
    ON auth_sessions (username);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
    ON auth_sessions (expires_at);
