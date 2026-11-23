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


def test_hourly_and_daily_excel_export_with_24h_matrix_and_highlights():
    """验证逐小时 Excel 导出包含当天 24h 汇总/横表矩阵/突发跳变红底批注，以及日报 Excel 补齐商业户明细。"""
    from io import BytesIO
    import openpyxl
    from projects.smart_heating_platform.services import report_query_service as rqs

    trend = [
        {
            "hour": h,
            "label": f"{h:02d}:00",
            "has_data": True,
            "station_count": 2,
            "hour_heat_gj": 100.0 + h,
            "heat_index_wm2": 35.0,
            "avg_sup_temp": 80.0,
            "avg_ret_temp": 45.0,
            "outdoor_temp": 2.0,
            "anomalies": (
                {"hour_heat_gj": {"count": 1, "note": "受 1 项异常修正影响：国运壹号: 突发热量跳变已修正（原值 26338 → 修正 0 GJ）"}}
                if h == 15
                else {}
            ),
        }
        for h in range(24)
    ]
    sample_report = {
        "meta": {"date": "2026-11-20", "hour": 15, "mode": "clean"},
        "kpis": {"total_stations": 2},
        "trend_24h": trend,
        "group_summaries": {
            "by_center": [
                {
                    "group_key": 60, "group_name": "华乐服务中心", "online_stations": 2, "total_stations": 2,
                    "covered_area_wan": 20.0, "hour_heat_gj": 115.0, "instant_load_gjh": 110.0,
                    "heat_index_wm2": 35.0, "hour_water_t": 5.0, "avg_sup_temp": 80.0, "avg_ret_temp": 45.0,
                    "anomalies": {},
                }
            ],
            "by_rdfz": [],
            "by_branch": [],
        },
        "stations": [
            {
                "station_id": "S1", "name": "国运壹号", "center_name": "华乐服务中心", "rdfz": "东环",
                "branch_name": "促进路分支", "covered_area": 100000.0, "online": True,
                "e1": 100.0, "e3": 80.0, "e4": 45.0, "e7": 0.8, "e8": 0.5, "e11": 0.0,
                "hour_heat_gj": 0.0, "hour_heat_source": "FALLBACK_INTEGRAL_15M", "heat_index_wm2": 0.0,
                "hour_water_t": 2.0, "value_source": "MASKED_PREV_HOLD",
                "field_notes": {"hour_heat_gj": "国运壹号: 突发热量跳变已修正（原值 26338 → 修正 0 GJ）"},
            }
        ],
        "upstream_points": [],
        "merchants": [],
    }
    export_ctx = {
        "report": sample_report,
        "entity_trend": {"entity_name": "华乐服务中心", "station_count": 2, "trend_24h": trend},
        "center_matrix_24h": [
            {
                "name": "华乐服务中心", "covered_area_wan": 20.0, "hours": [10.0] * 24,
                "hour_notes": {15: "突发热量跳变"}, "day_heat_gj": 240.0, "heat_per_wan_gj": 12.0,
            }
        ],
        "rdfz_matrix_24h": [
            {
                "name": "东环", "covered_area_wan": 20.0, "hours": [10.0] * 24,
                "hour_notes": {}, "day_heat_gj": 240.0, "heat_per_wan_gj": 12.0,
            }
        ],
        "station_matrix_24h": [
            {
                "name": "国运壹号", "center_name": "华乐服务中心", "rdfz": "东环", "branch_name": "促进路分支",
                "covered_area": 100000.0, "hours": [10.0] * 24, "hour_notes": {15: "国运壹号: 突发热量跳变已修正"},
                "day_heat_gj": 240.0, "heat_per_wan_gj": 24.0, "anomaly_note": "15:00 突发热量跳变已修正",
            }
        ],
        "burst_events": [
            {"hour": 15, "label": "15:00", "entity_type": "换热站", "entity_name": "国运壹号", "metric": "小时供热量(GJ)", "note": "原值 26338 → 修正 0 GJ"}
        ],
    }

    xls_bytes = rqs.build_hourly_excel(sample_report, export_ctx=export_ctx)
    wb = openpyxl.load_workbook(BytesIO(xls_bytes))
    assert wb.sheetnames[:5] == [
        "全网24小时逐时统计",
        "华乐服务中心_24小时",
        "9大中心_24小时供热矩阵",
        "主干热网_24小时供热矩阵",
        "242站_24小时供热矩阵",
    ]
    assert "当日突发跳变记录" in wb.sheetnames
    ws1 = wb["全网24小时逐时统计"]
    # 第 15:00 行是第 17 行 (1表头 + 0..15共16行)，第3列小时供热量(GJ) 应标红且带批注
    c15 = ws1.cell(row=17, column=3)
    assert c15.fill.start_color.rgb.endswith("FEE2E2")
    assert c15.comment is not None and "国运壹号" in c15.comment.text
    assert ws1.cell(row=27, column=1).value == "全天合计/均值"

    ws_st_mat = wb["242站_24小时供热矩阵"]
    headers_st = [ws_st_mat.cell(row=1, column=i).value for i in range(1, ws_st_mat.max_column + 1)]
    assert "00:00" in headers_st and "23:00" in headers_st
    assert ws_st_mat.cell(row=2, column=6 + 15).fill.start_color.rgb.endswith("FEE2E2")

    daily_report_sample = {
        "meta": {"date": "2026-11-20", "period_mode": "natural", "mode": "clean", "window_start": "2026-11-20 00:00", "window_end": "2026-11-21 00:00"},
        "center_comparison": [
            {
                "center_name": "华乐服务中心", "covered_area_wan": 20.0, "sys_heat_gj": 220.0, "man_heat_gj": 180.0,
                "heat_diff_gj": 40.0, "heat_diff_pct": 22.22, "is_heat_alert": True, "heat_per_wan_gj": 11.0,
                "sys_water_t": 10.0, "man_water_t": 9.0, "avg_room_temp": 21.2, "anomalies": {},
            }
        ],
        "station_daily": [
            {
                "name": "国运壹号", "center_name": "华乐服务中心", "rdfz": "东环", "covered_area": 100000.0,
                "hours_count": 24, "meter_diff_hours": 22, "start_tot_j": 100.0, "end_tot_j": 320.0,
                "day_heat_gj": 220.0, "heat_per_wan_gj": 22.0, "day_flow_t": 5000.0, "day_water_t": 10.0,
                "day_elec_kwh": 300.0, "avg_sup_temp": 78.5, "avg_ret_temp": 44.2, "anomalies": {},
            }
        ],
        "merchant_daily": [{"name": "测试商业A", "rdfz": "东环", "rdry": "水", "rdss": "私有", "rdjg": "商业", "rdgz": "已改", "daily_consumption": 12.34, "daily_unit_heat": 0.5}],
    }
    daily_ctx = {
        "report": daily_report_sample,
        "date_labels": ["11-19", "11-20"],
        "tot_area_wan": 20.0,
        "daily_overview": [
            {"date": "2026-11-19", "avg_outdoor_temp": 3.0, "sys_heat_gj": 200.0, "man_heat_gj": 200.0, "heat_diff_gj": 0.0, "heat_diff_pct": 0.0, "heat_per_wan_gj": 10.0, "sys_water_t": 8.0, "man_water_t": 8.0, "merchant_heat_gj": 10.0, "anomaly_note": ""},
            {"date": "2026-11-20", "avg_outdoor_temp": 2.0, "sys_heat_gj": 220.0, "man_heat_gj": 180.0, "heat_diff_gj": 40.0, "heat_diff_pct": 22.22, "heat_per_wan_gj": 11.0, "sys_water_t": 10.0, "man_water_t": 9.0, "merchant_heat_gj": 12.34, "anomaly_note": "15:00 国运壹号 突跳"},
        ],
        "center_matrix": [
            {"name": "华乐服务中心", "covered_area_wan": 20.0, "values": [200.0, 220.0], "diff_pcts": [0.0, 22.22], "day_notes": {1: "突发跳变"}, "sum_heat_gj": 420.0, "avg_per_wan_gj": 10.5}
        ],
        "station_matrix": [
            {"name": "国运壹号", "center_name": "华乐服务中心", "rdfz": "东环", "covered_area": 100000.0, "values": [200.0, 220.0], "day_notes": {1: "突发跳变"}, "sum_heat_gj": 420.0, "avg_per_wan_gj": 21.0, "anomaly_summary": "11-20 突跳"}
        ],
    }
    daily_bytes = rqs.build_daily_excel(daily_report_sample, export_ctx=daily_ctx)
    wb_daily = openpyxl.load_workbook(BytesIO(daily_bytes))
    assert wb_daily.sheetnames == [
        "全网逐日统计总览",
        "9大中心_逐日供热矩阵",
        "9大中心_逐日双轨偏差率",
        "242站_逐日供热矩阵",
        "11-20_9大中心核对",
        "11-20_242站日耗",
        "11-20_464商业用户",
    ]
    assert wb_daily["全网逐日统计总览"].cell(row=4, column=1).value == "期间合计/均值"
    assert wb_daily["9大中心_逐日双轨偏差率"].cell(row=2, column=4).fill.start_color.rgb.endswith("FEF3C7")
    assert wb_daily["11-20_242站日耗"].cell(row=1, column=5).value == "有效热量小时"
    assert wb_daily["11-20_242站日耗"].cell(row=2, column=15).value == 78.5
    assert wb_daily["11-20_464商业用户"].cell(row=1, column=3).value == "介质 (rdry)"
    assert wb_daily["11-20_464商业用户"].cell(row=1, column=9).value == "计算状态"
    assert wb_daily["11-20_464商业用户"].cell(row=2, column=7).value == 12.34
    assert wb_daily["11-20_464商业用户"].cell(row=2, column=9).value == "正常"
    assert wb_daily["11-20_464商业用户"].cell(row=3, column=7).value == 12.34


def test_daily_report_station_missing_end_meter_and_merchant_breakdown(monkeypatch):
    """验证无热量读数站不计有效小时且耗热为None、止表取结算结束时刻、商户三类统计精确拆分。"""
    from types import SimpleNamespace
    import backend.projects.smart_heating_platform.services.report_query_service as rqs

    class _FakeRes:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            sql = str(stmt)
            if "FROM smart_heating_platform.dict_service_center" in sql:
                return _FakeRes([SimpleNamespace(_mapping={"center_id": 63, "name": "香炉礁中心"})])
            if "FROM smart_heating_platform.dict_heating_station" in sql:
                return _FakeRes([
                    SimpleNamespace(
                        station_id="ST_XLJ",
                        _mapping={
                            "station_id": "ST_XLJ",
                            "name": "香炉礁",
                            "center_id": 63,
                            "center_name": "香炉礁中心",
                            "covered_area": 100000.0,
                            "rdfz": "香海",
                        },
                    ),
                    SimpleNamespace(
                        station_id="ST_EMPTY",
                        _mapping={
                            "station_id": "ST_EMPTY",
                            "name": "东北名苑",
                            "center_id": 63,
                            "center_name": "香炉礁中心",
                            "covered_area": 50000.0,
                            "rdfz": "北海",
                        },
                    ),
                ])
            if "WHERE biz_hour = :we" in sql:
                return _FakeRes([
                    SimpleNamespace(station_id="ST_XLJ", tot_j=1420527.30),
                    SimpleNamespace(station_id="ST_EMPTY", tot_j=None),
                ])
            if "FROM smart_heating_platform.fact_station_hourly" in sql:
                rows = []
                for h in range(24):
                    bh = datetime(2026, 11, 20, h, 0, tzinfo=EAST_8)
                    rows.append(
                        SimpleNamespace(
                            biz_hour=bh,
                            station_id="ST_XLJ",
                            e1_raw=100.0, e1_clean=100.0,
                            e3_raw=75.0, e3_clean=75.0,
                            e4_raw=45.0, e4_clean=45.0,
                            e7_raw=0.8, e7_clean=0.8,
                            e8_raw=0.5, e8_clean=0.5,
                            e11_raw=37.0, e11_clean=37.0,
                            e14_raw=1.0, e14_clean=1.0,
                            tot_j=1419634.24 if h == 0 else (1420490.01 if h == 23 else 1419634.24 + h * 37.2),
                            hour_heat_raw_gj=37.2108,
                            hour_heat_gj=37.2108,
                            hour_heat_source="METER_DIFF",
                            hour_flow_t=100.0,
                            hour_water_t=1.0,
                            hour_elec_kwh=10.0,
                            value_source="REAL",
                            fault_tag=None,
                            _mapping={
                                "biz_hour": bh, "station_id": "ST_XLJ",
                                "e1_raw": 100.0, "e1_clean": 100.0, "e3_raw": 75.0, "e3_clean": 75.0,
                                "e4_raw": 45.0, "e4_clean": 45.0, "e7_raw": 0.8, "e7_clean": 0.8,
                                "e8_raw": 0.5, "e8_clean": 0.5, "e11_raw": 37.0, "e11_clean": 37.0,
                                "e14_raw": 1.0, "e14_clean": 1.0, "tot_j": 1419634.24,
                                "hour_heat_raw_gj": 37.2108, "hour_heat_gj": 37.2108,
                                "hour_heat_source": "METER_DIFF", "hour_flow_t": 100.0,
                                "hour_water_t": 1.0, "hour_elec_kwh": 10.0,
                                "value_source": "REAL", "fault_tag": None,
                            },
                        )
                    )
                    # 东北名苑有24条小时记录（如供回温有数），但全天没有热量与表底读数
                    rows.append(
                        SimpleNamespace(
                            biz_hour=bh,
                            station_id="ST_EMPTY",
                            e1_raw=None, e1_clean=None,
                            e3_raw=70.0, e3_clean=70.0,
                            e4_raw=35.0, e4_clean=35.0,
                            e7_raw=0.9, e7_clean=0.9,
                            e8_raw=0.4, e8_clean=0.4,
                            e11_raw=None, e11_clean=None,
                            e14_raw=None, e14_clean=None,
                            tot_j=None,
                            hour_heat_raw_gj=None,
                            hour_heat_gj=None,
                            hour_heat_source="INTEGRAL_15M",
                            hour_flow_t=None,
                            hour_water_t=None,
                            hour_elec_kwh=None,
                            value_source="REAL",
                            fault_tag=None,
                            _mapping={
                                "biz_hour": bh, "station_id": "ST_EMPTY",
                                "e1_raw": None, "e1_clean": None, "e3_raw": 70.0, "e3_clean": 70.0,
                                "e4_raw": 35.0, "e4_clean": 35.0, "e7_raw": 0.9, "e7_clean": 0.9,
                                "e8_raw": 0.4, "e8_clean": 0.4, "e11_raw": None, "e11_clean": None,
                                "e14_raw": None, "e14_clean": None, "tot_j": None,
                                "hour_heat_raw_gj": None, "hour_heat_gj": None,
                                "hour_heat_source": "INTEGRAL_15M", "hour_flow_t": None,
                                "hour_water_t": None, "hour_elec_kwh": None,
                                "value_source": "REAL", "fault_tag": None,
                            },
                        )
                    )
                return _FakeRes(rows)
            if "FROM smart_heating_platform.dict_merchant" in sql:
                return _FakeRes([
                    SimpleNamespace(_mapping={
                        "merchant_id": "M1", "name": "正常商户", "rdfz": "南环", "rdry": "高温水",
                        "rdss": "私有", "rdjg": "商业", "rdgz": "已改",
                        "fact_id": 1, "daily_consumption": 15.2, "daily_unit_heat": 0.4,
                        "raw_payload": {"tot_prev": 100.0, "tot_curr": 115.2},
                    }),
                    SimpleNamespace(_mapping={
                        "merchant_id": "M2", "name": "云河会馆", "rdfz": "南环", "rdry": "高温水",
                        "rdss": "私有", "rdjg": "商业", "rdgz": "已改",
                        "fact_id": 2, "daily_consumption": None, "daily_unit_heat": -1333.0,
                        "raw_payload": {"tot_prev": 1333.0, "tot_curr": 0.0, "unit": -1333},
                    }),
                    SimpleNamespace(_mapping={
                        "merchant_id": "M3", "name": "新华医院", "rdfz": "南环", "rdry": "高温水",
                        "rdss": "私有", "rdjg": "商业", "rdgz": "已改",
                        "fact_id": None, "daily_consumption": None, "daily_unit_heat": None,
                        "raw_payload": None,
                    }),
                ])
            return _FakeRes([])

    monkeypatch.setattr(rqs, "engine", SimpleNamespace(connect=lambda: _FakeConn()))
    monkeypatch.setattr(rqs, "get_collector_settings_view", lambda: {"snapshot_interval_minutes": 5})

    rep = rqs.get_daily_report("2026-11-20", period_mode="natural", mode="clean")
    st_map = {s["name"]: s for s in rep["station_daily"]}

    # 1. 香炉礁：止表底取到 2026-11-21 00:00 的 1420527.30，与起表底 1419634.24 相差 893.06 GJ
    xlj = st_map["香炉礁"]
    assert xlj["hours_count"] == 24
    assert xlj["start_tot_j"] == 1419634.24
    assert xlj["end_tot_j"] == 1420527.3
    assert round(xlj["end_tot_j"] - xlj["start_tot_j"], 2) == 893.06
    assert xlj["day_heat_gj"] == 893.06

    # 2. 东北名苑：24小时均无热量读数 -> 有效小时 0，日耗/万平/流量/补水/电耗均为 None（不再显示 24h / 0）
    dmy = st_map["东北名苑"]
    assert dmy["hours_count"] == 0
    assert dmy["meter_diff_hours"] == 0
    assert dmy["day_heat_gj"] is None
    assert dmy["heat_per_wan_gj"] is None
    assert dmy["day_flow_t"] is None
    assert dmy["day_water_t"] is None
    assert dmy["day_elec_kwh"] is None

    # 3. 商业用户三类拆分汇总及单户状态
    assert rep["merchant_summary"] == {
        "total_count": 3,
        "valid_count": 1,
        "missing_record_count": 1,
        "rollback_count": 1,
    }
    mc_map = {m["name"]: m for m in rep["merchant_daily"]}
    assert mc_map["正常商户"]["calc_status"] == "VALID"
    assert mc_map["云河会馆"]["calc_status"] == "METER_ROLLBACK"
    assert mc_map["云河会馆"]["daily_unit_heat"] is None
    assert "1333" in mc_map["云河会馆"]["status_note"]
    assert mc_map["新华医院"]["calc_status"] == "MISSING_RECORD"
    assert "/getall_bb_shrb/" in mc_map["新华医院"]["status_note"]


def test_oscillating_elec_water_meter_isolation_and_daily_dual_track(monkeypatch):
    """验证电表/水表锯齿倒走序列拦截与超限屏蔽，以及日报手工耗电(万kWh折算)和耗水双轨对比。"""
    from datetime import timedelta
    from types import SimpleNamespace
    import backend.projects.smart_heating_platform.services.cleaning_engine as ce
    import backend.projects.smart_heating_platform.services.report_query_service as rqs

    # 1. cleaning_engine 锯齿序列识别与按面积上限
    t0 = datetime(2026, 11, 21, 0, 0, tzinfo=EAST_8)
    osc_seq = [
        (t0, 5812412.5),
        (t0 + timedelta(minutes=15), 5812340.5),
        (t0 + timedelta(minutes=30), 5812218.0),
        (t0 + timedelta(minutes=45), 5812750.5),
    ]
    is_osc, msg = ce.is_meter_sequence_oscillating(osc_seq, min_reversal=1.0)
    assert is_osc is True and "2次" in (msg or "")
    assert ce.station_max_hourly_elec_kwh(83348.24) == round(83348.24 * 0.0012, 4)

    class _FakeRes:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

    class _FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            sql = str(stmt)
            if "FROM smart_heating_platform.dict_service_center" in sql:
                return _FakeRes([SimpleNamespace(_mapping={"center_id": 61, "name": "北岗服务中心"})])
            if "FROM smart_heating_platform.dict_heating_station" in sql:
                return _FakeRes([
                    SimpleNamespace(station_id="ST_NORM", _mapping={"station_id": "ST_NORM", "name": "正常站", "center_id": 61, "center_name": "北岗服务中心", "covered_area": 100000.0, "rdfz": "南环"}),
                    SimpleNamespace(station_id="ST_BAD_E", _mapping={"station_id": "ST_BAD_E", "name": "信兴花园", "center_id": 61, "center_name": "北岗服务中心", "covered_area": 83348.24, "rdfz": "南环"}),
                    SimpleNamespace(station_id="ST_BAD_W", _mapping={"station_id": "ST_BAD_W", "name": "坏水表站", "center_id": 61, "center_name": "北岗服务中心", "covered_area": 50000.0, "rdfz": "南环"}),
                ])
            if "FROM smart_heating_platform.fact_station_hourly" in sql and "WHERE biz_hour >= :ws" in sql:
                rows = []
                for h in range(4):
                    bh = datetime(2026, 11, 20, h, 0, tzinfo=EAST_8)
                    rows.append(SimpleNamespace(
                        biz_hour=bh, station_id="ST_NORM",
                        e1_raw=40.0, e1_clean=40.0, e3_raw=78.0, e3_clean=78.0, e4_raw=42.0, e4_clean=42.0,
                        e7_raw=0.8, e7_clean=0.8, e8_raw=0.4, e8_clean=0.4, e11_raw=10.0, e11_clean=10.0,
                        e14_raw=2.0, e14_clean=2.0, tot_j=100.0 + h * 10.0,
                        hour_heat_raw_gj=10.0, hour_heat_gj=10.0, hour_heat_source="METER_DIFF",
                        hour_flow_t=40.0, hour_water_t=2.0, hour_elec_kwh=25.0,
                        tot_water_f254=1000.0 + h * 2.0, tot_elec_f253=5000.0 + h * 25.0,
                        value_source="REAL", fault_tag=None,
                        _mapping={
                            "biz_hour": bh, "station_id": "ST_NORM", "e1_raw": 40.0, "e1_clean": 40.0,
                            "e3_raw": 78.0, "e3_clean": 78.0, "e4_raw": 42.0, "e4_clean": 42.0,
                            "e7_raw": 0.8, "e7_clean": 0.8, "e8_raw": 0.4, "e8_clean": 0.4,
                            "e11_raw": 10.0, "e11_clean": 10.0, "e14_raw": 2.0, "e14_clean": 2.0,
                            "tot_j": 100.0 + h * 10.0, "hour_heat_raw_gj": 10.0, "hour_heat_gj": 10.0,
                            "hour_heat_source": "METER_DIFF", "hour_flow_t": 40.0, "hour_water_t": 2.0,
                            "hour_elec_kwh": 25.0, "tot_water_f254": 1000.0 + h * 2.0, "tot_elec_f253": 5000.0 + h * 25.0,
                            "value_source": "REAL", "fault_tag": None,
                        },
                    ))
                    tot_e_bad = [5812441.0, 5812700.3, 5812306.8, 5838037.5][h]
                    hr_e_bad = [259.3, None, 262.7, None][h]
                    rows.append(SimpleNamespace(
                        biz_hour=bh, station_id="ST_BAD_E",
                        e1_raw=35.0, e1_clean=35.0, e3_raw=78.0, e3_clean=78.0, e4_raw=42.0, e4_clean=42.0,
                        e7_raw=0.8, e7_clean=0.8, e8_raw=0.4, e8_clean=0.4, e11_raw=5.0, e11_clean=5.0,
                        e14_raw=0.0, e14_clean=0.0, tot_j=200.0 + h * 5.0,
                        hour_heat_raw_gj=5.0, hour_heat_gj=5.0, hour_heat_source="METER_DIFF",
                        hour_flow_t=35.0, hour_water_t=0.0, hour_elec_kwh=hr_e_bad,
                        tot_water_f254=10.0, tot_elec_f253=tot_e_bad,
                        value_source="REAL", fault_tag=None,
                        _mapping={
                            "biz_hour": bh, "station_id": "ST_BAD_E", "e1_raw": 35.0, "e1_clean": 35.0,
                            "e3_raw": 78.0, "e3_clean": 78.0, "e4_raw": 42.0, "e4_clean": 42.0,
                            "e7_raw": 0.8, "e7_clean": 0.8, "e8_raw": 0.4, "e8_clean": 0.4,
                            "e11_raw": 5.0, "e11_clean": 5.0, "e14_raw": 0.0, "e14_clean": 0.0,
                            "tot_j": 200.0 + h * 5.0, "hour_heat_raw_gj": 5.0, "hour_heat_gj": 5.0,
                            "hour_heat_source": "METER_DIFF", "hour_flow_t": 35.0, "hour_water_t": 0.0,
                            "hour_elec_kwh": hr_e_bad, "tot_water_f254": 10.0, "tot_elec_f253": tot_e_bad,
                            "value_source": "REAL", "fault_tag": None,
                        },
                    ))
                    tot_w_bad = [300.0, 290.0, 310.0, 295.0][h]
                    hr_w_bad = [15.0, None, 20.0, None][h]
                    rows.append(SimpleNamespace(
                        biz_hour=bh, station_id="ST_BAD_W",
                        e1_raw=20.0, e1_clean=20.0, e3_raw=78.0, e3_clean=78.0, e4_raw=42.0, e4_clean=42.0,
                        e7_raw=0.8, e7_clean=0.8, e8_raw=0.4, e8_clean=0.4, e11_raw=4.0, e11_clean=4.0,
                        e14_raw=1.0, e14_clean=1.0, tot_j=300.0 + h * 4.0,
                        hour_heat_raw_gj=4.0, hour_heat_gj=4.0, hour_heat_source="METER_DIFF",
                        hour_flow_t=20.0, hour_water_t=hr_w_bad, hour_elec_kwh=10.0,
                        tot_water_f254=tot_w_bad, tot_elec_f253=2000.0 + h * 10.0,
                        value_source="REAL", fault_tag=None,
                        _mapping={
                            "biz_hour": bh, "station_id": "ST_BAD_W", "e1_raw": 20.0, "e1_clean": 20.0,
                            "e3_raw": 78.0, "e3_clean": 78.0, "e4_raw": 42.0, "e4_clean": 42.0,
                            "e7_raw": 0.8, "e7_clean": 0.8, "e8_raw": 0.4, "e8_clean": 0.4,
                            "e11_raw": 4.0, "e11_clean": 4.0, "e14_raw": 1.0, "e14_clean": 1.0,
                            "tot_j": 300.0 + h * 4.0, "hour_heat_raw_gj": 4.0, "hour_heat_gj": 4.0,
                            "hour_heat_source": "METER_DIFF", "hour_flow_t": 20.0, "hour_water_t": hr_w_bad,
                            "hour_elec_kwh": 10.0, "tot_water_f254": tot_w_bad, "tot_elec_f253": 2000.0 + h * 10.0,
                            "value_source": "REAL", "fault_tag": None,
                        },
                    ))
                return _FakeRes(rows)
            if "FROM public.daily_basic_data" in sql:
                return _FakeRes([
                    SimpleNamespace(company="BeiGang_Center", item="consumption_station_heat", value=80.0, unit="GJ"),
                    SimpleNamespace(company="BeiGang_Center", item="consumption_station_fill_water", value=10.0, unit="吨"),
                    SimpleNamespace(company="BeiGang_Center", item="consumption_station_purchased_power", value=0.02, unit="万kWh"),
                ])
            return _FakeRes([])

    monkeypatch.setattr(rqs, "engine", SimpleNamespace(connect=lambda: _FakeConn()))
    monkeypatch.setattr(rqs, "get_collector_settings_view", lambda: {"snapshot_interval_minutes": 5})

    rep = rqs.get_daily_report("2026-11-20", period_mode="natural", mode="clean")
    st_map = {s["name"]: s for s in rep["station_daily"]}
    # 信兴花园电表被隔离，不贡献虚假 522 kWh；正常站(100) + 坏水表站电表(40) = 140 kWh
    assert st_map["信兴花园"]["day_elec_kwh"] is None
    assert "day_elec_kwh" in st_map["信兴花园"]["anomalies"]
    assert st_map["坏水表站"]["day_water_t"] is None
    assert "day_water_t" in st_map["坏水表站"]["anomalies"]

    # 日报手工水/电双轨对比：手工 0.02 万kWh -> 200 kWh，系统 140 kWh -> 偏差 -60 kWh (-30%)
    cc = rep["center_comparison"][0]
    assert cc["sys_water_t"] == 8.0 and cc["man_water_t"] == 10.0
    assert cc["water_diff_t"] == -2.0 and cc["water_diff_pct"] == -20.0 and cc["is_water_alert"] is True
    assert cc["sys_elec_kwh"] == 140.0 and cc["man_elec_kwh"] == 200.0
    assert cc["elec_diff_kwh"] == -60.0 and cc["elec_diff_pct"] == -30.0 and cc["is_elec_alert"] is True
    assert rep["kpis"]["manual_total_elec_kwh"] == 200.0
    assert rep["kpis"]["elec_diff_pct"] == -30.0
    assert rep["kpis"]["manual_total_water_t"] == 10.0
    assert rep["kpis"]["water_diff_pct"] == -20.0



def test_dashboard_overview_api_and_deltas(monkeypatch):
    """验证领导驾驶舱 /reports/dashboard 载荷包含昨日同期对比、24h/7d 气温供热趋势与重点榜单。"""
    from types import SimpleNamespace
    import backend.projects.smart_heating_platform.services.report_query_service as rqs

    fake_curr = {
        "meta": {"date": "2026-11-20", "hour": 10, "biz_hour_label": "2026-11-20 10:00", "mode": "clean"},
        "kpis": {
            "outdoor_temp": 2.0,
            "covered_area_m2": 23000000.0,
            "covered_area_wan": 2300.0,
            "online_stations": 240,
            "total_stations": 242,
            "hour_heat_gj": 1500.0,
            "heat_index_wm2": 36.2,
            "heat_per_wan_gj": 0.65,
            "hour_water_t": 120.0,
            "water_per_wan_t": 0.05,
            "hour_elec_kwh": 240.0,
            "elec_per_wan_kwh": 0.1,
            "avg_sup_temp": 78.0,
            "avg_ret_temp": 44.0,
            "avg_temp_diff": 34.0,
            "avg_room_temp": None,
            "temp_pass_rate_pct": None,
            "temp_comfort_rate_pct": None,
        },
        "trend_24h": [
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "has_data": h <= 10,
                "hour_heat_gj": 100.0 + h if h <= 10 else None,
                "heat_index_wm2": 35.0 if h <= 10 else None,
                "outdoor_temp": 1.0 + h * 0.1 if h <= 10 else None,
            }
            for h in range(24)
        ],
        "group_summaries": {
            "by_center": [
                {
                    "group_key": 60, "group_name": "华乐服务中心", "covered_area_wan": 300.0,
                    "online_stations": 30, "total_stations": 30, "hour_heat_gj": 200.0,
                    "heat_per_wan_gj": 0.67, "heat_index_wm2": 37.0, "avg_room_temp": None,
                    "temp_pass_rate_pct": None,
                }
            ],
            "by_rdfz": [
                {
                    "group_key": "香海", "group_name": "香海", "covered_area_wan": 1000.0,
                    "hour_heat_gj": 700.0, "heat_per_wan_gj": 0.7, "avg_room_temp": None,
                }
            ],
        },
        "stations": [
            {
                "station_id": "S1", "name": "高热测试站", "center_name": "华乐服务中心",
                "covered_area": 50000.0, "heat_index_wm2": 65.0, "hour_heat_gj": 11.7,
                "hour_water_t": 8.0, "e14": 8.0, "hour_elec_kwh": 88.0, "avg_room_temp": None, "temp_pass_rate_pct": None,
            },
            {
                "station_id": "S2", "name": "标杆测试站", "center_name": "华乐服务中心",
                "covered_area": 50000.0, "heat_index_wm2": 28.0, "hour_heat_gj": 5.0,
                "hour_water_t": 0.5, "e14": 0.5, "hour_elec_kwh": 24.0, "avg_room_temp": None, "temp_pass_rate_pct": None,
            },
            {
                "station_id": "S_FAULT", "name": "故障高耗假站点", "center_name": "华乐服务中心",
                "covered_area": 50000.0, "heat_index_wm2": 120.0, "hour_heat_gj": 22.0,
                "hour_water_t": 20.0, "e14": 20.0, "hour_elec_kwh": 300.0, "fault_tag": "SOFTWARE_DEFECT", "day_anomaly_count": 8,
            },
            {
                "station_id": "S_ZERO", "name": "零能耗异常站", "center_name": "华乐服务中心",
                "covered_area": 50000.0, "heat_index_wm2": 0.0, "hour_heat_gj": 0.0,
                "hour_water_t": 15.0, "e14": 15.0, "hour_elec_kwh": 180.0,
            },
        ],
        "merchant_summary": {"total_merchants": 464, "active_heat_merchants": 300, "total_hour_heat_gj": 180.0},
        "temp_summary": {
            "valid_devices": 0,
            "distribution": {"under_18": 0, "ok_18_20": 0, "comfort_20_25": 0, "over_25": 0},
            "station_rankings": [],
        },
    }

    monkeypatch.setattr(rqs, "get_hourly_report", lambda **kw: fake_curr)
    monkeypatch.setattr(rqs, "_load_outdoor_temps_24h", lambda d: {10: 4.0})
    monkeypatch.setattr(
        rqs,
        "_build_trend_24h_from_rows",
        lambda rows, out, mode, temp_24h_map=None: [
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "has_data": h == 10,
                "hour_heat_gj": 1250.0 if h == 10 else None,
                "heat_index_wm2": 30.0 if h == 10 else None,
                "outdoor_temp": 4.0 if h == 10 else None,
            }
            for h in range(24)
        ],
    )

    class _MockRes:
        def __init__(self, rows):
            self._rows = rows

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def scalar(self):
            return self._rows[0] if self._rows else None

    class _MockConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            s = str(stmt)
            if "SUM(COALESCE(hour_water_t" in s:
                return _MockRes([SimpleNamespace(water_sum=100.0, elec_sum=200.0)])
            if "MAX(biz_hour) FROM smart_heating_platform.fact_temp_hourly" in s:
                return _MockRes([datetime(2026, 11, 20, 14, 0, tzinfo=EAST_8)])
            if "FROM smart_heating_platform.fact_temp_hourly t" in s:
                return _MockRes([
                    SimpleNamespace(station_id="S2", station_name="标杆测试站", center_id=60, center_name="华乐服务中心", rdfz="香海", temp_clean=21.2),
                    SimpleNamespace(station_id="S3", station_name="低温关注站", center_id=60, center_name="华乐服务中心", rdfz="香海", temp_clean=17.4),
                ])
            if "DATE_TRUNC('hour', biz_hour" in s:
                return _MockRes([SimpleNamespace(bh=datetime(2026, 11, 20, 10, 0), hour_heat_gj=1500.0, instant_load_gjh=1500.0, station_count=242)])
            if "DATE_TRUNC('hour', date_time)" in s:
                return _MockRes([SimpleNamespace(bh=datetime(2026, 11, 20, 10, 0), val=2.0)])
            if "GROUP BY 1 ORDER BY 1" in s and "fact_station_hourly" in s:
                from datetime import date
                return _MockRes([SimpleNamespace(d=date(2026, 11, 20), day_heat=35000.0, day_water=4000.0, hrs_cnt=24)])
            return _MockRes([])

    monkeypatch.setattr(rqs, "engine", SimpleNamespace(connect=lambda: _MockConn()))
    ov = rqs.get_dashboard_overview("2026-11-20", 10, "clean")

    assert ov["comparison"]["heat_diff_pct"] == 20.0
    assert ov["comparison"]["outdoor_diff_c"] == -2.0
    assert ov["comparison"]["water_diff_pct"] == 20.0
    assert ov["comparison"]["elec_diff_pct"] == 20.0
    assert len(ov["trend_72h"]) == 72
    assert any(pt["hour_heat_gj"] == 1500.0 and pt["outdoor_temp"] == 2.0 for pt in ov["trend_72h"])
    assert len(ov["trend_24h"]) == 24
    assert ov["trend_24h"][10]["prev_hour_heat_gj"] == 1250.0
    assert ov["trend_24h"][10]["avg_room_temp"] is None
    assert len(ov["trend_7d"]) == 7
    assert "avg_room_temp" not in ov["trend_7d"][0]
    assert ov["current_temp"]["biz_hour_label"] == "2026-11-20 14:00"
    assert ov["current_temp"]["avg_room_temp"] == 19.3
    assert ov["watchlists"]["high_heat"][0]["name"] == "高热测试站"
    assert ov["watchlists"]["high_water"][0]["name"] == "高热测试站"
    assert ov["watchlists"]["high_elec"][0]["name"] == "高热测试站"
    assert ov["watchlists"]["benchmark"][0]["name"] == "标杆测试站"
    assert "low_temp" not in ov["watchlists"]
    for wl_key in ("high_heat", "high_water", "high_elec", "benchmark"):
        names = {it["name"] for it in ov["watchlists"][wl_key]}
        assert "故障高耗假站点" not in names
        assert "零能耗异常站" not in names
        assert all("avg_room_temp" not in it for it in ov["watchlists"][wl_key])
    assert "低温预警站" in " ".join(ov["brief"]["highlights"])

    app = create_app()
    client = TestClient(app)
    app.dependency_overrides[get_current_session] = lambda: _session("Group_admin")
    assert client.get("/api/v1/projects/smart_heating_platform/reports/dashboard").status_code == 403
    app.dependency_overrides[get_current_session] = lambda: _session("Global_admin")
    resp = client.get("/api/v1/projects/smart_heating_platform/reports/dashboard?date=2026-11-20&hour=10")
    assert resp.status_code == 200 and resp.json()["ok"] is True
    assert resp.json()["data"]["comparison"]["heat_diff_pct"] == 20.0


def test_f209_capture_and_hour_water_integral_fallback(monkeypatch):
    import backend.projects.smart_heating_platform.services.collector_engine as ce

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
    hr07 = datetime(2026, 11, 18, 7, 0, tzinfo=EAST_8)

    # 1. 无 f254 累计水表，仅上报瞬时补水流量 f209：应采集至 e14_raw/e14_clean 且 hour_water_t 回落 INTEGRAL_15M 积分
    def _fake_f209_only(client, url, data=None, headers=None, retries=2):
        return _FakeResp([
            {"create_time": "2026-11-18 07:00:00", "f1": 0.4, "f2": 100.0, "f3": 65.0, "f4": 0.3, "f5": 40.0, "f209": 10.0, "f220": 500.0, "f221": 1000.0, "f222": 10.0, "f253": None, "f254": None},
            {"create_time": "2026-11-18 07:30:00", "f1": 0.4, "f2": 100.0, "f3": 65.0, "f4": 0.3, "f5": 40.0, "f209": 14.0, "f220": 550.0, "f221": 1005.0, "f222": 10.0, "f253": None, "f254": None},
            {"create_time": "2026-11-18 08:00:00", "f1": 0.4, "f2": 100.0, "f3": 65.0, "f4": 0.3, "f5": 40.0, "f209": 10.0, "f220": 600.0, "f221": 1010.0, "f222": 10.0, "f253": None, "f254": None},
        ])

    monkeypatch.setattr(ce, "_post_with_retry", _fake_f209_only)
    _, rows1, faults1, ok1 = ce._process_station_calibration(
        {"station_id": "st_fhly", "name": "泛华领域", "covered_area": 100000.0},
        "http://mock",
        "2026-11-18 06:30:00",
        "2026-11-18 08:30:00",
        [hr07],
        10.0,
        prev_station_db=None,
    )
    assert ok1 is True and len(rows1) == 1
    assert rows1[0]["e14_raw"] == 10.0
    assert rows1[0]["e14_clean"] == 10.0
    assert rows1[0]["hour_water_t"] == 12.0
    assert rows1[0]["hour_water_source"] == "INTEGRAL_15M"
    assert faults1 == []

    # 2. f209 超上限 (>100 t/h) 满量程坏表样本应被过滤（e14_clean 置空、积分不带入坏值），
    # 且 f253 锯齿坏表应置空 hour_elec_kwh 并记录 METER_JUMP
    def _fake_bad_f209_and_osc_e(client, url, data=None, headers=None, retries=2):
        return _FakeResp([
            {"create_time": "2026-11-18 07:00:00", "f1": 0.4, "f2": 80.0, "f3": 60.0, "f4": 0.3, "f5": 40.0, "f209": 6.0, "f220": 200.0, "f221": 300.0, "f222": 8.0, "f253": 100.0, "f254": None},
            {"create_time": "2026-11-18 07:15:00", "f1": 0.4, "f2": 80.0, "f3": 60.0, "f4": 0.3, "f5": 40.0, "f209": 999.0, "f220": 220.0, "f221": 302.0, "f222": 8.0, "f253": 108.0, "f254": None},
            {"create_time": "2026-11-18 07:30:00", "f1": 0.4, "f2": 80.0, "f3": 60.0, "f4": 0.3, "f5": 40.0, "f209": 8.0, "f220": 240.0, "f221": 304.0, "f222": 8.0, "f253": 100.0, "f254": None},
            {"create_time": "2026-11-18 07:45:00", "f1": 0.4, "f2": 80.0, "f3": 60.0, "f4": 0.3, "f5": 40.0, "f209": 7.0, "f220": 260.0, "f221": 306.0, "f222": 8.0, "f253": 109.0, "f254": None},
            {"create_time": "2026-11-18 08:00:00", "f1": 0.4, "f2": 80.0, "f3": 60.0, "f4": 0.3, "f5": 40.0, "f209": 200.0, "f220": 280.0, "f221": 308.0, "f222": 8.0, "f253": 100.0, "f254": None},
        ])

    monkeypatch.setattr(ce, "_post_with_retry", _fake_bad_f209_and_osc_e)
    _, rows2, faults2, ok2 = ce._process_station_calibration(
        {"station_id": "st_xxhy", "name": "信兴花园", "covered_area": 50000.0},
        "http://mock",
        "2026-11-18 06:30:00",
        "2026-11-18 08:30:00",
        [hr07],
        10.0,
        prev_station_db={"e14_clean": 5.5},
    )
    assert ok2 is True and len(rows2) == 1
    assert rows2[0]["e14_raw"] == 200.0
    assert rows2[0]["e14_clean"] == 5.5
    assert rows2[0]["hour_water_t"] == 7.1667
    assert rows2[0]["hour_water_source"] == "INTEGRAL_15M"
    assert rows2[0]["hour_elec_kwh"] is None
    assert rows2[0]["hour_elec_source"] == "NONE"
    assert any(f["fault_code"] == FAULT_SENSOR_RANGE for f in faults2)
    assert any(f["fault_code"] == ce.FAULT_METER_JUMP for f in faults2)


def test_fault_coverage_diagnostics_and_api(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from backend.services.auth_manager import get_current_session
    import backend.projects.smart_heating_platform.services.report_query_service as rqs

    class _Row(SimpleNamespace):
        @property
        def _mapping(self):
            return self.__dict__

    def _session(group):
        return _Row(username="tester", group=group, company="GongRe", has_project_access=lambda pid: True)

    class _MockRes:
        def __init__(self, rows=None, scalar=None):
            self._rows = rows or []
            self._scalar = scalar

        def fetchall(self):
            return self._rows

        def scalar_one(self):
            return self._scalar

    class _MockConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, stmt, params=None):
            s = str(stmt)
            if "FROM smart_heating_platform.dict_heating_station" in s:
                return _MockRes([
                    _Row(station_id="S1", name="正常站", covered_area=100000.0, rdfz="香海", center_name="华乐服务中心"),
                    _Row(station_id="S2", name="缺表积分站", covered_area=100000.0, rdfz="香海", center_name="华乐服务中心"),
                    _Row(station_id="S3", name="双缺坏表站", covered_area=None, rdfz="香海", center_name="华乐服务中心"),
                ])
            if "FROM smart_heating_platform.fact_station_hourly" in s:
                return _MockRes([
                    _Row(biz_hour=datetime(2026, 11, 18, 10, 0, tzinfo=EAST_8), station_id="S1", hour_heat_gj=20.0, hour_heat_source="METER_DIFF", hour_water_t=2.0, hour_water_source="METER_DIFF", hour_elec_kwh=40.0, hour_elec_source="METER_DIFF", e14_clean=2.0, tot_water_f254=100.0, tot_elec_f253=500.0, value_source="REAL", fault_tag=None),
                    _Row(biz_hour=datetime(2026, 11, 18, 11, 0, tzinfo=EAST_8), station_id="S1", hour_heat_gj=21.0, hour_heat_source="METER_DIFF", hour_water_t=2.0, hour_water_source="METER_DIFF", hour_elec_kwh=42.0, hour_elec_source="METER_DIFF", e14_clean=2.0, tot_water_f254=102.0, tot_elec_f253=542.0, value_source="REAL", fault_tag=None),
                    _Row(biz_hour=datetime(2026, 11, 18, 10, 0, tzinfo=EAST_8), station_id="S2", hour_heat_gj=15.0, hour_heat_source="INTEGRAL_15M", hour_water_t=12.0, hour_water_source="INTEGRAL_15M", hour_elec_kwh=None, hour_elec_source="NONE", e14_clean=12.0, tot_water_f254=None, tot_elec_f253=0.0, value_source="REAL", fault_tag=None),
                    _Row(biz_hour=datetime(2026, 11, 18, 10, 0, tzinfo=EAST_8), station_id="S3", hour_heat_gj=None, hour_heat_source="SOURCE_EMPTY", hour_water_t=None, hour_water_source="NONE", hour_elec_kwh=None, hour_elec_source="NONE", e14_clean=None, tot_water_f254=None, tot_elec_f253=1000000000.0, value_source="SOURCE_EMPTY", fault_tag="COMM_OFFLINE"),
                ])
            if "FROM smart_heating_platform.dict_merchant" in s:
                return _MockRes([_Row(merchant_id="M1", name="正常商户", rdfz="香海", rdry="热水"), _Row(merchant_id="M2", name="缺数商户", rdfz="香海", rdry="蒸汽")])
            if "FROM smart_heating_platform.fact_merchant_hourly" in s:
                return _MockRes([_Row(merchant_id="M1", source_name="正常商户", is_registered=True, online=True, hour_heat_gj=1.2, value_source="REAL", fault_tag=None)])
            if "FROM smart_heating_platform.fact_merchant_daily" in s:
                return _MockRes([_Row(merchant_id="M1", daily_consumption=15.0, raw_payload={"tot_curr": 115.0, "tot_prev": 100.0}), _Row(merchant_id="M2", daily_consumption=None, raw_payload={"tot_curr": 5.0, "tot_prev": 20.0})])
            if "FROM smart_heating_platform.dict_temp_device" in s:
                return _MockRes([_Row(temp_device_id="T1", device_name="1-101", station_id="S1", station_name="正常站"), _Row(temp_device_id="T2", device_name="1-102", station_id="S1", station_name="正常站")])
            if "SELECT MAX(biz_hour) FROM smart_heating_platform.fact_temp_hourly" in s:
                return _MockRes(scalar=datetime(2026, 11, 18, 14, 0, tzinfo=EAST_8))
            if "FROM smart_heating_platform.fact_temp_hourly WHERE" in s:
                return _MockRes([
                    _Row(temp_device_id="T1", station_id="S1", is_registered=True, village_name="1-101", station_name_raw="正常站", temp_raw=21.5, upload_time=datetime(2026, 11, 18, 13, 0, tzinfo=EAST_8), is_online_valid=True, fault_tag=None),
                    _Row(temp_device_id="T2", station_id="S1", is_registered=True, village_name="1-102", station_name_raw="正常站", temp_raw=-50.0, upload_time=datetime(2026, 11, 18, 13, 0, tzinfo=EAST_8), is_online_valid=False, fault_tag="SENSOR_OUT_OF_RANGE"),
                ])
            if "FROM smart_heating_platform.dict_upstream_point" in s:
                return _MockRes([_Row(point_id=1, data_zone="dc_dict", source_name="点A", name="点A", category="电厂", sub_category="香海")])
            if "FROM smart_heating_platform.fact_upstream_hourly" in s:
                return _MockRes([_Row(data_zone="dc_dict", source_name="点A", is_core_gk=True, heat_clean=100.0, flow_clean=500.0, value_source="REAL", fault_tag=None)])
            return _MockRes([])

    monkeypatch.setattr(rqs, "ensure_smart_heating_fact_tables", lambda: None)
    monkeypatch.setattr(rqs, "engine", SimpleNamespace(connect=lambda: _MockConn()))

    diag = rqs.get_collection_coverage_diagnostics("2026-11-18")
    assert diag["station"]["heat"] == {"meter_diff_ok": 1, "scaled_ok": 0, "partial_fallback": 0, "missing_cum_total": 2, "fallback_integral": 1, "both_missing": 1}
    assert diag["station"]["anomaly_summary"] == {
        "heat_anomaly_stations": 2,
        "water_anomaly_stations": 2,
        "water_partial_fallback": 0,
        "elec_anomaly_stations": 2,
        "total_anomaly_stations": 2,
    }
    assert diag["station"]["water"]["meter_diff_ok"] == 1
    assert diag["station"]["water"]["missing_cum_total"] == 2
    assert diag["station"]["water"]["fallback_integral"] == 1
    assert diag["station"]["water"]["both_missing"] == 1
    assert diag["station"]["elec"]["meter_ok"] == 1
    assert diag["station"]["elec"]["f253_const_zero"] == 1
    assert diag["station"]["elec"]["f253_frozen_or_overflow"] == 1
    assert diag["merchant"]["hourly"]["missing_count"] == 1
    assert diag["merchant"]["daily"]["rollback_count"] == 1
    assert diag["temp_device"]["valid_count"] == 1
    assert diag["temp_device"]["out_of_range"] == 1

    app = create_app()
    client = TestClient(app)
    app.dependency_overrides[get_current_session] = lambda: _session("Group_admin")
    assert client.get("/api/v1/projects/smart_heating_platform/faults/coverage").status_code == 403
    app.dependency_overrides[get_current_session] = lambda: _session("Global_admin")
    resp = client.get("/api/v1/projects/smart_heating_platform/faults/coverage?date=2026-11-18")
    assert resp.status_code == 200 and resp.json()["ok"] is True
    assert resp.json()["data"]["station"]["elec"]["missing_total"] == 2


def test_scheduler_hourly_offset_and_upstream_overflow_guard(monkeypatch):
    """验证 5 分钟采样叠加 hourly_offset_minutes=5 时不跳过整点桶且整点后按偏移触发 /jumin/，并防护 ±1e9 溢出。"""
    import backend.projects.smart_heating_platform.services.scheduler_service as ss
    from backend.projects.smart_heating_platform.services.cleaning_engine import (
        clean_temp_device,
        clean_upstream_point,
    )

    sched = ss.SmartHeatingSchedulerService()
    calls = []

    def _capture_spawn(name, fn):
        if name == "snapshot":
            # 拦截 run_snapshot_cycle 确认 include_jumin 参数
            fn()

    monkeypatch.setattr(sched, "_spawn_job", _capture_spawn)
    monkeypatch.setattr(
        ss,
        "run_snapshot_cycle",
        lambda include_jumin=None, trigger="AUTO": calls.append(bool(include_jumin)),
    )
    monkeypatch.setattr(
        ss,
        "_read_raw_config",
        lambda: {
            "scheduler_enabled": True,
            "auto_gap_recovery": False,
            "auto_heat_audit_fix": False,
            "snapshot_interval_minutes": 5,
            "hourly_offset_minutes": 5,
            "table_bottom_sync_hours": 6,
        },
    )

    current_dt = [datetime(2026, 11, 23, 14, 1, tzinfo=EAST_8)]

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return current_dt[0]

    monkeypatch.setattr(ss, "datetime", _FakeDatetime)
    sched._tick()  # 14:01 -> 命中 14:00 桶，尚未到 offset=5，仅采上游/商户
    current_dt[0] = datetime(2026, 11, 23, 14, 5, tzinfo=EAST_8)
    sched._tick()  # 14:05 -> 命中 14:05 桶，到达 offset=5，附带 /jumin/
    current_dt[0] = datetime(2026, 11, 23, 14, 10, tzinfo=EAST_8)
    sched._tick()  # 14:10 -> 命中 14:10 桶，同小时已采过 /jumin/，不再重复
    assert calls == [False, True, False]

    # 验证 ±1e9 寄存器极值不会溢出 NUMERIC(12,3) / NUMERIC(8,2)
    cleaned_up, up_faults = clean_upstream_point(
        {"item_name": "香首_高温水回水", "WENDU": 1000000000.0, "PINLV": -1000000000.0, "YALI": 0.45},
        {"point_id": None, "data_zone": "sz_dict", "source_name": "香首_高温水回水", "name": "香首_高温水回水", "category": "首站"},
        datetime(2026, 11, 23, 14, 40, tzinfo=EAST_8),
        prev_valid={"temp_clean": 55.2},
    )
    assert cleaned_up["temp_raw"] is None
    assert cleaned_up["temp_clean"] == 55.2
    assert cleaned_up["freq_val"] is None
    assert cleaned_up["pressure_raw"] == 0.45
    assert any("1000000000.0" in f["raw_value_text"] for f in up_faults)

    cleaned_jm, jm_faults = clean_temp_device(
        {"id": "T_OVF", "wd1": 1000000000.0, "upload_time": "2026-11-23 14:00:00"},
        {"T_OVF": {"station_id": "S1", "station_name": "正常站"}},
        {},
        datetime(2026, 11, 23, 14, 40, tzinfo=EAST_8),
    )
    assert cleaned_jm["temp_raw"] is None
    assert cleaned_jm["temp_clean"] is None
    assert cleaned_jm["is_online_valid"] is False
    assert any("1000000000.0" in f["raw_value_text"] for f in jm_faults)
