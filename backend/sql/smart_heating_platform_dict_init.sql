-- ==============================================================================
-- 智慧供热管理平台 v2.0 旁路分析系统 —— 标准基础台账字典库初始化脚本
-- 适用数据库：PostgreSQL 12+
-- Schema: smart_heating_platform
-- 数据来源：configs/成果_智慧供热平台基础台账.xlsx
-- 说明：
-- 1. 创建独立 schema `smart_heating_platform` 存放全网八大统计主体字典表（全部以 `dict_` 为前缀）；
-- 2. 去除台账表头中的“主键”“外键”中文前缀，保留标准英文列名并严格建立物理 PRIMARY KEY 与 FOREIGN KEY 约束；
-- 3. `center_id` / `main_network_id` / `branch_network_id` 采用 INTEGER 数值类型；
--    `station_id` / `merchant_id`（32位哈希）、`secondary_zone_id`（SZ0001~SZ0580）与
--    `temp_device_id`（15~20位 IMEI/ICCID，超过 BIGINT 与 JS 安全整数范围）采用 VARCHAR；
-- 4. 各主体同步保留 `name`（对外展示标准名）与 `name_raw`（源系统原始名）。
-- ==============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 0. 创建专用 Schema
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS smart_heating_platform;
COMMENT ON SCHEMA smart_heating_platform IS '智慧供热管理平台旁路分析与质检系统专用 schema（含八大主体标准字典与后续运行时序数据）';


-- -----------------------------------------------------------------------------
-- 1. 服务中心字典表（逻辑主体 · 9 个）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_service_center (
    center_id   INTEGER PRIMARY KEY,
    name        VARCHAR(64) NOT NULL UNIQUE,
    name_raw    VARCHAR(64) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE smart_heating_platform.dict_service_center IS '主体6：服务中心标准字典表（9个行政管辖服务中心）';
COMMENT ON COLUMN smart_heating_platform.dict_service_center.center_id IS '服务中心主键ID（沿用源系统 60~68）';
COMMENT ON COLUMN smart_heating_platform.dict_service_center.name IS '服务中心标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_service_center.name_raw IS '源系统原始服务中心名称';
COMMENT ON COLUMN smart_heating_platform.dict_service_center.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_service_center.updated_at IS '记录最后更新时间';


-- -----------------------------------------------------------------------------
-- 2. 主干网字典表（逻辑主体 · 15 条）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_main_network (
    main_network_id INTEGER PRIMARY KEY,
    name            VARCHAR(64) NOT NULL UNIQUE,
    name_raw        VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE smart_heating_platform.dict_main_network IS '主体7：主干热源/主干网标准字典表（15条物理干线）';
COMMENT ON COLUMN smart_heating_platform.dict_main_network.main_network_id IS '主干网主键ID（沿用源系统 2~16）';
COMMENT ON COLUMN smart_heating_platform.dict_main_network.name IS '主干网标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_main_network.name_raw IS '源系统原始主干网名称';
COMMENT ON COLUMN smart_heating_platform.dict_main_network.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_main_network.updated_at IS '记录最后更新时间';


-- -----------------------------------------------------------------------------
-- 3. 支线网字典表（逻辑主体 · 41 条）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_branch_network (
    branch_network_id   INTEGER PRIMARY KEY,
    main_network_id     INTEGER NOT NULL,
    name                VARCHAR(64) NOT NULL,
    name_raw            VARCHAR(64) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dict_branch_network_main_network
        FOREIGN KEY (main_network_id)
        REFERENCES smart_heating_platform.dict_main_network (main_network_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

COMMENT ON TABLE smart_heating_platform.dict_branch_network IS '主体8：支线网（二级分支）标准字典表（41条支线）';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.branch_network_id IS '支线网主键ID（沿用源系统 17~57）';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.main_network_id IS '外键：所属主干网ID';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.name IS '支线网标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.name_raw IS '源系统原始支线网名称';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_branch_network.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_branch_network_main_id
    ON smart_heating_platform.dict_branch_network (main_network_id);


-- -----------------------------------------------------------------------------
-- 4. 换热站字典表（物理主体 · 242 座，已剔除 11 个全空冗余字段）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_heating_station (
    station_id          VARCHAR(64) PRIMARY KEY,
    center_id           INTEGER NOT NULL,
    branch_network_id   INTEGER NOT NULL,
    name                VARCHAR(128) NOT NULL,
    name_raw            VARCHAR(128) NOT NULL,
    rd_code             VARCHAR(32) NOT NULL UNIQUE,
    covered_area        NUMERIC(14, 2),
    rdfz                VARCHAR(64) NOT NULL,
    rdry                VARCHAR(64) NOT NULL,
    rdss                VARCHAR(32) NOT NULL,
    latitude            NUMERIC(12, 8),
    longitude           NUMERIC(12, 8),
    first_run_time      VARCHAR(32),
    heating_medium      SMALLINT,
    heat_transfer_mode  SMALLINT,
    power_supply_mode   SMALLINT,
    run_mode            SMALLINT,
    jlzq                SMALLINT,
    sfzz                SMALLINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dict_heating_station_center
        FOREIGN KEY (center_id)
        REFERENCES smart_heating_platform.dict_service_center (center_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_dict_heating_station_branch_network
        FOREIGN KEY (branch_network_id)
        REFERENCES smart_heating_platform.dict_branch_network (branch_network_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT chk_dict_heating_station_covered_area_nonnegative
        CHECK (covered_area IS NULL OR covered_area >= 0)
);

COMMENT ON TABLE smart_heating_platform.dict_heating_station IS '主体2：换热站（全站及一次网）标准字典表（242座，已丢弃11个全空冗余字段）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.station_id IS '换热站主键ID（源系统32位哈希ID）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.center_id IS '外键：所属服务中心ID';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.branch_network_id IS '外键：所属支线网ID';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.name IS '换热站标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.name_raw IS '源系统原始换热站名称';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.rd_code IS '源系统MySQL历史分表名（如 Data0521）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.covered_area IS '在网供热面积（平方米；32座缺失待补录）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.rdfz IS '经营核算维度：9大热源大网口径';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.rdry IS '经营核算维度：供热介质类别';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.rdss IS '经营核算维度：产权归属（股份/集团）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.latitude IS '站点纬度';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.longitude IS '站点经度';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.first_run_time IS '首次投运时间（YYYY-M）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.heating_medium IS '源系统热媒编码（0/1/2）';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.heat_transfer_mode IS '换热方式编码';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.power_supply_mode IS '供电方式编码';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.run_mode IS '运行模式编码';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.jlzq IS '计量周期编码';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.sfzz IS '是否自管/直管标志编码';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_heating_station.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_heating_station_center_id
    ON smart_heating_platform.dict_heating_station (center_id);

CREATE INDEX IF NOT EXISTS idx_dict_heating_station_branch_id
    ON smart_heating_platform.dict_heating_station (branch_network_id);

CREATE INDEX IF NOT EXISTS idx_dict_heating_station_name
    ON smart_heating_platform.dict_heating_station (name);

CREATE INDEX IF NOT EXISTS idx_dict_heating_station_rdfz
    ON smart_heating_platform.dict_heating_station (rdfz);


-- -----------------------------------------------------------------------------
-- 5. 换热站二次网分区字典表（物理主体 · 580 个）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_secondary_zone (
    secondary_zone_id   VARCHAR(32) PRIMARY KEY,
    station_id          VARCHAR(64) NOT NULL,
    zone_name           VARCHAR(64) NOT NULL,
    is_online           BOOLEAN NOT NULL DEFAULT TRUE,
    online_status_raw   VARCHAR(16) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dict_secondary_zone_station
        FOREIGN KEY (station_id)
        REFERENCES smart_heating_platform.dict_heating_station (station_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT uq_dict_secondary_zone_station_name
        UNIQUE (station_id, zone_name)
);

COMMENT ON TABLE smart_heating_platform.dict_secondary_zone IS '主体3：换热站二次网供热分区标准字典表（580个分区，5座站无分区）';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.secondary_zone_id IS '二次网分区主键ID（固定编号 SZ0001~SZ0580）';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.station_id IS '外键：所属换热站ID';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.zone_name IS '二次网分区名称（如 低区/高区/地热低区，同站内唯一）';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.is_online IS '台账基准是否在线（TRUE=在线, FALSE=离线）';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.online_status_raw IS '台账原始在线状态文本（在线/离线）';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_secondary_zone.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_secondary_zone_station_id
    ON smart_heating_platform.dict_secondary_zone (station_id);


-- -----------------------------------------------------------------------------
-- 6. 居民室温测温用户字典表（物理主体 · 2,097 户）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_temp_device (
    temp_device_id      VARCHAR(32) PRIMARY KEY,
    station_id          VARCHAR(64) NOT NULL,
    name                VARCHAR(128) NOT NULL,
    terminal_model      VARCHAR(32) NOT NULL,
    install_batch       VARCHAR(64),
    remark              TEXT,
    station_name        VARCHAR(128) NOT NULL,
    station_name_raw    VARCHAR(128) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dict_temp_device_station
        FOREIGN KEY (station_id)
        REFERENCES smart_heating_platform.dict_heating_station (station_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

COMMENT ON TABLE smart_heating_platform.dict_temp_device IS '主体5：居民室温测温终端标准字典表（2,097户真实测点，已完成100%换热站归口）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.temp_device_id IS '测温终端硬件主键ID（IMEI/ICCID，15~20位字符串，避免64位整数溢出）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.station_id IS '外键：归口后的标准换热站ID';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.name IS '居民精确门牌地址（对应源接口 village_name）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.terminal_model IS '测温终端硬件型号（T102/T401/TN801）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.install_batch IS '安装批次与终端供电类型';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.remark IS '现场巡检备注（含停供/丢表/靠窗等关键状态）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.station_name IS '归口后的标准换热站名称';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.station_name_raw IS '源系统接口返回的原始换热站名称（含15组非标别名）';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_temp_device.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_temp_device_station_id
    ON smart_heating_platform.dict_temp_device (station_id);

CREATE INDEX IF NOT EXISTS idx_dict_temp_device_station_name_raw
    ON smart_heating_platform.dict_temp_device (station_name_raw);

CREATE INDEX IF NOT EXISTS idx_dict_temp_device_name
    ON smart_heating_platform.dict_temp_device (name);


-- -----------------------------------------------------------------------------
-- 7. 商业用户/商户字典表（物理主体 · 464 户）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_merchant (
    merchant_id         VARCHAR(64) PRIMARY KEY,
    branch_network_id   INTEGER NOT NULL,
    name                VARCHAR(128) NOT NULL,
    name_raw            VARCHAR(128) NOT NULL,
    table_name          VARCHAR(32) NOT NULL UNIQUE,
    merchant_type       SMALLINT,
    rdfz                VARCHAR(64),
    rdry                VARCHAR(64),
    rdss                VARCHAR(32),
    rdjg                VARCHAR(32),
    rdgz                VARCHAR(64),
    latitude            NUMERIC(12, 8),
    longitude           NUMERIC(12, 8),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_dict_merchant_branch_network
        FOREIGN KEY (branch_network_id)
        REFERENCES smart_heating_platform.dict_branch_network (branch_network_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

COMMENT ON TABLE smart_heating_platform.dict_merchant IS '主体4：商业用户/商户标准字典表（464户；台账仅挂接支线网，无center_id归属）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.merchant_id IS '商户主键ID（源系统32位哈希ID）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.branch_network_id IS '外键：所属支线网ID';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.name IS '商户标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.name_raw IS '源系统原始商户名称';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.table_name IS '源系统MySQL商业用户历史分表名（如 F021/A004）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.merchant_type IS '源系统商户类型编码（type）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.rdfz IS '经营核算维度：9大热源大网（国泰大厦/鸿霖大厦待补录）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.rdry IS '经营核算维度：供热介质';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.rdss IS '经营核算维度：产权归属';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.rdjg IS '经营核算维度：商户价格分类（香洲酒店等3户待补录）';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.rdgz IS '经营核算维度：改造批次';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.latitude IS '商户纬度';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.longitude IS '商户经度';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_merchant.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_merchant_branch_id
    ON smart_heating_platform.dict_merchant (branch_network_id);

CREATE INDEX IF NOT EXISTS idx_dict_merchant_rdfz
    ON smart_heating_platform.dict_merchant (rdfz);


-- -----------------------------------------------------------------------------
-- 8. 热源/首站/网口核心监测点字典表（物理主体 · 82 点，含预留主键字段）
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS smart_heating_platform.dict_upstream_point (
    point_id                    SERIAL PRIMARY KEY,
    heat_source_id              VARCHAR(64),
    initial_heating_station_id  VARCHAR(64),
    measurement_point_id        VARCHAR(64) UNIQUE,
    source_page                 VARCHAR(64) NOT NULL,
    category                    VARCHAR(32) NOT NULL,
    sub_category                VARCHAR(64),
    data_zone                   VARCHAR(32) NOT NULL,
    name                        VARCHAR(128) NOT NULL UNIQUE,
    name_raw                    VARCHAR(128) NOT NULL,
    source_name                 VARCHAR(128) NOT NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dict_upstream_point_zone_source
        UNIQUE (data_zone, source_name)
);

COMMENT ON TABLE smart_heating_platform.dict_upstream_point IS '主体1：上游热源/首站/网口核心监测点字典表（82点工况一览映射，预留标准编码字段）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.point_id IS '自增代理主键（表8暂无源系统编码时用于唯一标识）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.heat_source_id IS '预留字段：热源主体ID（待后续补齐）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.initial_heating_station_id IS '预留字段：首站主体ID（待后续补齐）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.measurement_point_id IS '预留字段：监测点标准编码（待后续补齐）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.source_page IS '来源页面表名（工况一览_表1~表4）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.category IS '监测点类别（电厂/首站/网口）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.sub_category IS '子类（如北海热电厂/香海热电厂）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.data_zone IS '源系统后端内存字典名（dc_dict/sz_dict/yw2_dict/yw_dict/sh_dict）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.name IS '监测点标准名称（对外展示）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.name_raw IS '页面原始显示名称';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.source_name IS '源系统接口采集名称（采集ETL映射键值）';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.created_at IS '记录创建时间';
COMMENT ON COLUMN smart_heating_platform.dict_upstream_point.updated_at IS '记录最后更新时间';

CREATE INDEX IF NOT EXISTS idx_dict_upstream_point_category
    ON smart_heating_platform.dict_upstream_point (category);


-- -----------------------------------------------------------------------------
-- 9. 辅助视图：测温用户非标站名别名归一化字典视图（派生自 dict_temp_device）
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW smart_heating_platform.v_temp_station_alias_map AS
SELECT
    station_name_raw,
    station_id,
    station_name,
    COUNT(*) AS device_count
FROM smart_heating_platform.dict_temp_device
WHERE station_name_raw <> station_name
GROUP BY station_name_raw, station_id, station_name
ORDER BY station_name_raw;

COMMENT ON VIEW smart_heating_platform.v_temp_station_alias_map IS '自动派生的15组测温终端非标换热站别名→标准station_id映射视图';

COMMIT;
