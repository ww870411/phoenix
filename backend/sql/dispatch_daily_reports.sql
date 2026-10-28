-- 调度生产日报全要素工业大宽表定义 (public.dispatch_daily_reports)
-- 包含 120+ 物理展开列，并保留机炉拓扑与微观抢修工作票 JSONB
-- 唯一约束：(project_key, biz_date)

DROP TABLE IF EXISTS public.dispatch_daily_reports CASCADE;

CREATE TABLE public.dispatch_daily_reports (
    -- 1. 基础发令与元数据
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(64) NOT NULL DEFAULT 'daily_report_25_26',
    biz_date DATE NOT NULL,
    issue_date DATE,
    publish_date VARCHAR(64),
    duty_staff VARCHAR(128),
    file_name VARCHAR(255),

    -- 2. 气象全要素
    wth_date DATE,
    wth_weekday VARCHAR(16),
    wth_condition VARCHAR(32),
    wth_temp_min NUMERIC(5, 2),
    wth_temp_max NUMERIC(5, 2),
    wth_hum_min INT,
    wth_hum_max INT,
    wth_wind_dir VARCHAR(32),
    wth_wind_scale VARCHAR(32),
    wth_raw_text TEXT,

    -- 3. 水网首站运行工况 (36列：6大首站 × 泵数/流量/供回压/供回温)
    -- 北海#1首站
    bh_s1_pumps INT,
    bh_s1_flow NUMERIC(10, 2),
    bh_s1_press_sup NUMERIC(6, 3),
    bh_s1_press_ret NUMERIC(6, 3),
    bh_s1_temp_sup NUMERIC(6, 2),
    bh_s1_temp_ret NUMERIC(6, 2),
    -- 北海#2首站
    bh_s2_pumps INT,
    bh_s2_flow NUMERIC(10, 2),
    bh_s2_press_sup NUMERIC(6, 3),
    bh_s2_press_ret NUMERIC(6, 3),
    bh_s2_temp_sup NUMERIC(6, 2),
    bh_s2_temp_ret NUMERIC(6, 2),
    -- 北海水炉首站
    bh_wl_pumps INT,
    bh_wl_flow NUMERIC(10, 2),
    bh_wl_press_sup NUMERIC(6, 3),
    bh_wl_press_ret NUMERIC(6, 3),
    bh_wl_temp_sup NUMERIC(6, 2),
    bh_wl_temp_ret NUMERIC(6, 2),
    -- 香海#1低真空
    xh_lv1_pumps INT,
    xh_lv1_flow NUMERIC(10, 2),
    xh_lv1_press_sup NUMERIC(6, 3),
    xh_lv1_press_ret NUMERIC(6, 3),
    xh_lv1_temp_sup NUMERIC(6, 2),
    xh_lv1_temp_ret NUMERIC(6, 2),
    -- 香海#3低真空
    xh_lv3_pumps INT,
    xh_lv3_flow NUMERIC(10, 2),
    xh_lv3_press_sup NUMERIC(6, 3),
    xh_lv3_press_ret NUMERIC(6, 3),
    xh_lv3_temp_sup NUMERIC(6, 2),
    xh_lv3_temp_ret NUMERIC(6, 2),
    -- 香海首站
    xh_main_pumps INT,
    xh_main_flow NUMERIC(10, 2),
    xh_main_press_sup NUMERIC(6, 3),
    xh_main_press_ret NUMERIC(6, 3),
    xh_main_temp_sup NUMERIC(6, 2),
    xh_main_temp_ret NUMERIC(6, 2),

    -- 4. 蒸汽网口工况 (12列：状态/压力/流量)
    bh_south_status VARCHAR(16),
    bh_south_press NUMERIC(6, 3),
    bh_south_flow NUMERIC(10, 2),
    xb_link_status VARCHAR(16),
    xb_link_press NUMERIC(6, 3),
    xb_link_flow NUMERIC(10, 2),
    xh_east_status VARCHAR(16),
    xh_east_press NUMERIC(6, 3),
    xh_east_flow NUMERIC(10, 2),
    xh_west_status VARCHAR(16),
    xh_west_press NUMERIC(6, 3),
    xh_west_flow NUMERIC(10, 2),

    -- 5. 燃煤收耗存统计 (25列：进煤说明 + 8主体进/耗/存)
    coal_remark TEXT,
    coal_bh_in NUMERIC(10, 2),
    coal_bh_use NUMERIC(10, 2),
    coal_bh_stock NUMERIC(10, 2),
    coal_xh_in NUMERIC(10, 2),
    coal_xh_use NUMERIC(10, 2),
    coal_xh_stock NUMERIC(10, 2),
    coal_main_sum_in NUMERIC(10, 2),
    coal_main_sum_use NUMERIC(10, 2),
    coal_main_sum_stock NUMERIC(10, 2),
    coal_jz_in NUMERIC(10, 2),
    coal_jz_use NUMERIC(10, 2),
    coal_jz_stock NUMERIC(10, 2),
    coal_bf_in NUMERIC(10, 2),
    coal_bf_use NUMERIC(10, 2),
    coal_bf_stock NUMERIC(10, 2),
    coal_zh_in NUMERIC(10, 2),
    coal_zh_use NUMERIC(10, 2),
    coal_zh_stock NUMERIC(10, 2),
    coal_dlg_in NUMERIC(10, 2),
    coal_dlg_use NUMERIC(10, 2),
    coal_dlg_stock NUMERIC(10, 2),
    coal_total_in NUMERIC(10, 2),
    coal_total_use NUMERIC(10, 2),
    coal_total_stock NUMERIC(10, 2),

    -- 6. 当日产量与计划比对 (20列)
    prod_bh_steam_coal_plan NUMERIC(10, 2),
    prod_bh_steam_coal_act NUMERIC(10, 2),
    prod_bh_water_coal_plan NUMERIC(10, 2),
    prod_bh_water_coal_act NUMERIC(10, 2),
    prod_bh_power_plan NUMERIC(10, 2),
    prod_bh_power_act NUMERIC(10, 2),
    prod_bh_heat_plan NUMERIC(10, 2),
    prod_bh_heat_act NUMERIC(10, 2),
    prod_xh_steam_coal_plan NUMERIC(10, 2),
    prod_xh_steam_coal_act NUMERIC(10, 2),
    prod_xh_power_plan NUMERIC(10, 2),
    prod_xh_power_act NUMERIC(10, 2),
    prod_xh_heat_plan NUMERIC(10, 2),
    prod_xh_heat_act NUMERIC(10, 2),
    prod_main_coal_plan NUMERIC(10, 2),
    prod_main_coal_act NUMERIC(10, 2),
    prod_main_power_plan NUMERIC(10, 2),
    prod_main_power_act NUMERIC(10, 2),
    prod_main_heat_plan NUMERIC(10, 2),
    prod_main_heat_act NUMERIC(10, 2),

    -- 7. 网口热量与供汽量 (6列)
    gw_high_temp_water NUMERIC(10, 2),
    gw_lv1_heat NUMERIC(10, 2),
    gw_lv3_heat NUMERIC(10, 2),
    gw_bh_south_steam NUMERIC(10, 2),
    gw_xh_ew_steam NUMERIC(10, 2),
    gw_xb_link_steam NUMERIC(10, 2),

    -- 8. 初期补水量全套 (6列)
    water_sup_bh_s1 NUMERIC(10, 2),
    water_sup_bh_s2 NUMERIC(10, 2),
    water_sup_period_last_year NUMERIC(10, 2),
    water_sup_accum NUMERIC(10, 2),
    water_sup_accum_last NUMERIC(10, 2),
    substations_filled INT,

    -- 9. 宏观四大总量 (汇总列)
    total_coal_consumed NUMERIC(14, 2),
    total_power_generated NUMERIC(14, 2),
    total_heat_supplied NUMERIC(14, 2),
    total_water_replenished NUMERIC(14, 2),

    -- 10. 高度动态结构化存根 (机炉矩阵与抢修日志流)
    eqp_status_json JSONB,
    boiler_turbine_status JSONB,
    log_items_json JSONB,
    operations_and_tickets JSONB,

    -- 11. 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_dispatch_biz_date UNIQUE (project_key, biz_date)
);

CREATE INDEX IF NOT EXISTS idx_dispatch_biz_date ON public.dispatch_daily_reports (biz_date DESC);
CREATE INDEX IF NOT EXISTS idx_dispatch_project_key ON public.dispatch_daily_reports (project_key);
