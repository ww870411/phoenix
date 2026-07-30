-- tube 项目第一阶段数据库初始化脚本
-- 适用数据库：PostgreSQL
-- 说明：
-- 1. 本脚本会创建独立 schema：tube
-- 2. 所有 tube 项目业务表均放置在 tube schema 下
-- 3. 本脚本以 V5.1 确认版流程计划为准

BEGIN;

CREATE SCHEMA IF NOT EXISTS tube;

COMMENT ON SCHEMA tube IS '保温管物流链管理项目专用 schema';


CREATE TABLE IF NOT EXISTS tube.tube_daily_plan (
    id BIGSERIAL PRIMARY KEY,
    plan_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    plan_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    filled_by VARCHAR(128),
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_daily_plan_plan_qty_nonnegative
        CHECK (plan_qty >= 0)
);

COMMENT ON TABLE tube.tube_daily_plan IS '每日计划长表';
COMMENT ON COLUMN tube.tube_daily_plan.plan_date IS '计划日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_plan.plan_qty IS '计划使用量';
COMMENT ON COLUMN tube.tube_daily_plan.filled_by IS '填报人，首版为现场负责人';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_plan_date_station_model
    ON tube.tube_daily_plan (plan_date, section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_station_date
    ON tube.tube_daily_plan (section_1_id, plan_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_plan_pipe_model_date
    ON tube.tube_daily_plan (pipe_model_id, plan_date);

CREATE TABLE IF NOT EXISTS tube.tube_delivery (
    id BIGSERIAL PRIMARY KEY,
    supply_entity_id VARCHAR(64) NOT NULL,
    order_no VARCHAR(64),
    shipment_no VARCHAR(64),
    vehicle_plate_no VARCHAR(32),
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    shipped_qty NUMERIC(18, 2) NOT NULL,
    arrived_qty NUMERIC(18, 2),
    received_qty NUMERIC(18, 2),
    shipped_at TIMESTAMPTZ NOT NULL,
    ship_contact_name VARCHAR(128),
    ship_contact_phone VARCHAR(64),
    ship_remark TEXT,
    arrived_confirm_by VARCHAR(128),
    arrived_confirm_at TIMESTAMPTZ,
    arrived_remark TEXT,
    received_confirm_by VARCHAR(128),
    received_confirm_at TIMESTAMPTZ,
    received_remark TEXT,
    warehouse_confirm_by VARCHAR(128),
    warehouse_confirm_at TIMESTAMPTZ,
    warehouse_remark TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_arrival',
    abnormal_flag BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_by VARCHAR(128),
    cancel_at TIMESTAMPTZ,
    cancel_reason TEXT,
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    diff_approve_by VARCHAR(128),
    diff_approve_at TIMESTAMPTZ,
    diff_approve_remark TEXT,
    is_timeout_receive BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_tube_delivery_shipped_qty_positive
        CHECK (shipped_qty > 0),
    CONSTRAINT chk_tube_delivery_arrived_qty_range
        CHECK (arrived_qty IS NULL OR (arrived_qty >= 0 AND arrived_qty <= shipped_qty)),
    CONSTRAINT chk_tube_delivery_received_qty_range
        CHECK (
            received_qty IS NULL OR (
                received_qty >= 0
                AND received_qty <= COALESCE(arrived_qty, shipped_qty)
            )
        ),
    CONSTRAINT chk_tube_delivery_status
        CHECK (
            status IN (
                'pending_arrival',
                'cancelled',
                'pending_receive',
                'pending_warehouse',
                'completed',
                'pending_diff_approve'
            )
        )
);

COMMENT ON TABLE tube.tube_delivery IS '发货、到货、施工接收、库管确认生命周期主表';
COMMENT ON COLUMN tube.tube_delivery.supply_entity_id IS '供给主体 ID，对应 tube_config.json 中 supply_entities';
COMMENT ON COLUMN tube.tube_delivery.order_no IS '订单号，由系统生成并落库，用于单条发货记录的展示、检索与统计';
COMMENT ON COLUMN tube.tube_delivery.shipment_no IS '运输车次号，由系统自动生成，用于同一车次发货记录的筛选与分组展示';
COMMENT ON COLUMN tube.tube_delivery.vehicle_plate_no IS '车牌号，按运输车次维度选填；同一 shipment_no 下应保持一致';
COMMENT ON COLUMN tube.tube_delivery.section_1_id IS '需求主体 ID';
COMMENT ON COLUMN tube.tube_delivery.pipe_model_id IS '保温管型号 ID';
COMMENT ON COLUMN tube.tube_delivery.shipped_qty IS '发货数量';
COMMENT ON COLUMN tube.tube_delivery.arrived_qty IS '到货确认数量，允许小于发货数量';
COMMENT ON COLUMN tube.tube_delivery.received_qty IS '施工接收数量，允许小于到货确认数量';
COMMENT ON COLUMN tube.tube_delivery.status IS '状态：pending_arrival/cancelled/pending_receive/pending_warehouse/completed/pending_diff_approve';
COMMENT ON COLUMN tube.tube_delivery.abnormal_flag IS '是否异常';
COMMENT ON COLUMN tube.tube_delivery.cancel_reason IS '发货撤销原因，仅允许在已发货待到货状态使用';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_by IS '现场负责人（Site Manager）差异审批的审批人账号';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_at IS '差异审批的具体处理时间戳';
COMMENT ON COLUMN tube.tube_delivery.diff_approve_remark IS '差异审批的审批意见与驳回备注';
COMMENT ON COLUMN tube.tube_delivery.is_timeout_receive IS '是否因到货确认 12 小时施工未签收触发系统自动强制接收标记';

CREATE INDEX IF NOT EXISTS idx_tube_delivery_status
    ON tube.tube_delivery (status);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_station
    ON tube.tube_delivery (section_1_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_supply_entity
    ON tube.tube_delivery (supply_entity_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_delivery_order_no
    ON tube.tube_delivery (order_no);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_shipment_no
    ON tube.tube_delivery (shipment_no);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_pipe_model
    ON tube.tube_delivery (pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_shipped_at
    ON tube.tube_delivery (shipped_at);

CREATE INDEX IF NOT EXISTS idx_tube_delivery_station_status
    ON tube.tube_delivery (section_1_id, status);

CREATE TABLE IF NOT EXISTS tube.tube_daily_usage (
    id BIGSERIAL PRIMARY KEY,
    usage_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    usage_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    loss_qty NUMERIC(18, 2) NOT NULL DEFAULT 0,
    filled_by VARCHAR(128),
    filled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tube_daily_usage_usage_qty_nonnegative
        CHECK (usage_qty >= 0),
    CONSTRAINT chk_tube_daily_usage_loss_qty_nonnegative
        CHECK (loss_qty >= 0)
);

COMMENT ON TABLE tube.tube_daily_usage IS '每日实际使用长表';
COMMENT ON COLUMN tube.tube_daily_usage.usage_date IS '实际使用日期，按自然日保存';
COMMENT ON COLUMN tube.tube_daily_usage.usage_qty IS '实际使用量';
COMMENT ON COLUMN tube.tube_daily_usage.filled_by IS '填报人，首版为现场负责人';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_daily_usage_date_station_model
    ON tube.tube_daily_usage (usage_date, section_1_id, pipe_model_id);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_station_date
    ON tube.tube_daily_usage (section_1_id, usage_date);

CREATE INDEX IF NOT EXISTS idx_tube_daily_usage_pipe_model_date
    ON tube.tube_daily_usage (pipe_model_id, usage_date);

CREATE TABLE IF NOT EXISTS tube.tube_inventory_adjustment (
    id BIGSERIAL PRIMARY KEY,
    adjust_date DATE NOT NULL,
    section_1_id VARCHAR(64) NOT NULL,
    pipe_model_id VARCHAR(64) NOT NULL,
    adjust_qty NUMERIC(18, 2) NOT NULL,
    adjust_type VARCHAR(32) NOT NULL,
    reason TEXT NOT NULL,
    operated_by VARCHAR(128),
    operated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    remark TEXT,
    CONSTRAINT chk_tube_inventory_adjustment_nonzero
        CHECK (adjust_qty <> 0)
);

COMMENT ON TABLE tube.tube_inventory_adjustment IS '库存调整预留表';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_qty IS '调整数量，正数增加，负数减少';
COMMENT ON COLUMN tube.tube_inventory_adjustment.adjust_type IS '调整类型，如盘盈、盘亏、退库、调剂、破损、纠错';
COMMENT ON COLUMN tube.tube_inventory_adjustment.reason IS '调整原因';

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_station_date
    ON tube.tube_inventory_adjustment (section_1_id, adjust_date);

CREATE INDEX IF NOT EXISTS idx_tube_inventory_adjustment_pipe_model_date
    ON tube.tube_inventory_adjustment (pipe_model_id, adjust_date);


-- =========================================================================
-- 大连主城区气象数据存储表 (2026-05-28 升级)
-- 包含日级聚合与逐小时温度记录，用以优化天气决策沙盘的加载性能
-- =========================================================================

CREATE TABLE IF NOT EXISTS tube.tube_weather_daily (
    id BIGSERIAL PRIMARY KEY,
    weather_date DATE NOT NULL,
    weather_code INTEGER NOT NULL DEFAULT 0,
    rain_sum NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    uv_index_max NUMERIC(18, 2) NOT NULL DEFAULT 0.00,
    temp_max NUMERIC(18, 2),
    temp_mean NUMERIC(18, 2),
    temp_min NUMERIC(18, 2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_weather_daily IS '大连主城区日级气象数据及施工决策聚合表';
COMMENT ON COLUMN tube.tube_weather_daily.weather_date IS '气象日期';
COMMENT ON COLUMN tube.tube_weather_daily.weather_code IS 'WMO 天气状态码';
COMMENT ON COLUMN tube.tube_weather_daily.rain_sum IS '日降水总量 (mm)';
COMMENT ON COLUMN tube.tube_weather_daily.uv_index_max IS '最大紫外线指数';
COMMENT ON COLUMN tube.tube_weather_daily.temp_max IS '日内最高气温 (℃)';
COMMENT ON COLUMN tube.tube_weather_daily.temp_mean IS '日内算术平均气温 (℃)';
COMMENT ON COLUMN tube.tube_weather_daily.temp_min IS '日内最低气温 (℃)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_daily_date
    ON tube.tube_weather_daily (weather_date);


CREATE TABLE IF NOT EXISTS tube.tube_weather_hourly (
    id BIGSERIAL PRIMARY KEY,
    weather_date_time TIMESTAMPTZ NOT NULL,
    temperature NUMERIC(18, 2) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_weather_hourly IS '大连主城区逐小时气温原始数据表';
COMMENT ON COLUMN tube.tube_weather_hourly.weather_date_time IS '日期时间粒度 (带时区)';
COMMENT ON COLUMN tube.tube_weather_hourly.temperature IS '逐小时气温 (℃)';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_weather_hourly_datetime
    ON tube.tube_weather_hourly (weather_date_time);


-- =========================================================================
-- 操作审计日志表 (2026-06-15 追加 & 2026-07-30 转移至 logs.tube_operation_logs)
-- =========================================================================

CREATE SCHEMA IF NOT EXISTS logs;

CREATE TABLE IF NOT EXISTS logs.tube_operation_logs (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    operator VARCHAR(100) NOT NULL,
    operator_group VARCHAR(100),
    action_type VARCHAR(50) NOT NULL,
    action_desc TEXT NOT NULL,
    resource_id VARCHAR(100),
    before_value JSONB,
    after_value JSONB,
    client_ip VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_logs_tube_op_operator ON logs.tube_operation_logs(operator);
CREATE INDEX IF NOT EXISTS idx_logs_tube_op_action_type ON logs.tube_operation_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_logs_tube_op_created_at ON logs.tube_operation_logs(created_at DESC);

COMMENT ON TABLE logs.tube_operation_logs IS '保温管供需管理系统操作审计日志表';
COMMENT ON COLUMN logs.tube_operation_logs.operator IS '操作人用户名';
COMMENT ON COLUMN logs.tube_operation_logs.action_type IS '操作动作类型';
COMMENT ON COLUMN logs.tube_operation_logs.action_desc IS '中文业务语义操作描述';
COMMENT ON COLUMN logs.tube_operation_logs.before_value IS '变更前 JSON 快照';
COMMENT ON COLUMN logs.tube_operation_logs.after_value IS '变更后 JSON 快照';


-- =========================================================================
-- GIS 地图标注持久化表 (支持 6 种点位类型与三通分支)
-- =========================================================================

CREATE TABLE IF NOT EXISTS tube.tube_gis (
    id BIGSERIAL PRIMARY KEY,
    project_key VARCHAR(64) NOT NULL DEFAULT 'insulation_pipe_supply_2026',
    marker_type VARCHAR(32) NOT NULL DEFAULT 'weld',
    section_name VARCHAR(128),
    pipeline_name VARCHAR(128) NOT NULL,
    code VARCHAR(64) NOT NULL,
    name VARCHAR(256) NOT NULL,
    lng NUMERIC(12, 6) NOT NULL,
    lat NUMERIC(12, 6) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'passed',
    spec VARCHAR(128),
    remarks TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    parent_code VARCHAR(64),
    created_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by VARCHAR(128),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tube.tube_gis IS '管网焊口、三通、补偿器、弯头、阀门与表计 GIS 地图标注点位存储表';
COMMENT ON COLUMN tube.tube_gis.project_key IS '项目标识';
COMMENT ON COLUMN tube.tube_gis.marker_type IS '标注点位类型: weld (焊口) / meter (表计) / tee (三通) / compensator (补偿器) / elbow (弯头) / valve (阀门)';
COMMENT ON COLUMN tube.tube_gis.section_name IS '工程施工标段名称 (如: 标段1, 标段2)';
COMMENT ON COLUMN tube.tube_gis.pipeline_name IS '管线名称/编号，同一名称管线自动连成轨迹';
COMMENT ON COLUMN tube.tube_gis.code IS '点位唯一编号/标识 (如 W-DL-001 或 T-DL-001)';
COMMENT ON COLUMN tube.tube_gis.name IS '点位名称或地理描述';
COMMENT ON COLUMN tube.tube_gis.lng IS '高德地图精准经度坐标 Lng (保留6位小数)';
COMMENT ON COLUMN tube.tube_gis.lat IS '高德地图精准纬度坐标 Lat (保留6位小数)';
COMMENT ON COLUMN tube.tube_gis.status IS '状态: passed(合格)/pending(待探伤)/failed(待复焊) 或 normal(正常)/warning(预警)/closed(关闭)/open(开启)';
COMMENT ON COLUMN tube.tube_gis.spec IS '关联保温管规格型号 (如 DN400 预制直埋保温管)';
COMMENT ON COLUMN tube.tube_gis.remarks IS '备注说明与质检记录';
COMMENT ON COLUMN tube.tube_gis.sort_order IS '连线/管线节点排序号';
COMMENT ON COLUMN tube.tube_gis.parent_code IS '上级节点编号 (仅焊口设定，指向上一焊口或三通节点；若多个焊口指向同一三通则自动分出多条路线)';
COMMENT ON COLUMN tube.tube_gis.created_at IS '点位数据录入/创建时间';

CREATE UNIQUE INDEX IF NOT EXISTS uq_tube_gis_project_code
    ON tube.tube_gis (project_key, code);

CREATE INDEX IF NOT EXISTS idx_tube_gis_section
    ON tube.tube_gis (project_key, section_name);

CREATE INDEX IF NOT EXISTS idx_tube_gis_pipeline
    ON tube.tube_gis (project_key, pipeline_name);

CREATE INDEX IF NOT EXISTS idx_tube_gis_marker_type
    ON tube.tube_gis (project_key, marker_type);

-- 全新 6 种点位类型与三通分支种子示例数据 (大连香炉礁供暖管网)
INSERT INTO tube.tube_gis 
(project_key, marker_type, section_name, pipeline_name, code, name, lng, lat, status, spec, remarks, sort_order, parent_code)
VALUES
-- 管线 1：香炉礁供暖主干线 (包含表计、阀门、弯头、三通、补偿器及焊口，并在三通处分叉)
('insulation_pipe_supply_2026', 'meter', '标段1', '香炉礁供暖主干线', 'M-DL-001', '香炉礁热电厂出口主热表', 121.602771, 38.927491, 'normal', 'DN400 高精度热网流量计', '厂区主热源出口总监测表计', 1, NULL),
('insulation_pipe_supply_2026', 'valve', '标段1', '香炉礁供暖主干线', 'V-DL-001', '1号主供水切断阀门', 121.603771, 38.927891, 'open', 'DN400 蝶阀电动执行机构', '厂外主供水管网控制阀', 2, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-001', '香炉礁热电厂出厂1号焊口', 121.604771, 38.928491, 'passed', 'DN400 预制直埋保温管', '大连热力施工组：探伤100%合格签认', 3, NULL),
('insulation_pipe_supply_2026', 'elbow', '标段1', '香炉礁供暖主干线', 'E-DL-001', '香工街转角弯头节点', 121.606771, 38.929891, 'normal', 'DN400 90度无缝冲压弯头', '香工街拐弯转向管道节点', 4, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-002', '香工街沿线2号对接焊口', 121.608771, 38.931491, 'pending', 'DN400 预制直埋保温管', '氩弧打底完成，等待安监质检组探伤', 5, 'W-DL-001'),
('insulation_pipe_supply_2026', 'tee', '标段1', '香炉礁供暖主干线', 'T-DL-001', '香工街与香周路分叉三通', 121.610771, 38.933491, 'normal', 'DN400/DN300 异径无缝三通', '关键管网分叉节点，引出香周路分支', 6, 'W-DL-002'),
('insulation_pipe_supply_2026', 'compensator', '标段1', '香炉礁供暖主干线', 'C-DL-001', '主线轴向波纹管补偿器', 121.611771, 38.934491, 'normal', 'DN400 轴向外压波纹补偿器', '吸收管线热膨胀伸缩应力', 7, NULL),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-003', '东北路交汇末端合拢焊口', 121.613771, 38.936491, 'passed', 'DN400 预制直埋保温管', '主干线施工完工合拢焊口', 8, 'T-DL-001'),

-- 管线 1 的分支：从 T-DL-001 (三通) 引出到香周路分支
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-004', '香周路分支1号对接焊口', 121.613271, 38.931891, 'passed', 'DN300 预制直埋保温管', '三通分支引出首段焊口', 9, 'T-DL-001'),
('insulation_pipe_supply_2026', 'valve', '标段1', '香炉礁供暖主干线', 'V-DL-002', '香周路分支隔离切断阀', 121.614871, 38.930491, 'open', 'DN300 手动阀门', '分支网维保检修控制阀', 10, 'W-DL-004'),
('insulation_pipe_supply_2026', 'weld', '标段1', '香炉礁供暖主干线', 'W-DL-005', '香周路分支末端焊口', 121.616771, 38.929091, 'pending', 'DN300 预制直埋保温管', '等待末端换热站对接', 11, 'V-DL-002'),

-- 管线 2：鞍山路预制管线 (含三通分叉)
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-001', '鞍山路管网起点对接焊口', 121.612771, 38.927491, 'pending', 'DN300 聚氨酯保温管', '标段2施工首段', 1, NULL),
('insulation_pipe_supply_2026', 'tee', '标段2', '鞍山路预制管线', 'T-AS-001', '鞍山路社区三通分流点', 121.614771, 38.929091, 'normal', 'DN300 等径三通', '社区二级供热网分流节点', 2, NULL),
('insulation_pipe_supply_2026', 'compensator', '标段2', '鞍山路预制管线', 'C-AS-001', '鞍山路中段波纹补偿器', 121.616771, 38.930091, 'normal', 'DN300 波纹管补偿器', '吸收管段位移', 3, NULL),
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-002', '鞍山路主线末端焊口', 121.618771, 38.931091, 'failed', 'DN300 聚氨酯保温管', '探伤微小瑕疵，安排复焊', 4, NULL),
('insulation_pipe_supply_2026', 'weld', '标段2', '鞍山路预制管线', 'W-AS-003', '鞍山路社区小区分支焊口', 121.616771, 38.927091, 'passed', 'DN200 保温管', '从 T-AS-001 三通引出的小区分支焊口', 5, 'T-AS-001')
ON CONFLICT (project_key, code) DO NOTHING;

COMMIT;

