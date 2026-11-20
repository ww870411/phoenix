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
    assert r_f.status_code == 200 and isinstance(r_f.json()["data"]["missing_area_stations"], int)
    assert r_f.json()["data"]["missing_area_stations"] >= 0

    r_dict = client.get("/api/v1/projects/smart_heating_platform/dicts/overview")
    assert r_dict.status_code == 200
    ov = r_dict.json()["data"]
    assert ov["stations"] == 242 and ov["zones"] == 580 and ov["temp_devices"] == 2097
    assert ov["main_networks"] == 9

    r_mn = client.get("/api/v1/projects/smart_heating_platform/dicts/items/main_networks")
    assert r_mn.status_code == 200
    assert len(r_mn.json()["data"]) == 9

    r_gap = client.get("/api/v1/projects/smart_heating_platform/reports/gap-status")
    assert r_gap.status_code == 200 and r_gap.json()["ok"] is True
    assert "tracks" in r_gap.json()["data"]


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


def test_detect_data_gaps_and_recovery_orchestration(monkeypatch):
    from datetime import date, timedelta
    from types import SimpleNamespace
    import backend.projects.smart_heating_platform.services.collector_engine as ce

    monkeypatch.setattr(ce, "ensure_smart_heating_fact_tables", lambda: None)
    monkeypatch.setattr(ce, "_read_raw_config", lambda: {"gap_recovery_start_date": "2026-11-01", "cookie": "sid=abc", "source_mode": "public"})

    class _MockResult:
        def __init__(self, rows):
            self._rows = rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return self._rows

    # 1. 空库场景：默认不触发自动补采，手动 include_empty_baseline=True 时返回自起始日起待补小时
    class _EmptyConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            s = str(stmt)
            if "MIN(biz_hour)" in s:
                return _MockResult([SimpleNamespace(min_h=None, max_h=None)])
            return _MockResult([])

    monkeypatch.setattr(ce, "engine", SimpleNamespace(connect=lambda: _EmptyConn()))
    ref = datetime(2026, 11, 20, 11, 25, tzinfo=EAST_8)
    empty_res = ce.detect_data_gaps(start_date_str="2026-11-19", reference_time=ref, include_empty_baseline=False)
    assert empty_res["has_gaps"] is False
    assert empty_res["empty_baseline"] is True

    manual_empty_res = ce.detect_data_gaps(start_date_str="2026-11-19", reference_time=ref, include_empty_baseline=True)
    assert manual_empty_res["has_gaps"] is True
    assert manual_empty_res["tracks"]["stations"]["missing_count"] == 35  # 11-19 00:00 ~ 11-20 10:00 共 35 小时

    # 2. 停机真空期：以 2026-11-19 00:00 为例，仅 12/14 时完整、13 时仅写入 10 站（半残缺），停机至 2026-11-20 11:25 重启
    st_present = [
        (datetime(2026, 11, 19, h, 0, tzinfo=EAST_8), 240) for h in range(0, 13)
    ] + [
        (datetime(2026, 11, 19, 13, 0, tzinfo=EAST_8), 10),   # 半残缺整点（低于峰值半数 120）应识别为缺失
        (datetime(2026, 11, 19, 14, 0, tzinfo=EAST_8), 240),
    ]
    up_present = [(datetime(2026, 11, 19, h, 0, tzinfo=EAST_8), 20) for h in range(0, 14)]  # 14:00 积分尚为空
    mh_present = [(datetime(2026, 11, 19, h, 0, tzinfo=EAST_8), 460) for h in range(0, 14)]

    class _GapConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            s = str(stmt)
            if "MIN(biz_hour)" in s and "fact_station_hourly" in s:
                return _MockResult([SimpleNamespace(min_h=st_present[0][0], max_h=st_present[-1][0])])
            if "MIN(biz_hour)" in s and "fact_upstream_hourly" in s:
                return _MockResult([SimpleNamespace(min_h=up_present[0][0], max_h=up_present[-1][0])])
            if "MIN(biz_hour)" in s and "fact_merchant_hourly" in s:
                return _MockResult([SimpleNamespace(min_h=mh_present[0][0], max_h=mh_present[-1][0])])
            if "fact_station_hourly" in s and "GROUP BY biz_hour" in s:
                return _MockResult([SimpleNamespace(biz_hour=h, cnt=c) for h, c in st_present])
            if "fact_upstream_hourly" in s and "GROUP BY biz_hour" in s:
                return _MockResult([SimpleNamespace(biz_hour=h, cnt=c) for h, c in up_present])
            if "fact_merchant_hourly" in s and "GROUP BY biz_hour" in s:
                return _MockResult([SimpleNamespace(biz_hour=h, cnt=c) for h, c in mh_present])
            if "fact_merchant_daily" in s:
                return _MockResult([])  # 11-19 缺失
            return _MockResult([])

    monkeypatch.setattr(ce, "engine", SimpleNamespace(connect=lambda: _GapConn()))
    gaps = ce.detect_data_gaps(start_date_str="2026-11-19", reference_time=ref)
    # 11-19 12:00 到 11-20 10:00 共 23 小时；站缺 21 时 (13:00半残缺 + 15..23 + 00..10)，上游与商户缺 21 时 (14..23 + 00..10)
    assert gaps["has_gaps"] is True
    assert gaps["missing_dates"] == ["2026-11-19", "2026-11-20"]
    assert gaps["tracks"]["stations"]["missing_count"] == 21
    assert "2026-11-19 13:00" in gaps["tracks"]["stations"]["missing_hours"]
    assert gaps["tracks"]["upstream"]["missing_count"] == 21
    assert gaps["tracks"]["merchant_hourly"]["missing_count"] == 21
    assert gaps["tracks"]["merchant_daily"]["missing_dates"] == ["2026-11-19"]

    # 3. 验证 run_gap_recovery 按缺失日期与缺失小时编排调起四路补采
    calls = []
    monkeypatch.setattr(ce, "_insert_run_log", lambda *a, **kw: 9001)
    monkeypatch.setattr(ce, "_finish_run_log", lambda *a, **kw: None)
    monkeypatch.setattr(
        ce,
        "run_table_bottom_calibration",
        lambda target_date_str=None, target_hours=None, trigger="AUTO", progress_cb=None: (
            (progress_cb(1, 1, "测试换热站") if progress_cb else None),
            calls.append(("station", target_date_str, len(target_hours or []))),
            {"updated_station_hours": len(target_hours or []) * 10},
        )[-1],
    )
    monkeypatch.setattr(
        ce,
        "run_upstream_hourly_backfill",
        lambda target_date_str=None, target_hours=None, trigger="AUTO", progress_cb=None: (
            (progress_cb(1, 1, "dc_dict:测试电厂") if progress_cb else None),
            calls.append(("upstream", target_date_str, len(target_hours or []))),
            {"updated_upstream_hours": len(target_hours or []) * 5},
        )[-1],
    )
    monkeypatch.setattr(
        ce,
        "run_merchant_hourly_backfill",
        lambda target_date_str=None, target_hours=None, trigger="AUTO", progress_cb=None: (
            (progress_cb(1, 1, "测试商业户") if progress_cb else None),
            calls.append(("merchant_hourly", target_date_str, len(target_hours or []))),
            {"updated_merchant_hours": len(target_hours or []) * 20},
        )[-1],
    )
    monkeypatch.setattr(
        ce,
        "run_merchant_daily_cycle",
        lambda target_date_str=None, trigger="AUTO": (
            calls.append(("merchant_daily", target_date_str, 1))
            or {"ok": True, "skipped": False}
        ),
    )

    # 首次调用 detect 返回缺口，第二次（复核）返回已补齐
    detect_seq = iter([
        gaps,
        {**gaps, "has_gaps": False, "total_missing_track_hours": 0, "missing_dates": []},
    ])
    monkeypatch.setattr(ce, "detect_data_gaps", lambda **kw: next(detect_seq))

    rec_res = ce.run_gap_recovery(trigger="AUTO_STARTUP")
    assert rec_res["ok"] is True
    assert rec_res["has_gaps"] is False
    assert rec_res["recovered_station_hours"] == 210
    assert rec_res["recovered_upstream_hours"] == 105
    assert rec_res["recovered_merchant_hours"] == 420
    assert rec_res["recovered_merchant_daily_days"] == 1
    assert ("station", "2026-11-19", 10) in calls
    assert ("station", "2026-11-20", 11) in calls
    assert ("merchant_daily", "2026-11-19", 1) in calls

    # 4. 验证运行时心跳与实况流水日志已在状态接口数据中保留并可追踪
    with ce._GAP_STATE_LOCK:
        st_snap = dict(ce._GAP_RUNTIME_STATE)
    assert st_snap["running"] is False
    assert st_snap["total_steps"] == 7
    assert st_snap["last_heartbeat_at"] is not None
    assert len(st_snap["recent_logs"]) >= 7
    assert st_snap["recovered_counts"]["station_hours"] == 210


def test_source_empty_placeholders_and_gap_distinction(monkeypatch):
    from types import SimpleNamespace
    import backend.projects.smart_heating_platform.services.collector_engine as ce

    monkeypatch.setattr(ce, "ensure_smart_heating_fact_tables", lambda: None)
    monkeypatch.setattr(
        ce,
        "_read_raw_config",
        lambda: {"gap_recovery_start_date": "2026-11-08", "source_mode": "public", "max_workers": 2, "request_timeout_seconds": 5},
    )
    monkeypatch.setattr(ce, "_insert_run_log", lambda *a, **kw: 9901)
    monkeypatch.setattr(ce, "_finish_run_log", lambda *a, **kw: None)
    monkeypatch.setattr(
        ce,
        "_load_dict_caches",
        lambda: {
            "merchants": [{"merchant_id": "M001", "name": "测试商户A"}],
            "merchant_by_name": {"测试商户A": {"merchant_id": "M001", "name": "测试商户A"}},
            "upstream_by_key": {
                ("dc_dict", "测试电厂"): {"point_id": 1, "data_zone": "dc_dict", "source_name": "测试电厂", "name": "测试电厂", "category": "电厂", "sub_category": None},
                ("sz_dict", "测试首站"): {"point_id": 2, "data_zone": "sz_dict", "source_name": "测试首站", "name": "测试首站", "category": "首站", "sub_category": None},
            },
        },
    )

    batches = []

    def _capture_upsert(conn, table_name, columns, conflict_cols, update_cols, rows, extra_set_clauses=None, do_nothing_on_conflict=False):
        batches.append((table_name, do_nothing_on_conflict, list(rows)))

    monkeypatch.setattr(ce, "_upsert_batch", _capture_upsert)

    class _FakeResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ce.httpx, "Client", _FakeClient)

    def _fake_post(client, url, data=None, headers=None, retries=2):
        if url.endswith("/sh_ls_zb/"):
            return _FakeResp(
                200,
                [{"tmDate": "2026-11-08 00:05:00", "fFlowJ": 10.0, "fFlowF": 2.0, "fTempJ": 60, "fTempF": 40, "fPresJ": 0.5, "fPresF": 0.4, "fValveOpen": 50, "fValveSet": 50}],
            )
        if url.endswith("/get_dc_data/1"):
            return _FakeResp(200, [{"name": "测试电厂", "id": "1"}])
        if url.endswith("/get_sz_data/1"):
            return _FakeResp(500, {})
        if url.endswith("/ry_dcls_xx/get_history"):
            return _FakeResp(200, [{"tmDate": "2026-11-08 00:10:00", "WENDU": 90.0, "YALI": 1.0, "LIULIANG": 100.0, "RELIANG": 200.0}])
        if url.endswith("/ry_szls_xx/get_history"):
            return _FakeResp(200, [])
        return _FakeResp(404, {})

    monkeypatch.setattr(ce, "_post_with_retry", _fake_post)

    class _KnownEngine:
        def connect(self):
            return self

        def begin(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt, params=None):
            class _R:
                def fetchall(self):
                    return [SimpleNamespace(data_zone="sz_dict", source_name="测试首站")]
            return _R()

    monkeypatch.setattr(ce, "engine", _KnownEngine())

    target_hrs = [datetime(2026, 11, 8, 0, 0, tzinfo=EAST_8), datetime(2026, 11, 8, 1, 0, tzinfo=EAST_8)]
    mc_res = ce.run_merchant_hourly_backfill(target_date_str="2026-11-08", target_hours=target_hrs, trigger="MANUAL")
    assert mc_res["updated_merchant_hours"] == 1
    assert mc_res["empty_merchant_hours"] == 1

    up_res = ce.run_upstream_hourly_backfill(target_date_str="2026-11-08", target_hours=target_hrs, trigger="MANUAL")
    assert up_res["points_total"] == 2  # /get_sz_data/1 报错时自动兜底补齐 sz_dict
    assert up_res["updated_upstream_hours"] == 1
    assert up_res["empty_upstream_hours"] == 3  # 电厂 01:00 空值占位 + 首站 00:00/01:00 空值占位

    empty_merchant_batches = [b for b in batches if b[0] == "fact_merchant_hourly" and b[1] is True]
    assert len(empty_merchant_batches) == 1
    assert empty_merchant_batches[0][2][0]["value_source"] == "SOURCE_EMPTY"
    assert empty_merchant_batches[0][2][0]["hour_heat_gj"] is None

    # 验证 detect_data_gaps SQL 包含 SOURCE_EMPTY 豁免条件（不把源站空值占位视为漏采）
    executed_sqls = []

    class _InspectConn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt, params=None):
            executed_sqls.append(str(stmt))
            class _R:
                def fetchone(self):
                    return SimpleNamespace(min_h=datetime(2026, 11, 8, 0, 0, tzinfo=EAST_8), max_h=datetime(2026, 11, 8, 1, 0, tzinfo=EAST_8))
                def fetchall(self):
                    return []
            return _R()

    monkeypatch.setattr(ce, "engine", SimpleNamespace(connect=lambda: _InspectConn()))
    ce.detect_data_gaps(start_date_str="2026-11-08", reference_time=datetime(2026, 11, 8, 2, 10, tzinfo=EAST_8))
    assert any("fact_upstream_hourly" in s and "SOURCE_EMPTY" in s and "GROUP BY biz_hour" in s for s in executed_sqls)
    assert any("fact_merchant_hourly" in s and "SOURCE_EMPTY" in s and "GROUP BY biz_hour" in s for s in executed_sqls)


def test_scheduler_gap_recovery_grace_and_wake(monkeypatch):
    from datetime import timedelta
    import backend.projects.smart_heating_platform.services.scheduler_service as ss

    sched = ss.SmartHeatingSchedulerService()
    spawned = []
    monkeypatch.setattr(sched, "_spawn_job", lambda name, fn: spawned.append(name))
    monkeypatch.setattr(
        ss,
        "_read_raw_config",
        lambda: {
            "scheduler_enabled": True,
            "auto_gap_recovery": True,
            "snapshot_interval_minutes": 60,
            "hourly_offset_minutes": 59,
            "table_bottom_sync_hours": 24,
        },
    )

    # 启动未满 10 秒宽限期：不触发启动真空期检查
    sched._started_at_monotonic = 100.0
    monkeypatch.setattr(ss.time, "monotonic", lambda: 102.0)
    sched._tick()
    assert "gap_recovery_startup" not in spawned

    # 超过 10 秒宽限期：触发一次启动真空期自动补采
    monkeypatch.setattr(ss.time, "monotonic", lambda: 112.0)
    sched._tick()
    assert spawned.count("gap_recovery_startup") == 1

    # 再次 tick 不重复触发启动补采
    sched._tick()
    assert spawned.count("gap_recovery_startup") == 1

    # 模拟进程休眠/挂起 2 小时后唤醒：触发 wake 真空期巡检
    sched._last_tick_e8 = datetime.now(EAST_8) - timedelta(hours=2)
    sched._tick()
    assert "gap_recovery_wake" in spawned


def test_station_heat_cleaning_scaling_and_daily_audit_schedule(monkeypatch):
    import backend.projects.smart_heating_platform.services.collector_engine as ce
    import backend.projects.smart_heating_platform.services.scheduler_service as ss
    from backend.projects.smart_heating_platform.services.cleaning_engine import station_max_hourly_heat_gj

    # 1. 小站物理热负荷上限按面积严谨核定（兴工街 19,080 ㎡ -> 25 GJ/h，不再放任 250 GJ/h）
    assert station_max_hourly_heat_gj(19080.46) == 25.0
    assert station_max_hourly_heat_gj(450152.59) == round(450152.59 * 0.00045, 4)

    # 2. _process_station_calibration：兴工街 f222 尖刺应过滤并留存 raw，同时写入 SENSOR_OUT_OF_RANGE 督办
    class _FakeResp:
        def __init__(self, payload):
            self.status_code = 200
            self._payload = payload

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ce.httpx, "Client", _FakeClient)

    def _fake_xinggong(client, url, data=None, headers=None, retries=2):
        return _FakeResp([
            {"create_time": "2026-11-14 07:07:00", "f1": 0.17, "f2": 0.54, "f3": 130.0, "f220": 15762.9, "f221": None, "f222": 18803.88},
            {"create_time": "2026-11-14 07:38:00", "f1": 0.17, "f2": 0.54, "f3": 130.4, "f220": 15763.2, "f221": None, "f222": 18583.58},
            {"create_time": "2026-11-14 07:53:00", "f1": 0.17, "f2": 0.54, "f3": 130.6, "f220": 15763.3, "f221": None, "f222": 0.0},
        ])

    monkeypatch.setattr(ce, "_post_with_retry", _fake_xinggong)
    hr07 = datetime(2026, 11, 14, 7, 0, tzinfo=EAST_8)
    _, st_rows, st_faults, ok_flag = ce._process_station_calibration(
        {"station_id": "st_xg", "name": "兴工街", "covered_area": 19080.46},
        "http://mock",
        "2026-11-14 06:30:00",
        "2026-11-14 08:30:00",
        [hr07],
        10.0,
        prev_station_db=None,
    )
    assert ok_flag is True
    assert len(st_rows) == 1
    assert st_rows[0]["hour_heat_raw_gj"] > 10000.0
    assert st_rows[0]["hour_heat_gj"] == 0.0
    assert any(f["fault_code"] == FAULT_SENSOR_RANGE for f in st_faults)

    # 3. 南山苑 10 倍累计表底自动 ÷10 折算并留存 hour_heat_raw_gj 与 SOFTWARE_DEFECT 审计记录
    def _fake_nanshan(client, url, data=None, headers=None, retries=2):
        return _FakeResp([
            {"create_time": "2026-11-14 07:00:00", "f1": 0.44, "f2": 199.0, "f3": 72.8, "f5": 42.0, "f220": 3.0, "f221": 2677125.0, "f222": 12.5},
            {"create_time": "2026-11-14 08:00:00", "f1": 0.43, "f2": 191.0, "f3": 72.7, "f5": 42.0, "f220": 3.1, "f221": 2677250.0, "f222": 12.5},
        ])

    monkeypatch.setattr(ce, "_post_with_retry", _fake_nanshan)
    _, ns_rows, ns_faults, _ = ce._process_station_calibration(
        {"station_id": "st_nsy", "name": "南山苑", "covered_area": 77815.57},
        "http://mock",
        "2026-11-14 06:30:00",
        "2026-11-14 08:30:00",
        [hr07],
        10.0,
        prev_station_db=None,
    )
    assert ns_rows[0]["hour_heat_raw_gj"] == 125.0
    assert ns_rows[0]["hour_heat_gj"] == 12.5
    assert any(f["fault_code"] == FAULT_SOFTWARE_DEFECT for f in ns_faults)

    # 4. 上游累计点位与超高极值清洗保护
    up_cum, up_faults = clean_upstream_point(
        {"RELIANG": 3862676.0, "LIULIANG": 0.0, "WENDU": 45.0, "SHIJIAN": "2026-11-14 07:00:00"},
        {"point_id": None, "data_zone": "sz_dict", "source_name": "热泵循环水累计吸收热量", "name": "热泵循环水累计吸收热量", "category": "首站"},
        datetime(2026, 11, 14, 7, 10, tzinfo=EAST_8),
    )
    assert up_cum["heat_raw"] == 3862676.0
    assert up_cum["heat_clean"] is None
    assert any(f["fault_code"] == FAULT_SOFTWARE_DEFECT for f in up_faults)

    # 5. 调度器在每日配置时刻（默认 00:00）触发一次 daily_heat_audit_fix
    sched = ss.SmartHeatingSchedulerService()
    sched._started_at_monotonic = 0.0
    sched._startup_gap_checked = True
    spawned = []
    monkeypatch.setattr(sched, "_spawn_job", lambda name, fn: spawned.append(name))
    monkeypatch.setattr(
        ss,
        "_read_raw_config",
        lambda: {
            "scheduler_enabled": True,
            "auto_gap_recovery": False,
            "auto_heat_audit_fix": True,
            "heat_audit_time": "00:00",
            "heat_audit_lookback_days": 3,
            "snapshot_interval_minutes": 60,
            "hourly_offset_minutes": 59,
            "table_bottom_sync_hours": 24,
        },
    )

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 21, 0, 2, tzinfo=tz or EAST_8)

    monkeypatch.setattr(ss, "datetime", _FixedDatetime)
    sched._tick()
    assert spawned.count("daily_heat_audit_fix") == 1
    sched._tick()
    assert spawned.count("daily_heat_audit_fix") == 1


def test_report_anomaly_propagation_and_notes():
    """验证单站热量/表底等被修正后，所有关联计算指标（总热量、单万㎡、瞬时负荷、热指标）均生成红色异常备注。"""
    from projects.smart_heating_platform.services import report_query_service as rqs

    station_row = {
        "e11_raw": 15000.0,
        "e11_clean": 100.0,
        "e14_raw": 20.0,
        "e14_clean": 20.0,
        "e3_raw": 75.0,
        "e3_clean": 75.0,
        "e4_raw": 45.0,
        "e4_clean": 45.0,
        "e7_raw": 52.0,
        "e7_clean": 52.0,
        "e8_raw": 41.0,
        "e8_clean": 41.0,
        "hour_heat_raw_gj": 15000.0,
        "hour_heat_gj": 36.0,
        "value_source": "CLEANED",
        "fault_tag": "HEAT_SPIKE",
    }
    field_notes = rqs._build_station_hour_anomalies(station_row, "测试换热站")
    assert "hour_heat_gj" in field_notes
    assert "e11" in field_notes
    assert "heat_index_wm2" in field_notes
    assert "15000" in field_notes["hour_heat_gj"]
    assert "36" in field_notes["hour_heat_gj"]

    station_entry = {
        "station_id": "S_TEST_01",
        "station_name": "测试换热站",
        "online": True,
        "covered_area": 100000.0,
        "e1": 500.0,
        "e11": 100.0,
        "e14": 20.0,
        "e3": 75.0,
        "e4": 45.0,
        "hour_heat_gj": 36.0,
        "heat_index_wm2": 100.0,
        "field_notes": field_notes,
    }
    normal_entry = {
        "station_id": "S_TEST_02",
        "station_name": "正常换热站",
        "online": True,
        "covered_area": 100000.0,
        "e1": 400.0,
        "e11": 80.0,
        "e14": 10.0,
        "e3": 70.0,
        "e4": 44.0,
        "hour_heat_gj": 18.0,
        "heat_index_wm2": 50.0,
        "field_notes": {},
    }
    kpi = rqs._compute_weighted_temp_and_kpis(
        [station_entry, normal_entry],
        {"S_TEST_01": [21.5], "S_TEST_02": [21.0]},
        "clean",
    )
    anomalies = kpi.get("anomalies") or {}
    for key in ("hour_heat_gj", "heat_per_wan_gj", "instant_load_gjh", "heat_index_wm2"):
        assert key in anomalies, f"{key} 应当继承热量异常标注"
        assert anomalies[key]["count"] == 1
        assert "测试换热站" in anomalies[key]["note"]
    assert "hour_water_t" not in anomalies
    assert "avg_sup_temp" not in anomalies


def test_only_burst_jump_highlights_red_and_temp_fallback_guard():
    """验证常规倍率换算与长期坏点不标红，只有突发跳变标红（clean/raw 双口径均生效）及温度脏基准回退保护。"""
    from projects.smart_heating_platform.services import cleaning_engine as ce
    from projects.smart_heating_platform.services import report_query_service as rqs

    # 1. 常规表底单位折算站（南山苑 ÷10）即使全天24小时 raw!=clean，也不应触发红标
    scale_row = {
        "hour_heat_raw_gj": 274.64,
        "hour_heat_gj": 27.46,
        "fault_tag": ce.FAULT_SOFTWARE_DEFECT,
    }
    assert rqs._build_station_hour_anomalies(scale_row, "南山苑", day_counts={"heat": 24}) == {}

    # 2. 全天长期损坏的温度传感器（>6小时且非超大跳变）不应把全网供回温图拖红
    chronic_temp_row = {
        "e3_raw": 163.0,
        "e3_clean": 65.0,
        "e4_raw": 45.0,
        "e4_clean": 45.0,
        "fault_tag": ce.FAULT_SENSOR_RANGE,
    }
    assert rqs._build_station_hour_anomalies(chronic_temp_row, "绿港湾", day_counts={"temp": 24}) == {}

    # 3. 突发大热量跳变（如国运壹号 -26333 -> 0 GJ）在 clean 和 raw 两种口径下都要标红
    burst_row = {
        "hour_heat_raw_gj": -26333.08,
        "hour_heat_gj": 0.0,
        "fault_tag": ce.FAULT_METER_JUMP,
    }
    clean_notes = rqs._build_station_hour_anomalies(burst_row, "国运壹号", day_counts={"heat": 2}, mode="clean")
    raw_notes = rqs._build_station_hour_anomalies(burst_row, "国运壹号", day_counts={"heat": 2}, mode="raw")
    assert "突发热量跳变已修正" in clean_notes["hour_heat_gj"]
    assert "突发热量跳变异常原值" in raw_notes["hour_heat_gj"]

    # 4. 历史脏基准温度（>150℃）禁止被回退逻辑继续继承
    cleaned_map, _, _, _ = ce._clean_station_primary_metrics(
        "S_DIRTY",
        "脏温保护站",
        10.0,
        181.5,
        45.0,
        0.8,
        0.5,
        5.0,
        1.0,
        prev_station_valid={"e3_clean": 170.8, "e4_clean": 45.0},
    )
    assert cleaned_map["e3_clean"] is None


def test_build_trend_24h_from_rows_for_single_entity():
    """验证单主体/单站 24 小时柱形与曲线聚合逻辑正确保留指标数值与突发跳变标注。"""
    from projects.smart_heating_platform.services import report_query_service as rqs

    rows = [
        {
            "hr": 7,
            "station_id": "S1",
            "station_name": "测试中心站A",
            "online": True,
            "covered_area": 100000.0,
            "e1_raw": 200.0,
            "e1_clean": 200.0,
            "e3_raw": 80.0,
            "e3_clean": 80.0,
            "e4_raw": 50.0,
            "e4_clean": 50.0,
            "e7_raw": 0.8,
            "e7_clean": 0.8,
            "e8_raw": 0.5,
            "e8_clean": 0.5,
            "e11_raw": 20.0,
            "e11_clean": 20.0,
            "e14_raw": 2.0,
            "e14_clean": 2.0,
            "hour_heat_raw_gj": 15483.87,
            "hour_heat_gj": 0.0,
            "hour_water_t": 2.0,
            "fault_tag": "METER_JUMP",
        },
        {
            "hr": 8,
            "station_id": "S1",
            "station_name": "测试中心站A",
            "online": True,
            "covered_area": 100000.0,
            "e1_raw": 200.0,
            "e1_clean": 200.0,
            "e3_raw": 81.0,
            "e3_clean": 81.0,
            "e4_raw": 51.0,
            "e4_clean": 51.0,
            "e7_raw": 0.8,
            "e7_clean": 0.8,
            "e8_raw": 0.5,
            "e8_clean": 0.5,
            "e11_raw": 22.0,
            "e11_clean": 22.0,
            "e14_raw": 2.0,
            "e14_clean": 2.0,
            "hour_heat_raw_gj": 22.0,
            "hour_heat_gj": 22.0,
            "hour_water_t": 2.0,
            "fault_tag": None,
        },
    ]
    trend_clean = rqs._build_trend_24h_from_rows(rows, {7: 1.5, 8: 2.0}, mode="clean")
    assert len(trend_clean) == 24
    assert trend_clean[7]["has_data"] is True
    assert trend_clean[7]["hour_heat_gj"] == 0.0
    assert trend_clean[7]["outdoor_temp"] == 1.5
    assert "hour_heat_gj" in trend_clean[7]["anomalies"]
    assert trend_clean[8]["hour_heat_gj"] == 22.0
    assert trend_clean[8]["anomalies"] == {}

    trend_raw = rqs._build_trend_24h_from_rows(rows, {7: 1.5, 8: 2.0}, mode="raw")
    assert trend_raw[7]["hour_heat_gj"] == 15483.87
    assert "突发热量跳变异常原值" in trend_raw[7]["anomalies"]["hour_heat_gj"]["note"]
