# -*- coding: utf-8 -*-
"""
tube 项目大连气象管理服务。
提供日级与小时级气温数据的外部 Fetch、导入前精确评估对比以及 SQL 覆盖落盘落库。
"""

from __future__ import annotations

import httpx
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from fastapi import HTTPException

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.projects.insulation_pipe_supply_2026.services.config_service import (
    load_tube_config,
    save_tube_config,
)

DEFAULT_WEATHER_API_URL = (
    "https://api.open-meteo.com/v1/forecast?latitude=38.875&longitude=121.625"
    "&timezone=Asia%2FSingapore&daily=weather_code,rain_sum,uv_index_max"
    "&hourly=temperature_2m&past_days=5"
)

WMO_CODE_TEXT = {
    0: "晴朗",
    1: "多云", 2: "多云",
    3: "阴天",
    45: "有雾", 48: "有雾",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨", 56: "冻雨", 57: "冻雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "冰雹/霰",
    80: "阵雨", 81: "中阵雨", 82: "强阵雨",
    85: "阵雪", 86: "阵雪",
    95: "雷阵雨", 96: "雷暴伴冰雹", 99: "雷暴伴冰雹"
}

def load_weather_api_url() -> str:
    """读取 tube_config.json 获取当前设定的 weather_api_url；未设定则返回默认 API"""
    try:
        payload = load_tube_config()
        return payload.get("weather_api_url") or DEFAULT_WEATHER_API_URL
    except Exception:
        return DEFAULT_WEATHER_API_URL


def get_weather_db_stats() -> Dict[str, Any]:
    """统计当前数据库表 tube_weather_daily & tube_weather_hourly 中已入库的记录状况"""
    session = SessionLocal()
    try:
        daily_count_sql = text("SELECT COUNT(*) FROM tube.tube_weather_daily")
        hourly_count_sql = text("SELECT COUNT(*) FROM tube.tube_weather_hourly")
        range_sql = text("SELECT MIN(weather_date), MAX(weather_date) FROM tube.tube_weather_daily")

        daily_count = session.execute(daily_count_sql).scalar() or 0
        hourly_count = session.execute(hourly_count_sql).scalar() or 0
        
        range_row = session.execute(range_sql).first()
        min_date = range_row[0].isoformat() if range_row and range_row[0] else None
        max_date = range_row[1].isoformat() if range_row and range_row[1] else None

        return {
            "daily_count": daily_count,
            "hourly_count": hourly_count,
            "min_date": min_date,
            "max_date": max_date,
            "weather_api_url": load_weather_api_url()
        }
    finally:
        session.close()


def fetch_and_parse_weather(api_url: str) -> Dict[str, Any]:
    """连线外部 Open-Meteo API 拉取数据并执行结构化解析与日气温算术平均计算"""
    # 强制将 open-meteo 的 HTML 文档文档的 docs URL 换成标准的 API v1 endpoint
    if "open-meteo.com/en/docs" in api_url:
        api_url = api_url.replace("open-meteo.com/en/docs", "api.open-meteo.com/v1/forecast")
    if "#" in api_url:
        api_url = api_url.split("#")[0]
        
    # 如果用户的 API 没有填上 hourly=temperature_2m，我们强行为其追加以计算日气温
    if "hourly=" not in api_url:
        api_url += "&hourly=temperature_2m"
    elif "hourly=temperature_2m" not in api_url and "hourly=" in api_url:
        # 如果是 hourly= 后面空的
        api_url = api_url.replace("hourly=", "hourly=temperature_2m")

    try:
        res = httpx.get(api_url, timeout=15.0)
        res.raise_for_status()
        data = res.json()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"连线大连外部气象服务失败，请检查 API 地址是否可达。异常: {exc}"
        )

    if "daily" not in data:
        raise HTTPException(status_code=422, detail="API 响应缺失 daily 节点数据，无法解析日天气指标。")
    if "hourly" not in data:
        raise HTTPException(status_code=422, detail="API 响应缺失 hourly 节点气温数据，无法精算日最高/平均温。")

    return data


def evaluate_weather_import(api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    预拉取气象数据并与本地数据库中已入库的记录进行闪电级字段对比评估。
    不写入数据库，仅返回：新增 (inserted)、更新 (updated)、未变化 (unchanged) 的分类统计及预览列表。
    """
    target_url = api_url or load_weather_api_url()
    data = fetch_and_parse_weather(target_url)

    daily_times: List[str] = data["daily"].get("time") or []
    rain_sums: List[float] = data["daily"].get("rain_sum") or []
    weather_codes: List[int] = data["daily"].get("weather_code") or []
    uv_indexes: List[float] = data["daily"].get("uv_index_max") or []

    hourly_times: List[str] = data["hourly"].get("time") or []
    hourly_temps: List[float] = data["hourly"].get("temperature_2m") or []

    session = SessionLocal()
    try:
        # 1. 抓取本地日级已存映射
        db_daily_sql = text(
            """
            SELECT weather_date, weather_code, rain_sum, uv_index_max, temp_max, temp_mean, temp_min
            FROM tube.tube_weather_daily
            """
        )
        db_daily_rows = session.execute(db_daily_sql).mappings().all()
        db_daily_map: Dict[str, Dict[str, Any]] = {}
        for r in db_daily_rows:
            d_str = r["weather_date"].isoformat()
            db_daily_map[d_str] = {
                "weather_code": int(r["weather_code"] or 0),
                "rain_sum": float(r["rain_sum"] or 0),
                "uv_index_max": float(r["uv_index_max"] or 0),
                "temp_max": float(r["temp_max"]) if r["temp_max"] is not None else None,
                "temp_mean": float(r["temp_mean"]) if r["temp_mean"] is not None else None,
                "temp_min": float(r["temp_min"]) if r["temp_min"] is not None else None,
            }

        # 2. 抓取本地小时级已存映射
        db_hourly_sql = text("SELECT weather_date_time, temperature FROM tube.tube_weather_hourly")
        db_hourly_rows = session.execute(db_hourly_sql).mappings().all()
        db_hourly_map: Dict[str, float] = {}
        for r in db_hourly_rows:
            dt_iso = r["weather_date_time"].isoformat()
            # 格式可能略有不同（去掉偏移或保留 Z），我们做一下标准化转换
            # ISO format: 2026-05-28T09:00:00+08:00
            db_hourly_map[dt_iso] = float(r["temperature"] or 0)

        # 3. 开始双轨评估
        inserted, updated, unchanged = 0, 0, 0
        h_inserted, h_updated, h_unchanged = 0, 0, 0
        preview_list: List[Dict[str, Any]] = []

        # 评估日级
        for idx, date_str in enumerate(daily_times):
            rain_val = float(rain_sums[idx] or 0)
            code_val = int(weather_codes[idx] or 0)
            uv_val = float(uv_indexes[idx] or 0)

            # 过滤出当天的逐小时气温
            day_temps = []
            for h_idx, h_time in enumerate(hourly_times):
                if h_time.startswith(date_str):
                    t_val = hourly_temps[h_idx]
                    if t_val is not None:
                        day_temps.append(float(t_val))
            
            temp_max, temp_mean, temp_min = None, None, None
            if day_temps:
                temp_max = max(day_temps)
                temp_mean = sum(day_temps) / len(day_temps)
                temp_min = min(day_temps)

            # 中文天气描述
            weather_text = WMO_CODE_TEXT.get(code_val, "未知")

            row_preview = {
                "date": date_str,
                "weather_code": code_val,
                "weather_text": weather_text,
                "rain_sum": rain_val,
                "uv_index_max": uv_val,
                "temp_max": temp_max,
                "temp_mean": temp_mean,
                "temp_min": temp_min,
                "status": "inserted", # 默认新增
            }

            if date_str in db_daily_map:
                db_row = db_daily_map[date_str]
                # 对比核心属性
                is_changed = (
                    db_row["weather_code"] != code_val
                    or abs(db_row["rain_sum"] - rain_val) > 0.01
                    or abs(db_row["uv_index_max"] - uv_val) > 0.01
                    or (db_row["temp_max"] is None and temp_max is not None)
                    or (db_row["temp_max"] is not None and temp_max is None)
                    or (db_row["temp_max"] is not None and temp_max is not None and abs(db_row["temp_max"] - temp_max) > 0.01)
                    or (db_row["temp_mean"] is None and temp_mean is not None)
                    or (db_row["temp_mean"] is not None and temp_mean is None)
                    or (db_row["temp_mean"] is not None and temp_mean is not None and abs(db_row["temp_mean"] - temp_mean) > 0.01)
                )
                if is_changed:
                    row_preview["status"] = "updated"
                    updated += 1
                else:
                    row_preview["status"] = "unchanged"
                    unchanged += 1
            else:
                inserted += 1

            preview_list.append(row_preview)

        # 评估小时级
        for h_idx, h_time in enumerate(hourly_times):
            t_val = hourly_temps[h_idx]
            if t_val is None:
                continue
            
            # API 传回的 2026-05-28T09:00 没有偏移，默认当作东八区时间
            # 我们标准化成 2026-05-28T09:00:00+08:00
            iso_normalized = f"{h_time}:00+08:00"
            
            if iso_normalized in db_hourly_map:
                if abs(db_hourly_map[iso_normalized] - float(t_val)) > 0.01:
                    h_updated += 1
                else:
                    h_unchanged += 1
            else:
                h_inserted += 1

        return {
            "ok": True,
            "project_key": "insulation_pipe_supply_2026",
            "eval_api_url": target_url,
            "daily_stats": {
                "total": len(preview_list),
                "inserted": inserted,
                "updated": updated,
                "unchanged": unchanged
            },
            "hourly_stats": {
                "total": len(hourly_times),
                "inserted": h_inserted,
                "updated": h_updated,
                "unchanged": h_unchanged
            },
            "preview_list": preview_list
        }
    finally:
        session.close()


def import_weather_data(api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch 并物理导入天气数据。使用 PostgreSQL SQL 级别的 ON CONFLICT 批量覆盖合并，
    确保重复日期记录完美覆盖更新，100% 达成数据幂等性与极速落库。
    """
    target_url = api_url or load_weather_api_url()
    data = fetch_and_parse_weather(target_url)

    daily_times: List[str] = data["daily"].get("time") or []
    rain_sums: List[float] = data["daily"].get("rain_sum") or []
    weather_codes: List[int] = data["daily"].get("weather_code") or []
    uv_indexes: List[float] = data["daily"].get("uv_index_max") or []

    hourly_times: List[str] = data["hourly"].get("time") or []
    hourly_temps: List[float] = data["hourly"].get("temperature_2m") or []

    session = SessionLocal()
    try:
        # 1. 批量导入日级数据
        daily_upsert_sql = text(
            """
            INSERT INTO tube.tube_weather_daily (
                weather_date, weather_code, rain_sum, uv_index_max, temp_max, temp_mean, temp_min, updated_at
            ) VALUES (
                :date, :code, :rain, :uv, :temp_max, :temp_mean, :temp_min, NOW()
            )
            ON CONFLICT (weather_date) DO UPDATE SET
                weather_code = EXCLUDED.weather_code,
                rain_sum = EXCLUDED.rain_sum,
                uv_index_max = EXCLUDED.uv_index_max,
                temp_max = EXCLUDED.temp_max,
                temp_mean = EXCLUDED.temp_mean,
                temp_min = EXCLUDED.temp_min,
                updated_at = NOW()
            """
        )

        daily_params = []
        for idx, date_str in enumerate(daily_times):
            # 过滤出当天的逐小时温度以计算最高温、算术平均温和最低温
            day_temps = []
            for h_idx, h_time in enumerate(hourly_times):
                if h_time.startswith(date_str):
                    t_val = hourly_temps[h_idx]
                    if t_val is not None:
                        day_temps.append(float(t_val))
            
            t_max, t_mean, t_min = None, None, None
            if day_temps:
                t_max = max(day_temps)
                t_mean = sum(day_temps) / len(day_temps)
                t_min = min(day_temps)

            daily_params.append({
                "date": date_str,
                "code": int(weather_codes[idx] or 0),
                "rain": float(rain_sums[idx] or 0),
                "uv": float(uv_indexes[idx] or 0),
                "temp_max": t_max,
                "temp_mean": t_mean,
                "temp_min": t_min
            })

        if daily_params:
            session.execute(daily_upsert_sql, daily_params)

        # 2. 批量导入小时级温度数据
        hourly_upsert_sql = text(
            """
            INSERT INTO tube.tube_weather_hourly (
                weather_date_time, temperature, updated_at
            ) VALUES (
                :date_time, :temperature, NOW()
            )
            ON CONFLICT (weather_date_time) DO UPDATE SET
                temperature = EXCLUDED.temperature,
                updated_at = NOW()
            """
        )

        hourly_params = []
        for h_idx, h_time in enumerate(hourly_times):
            t_val = hourly_temps[h_idx]
            if t_val is None:
                continue
            
            # 同样格式化时区以符合 PostgreSQL TIMESTAMPTZ 格式
            iso_normalized = f"{h_time}:00+08:00"
            hourly_params.append({
                "date_time": iso_normalized,
                "temperature": float(t_val)
            })

        if hourly_params:
            session.execute(hourly_upsert_sql, hourly_params)

        session.commit()

        return {
            "ok": True,
            "project_key": "insulation_pipe_supply_2026",
            "imported_api_url": target_url,
            "daily_count": len(daily_params),
            "hourly_count": len(hourly_params)
        }
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"写入大连主城区天气数据库失败，事务已安全回滚。异常: {exc}"
        )
    finally:
        session.close()


def get_weather_dashboard_data(show_date_str: str) -> Dict[str, Any]:
    """
    大盘气象专用接口。
    获取 show_date_str（YYYY-MM-DD）对应的昨日、当日、明日、后日这 4 天的气象数据。
    如果数据库有缺漏（比如未来的数据还未手动导入），则静默连线外部 API 自动增量合并入库补齐，实现高鲁棒的缓存机制。
    """
    try:
        base_date = date.fromisoformat(show_date_str)
    except ValueError:
        base_date = date.today()

    from datetime import timedelta
    yesterday = base_date - timedelta(days=1)
    today = base_date
    tomorrow = base_date + timedelta(days=1)
    after_tomorrow = base_date + timedelta(days=2)

    target_dates = [yesterday, today, tomorrow, after_tomorrow]
    target_dates_str = [d.isoformat() for d in target_dates]

    session = SessionLocal()
    try:
        # 1. 尝试从本地 PostgreSQL 表中查询这 4 天的天气记录
        query_sql = text(
            """
            SELECT weather_date, weather_code, rain_sum, uv_index_max, temp_max, temp_mean, temp_min
            FROM tube.tube_weather_daily
            WHERE weather_date IN :dates
            """
        )
        rows = session.execute(query_sql, {"dates": tuple(target_dates)}).mappings().all()
        db_dates = {r["weather_date"] for r in rows}

        # 2. 如果这 4 天的数据在本地数据库中有缺漏，则触发“自动连线 API 静默合并入库补齐”
        missing_any = any(d not in db_dates for d in target_dates)
        if missing_any:
            # 自动加载配置中的 API URL，静默完成一次外部 fetch 与物理 upsert 入库
            try:
                import_weather_data()
                # 重新查库以获取最新合并的数据
                rows = session.execute(query_sql, {"dates": tuple(target_dates)}).mappings().all()
            except Exception as e:
                # 即使连线外部 API 出错，我们也绝不影响主流程，保持优雅的降级表现
                print(f"[Weather Dynamic Cache Helper] 静默增量补齐天气数据失败，降级展示已有数据。异常: {e}")

        # 3. 组织前端渲染所需的高阶属性，保持跨端命名及结构高度统一
        weather_days_list = []
        rows_map = {r["weather_date"].isoformat(): r for r in rows}

        labels = ["前一日", "当日", "明日", "后日"]
        for idx, d_str in enumerate(target_dates_str):
            r = rows_map.get(d_str)
            if r:
                code_val = int(r["weather_code"] or 0)
                weather_days_list.append({
                    "date": d_str,
                    "label": labels[idx],
                    "weather_code": code_val,
                    "weather_text": WMO_CODE_TEXT.get(code_val, "未知"),
                    "rain_sum": float(r["rain_sum"] or 0),
                    "uv_index_max": float(r["uv_index_max"] or 0),
                    "temp_max": float(r["temp_max"]) if r["temp_max"] is not None else None,
                    "temp_mean": float(r["temp_mean"]) if r["temp_mean"] is not None else None,
                    "temp_min": float(r["temp_min"]) if r["temp_min"] is not None else None,
                })
            else:
                # 实在没有的缺漏日期，返回优雅的空值占位
                weather_days_list.append({
                    "date": d_str,
                    "label": labels[idx],
                    "weather_code": 0,
                    "weather_text": "未入库",
                    "rain_sum": 0.0,
                    "uv_index_max": 0.0,
                    "temp_max": None,
                    "temp_mean": None,
                    "temp_min": None,
                })

        return {
            "ok": True,
            "project_key": "insulation_pipe_supply_2026",
            "show_date": show_date_str,
            "weather_days": weather_days_list
        }
    finally:
        session.close()
