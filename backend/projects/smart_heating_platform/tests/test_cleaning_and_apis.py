# -*- coding: utf-8 -*-
"""智慧供热旁路精算与质检平台 —— 清洗引擎、梯形积分、表底插值与业务 API 测试。"""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.projects.smart_heating_platform.services.cleaning_engine import (
    EAST_8,
    FAULT_COMM_OFFLINE,
    FAULT_HEAT_IMBALANCE,
    FAULT_SENSOR_RANGE,
    FAULT_SOFTWARE_DEFECT,
    FAULT_TEMP_INVERSION,
    SRC_MASKED_PREV,
    SRC_PERM_OFFLINE,
    SRC_TEMP_OFFLINE,
    clean_merchant_point,
    clean_station_and_zones,
    clean_station_history_point,
    clean_temp_device,
    clean_upstream_point,
    floor_to_bucket,
    interpolate_meter_at_hour,
    trapezoidal_hour_integral,
    validate_meter_delta,
)
from backend.services.auth_manager import ActionFlags, AuthSession, GroupPermissions, get_current_session


def _session(group: str) -> AuthSession:
    return AuthSession(
        username="tester",
        group=group,
        unit="系统管理员",
        hierarchy=100 if group == "Global_admin" else 50,
        permissions=GroupPermissions(
            name=group,
            hierarchy=100 if group == "Global_admin" else 50,
            page_access={"*"},
            sheet_rules={},
            units_access=["*"],
            actions=ActionFlags(),
            projects={},
        ),
        allowed_units={"*"},
        token="tok",
        issued_at=datetime.now(EAST_8),
    )


def test_trapezoidal_integral_and_meter_interpolation():
    t0 = datetime(2026, 11, 19, 8, 0, tzinfo=EAST_8)
    t1 = datetime(2026, 11, 19, 8, 15, tzinfo=EAST_8)
    t2 = datetime(2026, 11, 19, 8, 30, tzinfo=EAST_8)
    t3 = datetime(2026, 11, 19, 8, 45, tzinfo=EAST_8)
    t4 = datetime(2026, 11, 19, 9, 0, tzinfo=EAST_8)

    # 4段梯形积分: (11 + 13 + 13 + 12) * 0.25 = 12.25 GJ
    integral = trapezoidal_hour_integral([(t0, 10.0), (t1, 12.0), (t2, 14.0), (t3, 12.0), (t4, 12.0)])
    assert integral == 12.25
    assert trapezoidal_hour_integral([(t0, 10.0), (t1, 12.0), (t2, 14.0), (t3, 12.0), (t4, 10.0)]) == 12.0

    # 线性插值：07:58 = 100.0, 08:13 = 103.0 -> 08:00 应为 100.4
    m0 = datetime(2026, 11, 19, 7, 58, tzinfo=EAST_8)
    m1 = datetime(2026, 11, 19, 8, 13, tzinfo=EAST_8)
    assert interpolate_meter_at_hour([(m0, 100.0), (m1, 103.0)], t0) == 100.4

    # 表底倒走与跳变拦截
    d_ok, jump_ok, _ = validate_meter_delta(100.4, 112.4, max_hourly_limit=200.0)
    assert d_ok == 12.0 and not jump_ok

    d_neg, jump_neg, _ = validate_meter_delta(112.4, 10.0, max_hourly_limit=200.0)
    assert d_neg is None and jump_neg is True

    d_big, jump_big, _ = validate_meter_delta(100.0, 600.0, max_hourly_limit=200.0)
    assert d_big is None and jump_big is True


def test_cleaning_rules_for_upstream_station_zone_and_temp():
    now = datetime(2026, 11, 19, 21, 0, tzinfo=EAST_8)

    # 1. 上游蒸汽 850℃ 断路屏蔽
    u_clean, u_faults = clean_upstream_point(
        {"WENDU": 850.0, "YALI": 1.2, "LIULIANG": 30.0, "SHIJIAN": "2026-11-19 20:55:00"},
        {"point_id": 1, "data_zone": "dc_dict", "source_name": "香海#4机主汽", "name": "香海#4机主汽", "category": "电厂", "sub_category": "香海热电厂"},
        now,
        prev_valid={"temp_clean": 530.5},
    )
    assert u_clean["temp_raw"] == 850.0
    assert u_clean["temp_clean"] == 530.5
    assert u_clean["value_source"] == SRC_MASKED_PREV
    assert FAULT_SENSOR_RANGE in (u_clean["fault_tag"] or "")
    assert len(u_faults) == 1

    # 2. 换热站：临时离线平滑 vs 常离线分区不造数 + 热平衡失真
    st_clean, zns, st_faults = clean_station_and_zones(
        station_meta={"station_id": "st1", "name": "金和苑"},
        zx_item={"online": False, "e1": "0", "e3": "0", "e4": "0", "e11": "0", "Nx": [{"name": "低区", "data": {"e2": "0", "e5": "0", "e6": "0", "e12": "1.82"}}]},
        yw_item={"update_time": "2026-11-19 18:00:00"},
        zone_meta_map={"低区": {"secondary_zone_id": "SZ0111", "is_online": False}},
        collected_at=now,
        prev_station_valid={"e1_clean": 40.0, "e3_clean": 80.0, "e4_clean": 40.0, "e11_clean": 6.5},
    )
    assert st_clean["value_source"] == SRC_TEMP_OFFLINE
    assert st_clean["e3_clean"] == 80.0
    assert zns[0]["value_source"] == SRC_PERM_OFFLINE
    assert FAULT_COMM_OFFLINE in (st_clean["fault_tag"] or "")

    # 3. 在线站物理倒挂 & 热平衡偏差 >20%
    st2, _, faults2 = clean_station_and_zones(
        station_meta={"station_id": "st2", "name": "测试站"},
        zx_item={"online": True, "e1": "20.0", "e3": "40.0", "e4": "45.0", "e11": "1.00", "Nx": [{"name": "低区", "data": {"e2": "50.0", "e5": "42.0", "e6": "36.0", "e12": "1.50"}}]},
        yw_item={"update_time": "2026-11-19 20:59:00"},
        zone_meta_map={"低区": {"secondary_zone_id": "SZ0001", "is_online": True}},
        collected_at=now,
        prev_station_valid={"e3_clean": 75.0, "e4_clean": 40.0},
    )
    assert FAULT_TEMP_INVERSION in (st2["fault_tag"] or "")
    assert FAULT_HEAT_IMBALANCE in (st2["fault_tag"] or "")
    assert st2["e3_clean"] == 75.0
    assert any(f["fault_code"] == FAULT_HEAT_IMBALANCE for f in faults2)

    # 4. 居民室温：未入台账设备阳面剔除、阴面保留
    t_unreg, t_faults = clean_temp_device(
        {"id": "999999999999999", "village_name": "新楼1-101", "station_name": "白兰", "wd1": 22.5, "upload_time": "2026-11-19 20:50:00"},
        device_dict={},
        alias_station_map={"白兰": "st_bl"},
        collected_at=now,
    )
    assert t_unreg["is_registered"] is False
    assert t_unreg["is_online_valid"] is False
    assert t_unreg["temp_clean"] is None
    assert any(f["fault_code"] == FAULT_SOFTWARE_DEFECT for f in t_faults)

    # 5. 上游 sh_dict 兼容 update_time 字段解析
    sh_up, _ = clean_upstream_point(
        {"WENDU": 137.1, "YALI": 0.236, "LIULIANG": 13.8, "RELIANG": 0, "update_time": "2026-11-19 20:50:00"},
        {"point_id": 82, "data_zone": "sh_dict", "source_name": "造船老厂（船舶重工）", "name": "造船（香）", "category": "首站"},
        now,
    )
    assert sh_up["source_time"] is not None and sh_up["source_time"].hour == 20

    # 6. 商业用户：测试户剔除 + 别名归口 + 物理倒挂回退
    mc_lookup = {"航运中心大厦": {"merchant_id": "m_hy", "name": "航运中心大厦"}}
    mc_test, mc_test_faults = clean_merchant_point(
        {"name": "测试商户", "xinhaoqiangdu": "0", "shunshireliang": 1.2, "gongshuiliuliang": 2.0},
        merchant_lookup=mc_lookup,
        collected_at=now,
    )
    assert mc_test["is_registered"] is False
    assert mc_test["heat_clean"] is None
    assert any(f["fault_code"] == FAULT_SOFTWARE_DEFECT for f in mc_test_faults)

    mc_alias, mc_inv_faults = clean_merchant_point(
        {
            "name": "国际航运中心大厦",
            "xinhaoqiangdu": 0,
            "gongshuiliuliang": 4.0,
            "gongshuiwendu": 30.0,
            "huishuiwendu": 35.0,
            "shunshireliang": 0.65,
        },
        merchant_lookup=mc_lookup,
        collected_at=now,
        prev_valid={"temp_sup_clean": 70.0, "temp_ret_clean": 38.0},
    )
    assert mc_alias["is_registered"] is True
    assert mc_alias["online"] is True
    assert mc_alias["merchant_id"] == "m_hy"
    assert mc_alias["source_name"] == "航运中心大厦"
    assert mc_alias["temp_sup_clean"] == 70.0
    assert any(f["fault_code"] == FAULT_TEMP_INVERSION for f in mc_inv_faults)

    # 7. 蒸汽商业户单位折算 (kg/h -> t/h, MJ/h -> GJ/h) 与 -200℃ 回温屏蔽
    mc_steam, mc_steam_faults = clean_merchant_point(
        {
            "name": "新船孔板",
            "xinhaoqiangdu": 0,
            "gongshuiliuliang": 18222.9,
            "gongshuiwendu": 180.7,
            "huishuiwendu": -200.0,
            "shunshireliang": 51423.1,
        },
        merchant_lookup={"新船孔板": {"merchant_id": "m_xckb", "name": "新船孔板", "rdry": "蒸汽"}},
        collected_at=now,
    )
    assert mc_steam["online"] is True
    assert abs(mc_steam["flow_clean"] - 18.2229) < 1e-4
    assert abs(mc_steam["heat_clean"] - 51.4231) < 1e-4
    assert mc_steam["temp_sup_clean"] == 180.7
    assert mc_steam["temp_ret_clean"] is None
    assert any(f["fault_code"] == FAULT_SOFTWARE_DEFECT for f in mc_steam_faults)


def test_platform_endpoints_smoke_and_permissions():
    app = create_app()
    client = TestClient(app)

    # 非 Global_admin 被拦截
    app.dependency_overrides[get_current_session] = lambda: _session("Group_admin")
    assert client.get("/api/v1/projects/smart_heating_platform/reports/hourly").status_code == 403
    assert client.get("/api/v1/projects/smart_heating_platform/faults/summary").status_code == 403
    assert client.get("/api/v1/projects/smart_heating_platform/dicts/overview").status_code == 403

    # Global_admin 正常响应
    app.dependency_overrides[get_current_session] = lambda: _session("Global_admin")
    r_h = client.get("/api/v1/projects/smart_heating_platform/reports/hourly")
    assert r_h.status_code == 200 and r_h.json()["ok"] is True
    assert len(r_h.json()["data"]["merchants"]) == 464
    assert r_h.json()["data"]["merchant_summary"]["total_merchants"] == 464

    # 校验无参数调用默认定位到最新有数据的日期和小时
    from backend.projects.smart_heating_platform.services.report_query_service import _resolve_latest_available_biz_hour
    from backend.db.database_daily_report_25_26 import engine

    with engine.connect() as conn:
        expected_bh = _resolve_latest_available_biz_hour(conn)
    if expected_bh is not None:
        assert r_h.json()["data"]["meta"]["date"] == expected_bh.date().isoformat()
        assert r_h.json()["data"]["meta"]["hour"] == expected_bh.hour

    r_d = client.get("/api/v1/projects/smart_heating_platform/reports/daily")
    assert r_d.status_code == 200 and len(r_d.json()["data"]["center_comparison"]) == 9

    r_f = client.get("/api/v1/projects/smart_heating_platform/faults/summary")
    assert r_f.status_code == 200 and r_f.json()["data"]["missing_area_stations"] == 32

    r_dict = client.get("/api/v1/projects/smart_heating_platform/dicts/overview")
    assert r_dict.status_code == 200
    ov = r_dict.json()["data"]
    assert ov["stations"] == 242 and ov["zones"] == 580 and ov["temp_devices"] == 2097


def test_prune_old_temp_hourly_cutoff():
    from backend.projects.smart_heating_platform.services.collector_engine import (
        TEMP_RETENTION_HOURS,
        prune_old_temp_hourly,
    )

    class _FakeRes:
        rowcount = 123

    class _FakeConn:
        def __init__(self):
            self.calls = []

        def execute(self, stmt, params=None):
            self.calls.append((str(stmt), params or {}))
            return _FakeRes()

    conn = _FakeConn()
    ref = datetime(2026, 11, 20, 5, 32, tzinfo=EAST_8)
    deleted = prune_old_temp_hourly(conn, reference_time=ref)
    assert TEMP_RETENTION_HOURS == 48
    assert deleted == 123
    assert len(conn.calls) == 1
    sql_text, params = conn.calls[0]
    assert "DELETE FROM smart_heating_platform.fact_temp_hourly" in sql_text
    assert params["cutoff"] == datetime(2026, 11, 18, 5, 0, tzinfo=EAST_8)


def test_5min_bucket_station_history_and_sampling_prune():
    from backend.projects.smart_heating_platform.services.collector_engine import (
        SAMPLING_KEEP_HOURS,
        prune_old_sampling_rows,
    )

    dt = datetime(2026, 11, 20, 8, 47, 29, tzinfo=EAST_8)
    assert floor_to_bucket(dt, 5) == datetime(2026, 11, 20, 8, 45, tzinfo=EAST_8)
    assert floor_to_bucket(dt, 15) == datetime(2026, 11, 20, 8, 45, tzinfo=EAST_8)

    # 路线 B：/hrz_ls_zb/ 代表断面温度越限与倒挂清洗
    cleaned, faults = clean_station_history_point(
        {"station_id": "st_hist", "name": "测试历史站"},
        {"f1": 0.6, "f2": 20.0, "f3": 42.0, "f4": 0.4, "f5": 48.0, "f222": 2.5},
        prev_station_valid={"e3_clean": 72.0, "e4_clean": 40.0},
    )
    assert cleaned["online"] is True
    assert cleaned["e3_clean"] == 72.0
    assert cleaned["e4_clean"] == 40.0
    assert cleaned["value_source"] == SRC_MASKED_PREV
    assert FAULT_TEMP_INVERSION in (cleaned["fault_tag"] or "")
    assert len(faults) == 1

    # 算完即清（2小时保留：当前小时 + 上一小时，删除 biz_hour < ref_hour - 1h）
    class _FakeRes:
        rowcount = 50

    class _FakeConn:
        def __init__(self):
            self.calls = []

        def execute(self, stmt, params=None):
            self.calls.append((str(stmt), params or {}))
            return _FakeRes()

    conn = _FakeConn()
    res = prune_old_sampling_rows(conn, reference_time=datetime(2026, 11, 20, 9, 12, tzinfo=EAST_8))
    assert SAMPLING_KEEP_HOURS == 2
    assert res["total"] == 200
    assert len(conn.calls) == 4
    assert conn.calls[0][1]["cutoff"] == datetime(2026, 11, 20, 8, 0, tzinfo=EAST_8)
