"""
Open-Meteo 天气数据获取服务。

当前阶段仅负责从用户指定的 API 读取逐小时气温数据，不执行数据库写入。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.database_daily_report_25_26 import TemperatureData
from backend.services.auth_manager import EAST_8

# 用户提供的 API，暂不允许自定义参数。
OPEN_METEO_API_URL = (
    "https://api.open-meteo.com/v1/forecast?"
    "latitude=38.875&longitude=121.625&hourly=temperature_2m"
    "&timezone=Asia%2FSingapore&past_days=3"
)


@dataclass
class HourlyTemperature:
    """逐小时气温结构。"""

    time: str
    value: float


class WeatherImporterError(RuntimeError):
    """天气数据获取过程中出现的通用错误。"""


def _validate_hourly_payload(payload: Dict) -> Sequence[HourlyTemperature]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise WeatherImporterError("Open-Meteo 响应缺少 hourly 字段。")

    times = hourly.get("time")
    temps = hourly.get("temperature_2m")
    if not isinstance(times, list) or not isinstance(temps, list):
        raise WeatherImporterError("hourly.time 或 hourly.temperature_2m 不是数组。")
    if len(times) != len(temps):
        raise WeatherImporterError("hourly.time 与 hourly.temperature_2m 数组长度不一致。")

    items: List[HourlyTemperature] = []
    for raw_time, raw_value in zip(times, temps):
        if not isinstance(raw_time, str):
            continue
        try:
            # 确保字符串格式合法，解析后再转回 ISO 字符串，便于前端展示。
            parsed = datetime.fromisoformat(raw_time)
            normalized = parsed.isoformat()
        except ValueError:
            normalized = raw_time
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        items.append(HourlyTemperature(time=normalized, value=value))
    return items


def _resolve_timezone(tz_name: Optional[str]) -> timezone:
    """
    根据接口声明的 timezone 解析偏移；若缺失/无法解析，默认东八区。
    """

    if isinstance(tz_name, str):
        # Open-Meteo 常用 'Asia/Singapore'，也可能返回 '+08' 形式
        if tz_name.startswith(('+', '-')) and len(tz_name) in {3, 5}:
            try:
                hours = int(tz_name[:3])
                minutes = int(tz_name[0] + tz_name[3:]) if len(tz_name) == 5 else 0
                return timezone(timedelta(hours=hours, minutes=minutes))
            except Exception:
                pass
    return EAST_8


def _normalize_hour(dt: datetime, tz_source: Optional[timezone]) -> datetime:
    """
    统一小时粒度：若缺失 tzinfo 则按 tz_source 贴上，转换到目标时区后截整点，保留 tzinfo。
    """

    target_tz = tz_source or EAST_8
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=target_tz)
    dt = dt.astimezone(target_tz)
    return dt.replace(minute=0, second=0, microsecond=0, tzinfo=target_tz)


def _parse_hourly_for_compare(
    hourly_items: Sequence[Dict[str, object]],
    tz_source: Optional[timezone],
) -> List[Tuple[datetime, float]]:
    parsed: List[Tuple[datetime, float]] = []
    for item in hourly_items:
        raw_time = item.get("time")
        raw_value = item.get("value")
        try:
            dt = datetime.fromisoformat(str(raw_time))
        except (TypeError, ValueError):
            continue
        try:
            val = float(raw_value)
        except (TypeError, ValueError):
            continue
        parsed.append((_normalize_hour(dt, tz_source), val))
    return parsed


def _dedupe_by_hour(parsed: Sequence[Tuple[datetime, float]]) -> Dict[datetime, float]:
    """
    将同一小时的记录去重，以最后出现的值为准，便于入库与比对。
    """

    bucket: Dict[datetime, float] = {}
    for dt, val in parsed:
        bucket[dt] = val
    return bucket


def compare_with_existing(
    session: Session, hourly_items: Sequence[Dict[str, object]], tz_name: Optional[str] = None
) -> Dict[str, object]:
    """
    比对 API 返回的逐小时气温与数据库 temperature_data 中的记录。

    返回：
    - overlap: 重合区间（start/end/hours）
    - differences: 同小时气温不一致的清单
    """

    tz_source = _resolve_timezone(tz_name)
    parsed = _parse_hourly_for_compare(hourly_items, tz_source)
    if not parsed:
        return {"overlap": None, "differences": [], "overlap_hours": 0}

    deduped = _dedupe_by_hour(parsed)
    times_only = list(deduped.keys())
    start_dt, end_dt = min(times_only), max(times_only)

    existing_rows = session.execute(
        select(TemperatureData.date_time, TemperatureData.value).where(
            TemperatureData.date_time >= start_dt, TemperatureData.date_time <= end_dt
        )
    ).all()
    existing_map: Dict[datetime, Optional[float]] = {}
    for row in existing_rows:
        key = _normalize_hour(row.date_time, tz_source)
        try:
            existing_map[key] = float(row.value) if row.value is not None else None
        except (TypeError, ValueError):
            existing_map[key] = None

    differences: List[Dict[str, object]] = []
    overlap_records: List[Dict[str, object]] = []
    overlap_keys = set()
    for dt, api_value in deduped.items():
        db_value = existing_map.get(dt)
        in_db = dt in existing_map
        if in_db:
            overlap_keys.add(dt)
        different = False
        if db_value is not None:
            different = abs(db_value - api_value) > 1e-6
            if different:
                differences.append(
                    {
                        "time": dt.isoformat(),
                        "api_value": api_value,
                        "db_value": db_value,
                    }
                )
        overlap_records.append(
            {
                "time": dt.isoformat(),
                "api_value": api_value,
                "db_value": db_value,
                "different": different,
                "in_db": in_db,
            }
        )

    return {
        "overlap": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "hours": len(overlap_keys),
        },
        "differences": differences,
        "overlap_hours": len(overlap_keys),
        "overlap_records": overlap_records,
    }


def persist_hourly_temperatures(
    session: Session, hourly_items: Sequence[Dict[str, object]], tz_name: Optional[str] = None
) -> Dict[str, object]:
    """
    将逐小时气温写入 temperature_data：先按时间范围删除，再写入去重后的小时粒度数据。
    """

    tz_source = _resolve_timezone(tz_name)
    parsed = _parse_hourly_for_compare(hourly_items, tz_source)
    if not parsed:
        return {"inserted": 0, "replaced": 0, "start": None, "end": None}

    deduped = _dedupe_by_hour(parsed)
    times_only = list(deduped.keys())
    start_dt, end_dt = min(times_only), max(times_only)

    existing_count = (
        session.query(TemperatureData)
        .filter(TemperatureData.date_time >= start_dt, TemperatureData.date_time <= end_dt)
        .count()
    )
    session.query(TemperatureData).filter(
        TemperatureData.date_time >= start_dt, TemperatureData.date_time <= end_dt
    ).delete(synchronize_session=False)

    now = datetime.now(tz=EAST_8)
    rows = [
        TemperatureData(date_time=dt, value=val, operation_time=now)
        for dt, val in deduped.items()
    ]
    session.bulk_save_objects(rows)
    session.commit()

    return {
        "inserted": len(rows),
        "replaced": existing_count,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
    }


def fetch_hourly_temperatures() -> Dict[str, object]:
    """
    从 Open-Meteo API 获取逐小时温度。

    返回值包含：
    - source: API 元信息；
    - hourly: 每条数据的时间与温度；
    - dates: 涵盖到的业务日期（去重/排序）。
    """

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(OPEN_METEO_API_URL)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise WeatherImporterError(f"请求 Open-Meteo 失败: {exc}") from exc
    except ValueError as exc:
        raise WeatherImporterError(f"解析 Open-Meteo 响应失败: {exc}") from exc

    hourly_items = _validate_hourly_payload(payload)
    unique_dates = sorted({item.time.split("T")[0] for item in hourly_items if "T" in item.time})

    return {
        "source": {
            "provider": "open-meteo",
            "url": OPEN_METEO_API_URL,
            "timezone": payload.get("timezone"),
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
        },
        "hourly": [item.__dict__ for item in hourly_items],
        "dates": unique_dates,
        "summary": {
            "total_hours": len(hourly_items),
        },
    }
