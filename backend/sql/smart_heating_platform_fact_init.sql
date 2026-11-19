-- ==============================================================================
-- 智慧供热管理平台 v2.0 旁路分析系统 —— 时序采样、精算汇总与阴面督办事实表初始化脚本
-- 适用数据库：PostgreSQL 12+
-- Schema: smart_heating_platform
-- 说明：
-- 1. 15分钟采样层（fact_*_15min）：支撑每 15 分钟高频批量采集与梯形面积积分；
-- 2. 小时精算层（fact_*_hourly）：支撑阳面《逐小时精细化运行报告》毫秒级查询，
--    统一记录 raw_val / clean_val / value_source / fault_tag 四维可审计结构；
-- 3. 日度与督办层（fact_merchant_daily / fact_fault_ticket）：支撑每日商业耗量
--    与阴面《下位机/上位机异常巡检督办单》派发。
-- ==============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. 采集运行审计表 (fact_collector_run)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_collector_run (
    run_id          BIGSERIAL PRIMARY KEY,
    biz_hour        TIMESTAMPTZ NOT NULL,
    run_type        VARCHAR(32) NOT NULL,   -- SNAPSHOT_15M | TABLE_BOTTOM_CALIB | MERCHANT_DAILY | MANUAL
    source_mode     VARCHAR(16) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    status          VARCHAR(16) NOT NULL,   -- RUNNING | SUCCESS | PARTIAL | FAILED
    cookie_valid    BOOLEAN,
    summary_json    JSONB,
    error_message   TEXT
);

COMMENT ON TABLE smart_heating_platform.fact_collector_run IS '采集引擎运行批次审计日志';
CREATE INDEX IF NOT EXISTS idx_fact_collector_run_hour_type
    ON smart_heating_platform.fact_collector_run (biz_hour DESC, run_type);


-- -----------------------------------------------------------------------------
-- 2. 上游热源/首站/网口 15 分钟采样明细表 (fact_upstream_15min)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_upstream_15min (
    id              BIGSERIAL PRIMARY KEY,
    sample_bucket   TIMESTAMPTZ NOT NULL,   -- 对齐到 15 分钟整刻度 (00/15/30/45)
    biz_hour        TIMESTAMPTZ NOT NULL,   -- 所属整点小时 (东八区截断至小时)
    point_id        INTEGER REFERENCES smart_heating_platform.dict_upstream_point(point_id)
                        ON UPDATE CASCADE ON DELETE SET NULL,
    data_zone       VARCHAR(32) NOT NULL,
    source_name     VARCHAR(128) NOT NULL,
    display_name    VARCHAR(128) NOT NULL,
    category        VARCHAR(32) NOT NULL,
    sub_category    VARCHAR(64),
    source_time     TIMESTAMPTZ,
    temp_raw        NUMERIC(12, 3),
    temp_clean      NUMERIC(12, 3),
    pressure_raw    NUMERIC(12, 4),
    pressure_clean  NUMERIC(12, 4),
    flow_raw        NUMERIC(14, 3),
    flow_clean      NUMERIC(14, 3),
    heat_raw        NUMERIC(14, 3),
    heat_clean      NUMERIC(14, 3),
    load_val        NUMERIC(12, 3),
    freq_val        NUMERIC(12, 3),
    value_source    VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag       VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_upstream_15min UNIQUE (sample_bucket, data_zone, source_name)
);

CREATE INDEX IF NOT EXISTS idx_fact_upstream_15min_biz_hour
    ON smart_heating_platform.fact_upstream_15min (biz_hour, data_zone, source_name);


-- -----------------------------------------------------------------------------
-- 3. 上游热源/首站/网口 小时精算表 (fact_upstream_hourly)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_upstream_hourly (
    id              BIGSERIAL PRIMARY KEY,
    biz_hour        TIMESTAMPTZ NOT NULL,
    point_id        INTEGER REFERENCES smart_heating_platform.dict_upstream_point(point_id)
                        ON UPDATE CASCADE ON DELETE SET NULL,
    data_zone       VARCHAR(32) NOT NULL,
    source_name     VARCHAR(128) NOT NULL,
    display_name    VARCHAR(128) NOT NULL,
    category        VARCHAR(32) NOT NULL,
    sub_category    VARCHAR(64),
    is_core_gk      BOOLEAN NOT NULL DEFAULT FALSE,
    sample_count    SMALLINT NOT NULL DEFAULT 0,
    source_time     TIMESTAMPTZ,
    temp_raw        NUMERIC(12, 3),
    temp_clean      NUMERIC(12, 3),
    pressure_raw    NUMERIC(12, 4),
    pressure_clean  NUMERIC(12, 4),
    flow_raw        NUMERIC(14, 3),
    flow_clean      NUMERIC(14, 3),
    heat_raw        NUMERIC(14, 3),
    heat_clean      NUMERIC(14, 3),
    hour_heat_gj    NUMERIC(14, 3),         -- 基于15分钟样本梯形积分的小时供热量(GJ)
    hour_flow_t     NUMERIC(14, 3),         -- 基于15分钟样本梯形积分的小时流量(t)
    value_source    VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag       VARCHAR(64),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_upstream_hourly UNIQUE (biz_hour, data_zone, source_name)
);

CREATE INDEX IF NOT EXISTS idx_fact_upstream_hourly_biz_hour
    ON smart_heating_platform.fact_upstream_hourly (biz_hour);


-- -----------------------------------------------------------------------------
-- 4. 换热站 15 分钟采样明细表 (fact_station_15min)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_station_15min (
    id                  BIGSERIAL PRIMARY KEY,
    sample_bucket       TIMESTAMPTZ NOT NULL,
    biz_hour            TIMESTAMPTZ NOT NULL,
    station_id          VARCHAR(64) NOT NULL REFERENCES smart_heating_platform.dict_heating_station(station_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    online              BOOLEAN NOT NULL DEFAULT TRUE,
    source_update_time  TIMESTAMPTZ,
    e1_raw              NUMERIC(12, 3),     -- 一网供水瞬时流量 (t/h)
    e1_clean            NUMERIC(12, 3),
    e3_raw              NUMERIC(10, 2),     -- 一网供水温度 (℃)
    e3_clean            NUMERIC(10, 2),
    e4_raw              NUMERIC(10, 2),     -- 一网回水温度 (℃)
    e4_clean            NUMERIC(10, 2),
    e7_raw              NUMERIC(10, 4),     -- 一网供水压力 (MPa)
    e7_clean            NUMERIC(10, 4),
    e8_raw              NUMERIC(10, 4),     -- 一网回水压力 (MPa)
    e8_clean            NUMERIC(10, 4),
    e11_raw             NUMERIC(12, 3),     -- 一网瞬时热量 (GJ/h)
    e11_clean           NUMERIC(12, 3),
    e13_raw             NUMERIC(12, 3),     -- 一网回水瞬时流量 (t/h)
    e14_raw             NUMERIC(12, 3),     -- 自来水瞬时补水 (t/h)
    e14_clean           NUMERIC(12, 3),
    e16_raw             NUMERIC(12, 2),     -- 水箱水位 (mm)
    zone_heat_sum_e12   NUMERIC(12, 3),     -- 下属分区二次网热量Σe12 (GJ/h)
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_station_15min UNIQUE (sample_bucket, station_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_station_15min_hour_station
    ON smart_heating_platform.fact_station_15min (biz_hour, station_id);


-- -----------------------------------------------------------------------------
-- 5. 换热站 小时精算断面表 (fact_station_hourly)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_station_hourly (
    id                  BIGSERIAL PRIMARY KEY,
    biz_hour            TIMESTAMPTZ NOT NULL,
    station_id          VARCHAR(64) NOT NULL REFERENCES smart_heating_platform.dict_heating_station(station_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    sample_count        SMALLINT NOT NULL DEFAULT 0,
    online              BOOLEAN NOT NULL DEFAULT TRUE,
    source_update_time  TIMESTAMPTZ,
    -- 瞬时代表断面 (清洗后供阳面展示) + 原始留痕
    e1_raw              NUMERIC(12, 3),
    e1_clean            NUMERIC(12, 3),
    e3_raw              NUMERIC(10, 2),
    e3_clean            NUMERIC(10, 2),
    e4_raw              NUMERIC(10, 2),
    e4_clean            NUMERIC(10, 2),
    e7_raw              NUMERIC(10, 4),
    e7_clean            NUMERIC(10, 4),
    e8_raw              NUMERIC(10, 4),
    e8_clean            NUMERIC(10, 4),
    e11_raw             NUMERIC(12, 3),
    e11_clean           NUMERIC(12, 3),
    e13_raw             NUMERIC(12, 3),
    e14_raw             NUMERIC(12, 3),
    e14_clean           NUMERIC(12, 3),
    e16_raw             NUMERIC(12, 2),
    zone_heat_sum_e12   NUMERIC(12, 3),
    heat_balance_diff_pct NUMERIC(10, 2),
    -- 整点线性插值累计表底 (来自 /hrz_ls_zb/ f220/f221/f254/f253)
    tot_j               NUMERIC(16, 4),     -- 整点一网累计热量表底 (GJ)
    tot_f               NUMERIC(16, 4),     -- 整点一网累计流量表底 (t)
    tot_water_f254      NUMERIC(16, 4),     -- 整点累计补水表底 (t)
    tot_elec_f253       NUMERIC(16, 4),     -- 整点累计电量表底 (kWh)
    -- 本小时真实累计耗量 (优先表底差值，兜底为15分钟梯形积分)
    hour_heat_gj        NUMERIC(14, 4),
    hour_heat_source    VARCHAR(32) NOT NULL DEFAULT 'INTEGRAL_15M',
    hour_flow_t         NUMERIC(14, 4),
    hour_flow_source    VARCHAR(32) NOT NULL DEFAULT 'INTEGRAL_15M',
    hour_water_t        NUMERIC(14, 4),
    hour_water_source   VARCHAR(32) NOT NULL DEFAULT 'INTEGRAL_15M',
    hour_elec_kwh       NUMERIC(14, 4),
    hour_elec_source    VARCHAR(32) NOT NULL DEFAULT 'NONE',
    -- 可审计清洗标记
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    audit_note          TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_station_hourly UNIQUE (biz_hour, station_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_station_hourly_hour
    ON smart_heating_platform.fact_station_hourly (biz_hour);


-- -----------------------------------------------------------------------------
-- 6. 二次网分区 15 分钟采样表 (fact_zone_15min) & 小时精算表 (fact_zone_hourly)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_zone_15min (
    id                  BIGSERIAL PRIMARY KEY,
    sample_bucket       TIMESTAMPTZ NOT NULL,
    biz_hour            TIMESTAMPTZ NOT NULL,
    secondary_zone_id   VARCHAR(32) NOT NULL REFERENCES smart_heating_platform.dict_secondary_zone(secondary_zone_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    station_id          VARCHAR(64) NOT NULL REFERENCES smart_heating_platform.dict_heating_station(station_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    e2_raw              NUMERIC(12, 3),     -- 二次网瞬时流量 (t/h)
    e2_clean            NUMERIC(12, 3),
    e5_raw              NUMERIC(10, 2),     -- 二次网供水温度 (℃)
    e5_clean            NUMERIC(10, 2),
    e6_raw              NUMERIC(10, 2),     -- 二次网回水温度 (℃)
    e6_clean            NUMERIC(10, 2),
    e9_raw              NUMERIC(10, 4),     -- 二次网供水压力 (MPa)
    e9_clean            NUMERIC(10, 4),
    e10_raw             NUMERIC(10, 4),     -- 二次网回水压力 (MPa)
    e10_clean           NUMERIC(10, 4),
    e12_raw             NUMERIC(12, 3),     -- 二次网瞬时热量 (仅审计比对)
    e15_raw             NUMERIC(12, 3),     -- 二次网瞬时补水 (t/h)
    e15_clean           NUMERIC(12, 3),
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_zone_15min UNIQUE (sample_bucket, secondary_zone_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_zone_15min_hour_zone
    ON smart_heating_platform.fact_zone_15min (biz_hour, secondary_zone_id);


CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_zone_hourly (
    id                  BIGSERIAL PRIMARY KEY,
    biz_hour            TIMESTAMPTZ NOT NULL,
    secondary_zone_id   VARCHAR(32) NOT NULL REFERENCES smart_heating_platform.dict_secondary_zone(secondary_zone_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    station_id          VARCHAR(64) NOT NULL REFERENCES smart_heating_platform.dict_heating_station(station_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    sample_count        SMALLINT NOT NULL DEFAULT 0,
    e2_raw              NUMERIC(12, 3),
    e2_clean            NUMERIC(12, 3),
    e5_raw              NUMERIC(10, 2),
    e5_clean            NUMERIC(10, 2),
    e6_raw              NUMERIC(10, 2),
    e6_clean            NUMERIC(10, 2),
    e9_raw              NUMERIC(10, 4),
    e9_clean            NUMERIC(10, 4),
    e10_raw             NUMERIC(10, 4),
    e10_clean           NUMERIC(10, 4),
    e12_raw             NUMERIC(12, 3),
    e15_raw             NUMERIC(12, 3),
    e15_clean           NUMERIC(12, 3),
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_zone_hourly UNIQUE (biz_hour, secondary_zone_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_zone_hourly_hour_station
    ON smart_heating_platform.fact_zone_hourly (biz_hour, station_id);


-- -----------------------------------------------------------------------------
-- 7. 居民室温小时断面表 (fact_temp_hourly)
--    注：按约定不对 temp_device_id 加硬性外键，以包容源站新增未入账3户，
--        并通过 is_registered 标记实现“阳面剔除、阴面保留提醒”。
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_temp_hourly (
    id                  BIGSERIAL PRIMARY KEY,
    biz_hour            TIMESTAMPTZ NOT NULL,
    temp_device_id      VARCHAR(32) NOT NULL,
    station_id          VARCHAR(64) REFERENCES smart_heating_platform.dict_heating_station(station_id)
                            ON UPDATE CASCADE ON DELETE SET NULL,
    is_registered       BOOLEAN NOT NULL DEFAULT TRUE,
    village_name        VARCHAR(128),
    station_name_raw    VARCHAR(128),
    zdxh                VARCHAR(32),
    temp_raw            NUMERIC(8, 2),
    temp_clean          NUMERIC(8, 2),
    upload_time         TIMESTAMPTZ,
    is_online_valid     BOOLEAN NOT NULL DEFAULT TRUE,   -- 阳面有效达标样本标记 (已入账 & 未掉线>7天 & 室温正常)
    remark_snapshot     TEXT,
    fault_tag           VARCHAR(64),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_temp_hourly UNIQUE (biz_hour, temp_device_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_temp_hourly_hour_station
    ON smart_heating_platform.fact_temp_hourly (biz_hour, station_id);


-- -----------------------------------------------------------------------------
-- 8. 商业用户日耗量表 (fact_merchant_daily)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_merchant_daily (
    id                  BIGSERIAL PRIMARY KEY,
    biz_date            DATE NOT NULL,
    merchant_id         VARCHAR(64) NOT NULL REFERENCES smart_heating_platform.dict_merchant(merchant_id)
                            ON UPDATE CASCADE ON DELETE RESTRICT,
    daily_consumption   NUMERIC(14, 4),
    daily_unit_heat     NUMERIC(14, 4),
    raw_payload         JSONB,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_merchant_daily UNIQUE (biz_date, merchant_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_merchant_daily_date
    ON smart_heating_platform.fact_merchant_daily (biz_date);


-- -----------------------------------------------------------------------------
-- 9. 阴面异常自动巡检与权责督办表 (fact_fault_ticket)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_fault_ticket (
    ticket_id           BIGSERIAL PRIMARY KEY,
    biz_hour            TIMESTAMPTZ NOT NULL,
    entity_type         VARCHAR(32) NOT NULL,   -- UPSTREAM | STATION | SECONDARY_ZONE | TEMP_DEVICE | MERCHANT
    entity_id           VARCHAR(128) NOT NULL,
    entity_name         VARCHAR(128) NOT NULL,
    fault_code          VARCHAR(64) NOT NULL,   -- SENSOR_OUT_OF_RANGE | COMM_OFFLINE | HEAT_IMBALANCE | TEMP_INVERSION | METER_JUMP | SOFTWARE_DEFECT
    owner_party         VARCHAR(32) NOT NULL,   -- RESEARCH_INSTITUTE | UNIVERSITY_SOFTWARE | SHARED
    raw_value_text      TEXT,
    clean_strategy      TEXT,
    rule_desc           TEXT NOT NULL,
    status              VARCHAR(24) NOT NULL DEFAULT 'OPEN', -- OPEN | ACKNOWLEDGED | RESOLVED
    handler_note        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_fault_ticket UNIQUE (biz_hour, entity_type, entity_id, fault_code)
);

COMMENT ON TABLE smart_heating_platform.fact_fault_ticket IS '阴面视图：自动化清洗拦截异常与三方权责督办清单';
CREATE INDEX IF NOT EXISTS idx_fact_fault_ticket_filter
    ON smart_heating_platform.fact_fault_ticket (biz_hour DESC, owner_party, status);


-- -----------------------------------------------------------------------------
-- 10. 商业用户 15 分钟采样明细表 (fact_merchant_15min)
--     注：source_name 不加硬外键以留痕源站多出的 4 户未入账测试商户
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_merchant_15min (
    id                  BIGSERIAL PRIMARY KEY,
    sample_bucket       TIMESTAMPTZ NOT NULL,
    biz_hour            TIMESTAMPTZ NOT NULL,
    merchant_id         VARCHAR(64) REFERENCES smart_heating_platform.dict_merchant(merchant_id)
                            ON UPDATE CASCADE ON DELETE SET NULL,
    source_name         VARCHAR(128) NOT NULL,
    is_registered       BOOLEAN NOT NULL DEFAULT TRUE,
    online              BOOLEAN NOT NULL DEFAULT TRUE,
    flow_raw            NUMERIC(12, 3),     -- 一次供水流量 (t/h)
    flow_clean          NUMERIC(12, 3),
    return_flow_raw     NUMERIC(12, 3),     -- 一次回水流量 (t/h)
    temp_sup_raw        NUMERIC(10, 2),     -- 一次供水温度 (℃)
    temp_sup_clean      NUMERIC(10, 2),
    temp_ret_raw        NUMERIC(10, 2),     -- 一次回水温度 (℃)
    temp_ret_clean      NUMERIC(10, 2),
    pres_sup_raw        NUMERIC(10, 4),     -- 一次供水压力 (MPa)
    pres_sup_clean      NUMERIC(10, 4),
    pres_ret_raw        NUMERIC(10, 4),     -- 一次回水压力 (MPa)
    pres_ret_clean      NUMERIC(10, 4),
    heat_raw            NUMERIC(12, 3),     -- 一次瞬时热量 (GJ/h)
    heat_clean          NUMERIC(12, 3),
    valve_open          NUMERIC(8, 2),      -- 阀门开度 (%)
    valve_set           NUMERIC(8, 2),      -- 设定开度 (%)
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_merchant_15min UNIQUE (sample_bucket, source_name)
);

CREATE INDEX IF NOT EXISTS idx_fact_merchant_15min_hour
    ON smart_heating_platform.fact_merchant_15min (biz_hour, merchant_id);


-- -----------------------------------------------------------------------------
-- 11. 商业用户 小时精算表 (fact_merchant_hourly)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.fact_merchant_hourly (
    id                  BIGSERIAL PRIMARY KEY,
    biz_hour            TIMESTAMPTZ NOT NULL,
    merchant_id         VARCHAR(64) REFERENCES smart_heating_platform.dict_merchant(merchant_id)
                            ON UPDATE CASCADE ON DELETE SET NULL,
    source_name         VARCHAR(128) NOT NULL,
    is_registered       BOOLEAN NOT NULL DEFAULT TRUE,
    sample_count        SMALLINT NOT NULL DEFAULT 0,
    online              BOOLEAN NOT NULL DEFAULT TRUE,
    flow_raw            NUMERIC(12, 3),
    flow_clean          NUMERIC(12, 3),
    return_flow_raw     NUMERIC(12, 3),
    temp_sup_raw        NUMERIC(10, 2),
    temp_sup_clean      NUMERIC(10, 2),
    temp_ret_raw        NUMERIC(10, 2),
    temp_ret_clean      NUMERIC(10, 2),
    pres_sup_raw        NUMERIC(10, 4),
    pres_sup_clean      NUMERIC(10, 4),
    pres_ret_raw        NUMERIC(10, 4),
    pres_ret_clean      NUMERIC(10, 4),
    heat_raw            NUMERIC(12, 3),
    heat_clean          NUMERIC(12, 3),
    valve_open          NUMERIC(8, 2),
    valve_set           NUMERIC(8, 2),
    hour_heat_gj        NUMERIC(14, 4),     -- 基于15分钟/5分钟样本梯形积分的小时供热量(GJ)
    hour_heat_source    VARCHAR(32) NOT NULL DEFAULT 'INTEGRAL_15M',
    hour_flow_t         NUMERIC(14, 4),     -- 基于15分钟/5分钟样本梯形积分的小时流量(t)
    hour_flow_source    VARCHAR(32) NOT NULL DEFAULT 'INTEGRAL_15M',
    value_source        VARCHAR(32) NOT NULL DEFAULT 'REAL',
    fault_tag           VARCHAR(64),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fact_merchant_hourly UNIQUE (biz_hour, source_name)
);

CREATE INDEX IF NOT EXISTS idx_fact_merchant_hourly_hour
    ON smart_heating_platform.fact_merchant_hourly (biz_hour, merchant_id);

COMMIT;
