# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 五重数据清洗、15分钟梯形积分与表底插值引擎。

核心原则：
1. 原始值 (raw) 与净化值 (clean) 严格分离，绝不丢弃现场异常证据；
2. 阳面仅对“临时离线”或“单小时物理倒挂/断路”做可审计平滑，长期停运/常离线保持离线标识；
3. 累计耗量优先采用整点线性插值表底差值（METER_DIFF），表底缺失/跳变时自动降级为
   15分钟梯形面积积分（INTEGRAL_15M）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

EAST_8 = timezone(timedelta(hours=8))

# 故障类型编码
FAULT_SENSOR_RANGE = "SENSOR_OUT_OF_RANGE"
FAULT_COMM_OFFLINE = "COMM_OFFLINE"
FAULT_HEAT_IMBALANCE = "HEAT_IMBALANCE"
FAULT_TEMP_INVERSION = "TEMP_INVERSION"
FAULT_METER_JUMP = "METER_JUMP"
FAULT_SOFTWARE_DEFECT = "SOFTWARE_DEFECT"

# 权责归属方
OWNER_RESEARCH = "RESEARCH_INSTITUTE"
OWNER_UNIVERSITY = "UNIVERSITY_SOFTWARE"
OWNER_SHARED = "SHARED"

# 数值来源标记
SRC_REAL = "REAL"
SRC_MASKED_PREV = "MASKED_PREV_HOLD"
SRC_TEMP_OFFLINE = "INTERP_TEMP_OFFLINE"
SRC_PERM_OFFLINE = "OFFLINE_PERMANENT"
SRC_METER_DIFF = "METER_DIFF"
SRC_INTEGRAL_15M = "INTEGRAL_15M"
SRC_FALLBACK_INTEGRAL = "FALLBACK_INTEGRAL_15M"
SRC_SOURCE_EMPTY = "SOURCE_EMPTY"

UPSTREAM_MAX_HEAT_GJH = 5000.0

# 经实测核实的站点累计热量表底倍率修正表: {站名: (折算系数, 口径说明)}
STATION_METER_SCALE_FACTORS: Dict[str, Tuple[float, str]] = {
    "南山苑": (0.1, "累计表底 totJ 为 0.1GJ 刻度（已自动÷10 折算为 GJ）"),
    "经典A": (0.1, "累计表底 totJ 为 0.1GJ 刻度（已自动÷10 折算为 GJ）"),
    "联通公司": (0.1, "累计表底 totJ 为 0.1GJ 刻度（已自动÷10 折算为 GJ）"),
    "恒元公寓": (3.6, "累计表底 totJ 为 MWh 刻度（已自动×3.6 折算为 GJ）"),
}


def station_max_hourly_heat_gj(covered_area: Optional[float]) -> float:
    """按供暖面积计算单站小时物理最大合理热负荷上限（125 W/㎡ = 0.00045 GJ/㎡·h，兜底 25 GJ/h）。"""
    area = float(covered_area) if (covered_area is not None and float(covered_area) > 0) else 100000.0
    return round(max(25.0, area * 0.00045), 4)


def station_max_hourly_elec_kwh(covered_area: Optional[float]) -> float:
    """按供暖面积计算单站小时基准电耗上限（12 kWh/万㎡·h，兜底 35 kWh/h；校验器按 1.5 倍判跳变）。"""
    area = float(covered_area) if (covered_area is not None and float(covered_area) > 0) else 100000.0
    return round(max(35.0, area * 0.0012), 4)


def station_max_hourly_water_t(covered_area: Optional[float]) -> float:
    """按供暖面积计算单站小时基准补水上限（5 t/万㎡·h，兜底 80 t/h；校验器按 1.5 倍判跳变）。"""
    area = float(covered_area) if (covered_area is not None and float(covered_area) > 0) else 100000.0
    return round(max(80.0, area * 0.0005), 4)


def is_meter_sequence_oscillating(
    records: Sequence[Tuple[datetime, Optional[float]]],
    min_reversal: float = 0.5,
) -> Tuple[bool, Optional[str]]:
    """
    检测表底时间序列是否存在频繁锯齿状倒走（如 PLC 寄存器字节错位/通信乱码）。

    当序列中连续出现 >= 2 次明显倒走（后点比前点小超过 min_reversal）时，
    判为整段表底不可信（避免局部上升沿漏过单小时上限校验生成虚假高值）。
    """
    valid = sorted(
        ((ts, val) for ts, val in records if ts is not None and val is not None),
        key=lambda x: x[0],
    )
    if len(valid) < 3:
        return False, None
    reversals: List[str] = []
    for idx in range(1, len(valid)):
        prev_ts, prev_v = valid[idx - 1]
        curr_ts, curr_v = valid[idx]
        diff = curr_v - prev_v
        if diff < -abs(min_reversal):
            reversals.append(f"{curr_ts.strftime('%H:%M')}({diff:+.1f})")
    if len(reversals) >= 2:
        preview = "、".join(reversals[:4]) + (" 等" if len(reversals) > 4 else "")
        return True, f"表底频繁锯齿倒走共{len(reversals)}次: {preview}"
    return False, None


def to_float(val: Any) -> Optional[float]:
    """安全将字符串或数值转为 float，无效空串/NaN 返回 None。"""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        if val != val:  # NaN check
            return None
        return float(val)
    text = str(val).strip()
    if text in ("", "-", "--", "null", "None", "nan", "NaN"):
        return None
    try:
        num = float(text)
        return None if num != num else num
    except (ValueError, TypeError):
        return None


def parse_dt_east8(val: Any) -> Optional[datetime]:
    """将源系统常见时间字符串解析为东八区 aware datetime。"""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=EAST_8) if val.tzinfo is None else val.astimezone(EAST_8)
    text = str(val).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=EAST_8)
        except ValueError:
            continue
    return None


def floor_to_bucket(dt: datetime, interval_minutes: int = 5) -> datetime:
    """将时间向下对齐至指定分钟步长整刻度（默认 5 分钟）。"""
    step = max(1, min(60, int(interval_minutes)))
    dt_e8 = dt.astimezone(EAST_8) if dt.tzinfo else dt.replace(tzinfo=EAST_8)
    minute = (dt_e8.minute // step) * step
    return dt_e8.replace(minute=minute, second=0, microsecond=0)


def floor_to_15min(dt: datetime) -> datetime:
    """将时间向下对齐至最近 15 分钟整刻度。"""
    return floor_to_bucket(dt, 15)


def floor_to_hour(dt: datetime) -> datetime:
    """将时间向下对齐至整点小时。"""
    dt_e8 = dt.astimezone(EAST_8) if dt.tzinfo else dt.replace(tzinfo=EAST_8)
    return dt_e8.replace(minute=0, second=0, microsecond=0)


def trapezoidal_hour_integral(samples: Sequence[Tuple[datetime, Optional[float]]]) -> Optional[float]:
    """
    基于小时内多点采样执行时间加权梯形积分，输出该小时累计量（如 GJ 或 t）。

    - 过滤值为 None 的样本；
    - 仅 1 个有效点时，直接以 `rate * 1.0h` 估算；
    - >= 2 个有效点时，计算相邻两点的梯形面积之和再按覆盖时长等比外推至整 1 小时，
      防止本小时尚未走完或缺少末尾点时低估小时累计总量。
    """
    valid = sorted(
        ((ts, val) for ts, val in samples if ts is not None and val is not None),
        key=lambda x: x[0],
    )
    if not valid:
        return None
    if len(valid) == 1:
        return round(max(0.0, valid[0][1]), 4)

    area = 0.0
    total_seconds = 0.0
    for idx in range(len(valid) - 1):
        t0, v0 = valid[idx]
        t1, v1 = valid[idx + 1]
        dt_sec = (t1 - t0).total_seconds()
        if dt_sec <= 0:
            continue
        avg_rate = max(0.0, (v0 + v1) / 2.0)
        area += avg_rate * (dt_sec / 3600.0)
        total_seconds += dt_sec

    if total_seconds <= 0:
        return round(max(0.0, valid[-1][1]), 4)

    # 折算到标准 1 小时 (3600 秒)
    normalized = area * (3600.0 / total_seconds)
    return round(normalized, 4)


def interpolate_meter_at_hour(
    records: Sequence[Tuple[datetime, Optional[float]]],
    target_hour: datetime,
    tolerance_minutes: int = 25,
) -> Optional[float]:
    """
    从 15 分钟周期历史表底序列中线性插值对齐到整点 `target_hour`。

    - 若刚好存在距离目标整点 <= 90 秒的记录，直接取该点；
    - 若目标整点两侧均有记录且跨度 <= 45 分钟，按时间比例线性插值；
    - 若仅单侧有记录且距整点 <= 10 分钟（如刚过整点尚未落齐下一条），取最近值容差对齐。
    """
    valid = sorted(
        ((ts, val) for ts, val in records if ts is not None and val is not None),
        key=lambda x: x[0],
    )
    if not valid:
        return None

    left: Optional[Tuple[datetime, float]] = None
    right: Optional[Tuple[datetime, float]] = None

    for ts, val in valid:
        diff_sec = (ts - target_hour).total_seconds()
        if abs(diff_sec) <= 90:
            return round(val, 4)
        if diff_sec < 0:
            left = (ts, val)
        elif diff_sec > 0 and right is None:
            right = (ts, val)
            break

    if left and right:
        span_sec = (right[0] - left[0]).total_seconds()
        if 0 < span_sec <= tolerance_minutes * 2 * 60:
            ratio = (target_hour - left[0]).total_seconds() / span_sec
            interp = left[1] + ratio * (right[1] - left[1])
            return round(interp, 4)

    for candidate in (left, right):
        if candidate and abs((candidate[0] - target_hour).total_seconds()) <= 600:
            return round(candidate[1], 4)

    return None


def validate_meter_delta(
    prev_val: Optional[float],
    curr_val: Optional[float],
    max_hourly_limit: float = 500.0,
) -> Tuple[Optional[float], bool, Optional[str]]:
    """
    校验相邻整点累计表底差值。

    返回：(有效差值, 是否异常, 异常说明)
    规则：delta < 0（表底清零/倒走）或 delta > max_hourly_limit * 1.5（表底跳变）均判异常。
    """
    if prev_val is None or curr_val is None:
        return None, False, None
    delta = curr_val - prev_val
    if delta < -0.01:
        return None, True, f"表底倒走/清零: prev={prev_val:.2f}, curr={curr_val:.2f}, delta={delta:.2f}"
    if delta > max_hourly_limit * 1.5:
        return None, True, f"表底异常跳变: prev={prev_val:.2f}, curr={curr_val:.2f}, delta={delta:.2f}"
    return round(max(0.0, delta), 4), False, None


def is_steam_point(name: str, sub_category: Optional[str], data_zone: str) -> bool:
    """判断上游监测点是否属于蒸汽/烟气/高温汽温点（判定阈值 >=600℃ 而非水温 >150℃）。"""
    text = f"{name or ''} {sub_category or ''}"
    if any(k in text for k in ("主汽", "进汽", "进气", "抽汽", "抽气", "排汽", "蒸汽", "调门", "母管")):
        return True
    if data_zone == "dc_dict" and not any(k in text for k in ("水", "低真空", "网", "补水", "出口")):
        return True
    return False


def clean_upstream_point(
    raw_item: Dict[str, Any],
    point_meta: Dict[str, Any],
    collected_at: datetime,
    prev_valid: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    清洗单条上游热源/首站/网口点位，返回 `(清洗后记录, 命中督办故障列表)`。
    """
    name = point_meta.get("name") or raw_item.get("item_name") or raw_item.get("name") or ""
    sub_cat = point_meta.get("sub_category")
    data_zone = point_meta.get("data_zone") or raw_item.get("dict_name") or ""
    steam = is_steam_point(name, sub_cat, data_zone)

    temp_raw = to_float(raw_item.get("WENDU"))
    pres_raw = to_float(raw_item.get("YALI"))
    flow_raw = to_float(raw_item.get("LIULIANG"))
    heat_raw = to_float(raw_item.get("RELIANG"))
    load_val = to_float(raw_item.get("FUHE"))
    freq_val = to_float(raw_item.get("PINLV"))
    source_dt = parse_dt_east8(raw_item.get("SHIJIAN") or raw_item.get("update_time"))

    temp_clean = temp_raw
    pres_clean = pres_raw
    flow_clean = flow_raw
    heat_clean = heat_raw
    value_source = SRC_REAL
    faults: List[Dict[str, Any]] = []
    fault_tags: List[str] = []

    # 1. 传感器越限检查（蒸汽 >= 600℃，水 > 150℃；停运备机 flow<=1 且 temp==0 不误报断路）
    is_running_flow = flow_raw is not None and flow_raw > 1.0
    if temp_raw is not None:
        temp_bad = (
            (steam and temp_raw >= 600.0)
            or (not steam and temp_raw > 150.0)
            or temp_raw < -10.0
            or (is_running_flow and temp_raw <= 0.0)
        )
        if temp_bad:
            fault_tags.append(FAULT_SENSOR_RANGE)
            prev_t = prev_valid.get("temp_clean") if prev_valid else None
            temp_clean = prev_t
            value_source = SRC_MASKED_PREV
            faults.append({
                "entity_type": "UPSTREAM",
                "entity_id": f"{data_zone}:{point_meta.get('source_name', name)}",
                "entity_name": name,
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"温度={temp_raw}℃",
                "clean_strategy": "屏蔽断路极值，回退前序正常有效值",
                "rule_desc": "汽温>=600℃/<=0℃ 或 水温>150℃/<=0℃",
            })

    if pres_raw is not None and (pres_raw < 0.0 or pres_raw > 15.0 if steam else (pres_raw < 0.0 or pres_raw > 2.5)):
        fault_tags.append(FAULT_SENSOR_RANGE)
        pres_clean = prev_valid.get("pressure_clean") if prev_valid else None
        value_source = SRC_MASKED_PREV
        faults.append({
            "entity_type": "UPSTREAM",
            "entity_id": f"{data_zone}:{point_meta.get('source_name', name)}",
            "entity_name": name,
            "fault_code": FAULT_SENSOR_RANGE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"压力={pres_raw}MPa",
            "clean_strategy": "屏蔽越限压力，回退前序正常有效值",
            "rule_desc": "水压越限(<0 或 >2.5MPa) / 汽压越限(<0 或 >15MPa)",
        })

    # 2. 上游热量量纲/累计寄存器越限校验
    is_cumulative_name = "累计" in str(name)
    if heat_raw is not None and (is_cumulative_name or heat_raw < 0.0 or heat_raw > UPSTREAM_MAX_HEAT_GJH):
        if is_cumulative_name:
            fault_tags.append(FAULT_SOFTWARE_DEFECT)
            heat_clean = None
            faults.append({
                "entity_type": "UPSTREAM",
                "entity_id": f"{data_zone}:{point_meta.get('source_name', name)}",
                "entity_name": name,
                "fault_code": FAULT_SOFTWARE_DEFECT,
                "owner_party": OWNER_UNIVERSITY,
                "raw_value_text": f"累计热量原值={heat_raw} GJ",
                "clean_strategy": "保留原始累计读数 heat_raw，避免将累计计数器按瞬时速率做小时积分",
                "rule_desc": "测点名称为累计量寄存器而非瞬时热量速率",
            })
        else:
            fault_tags.append(FAULT_SENSOR_RANGE)
            heat_clean = prev_valid.get("heat_clean") if prev_valid else None
            value_source = SRC_MASKED_PREV
            faults.append({
                "entity_type": "UPSTREAM",
                "entity_id": f"{data_zone}:{point_meta.get('source_name', name)}",
                "entity_name": name,
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"热量={heat_raw} GJ/h",
                "clean_strategy": "保留原值 heat_raw，超限热量置空/回退前序有效值",
                "rule_desc": f"上游测点瞬时热量 <0 或 >{UPSTREAM_MAX_HEAT_GJH:.0f} GJ/h（疑似单位混用或传感器极值）",
            })

    # 3. 通讯停滞检查 (> 2 小时)
    if source_dt is not None and (collected_at - source_dt).total_seconds() > 7200:
        fault_tags.append(FAULT_COMM_OFFLINE)
        faults.append({
            "entity_type": "UPSTREAM",
            "entity_id": f"{data_zone}:{point_meta.get('source_name', name)}",
            "entity_name": name,
            "fault_code": FAULT_COMM_OFFLINE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"最后时间={source_dt.strftime('%Y-%m-%d %H:%M:%S')}",
            "clean_strategy": "保留停滞断面并标注通讯滞后",
            "rule_desc": "热源/首站采集时间戳滞后超过 2 小时",
        })

    cleaned = {
        "point_id": point_meta.get("point_id"),
        "data_zone": data_zone,
        "source_name": point_meta.get("source_name") or name,
        "display_name": name,
        "category": point_meta.get("category") or data_zone,
        "sub_category": sub_cat,
        "source_time": source_dt,
        "temp_raw": temp_raw,
        "temp_clean": temp_clean,
        "pressure_raw": pres_raw,
        "pressure_clean": pres_clean,
        "flow_raw": flow_raw,
        "flow_clean": flow_clean,
        "heat_raw": heat_raw,
        "heat_clean": heat_clean,
        "load_val": load_val,
        "freq_val": freq_val,
        "value_source": value_source,
        "fault_tag": ",".join(dict.fromkeys(fault_tags)) if fault_tags else None,
    }
    return cleaned, faults


def _clean_station_primary_metrics(
    station_id: str,
    station_name: str,
    e1_raw: Optional[float],
    e3_raw: Optional[float],
    e4_raw: Optional[float],
    e7_raw: Optional[float],
    e8_raw: Optional[float],
    e11_raw: Optional[float],
    e14_raw: Optional[float],
    prev_station_valid: Optional[Dict[str, Any]] = None,
    max_hourly_heat: float = 250.0,
) -> Tuple[Dict[str, Optional[float]], str, List[str], List[Dict[str, Any]]]:
    """对换热站一次网瞬时温压流热量补水执行传感器越限与物理倒挂清洗。"""
    e1_clean, e3_clean, e4_clean = e1_raw, e3_raw, e4_raw
    e7_clean, e8_clean, e11_clean, e14_clean = e7_raw, e8_raw, e11_raw, e14_raw
    value_source = SRC_REAL
    faults: List[Dict[str, Any]] = []
    fault_tags: List[str] = []

    for lbl, val, low, high in (
        ("一网供温", e3_raw, 0.0, 150.0),
        ("一网回温", e4_raw, 0.0, 150.0),
    ):
        if val is not None and (val <= low or val > high):
            fault_tags.append(FAULT_SENSOR_RANGE)
            faults.append({
                "entity_type": "STATION",
                "entity_id": station_id,
                "entity_name": station_name,
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"{lbl}={val}℃",
                "clean_strategy": "屏蔽温度极值并回退前序正常值",
                "rule_desc": "一网水温 <=0℃ 或 >150℃",
            })
            if lbl == "一网供温" and prev_station_valid:
                prev_e3 = prev_station_valid.get("e3_clean")
                e3_clean = prev_e3 if (prev_e3 is not None and 0.0 < prev_e3 <= 150.0) else None
            elif lbl == "一网供温":
                e3_clean = None
            if lbl == "一网回温" and prev_station_valid:
                prev_e4 = prev_station_valid.get("e4_clean")
                e4_clean = prev_e4 if (prev_e4 is not None and 0.0 < prev_e4 <= 150.0) else None
            elif lbl == "一网回温":
                e4_clean = None
            value_source = SRC_MASKED_PREV

    for lbl, val in (("一网供压", e7_raw), ("一网回压", e8_raw)):
        if val is not None and (val < 0.0 or val > 2.5):
            fault_tags.append(FAULT_SENSOR_RANGE)
            faults.append({
                "entity_type": "STATION",
                "entity_id": station_id,
                "entity_name": station_name,
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"{lbl}={val}MPa",
                "clean_strategy": "屏蔽越限压力并回退前序正常值",
                "rule_desc": "压力 <0 或 >2.5MPa",
            })
            if lbl == "一网供压":
                prev_e7 = prev_station_valid.get("e7_clean") if prev_station_valid else None
                e7_clean = prev_e7 if (prev_e7 is not None and 0.0 <= prev_e7 <= 2.5) else None
            if lbl == "一网回压":
                prev_e8 = prev_station_valid.get("e8_clean") if prev_station_valid else None
                e8_clean = prev_e8 if (prev_e8 is not None and 0.0 <= prev_e8 <= 2.5) else None
            value_source = SRC_MASKED_PREV

    if e14_raw is not None and (e14_raw < 0.0 or e14_raw > 100.0):
        fault_tags.append(FAULT_SENSOR_RANGE)
        faults.append({
            "entity_type": "STATION",
            "entity_id": station_id,
            "entity_name": station_name,
            "fault_code": FAULT_SENSOR_RANGE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"自来水瞬时补水={e14_raw}t/h",
            "clean_strategy": "屏蔽满量程坏表极值并回退前序正常值（无前值则置空）",
            "rule_desc": "单站瞬时补水量 <0 或 >100 t/h",
        })
        prev_e14 = prev_station_valid.get("e14_clean") if prev_station_valid else None
        e14_clean = prev_e14 if (prev_e14 is not None and 0.0 <= prev_e14 <= 100.0) else None
        value_source = SRC_MASKED_PREV

    e11_limit = max_hourly_heat * 1.5
    if e11_raw is not None and (e11_raw < 0.0 or e11_raw > e11_limit):
        fault_tags.append(FAULT_SENSOR_RANGE)
        faults.append({
            "entity_type": "STATION",
            "entity_id": station_id,
            "entity_name": station_name,
            "fault_code": FAULT_SENSOR_RANGE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"一网瞬时热量={e11_raw} GJ/h (物理上限={e11_limit:.1f} GJ/h)",
            "clean_strategy": "忠实留存 e11_raw，超限瞬间热量回退前序有效断面（无前值则置空）",
            "rule_desc": "单站一次网瞬时热量 <0 或超过按供暖面积核定极限热负荷 1.5 倍",
        })
        e11_clean = prev_station_valid.get("e11_clean") if prev_station_valid else None
        if e11_clean is not None and (e11_clean < 0.0 or e11_clean > e11_limit):
            e11_clean = None
        value_source = SRC_MASKED_PREV

    if e1_raw is not None and e1_raw > 1.0 and e3_raw is not None and e4_raw is not None and e3_raw <= e4_raw:
        fault_tags.append(FAULT_TEMP_INVERSION)
        faults.append({
            "entity_type": "STATION",
            "entity_id": station_id,
            "entity_name": station_name,
            "fault_code": FAULT_TEMP_INVERSION,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"e1={e1_raw}t/h, 供温={e3_raw}℃ <= 回温={e4_raw}℃",
            "clean_strategy": "回退相邻正常小时温差避免物理倒挂",
            "rule_desc": "正常供暖站出现一次网供温 <= 回温",
        })
        if prev_station_valid:
            e3_clean = prev_station_valid.get("e3_clean")
            e4_clean = prev_station_valid.get("e4_clean")
            value_source = SRC_MASKED_PREV

    return {
        "e1_clean": e1_clean,
        "e3_clean": e3_clean,
        "e4_clean": e4_clean,
        "e7_clean": e7_clean,
        "e8_clean": e8_clean,
        "e11_clean": e11_clean,
        "e14_clean": e14_clean,
    }, value_source, fault_tags, faults


def clean_station_history_point(
    station_meta: Dict[str, Any],
    rep_record: Optional[Dict[str, Any]],
    prev_station_valid: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """清洗从 `/hrz_ls_zb/` 提取的换热站小时代表断面（路线 B 专用）。"""
    station_id = station_meta["station_id"]
    station_name = station_meta["name"]
    if rep_record is None:
        if prev_station_valid:
            return {
                "online": False,
                "e1_raw": None, "e1_clean": prev_station_valid.get("e1_clean"),
                "e3_raw": None, "e3_clean": prev_station_valid.get("e3_clean"),
                "e4_raw": None, "e4_clean": prev_station_valid.get("e4_clean"),
                "e7_raw": None, "e7_clean": prev_station_valid.get("e7_clean"),
                "e8_raw": None, "e8_clean": prev_station_valid.get("e8_clean"),
                "e11_raw": None, "e11_clean": prev_station_valid.get("e11_clean"),
                "e14_raw": None, "e14_clean": prev_station_valid.get("e14_clean"),
                "value_source": SRC_TEMP_OFFLINE,
                "fault_tag": FAULT_COMM_OFFLINE,
            }, [{
                "entity_type": "STATION",
                "entity_id": station_id,
                "entity_name": station_name,
                "fault_code": FAULT_COMM_OFFLINE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": "该小时 /hrz_ls_zb/ 无上报记录",
                "clean_strategy": "回退前序有效断面并标注离线估值",
                "rule_desc": "换热站整小时无历史表底与瞬时上报",
            }]
        return {
            "online": False,
            "e1_raw": None, "e1_clean": None,
            "e3_raw": None, "e3_clean": None,
            "e4_raw": None, "e4_clean": None,
            "e7_raw": None, "e7_clean": None,
            "e8_raw": None, "e8_clean": None,
            "e11_raw": None, "e11_clean": None,
            "e14_raw": None, "e14_clean": None,
            "value_source": SRC_PERM_OFFLINE,
            "fault_tag": FAULT_COMM_OFFLINE,
        }, []

    e1_raw = rep_record.get("f2")
    e3_raw = rep_record.get("f3")
    e4_raw = rep_record.get("f5")
    e7_raw = rep_record.get("f1")
    e8_raw = rep_record.get("f4")
    e11_raw = rep_record.get("f222")
    e14_raw = rep_record.get("f209")
    max_hourly_heat = station_max_hourly_heat_gj(station_meta.get("covered_area"))
    cleaned_map, value_source, fault_tags, faults = _clean_station_primary_metrics(
        station_id, station_name,
        e1_raw, e3_raw, e4_raw, e7_raw, e8_raw, e11_raw, e14_raw,
        prev_station_valid=prev_station_valid,
        max_hourly_heat=max_hourly_heat,
    )
    return {
        "online": True,
        "e1_raw": e1_raw, "e1_clean": cleaned_map["e1_clean"],
        "e3_raw": e3_raw, "e3_clean": cleaned_map["e3_clean"],
        "e4_raw": e4_raw, "e4_clean": cleaned_map["e4_clean"],
        "e7_raw": e7_raw, "e7_clean": cleaned_map["e7_clean"],
        "e8_raw": e8_raw, "e8_clean": cleaned_map["e8_clean"],
        "e11_raw": e11_raw, "e11_clean": cleaned_map["e11_clean"],
        "e14_raw": e14_raw, "e14_clean": cleaned_map["e14_clean"],
        "value_source": value_source,
        "fault_tag": ",".join(dict.fromkeys(fault_tags)) if fault_tags else None,
    }, faults


def clean_station_and_zones(
    station_meta: Dict[str, Any],
    zx_item: Optional[Dict[str, Any]],
    yw_item: Optional[Dict[str, Any]],
    zone_meta_map: Dict[str, Dict[str, Any]],
    collected_at: datetime,
    prev_station_valid: Optional[Dict[str, Any]] = None,
    prev_zones_valid: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    清洗单个换热站及其下属二次网分区，返回：
    `(换热站清洗记录, 二次网分区清洗列表, 督办故障列表)`。
    """
    station_id = station_meta["station_id"]
    station_name = station_meta["name"]
    faults: List[Dict[str, Any]] = []
    fault_tags: List[str] = []

    zx = zx_item or {}
    yw = yw_item or {}

    online = bool(zx.get("online")) if zx_item is not None else False
    update_dt = parse_dt_east8(yw.get("update_time"))

    # 一网原始参数优先取 /zx_hrz/ (e1..e16)，缺失时参考 /get_yw_data/1 (f1..f5, f222)
    e1_raw = to_float(zx.get("e1")) if zx_item is not None else to_float(yw.get("f2"))
    e3_raw = to_float(zx.get("e3")) if zx_item is not None else to_float(yw.get("f3"))
    e4_raw = to_float(zx.get("e4")) if zx_item is not None else to_float(yw.get("f5"))
    e7_raw = to_float(zx.get("e7")) if zx_item is not None else to_float(yw.get("f1"))
    e8_raw = to_float(zx.get("e8")) if zx_item is not None else to_float(yw.get("f4"))
    e11_raw = to_float(zx.get("e11")) if zx_item is not None else to_float(yw.get("f222"))
    e13_raw = to_float(zx.get("e13"))
    e14_raw = to_float(zx.get("e14"))
    e16_raw = to_float(zx.get("e16"))
    if e16_raw is None and zx.get("Nx"):
        # 规范书特例：“香炉礁”站水位 e16 在 Nx[0].data.e16 中
        first_nx_data = (zx["Nx"][0] or {}).get("data") or {}
        e16_raw = to_float(first_nx_data.get("e16"))

    e1_clean, e3_clean, e4_clean = e1_raw, e3_raw, e4_raw
    e7_clean, e8_clean, e11_clean, e14_clean = e7_raw, e8_raw, e11_raw, e14_raw
    value_source = SRC_REAL

    # 换热站通讯离线以 /zx_hrz/ 的 online 为核心判据（/get_yw_data/1 的 update_time 在源站存在全网级滞后，不直接判定站掉线）
    is_offline = (zx_item is not None and not online)

    if is_offline:
        fault_tags.append(FAULT_COMM_OFFLINE)
        faults.append({
            "entity_type": "STATION",
            "entity_id": station_id,
            "entity_name": station_name,
            "fault_code": FAULT_COMM_OFFLINE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"online={online}, update_time={yw.get('update_time')}",
            "clean_strategy": "临时离线使用前序正常值平滑估值并加审计角标" if prev_station_valid else "标记通讯离线",
            "rule_desc": "换热站通讯状态 online == false",
        })
        if prev_station_valid:
            e1_clean = prev_station_valid.get("e1_clean")
            e3_clean = prev_station_valid.get("e3_clean")
            e4_clean = prev_station_valid.get("e4_clean")
            e7_clean = prev_station_valid.get("e7_clean")
            e8_clean = prev_station_valid.get("e8_clean")
            e11_clean = prev_station_valid.get("e11_clean")
            e14_clean = prev_station_valid.get("e14_clean")
            value_source = SRC_TEMP_OFFLINE
        else:
            value_source = SRC_PERM_OFFLINE
    else:
        max_hourly_heat = station_max_hourly_heat_gj(station_meta.get("covered_area"))
        cleaned_map, value_source, p_tags, p_faults = _clean_station_primary_metrics(
            station_id, station_name,
            e1_raw, e3_raw, e4_raw, e7_raw, e8_raw, e11_raw, e14_raw,
            prev_station_valid=prev_station_valid,
            max_hourly_heat=max_hourly_heat,
        )
        e1_clean = cleaned_map["e1_clean"]
        e3_clean = cleaned_map["e3_clean"]
        e4_clean = cleaned_map["e4_clean"]
        e7_clean = cleaned_map["e7_clean"]
        e8_clean = cleaned_map["e8_clean"]
        e11_clean = cleaned_map["e11_clean"]
        e14_clean = cleaned_map["e14_clean"]
        fault_tags.extend(p_tags)
        faults.extend(p_faults)

    # 清洗下属二次网分区
    cleaned_zones: List[Dict[str, Any]] = []
    zone_heat_sum = 0.0
    has_zone_heat = False
    prev_z_map = prev_zones_valid or {}

    for nx in zx.get("Nx") or []:
        z_name = str(nx.get("name") or "").strip()
        z_meta = zone_meta_map.get(z_name)
        if not z_meta:
            continue
        z_id = z_meta["secondary_zone_id"]
        is_baseline_online = bool(z_meta.get("is_online", True))
        z_data = nx.get("data") or {}

        e2_raw = to_float(z_data.get("e2"))
        e5_raw = to_float(z_data.get("e5"))
        e6_raw = to_float(z_data.get("e6"))
        e9_raw = to_float(z_data.get("e9"))
        e10_raw = to_float(z_data.get("e10"))
        e12_raw = to_float(z_data.get("e12"))
        e15_raw = to_float(z_data.get("e15"))

        if e12_raw is not None:
            zone_heat_sum += e12_raw
            has_zone_heat = True

        e2_clean, e5_clean, e6_clean = e2_raw, e5_raw, e6_raw
        e9_clean, e10_clean, e15_clean = e9_raw, e10_raw, e15_raw
        z_src = SRC_REAL if is_baseline_online else SRC_PERM_OFFLINE
        z_tags: List[str] = []
        prev_z = prev_z_map.get(z_id)

        if not is_baseline_online:
            z_tags.append(FAULT_COMM_OFFLINE)
        else:
            if e5_raw is not None and e6_raw is not None and e2_raw is not None and e2_raw > 1.0 and e5_raw <= e6_raw:
                z_tags.append(FAULT_TEMP_INVERSION)
                faults.append({
                    "entity_type": "SECONDARY_ZONE",
                    "entity_id": z_id,
                    "entity_name": f"{station_name}-{z_name}",
                    "fault_code": FAULT_TEMP_INVERSION,
                    "owner_party": OWNER_RESEARCH,
                    "raw_value_text": f"二网供温={e5_raw}℃ <= 回温={e6_raw}℃",
                    "clean_strategy": "回退前序正常二网温度",
                    "rule_desc": "二次网循环流量 > 1 t/h 时供温 <= 回温",
                })
                if prev_z:
                    e5_clean = prev_z.get("e5_clean")
                    e6_clean = prev_z.get("e6_clean")
                    z_src = SRC_MASKED_PREV

            if e5_raw is not None and e3_raw is not None and e3_raw > 10.0 and e5_raw > e3_raw + 0.5:
                z_tags.append(FAULT_TEMP_INVERSION)
                faults.append({
                    "entity_type": "SECONDARY_ZONE",
                    "entity_id": z_id,
                    "entity_name": f"{station_name}-{z_name}",
                    "fault_code": FAULT_TEMP_INVERSION,
                    "owner_party": OWNER_RESEARCH,
                    "raw_value_text": f"二网供温={e5_raw}℃ > 一网供温={e3_raw}℃",
                    "clean_strategy": "回退前序正常二网供温，保障物理换热自洽",
                    "rule_desc": "二次网供温高于一次网供温（违反热力学定律）",
                })
                if prev_z:
                    e5_clean = prev_z.get("e5_clean")
                    z_src = SRC_MASKED_PREV

        cleaned_zones.append({
            "secondary_zone_id": z_id,
            "station_id": station_id,
            "e2_raw": e2_raw,
            "e2_clean": e2_clean,
            "e5_raw": e5_raw,
            "e5_clean": e5_clean,
            "e6_raw": e6_raw,
            "e6_clean": e6_clean,
            "e9_raw": e9_raw,
            "e9_clean": e9_clean,
            "e10_raw": e10_raw,
            "e10_clean": e10_clean,
            "e12_raw": e12_raw,
            "e15_raw": e15_raw,
            "e15_clean": e15_clean,
            "value_source": z_src,
            "fault_tag": ",".join(dict.fromkeys(z_tags)) if z_tags else None,
        })

    # 一二网热平衡失真审计（仅比对，阳面严禁使用 e12）
    heat_diff_pct: Optional[float] = None
    if has_zone_heat:
        if e11_raw is not None and e11_raw > 0.05:
            heat_diff_pct = round((zone_heat_sum - e11_raw) / e11_raw * 100.0, 2)
            if abs(heat_diff_pct) > 20.0:
                fault_tags.append(FAULT_HEAT_IMBALANCE)
                faults.append({
                    "entity_type": "STATION",
                    "entity_id": station_id,
                    "entity_name": station_name,
                    "fault_code": FAULT_HEAT_IMBALANCE,
                    "owner_party": OWNER_RESEARCH,
                    "raw_value_text": f"一网e11={e11_raw:.2f} GJ/h, 二网Σe12={zone_heat_sum:.2f} GJ/h (偏差 {heat_diff_pct:+.1f}%)",
                    "clean_strategy": "阳面热量强制采用一次网 e11/totJ，隐藏失真二网热量 e12",
                    "rule_desc": "一二网热量偏差 |(Σe12 - e11)/e11| > 20%",
                })
        elif (e11_raw is None or e11_raw == 0.0) and zone_heat_sum > 0.2 and online:
            fault_tags.append(FAULT_HEAT_IMBALANCE)
            faults.append({
                "entity_type": "STATION",
                "entity_id": station_id,
                "entity_name": station_name,
                "fault_code": FAULT_HEAT_IMBALANCE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"在线站一网e11={e11_raw}, 二网Σe12={zone_heat_sum:.2f} GJ/h",
                "clean_strategy": "保留一网表底核算并对该站表计掉零发起督办",
                "rule_desc": "在线换热站一次网瞬时热量为0但二次网存在明显负荷",
            })

    station_cleaned = {
        "station_id": station_id,
        "online": online,
        "source_update_time": update_dt,
        "e1_raw": e1_raw,
        "e1_clean": e1_clean,
        "e3_raw": e3_raw,
        "e3_clean": e3_clean,
        "e4_raw": e4_raw,
        "e4_clean": e4_clean,
        "e7_raw": e7_raw,
        "e7_clean": e7_clean,
        "e8_raw": e8_raw,
        "e8_clean": e8_clean,
        "e11_raw": e11_raw,
        "e11_clean": e11_clean,
        "e13_raw": e13_raw,
        "e14_raw": e14_raw,
        "e14_clean": e14_clean,
        "e16_raw": e16_raw,
        "zone_heat_sum_e12": round(zone_heat_sum, 3) if has_zone_heat else None,
        "heat_balance_diff_pct": heat_diff_pct,
        "value_source": value_source,
        "fault_tag": ",".join(dict.fromkeys(fault_tags)) if fault_tags else None,
    }
    return station_cleaned, cleaned_zones, faults


def clean_temp_device(
    raw_item: Dict[str, Any],
    device_dict: Dict[str, Dict[str, Any]],
    alias_station_map: Dict[str, str],
    collected_at: datetime,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    清洗单条居民室温终端数据（/jumin/ 字段为 wd1）。

    约定：未纳入标准台账的新增终端（如多出的 3 户）在阳面标记 is_online_valid=False 并剔除，
    同时写入阴面提示；掉线 > 7 天或室温 <=5℃/>40℃ 同样从阳面剔除并写入督办。
    """
    device_id = str(raw_item.get("id") or "").strip()
    village_name = str(raw_item.get("village_name") or "").strip()
    station_name_raw = str(raw_item.get("station_name") or "").strip()
    zdxh = str(raw_item.get("zdxh") or "").strip()
    remark = str(raw_item.get("Beizhu") or "").strip()
    temp_raw = to_float(raw_item.get("wd1") if raw_item.get("wd1") is not None else raw_item.get("temp"))
    upload_dt = parse_dt_east8(raw_item.get("upload_time"))

    meta = device_dict.get(device_id)
    is_registered = meta is not None
    station_id = meta["station_id"] if meta else alias_station_map.get(station_name_raw)

    faults: List[Dict[str, Any]] = []
    fault_tags: List[str] = []
    is_valid = is_registered
    temp_clean = temp_raw

    if not is_registered:
        fault_tags.append(FAULT_SOFTWARE_DEFECT)
        is_valid = False
        temp_clean = None
        faults.append({
            "entity_type": "TEMP_DEVICE",
            "entity_id": device_id,
            "entity_name": f"{station_name_raw or '未知站'}-{village_name or device_id}",
            "fault_code": FAULT_SOFTWARE_DEFECT,
            "owner_party": OWNER_UNIVERSITY,
            "raw_value_text": f"未入台账终端 (wd1={temp_raw}℃, 站名={station_name_raw})",
            "clean_strategy": "阳面统计严格剔除未入台账终端，阴面保留提醒核实",
            "rule_desc": "/jumin/ 返回终端未在基础台账 2,097 户清单内",
        })

    if upload_dt is None or (collected_at - upload_dt).total_seconds() > 7 * 86400:
        fault_tags.append(FAULT_COMM_OFFLINE)
        is_valid = False
        temp_clean = None
        faults.append({
            "entity_type": "TEMP_DEVICE",
            "entity_id": device_id,
            "entity_name": f"{(meta or {}).get('station_name') or station_name_raw}-{village_name or device_id}",
            "fault_code": FAULT_COMM_OFFLINE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"最后上传={raw_item.get('upload_time') or '空'}",
            "clean_strategy": "从阳面室温均温与达标率中剔除僵尸掉线户",
            "rule_desc": "居民测温终端 upload_time 超过 7 天未更新",
        })

    if temp_raw is None or temp_raw <= 5.0 or temp_raw > 40.0:
        fault_tags.append(FAULT_SENSOR_RANGE)
        is_valid = False
        temp_clean = None
        faults.append({
            "entity_type": "TEMP_DEVICE",
            "entity_id": device_id,
            "entity_name": f"{(meta or {}).get('station_name') or station_name_raw}-{village_name or device_id}",
            "fault_code": FAULT_SENSOR_RANGE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"室温={temp_raw}℃",
            "clean_strategy": "从阳面均值剔除超限无效室温",
            "rule_desc": "居民室温 <=5℃ 或 >40℃ 或为空",
        })

    return {
        "temp_device_id": device_id,
        "station_id": station_id,
        "is_registered": is_registered,
        "village_name": village_name[:128],
        "station_name_raw": station_name_raw[:128],
        "zdxh": zdxh[:32],
        "temp_raw": temp_raw,
        "temp_clean": temp_clean,
        "upload_time": upload_dt,
        "is_online_valid": is_valid,
        "remark_snapshot": remark,
        "fault_tag": ",".join(dict.fromkeys(fault_tags)) if fault_tags else None,
    }, faults


MERCHANT_ALIAS_MAP: Dict[str, str] = {
    "国际航运中心大厦": "航运中心大厦",
}


def clean_merchant_point(
    raw_item: Dict[str, Any],
    merchant_lookup: Dict[str, Dict[str, Any]],
    collected_at: datetime,
    prev_valid: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    清洗单条商业用户实时/历史点位（/get_sh_data/ 或 /sh_ls_zb/）。

    - 自动归一化名称别名（如“国际航运中心大厦” -> “航运中心大厦”）；
    - 未在 dict_merchant 464 户台账内的测试/未入账商户（如“测试商户”）在阳面标记
      `is_registered=False` 并置空净化指标，同时写入阴面督办提醒；
    - 离线/温度越限/压力越限/物理倒挂回退最近 6 小时有效值并留存 raw 值证据。
    """
    source_name = str(raw_item.get("name") or "").strip()
    canonical_name = MERCHANT_ALIAS_MAP.get(source_name, source_name)
    meta = merchant_lookup.get(source_name) or merchant_lookup.get(canonical_name)
    is_registered = meta is not None
    merchant_id = meta["merchant_id"] if meta else None

    if "xinhaoqiangdu" in raw_item:
        sig_val = raw_item.get("xinhaoqiangdu")
        online = (str(sig_val).strip() == "0") if sig_val is not None else False
    else:
        online = True

    is_steam_merchant = str(meta.get("rdry") or "").strip() == "蒸汽" if meta else False

    flow_raw = to_float(raw_item.get("gongshuiliuliang") if "gongshuiliuliang" in raw_item else raw_item.get("fFlowF"))
    ret_flow_raw = to_float(
        raw_item.get("huishuliuliang") if "huishuliuliang" in raw_item else raw_item.get("ShunShiHuiShuiLiuLiang")
    )
    temp_sup_raw = to_float(raw_item.get("gongshuiwendu") if "gongshuiwendu" in raw_item else raw_item.get("fTempSupply"))
    temp_ret_raw = to_float(raw_item.get("huishuiwendu") if "huishuiwendu" in raw_item else raw_item.get("fTempReturn"))
    pres_sup_raw = to_float(raw_item.get("gongshuiyali") if "gongshuiyali" in raw_item else raw_item.get("GongShuiYaLi"))
    pres_ret_raw = to_float(raw_item.get("huishuiyali") if "huishuiyali" in raw_item else raw_item.get("HuiShuiYaLi"))
    heat_raw = to_float(raw_item.get("shunshireliang") if "shunshireliang" in raw_item else raw_item.get("fFlowJ"))
    valve_open = to_float(raw_item.get("famenkaidu"))
    valve_set = to_float(raw_item.get("shedingfamen"))

    faults: List[Dict[str, Any]] = []
    fault_tags: List[str] = []

    if not is_registered:
        fault_tags.append(FAULT_SOFTWARE_DEFECT)
        faults.append({
            "entity_type": "MERCHANT",
            "entity_id": source_name or "UNKNOWN_MERCHANT",
            "entity_name": source_name or "未命名商业户",
            "fault_code": FAULT_SOFTWARE_DEFECT,
            "owner_party": OWNER_UNIVERSITY,
            "raw_value_text": f"未入台账商业户 (瞬时热量={heat_raw} GJ/h, 流量={flow_raw} t/h)",
            "clean_strategy": "阳面商业小时报表剔除测试/未入账商户，阴面保留提醒核实",
            "rule_desc": "/get_sh_data/ 返回商户未在标准 464 户基础台账内",
        })
        return {
            "merchant_id": None,
            "source_name": source_name[:128],
            "is_registered": False,
            "online": False,
            "flow_raw": flow_raw,
            "flow_clean": None,
            "return_flow_raw": ret_flow_raw,
            "temp_sup_raw": temp_sup_raw,
            "temp_sup_clean": None,
            "temp_ret_raw": temp_ret_raw,
            "temp_ret_clean": None,
            "pres_sup_raw": pres_sup_raw,
            "pres_sup_clean": None,
            "pres_ret_raw": pres_ret_raw,
            "pres_ret_clean": None,
            "heat_raw": heat_raw,
            "heat_clean": None,
            "valve_open": valve_open,
            "valve_set": valve_set,
            "value_source": SRC_PERM_OFFLINE,
            "fault_tag": FAULT_SOFTWARE_DEFECT,
        }, faults

    flow_clean = (round(flow_raw / 1000.0, 4) if (is_steam_merchant and flow_raw is not None) else flow_raw)
    temp_sup_clean = temp_sup_raw
    temp_ret_clean = None if (is_steam_merchant and temp_ret_raw is not None and temp_ret_raw <= -10.0) else temp_ret_raw
    pres_sup_clean = pres_sup_raw
    pres_ret_clean = pres_ret_raw
    heat_clean = (round(heat_raw / 1000.0, 4) if (is_steam_merchant and heat_raw is not None) else heat_raw)
    value_source = SRC_REAL

    if is_steam_merchant and ((flow_raw is not None and flow_raw > 0) or (heat_raw is not None and heat_raw > 0)):
        fault_tags.append(FAULT_SOFTWARE_DEFECT)
        faults.append({
            "entity_type": "MERCHANT",
            "entity_id": merchant_id,
            "entity_name": meta["name"],
            "fault_code": FAULT_SOFTWARE_DEFECT,
            "owner_party": OWNER_UNIVERSITY,
            "raw_value_text": f"蒸汽户原值: flow={flow_raw} kg/h, heat={heat_raw} MJ/h, ret_temp={temp_ret_raw}℃",
            "clean_strategy": "蒸汽商业户流量/热量自动÷1000折算为 t/h 与 GJ/h，屏蔽-200℃回温",
            "rule_desc": "蒸汽商户接口单位未折算（kg/h、MJ/h 放大1000倍）",
        })

    if not online:
        fault_tags.append(FAULT_COMM_OFFLINE)
        faults.append({
            "entity_type": "MERCHANT",
            "entity_id": merchant_id,
            "entity_name": meta["name"],
            "fault_code": FAULT_COMM_OFFLINE,
            "owner_party": OWNER_RESEARCH,
            "raw_value_text": f"xinhaoqiangdu={raw_item.get('xinhaoqiangdu')}",
            "clean_strategy": "临时离线回退前序有效断面，无前值则保持离线标识" if prev_valid else "标记商业户通讯离线",
            "rule_desc": "商业用户信号强度 != 0（通讯离线）",
        })
        if prev_valid:
            flow_clean = prev_valid.get("flow_clean")
            temp_sup_clean = prev_valid.get("temp_sup_clean")
            temp_ret_clean = prev_valid.get("temp_ret_clean")
            pres_sup_clean = prev_valid.get("pres_sup_clean")
            pres_ret_clean = prev_valid.get("pres_ret_clean")
            heat_clean = prev_valid.get("heat_clean")
            value_source = SRC_TEMP_OFFLINE
        else:
            value_source = SRC_PERM_OFFLINE
    else:
        max_temp = 600.0 if is_steam_merchant else 150.0
        temp_pairs = (("商业供温", temp_sup_raw),) if is_steam_merchant else (("商业供温", temp_sup_raw), ("商业回温", temp_ret_raw))
        water_temp_broken = False
        for lbl, val in temp_pairs:
            eff_flow = (flow_clean or 0.0)
            if val is not None and (val < -10.0 or val > max_temp or (eff_flow > 0.5 and val <= 0.0)):
                fault_tags.append(FAULT_SENSOR_RANGE)
                faults.append({
                    "entity_type": "MERCHANT",
                    "entity_id": merchant_id,
                    "entity_name": meta["name"],
                    "fault_code": FAULT_SENSOR_RANGE,
                    "owner_party": OWNER_RESEARCH,
                    "raw_value_text": f"{lbl}={val}℃",
                    "clean_strategy": "屏蔽超限温度并回退前序正常有效值",
                    "rule_desc": f"商业户温度越限（<-10℃ 或 >{max_temp:.0f}℃ 或带流量<=0℃）",
                })
                if lbl == "商业供温":
                    temp_sup_clean = prev_valid.get("temp_sup_clean") if prev_valid else None
                else:
                    temp_ret_clean = prev_valid.get("temp_ret_clean") if prev_valid else None
                if not is_steam_merchant and val < -10.0:
                    water_temp_broken = True
                value_source = SRC_MASKED_PREV

        max_pres = 15.0 if is_steam_merchant else 2.5
        for lbl, val in (("商业供压", pres_sup_raw), ("商业回压", pres_ret_raw)):
            if val is not None and (val < 0.0 or val > max_pres):
                fault_tags.append(FAULT_SENSOR_RANGE)
                faults.append({
                    "entity_type": "MERCHANT",
                    "entity_id": merchant_id,
                    "entity_name": meta["name"],
                    "fault_code": FAULT_SENSOR_RANGE,
                    "owner_party": OWNER_RESEARCH,
                    "raw_value_text": f"{lbl}={val}MPa",
                    "clean_strategy": "屏蔽越限压力并回退前序正常有效值",
                    "rule_desc": f"商业户压力 <0 或 >{max_pres}MPa",
                })
                if lbl == "商业供压":
                    pres_sup_clean = prev_valid.get("pres_sup_clean") if prev_valid else None
                else:
                    pres_ret_clean = prev_valid.get("pres_ret_clean") if prev_valid else None
                value_source = SRC_MASKED_PREV

        if water_temp_broken or (heat_clean is not None and (heat_clean < 0.0 or heat_clean > 500.0)):
            fault_tags.append(FAULT_SENSOR_RANGE)
            faults.append({
                "entity_type": "MERCHANT",
                "entity_id": merchant_id,
                "entity_name": meta["name"],
                "fault_code": FAULT_SENSOR_RANGE,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"瞬时热量={heat_raw} (折算 {heat_clean} GJ/h)",
                "clean_strategy": "屏蔽断路温度导致的失真热量极值并回退前序正常值",
                "rule_desc": "单商业户折算瞬时热量 <0 或 >500 GJ/h 或受温度断路(-200℃)污染",
            })
            heat_clean = prev_valid.get("heat_clean") if prev_valid else None
            value_source = SRC_MASKED_PREV

        if (
            not is_steam_merchant
            and flow_clean is not None and flow_clean > 0.5
            and temp_sup_raw is not None and temp_ret_raw is not None
            and temp_sup_raw <= temp_ret_raw
        ):
            fault_tags.append(FAULT_TEMP_INVERSION)
            faults.append({
                "entity_type": "MERCHANT",
                "entity_id": merchant_id,
                "entity_name": meta["name"],
                "fault_code": FAULT_TEMP_INVERSION,
                "owner_party": OWNER_RESEARCH,
                "raw_value_text": f"供流={flow_clean}t/h, 供温={temp_sup_raw}℃ <= 回温={temp_ret_raw}℃",
                "clean_strategy": "回退前序正常供回温差避免物理倒挂",
                "rule_desc": "商业户正常用热流量 >0.5t/h 时供温 <= 回温",
            })
            if prev_valid:
                temp_sup_clean = prev_valid.get("temp_sup_clean")
                temp_ret_clean = prev_valid.get("temp_ret_clean")
                value_source = SRC_MASKED_PREV

    return {
        "merchant_id": merchant_id,
        "source_name": meta["name"],
        "is_registered": True,
        "online": online,
        "flow_raw": flow_raw,
        "flow_clean": flow_clean,
        "return_flow_raw": ret_flow_raw,
        "temp_sup_raw": temp_sup_raw,
        "temp_sup_clean": temp_sup_clean,
        "temp_ret_raw": temp_ret_raw,
        "temp_ret_clean": temp_ret_clean,
        "pres_sup_raw": pres_sup_raw,
        "pres_sup_clean": pres_sup_clean,
        "pres_ret_raw": pres_ret_raw,
        "pres_ret_clean": pres_ret_clean,
        "heat_raw": heat_raw,
        "heat_clean": heat_clean,
        "valve_open": valve_open,
        "valve_set": valve_set,
        "value_source": value_source,
        "fault_tag": ",".join(dict.fromkeys(fault_tags)) if fault_tags else None,
    }, faults
