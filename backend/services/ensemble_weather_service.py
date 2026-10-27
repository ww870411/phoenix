"""Open-Meteo 35天集合气温预报拉取、清洗均值与入库服务。

业务规则:
1. 从 Open-Meteo Ensemble API 获取 35 天逐小时气温集合 (31 个 member);
2. 逐小时计算有效 member 的算术平均值 (遇到某个 member 为 null 忽略，不计入分子及分母);
3. 当遇到某一时刻全部 member 均为 null 时，截断至该时刻前的最后一个非全 null 时刻;
4. 结果入库 public.temperature_data 表，type 字段标记为 'far';
5. 若已存在同时间戳记录，采用 ON CONFLICT (date_time) DO UPDATE 覆盖更新 value 与 type。
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple
import httpx
import psycopg2
from psycopg2.extras import execute_batch

EAST_8 = timezone(timedelta(hours=8))

# 默认大连地理坐标
DEFAULT_LATITUDE = 38.875
DEFAULT_LONGITUDE = 121.625
ENSEMBLE_API_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"


def fetch_and_import_ensemble_weather(
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    db_url: str = None,
) -> Dict[str, Any]:
    """
    拉取 35 天集合气温预报，计算各时刻算术平均，截断全 null，并覆盖写入 public.temperature_data。
    """
    if not db_url:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/phoenix")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m",
        "models": "gfs05",
        "forecast_days": 35,
        "timezone": "Asia/Singapore",
    }

    headers = {"User-Agent": "Phoenix/1.0 (DynamicPlanForecast)"}

    # 1. 发起网络请求获取集合预报
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(ENSEMBLE_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        raise ValueError("Open-Meteo Ensemble API 未返回任何 hourly.time 时刻数据")

    # 提取所有 temperature_2m 相关的预测数组成员 (包含基础 temperature_2m 以及 member01..member30)
    member_keys = [k for k in hourly.keys() if "temperature_2m" in k]
    if not member_keys:
        raise ValueError("Open-Meteo Ensemble API 返回中未找到任何 temperature_2m 预测成员")

    total_time_slots = len(times)
    records_to_upsert: List[Tuple[datetime, float]] = []
    truncated_at = None

    # 2. 逐小时清洗并计算算术平均值 (遇到全 null 截断)
    for i in range(total_time_slots):
        slot_time_str = times[i]
        valid_values: List[float] = []

        for m_key in member_keys:
            val = hourly[m_key][i]
            if val is not None:
                try:
                    valid_values.append(float(val))
                except (TypeError, ValueError):
                    pass

        # 若该时刻所有 member 均为 null，则截断至前一时刻
        if not valid_values:
            truncated_at = slot_time_str
            break

        # 计算该时刻有效 member 的算术平均值
        avg_temp = round(sum(valid_values) / len(valid_values), 4)

        # 解析 ISO 时间戳并绑定东八区
        try:
            dt = datetime.fromisoformat(slot_time_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=EAST_8)
            else:
                dt = dt.astimezone(EAST_8)
        except Exception as e:
            continue

        records_to_upsert.append((dt, avg_temp))

    if not records_to_upsert:
        return {
            "ok": False,
            "message": "未能计算出任何有效逐小时平均气温记录",
            "inserted_or_updated": 0,
        }

    # 3. 幂等批量写入数据库 public.temperature_data (标记 type = 'far')
    upsert_sql = """
    INSERT INTO public.temperature_data (
        date_time, value, type, operation_time
    ) VALUES (%s, %s, 'far', CURRENT_TIMESTAMP)
    ON CONFLICT (date_time) DO UPDATE SET
        value = EXCLUDED.value,
        type = 'far',
        operation_time = CURRENT_TIMESTAMP;
    """

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            execute_batch(cur, upsert_sql, records_to_upsert, page_size=200)
        conn.commit()
    finally:
        conn.close()

    start_dt = records_to_upsert[0][0].isoformat()
    end_dt = records_to_upsert[-1][0].isoformat()

    return {
        "ok": True,
        "message": f"成功拉取并入库 35 天集合预报均值气温共 {len(records_to_upsert)} 条",
        "inserted_or_updated": len(records_to_upsert),
        "start_time": start_dt,
        "end_time": end_dt,
        "truncated_at": truncated_at,
        "members_count": len(member_keys),
    }
