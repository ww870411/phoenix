"""每日简报：复用日报算法，以可追溯的事实、同比与连续变化组织阅读。"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime, timedelta

from sqlalchemy import text

from backend.services.auth_manager import EAST_8
from backend.services.heating_metrics.daily_engine import (
    DailyDashboardEngine, GROUP_COMPANIES, ZHUCHENGQU_COMPANIES, SPECIAL_STATION_HEAT_PLANTS,
)
from backend.services.heating_metrics.season_utils import get_peer_date, get_season_period, get_season_windows

logger = logging.getLogger(__name__)
PROJECT_KEY = "daily_report_25_26"
COMPANIES = {
    "Group": "集团全口径", "ZhuChengQu": "主城区", "BeiHai": "北海热电厂",
    "XiangHai": "香海热电厂", "GongRe": "供热公司", "JinZhou": "金州热电",
    "BeiFang": "北方热电", "JinPu": "金普热电", "ZhuangHe": "庄河环海", "YanJiuYuan": "研究院",
}
# 展示精度同时用于识别连续变化，避免小于显示精度的噪声进入摘要。
METRICS = (
    ("eco_comparable_marginal_profit", "可比煤价边际利润", "万元", 2),
    ("consumption_std_coal", "标煤耗量", "吨", 2),
    ("consumption_station_heat", "站内耗热量", "GJ", 2),
    ("amount_daily_service_complaints", "省市平台投诉量", "件", 0),
    ("amount_daily_net_complaints", "净投诉量", "件", 0),
    ("eco_marginal_profit", "实际边际利润", "万元", 2),
    ("amount_heat_supply", "供热量", "GJ", 2),
    ("amount_power_sales", "售电量", "万kWh", 2),
    ("rate_std_coal_per_heat", "供热标煤单耗", "吨/万㎡", 3),
    ("rate_heat_per_10k_m2", "供暖热单耗", "GJ/万㎡", 2),
    ("amount_daily_net_complaints_per_10k_m2", "万平方米净投诉量", "件/万㎡", 4),
    ("amount_power_generation", "发电量", "万kWh", 2),
    ("amount_hot_water_sales", "高温水销售量", "GJ", 2),
    ("amount_steam_sales", "售汽量", "吨", 2),
    ("rate_water_per_10k_m2", "供暖水单耗", "吨/万㎡", 2),
    ("rate_power_per_10k_m2", "供暖电单耗", "kWh/万㎡", 2),
    ("amount_turbine_running", "汽轮机", "台", 0),
    ("amount_boiler_steam_running", "蒸汽锅炉", "台", 0),
    ("amount_boiler_water_running", "水炉", "台", 0),
    ("amount_boiler_room_running", "锅炉房锅炉", "台", 0),
)
PRICE_INPUTS = {
    "amount_power_sales": "price_power_sales", "amount_heat_supply": "price_inner_heat_sales",
    "amount_hot_water_sales": "price_hot_water_sales", "amount_steam_sales": "price_steam_sales",
    "consumption_natural_gas": "price_natural_gas", "consumption_purchased_power": "price_purchased_power",
    "consumption_water": "price_purchased_water", "consumption_outer_purchased_heat": "price_outer_purchased_heat",
    "amount_network_interface_heat_supply": "price_inner_purchased_heat",
    "consumption_acid": "price_acid", "consumption_alkali": "price_alkali",
    "consumption_oil": "price_oil", "consumption_ammonia_water": "price_n_ammonia_water",
    "consumption_limestone": "price_limestone", "consumption_limestone_powder": "price_limestone_powder",
    "consumption_magnesium_oxide": "price_magnesium_oxide", "consumption_denitration_agent": "price_denitration_agent",
}
PROFIT_INPUTS = set(PRICE_INPUTS) | {"consumption_std_coal", "eco_hot_water_supply_income", "eco_steam_supply_income"}


def number(value):
    """拒绝 NaN/Infinity；显式零值有效。"""
    try:
        result = float(value) if value is not None else None
        return result if result is not None and math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def comparison(current, peer, digits=2):
    """负基数、零基数与盈亏转换只报告差额，不制造误导性增长率。"""
    current, peer = number(current), number(peer)
    result = {"delta": None, "percent": None, "direction": "unknown", "note": "比较数据不足"}
    if current is None or peer is None:
        return result
    delta = current - peer
    direction = "up" if round(delta, digits) > 0 else "down" if round(delta, digits) < 0 else "flat"
    result.update(delta=delta, direction=direction, note="")
    if peer > 0 and current >= 0 and round(peer, digits) > 0:
        result["percent"] = delta / peer * 100
    elif peer == 0 or round(abs(peer), digits) == 0:
        result["note"] = "同期为零或低于显示精度，仅比较增减量"
    elif peer < 0 or current < 0:
        result["note"] = "存在负值，仅比较增减量"
    return result


def describe_change(label, current, peer, unit, digits):
    comp = comparison(current, peer, digits)
    if number(current) is None:
        return f"{label}：—。"
    if number(peer) is None:
        return f"{label}{current:,.{digits}f}{unit}，同期 —。"
    if comp["direction"] == "flat":
        return f"{label}{current:,.{digits}f}{unit}，同比持平。"
    verb = "增加" if comp["direction"] == "up" else "减少"
    extra = f"（{abs(comp['percent']):.1f}%）" if comp["percent"] is not None else ""
    transition = ""
    if "利润" in label:
        if peer < 0 <= current:
            transition = "，由亏转盈" if current > 0 else "，由亏损转为持平"
        elif peer >= 0 > current:
            transition = "，由盈转亏" if peer > 0 else "，由持平转为亏损"
        elif peer < 0 and current < 0:
            transition = "，亏损额收窄" if current > peer else "，亏损额扩大"
    return f"{label}{current:,.{digits}f}{unit}，同比{verb}{abs(comp['delta']):,.{digits}f}{unit}{extra}{transition}。"


def trend_summary(points, label, unit, digits):
    """只从连续、完整、可比较的日序列得出描述，缺一天即中断连续性。"""
    valid = [p for p in points if number(p["value"]) is not None and number(p["peer"]) is not None]
    yoy_run, direction = 0, None
    for point in reversed(points):
        change = comparison(point["value"], point["peer"], digits)["direction"]
        if change not in ("up", "down") or direction and change != direction:
            break
        direction = change
        yoy_run += 1
    daily_run, daily_direction = 0, None
    for index in range(len(points) - 1, 0, -1):
        change = comparison(points[index]["value"], points[index - 1]["value"], digits)["direction"]
        if change not in ("up", "down") or daily_direction and change != daily_direction:
            break
        daily_direction = change
        daily_run += 1
    sentences = []
    if yoy_run >= 3:
        sentences.append(f"{label}连续{yoy_run}日{'高于' if direction == 'up' else '低于'}各自同期")
    if daily_run >= 3:
        sentences.append(f"连续{daily_run}次日间比较{'增加' if daily_direction == 'up' else '减少'}")
    return {
        "text": "；".join(sentences) + "。" if sentences else "", "comparable_days": len(valid), "expected_days": len(points),
        "yoy_run": yoy_run, "direction": direction, "daily_run": daily_run,
        "current_average": sum(p["value"] for p in points) / len(points) if all(number(p["value"]) is not None for p in points) else None,
        "peer_average": sum(p["peer"] for p in points) / len(points) if all(number(p["peer"]) is not None for p in points) else None,
    }


class BriefEvidence:
    """在既有算法外保留底表完整性证据，禁止算法补零变成简报中的真实零。"""

    def __init__(self, raw_rows, expected_rows, constants):
        self.raw = {(r["company"], r["item"], r["date"]): number(r["value"]) for r in raw_rows}
        self.expected = {}
        for row in expected_rows:
            self.expected.setdefault((row["company"], row["period"]), set()).add(row["item"])
        self.constants = {(r["company"], r["item"], r["period"]): number(r["value"]) for r in constants}

    def check(self, company, metric, day):
        leaves = GROUP_COMPANIES if company == "Group" else ZHUCHENGQU_COMPANIES if company == "ZhuChengQu" else [company]
        period = get_season_period(day)
        failures, applicable = [], False
        for leaf in leaves:
            known = self.expected.get((leaf, period), set())
            if metric.startswith("eco_"):
                dependencies = known & PROFIT_INPUTS
                # 经济计算需要本期暖收入常量；其余非零耗量/销量也必须有有效单价。
                required_constants = {"eco_season_heating_income"} if leaf not in {"BeiHai", "XiangHai"} else set()
                price_inputs = dict(PRICE_INPUTS)
                price_inputs["consumption_std_coal"] = "price_std_coal_comparable" if metric == "eco_comparable_marginal_profit" else "price_std_coal"
                for raw_item, price in price_inputs.items():
                    if leaf == "GongRe" and raw_item in {"amount_hot_water_sales", "amount_steam_sales"}:
                        continue
                    if company in {"Group", "ZhuChengQu"} and raw_item in {"amount_heat_supply", "amount_network_interface_heat_supply"}:
                        continue  # 集团/主城区内部购销热已抵消，无需内部热价。
                    value = self.raw.get((leaf, raw_item, day))
                    if value is not None and value != 0:
                        required_constants.add(price)
                failures.extend(f"{COMPANIES[leaf]}：缺少常量 {key}" for key in sorted(required_constants)
                                if self.constants.get((leaf, key, period)) is None)
            else:
                base = {"rate_std_coal_per_heat": "consumption_std_coal", "rate_heat_per_10k_m2": "consumption_station_heat",
                        "rate_power_per_10k_m2": "consumption_station_purchased_power",
                        "amount_daily_net_complaints_per_10k_m2": "amount_daily_net_complaints"}.get(metric, metric)
                dependencies = {base}
                if metric == "rate_water_per_10k_m2":
                    dependencies = {"consumption_network_fill_water", "consumption_station_fill_water", "consumption_network_water"}
                if base == "consumption_station_heat" and leaf in SPECIAL_STATION_HEAT_PLANTS:
                    dependencies = {"amount_heat_supply", "amount_hot_water_sales"}
                dependencies &= known
                if metric in {"rate_std_coal_per_heat", "rate_heat_per_10k_m2", "amount_daily_net_complaints_per_10k_m2",
                              "rate_water_per_10k_m2", "rate_power_per_10k_m2"}:
                    area = self.constants.get((leaf, "amount_heating_fee_area", period))
                    # 纯热源厂没有终端供暖面积；集团面积由供热侧构成，不能要求热源厂也有面积。
                    if leaf not in {"BeiHai", "XiangHai"} and (area is None or area <= 0):
                        failures.append(f"{COMPANIES[leaf]}：供暖面积缺失或非正数")
            if dependencies:
                applicable = True
                failures.extend(f"{COMPANIES[leaf]}：{key}未报或为空" for key in sorted(dependencies)
                                if self.raw.get((leaf, key, day)) is None)
            elif metric.startswith("eco_"):
                failures.append(f"{COMPANIES[leaf]}：缺少经营原始数据")
        if not applicable:
            failures.append("本口径未找到该指标的原始申报依据")
        return list(dict.fromkeys(failures))

    def has_profit_source(self, company, day):
        """利润沿用既有补零规则，但整家单位缺报时不能仅凭暖收入生成完整利润。"""
        leaves = GROUP_COMPANIES if company == "Group" else ZHUCHENGQU_COMPANIES if company == "ZhuChengQu" else [company]
        return all(any(self.raw.get((leaf, item, day)) is not None for item in PROFIT_INPUTS) for leaf in leaves)


def _optional(session, title, reader):
    """补充板块独立隔离；某张可选表不存在时不得误称业务平稳。"""
    try:
        with session.begin_nested():
            return reader()
    except Exception:
        logger.warning("每日简报的%s数据暂不可用", title, exc_info=True)
        return {"title": title, "status": "unavailable", "summary": "数据暂不可用。", "facts": []}


def read_spot(session, day):
    rows = session.execute(text("""
        SELECT trade_date, COUNT(DISTINCT point_index) AS points,
          COUNT(day_ahead_price) AS da_points, COUNT(real_time_price) AS rt_points,
          AVG(day_ahead_price) AS da, AVG(real_time_price) AS rt,
          MIN(real_time_price) AS low, MAX(real_time_price) AS high,
          COUNT(*) FILTER (WHERE real_time_price < 0) AS negative
        FROM spot_electricity_15min_data WHERE trade_date IN (:day, :previous)
        GROUP BY trade_date
    """), {"day": day, "previous": day - timedelta(days=1)}).mappings().all()
    by_day = {r["trade_date"]: r for r in rows}
    row = by_day.get(day)
    if row is None:
        return {"title": "电力现货", "status": "missing", "summary": "当日暂无电力现货数据。", "facts": []}
    complete = row["points"] == row["da_points"] == row["rt_points"] == 96
    facts = [f"日前均价 {number(row['da']):,.2f} 元/MWh" if number(row["da"]) is not None else "日前价格缺失",
             f"实时均价 {number(row['rt']):,.2f} 元/MWh" if number(row["rt"]) is not None else "实时价格缺失",
             f"实时价格范围 {row['low']:,.2f}—{row['high']:,.2f} 元/MWh" if row["low"] is not None and row["high"] is not None else "实时价格范围不足",
             f"实时负价时点 {row['negative']} 个"]
    previous = by_day.get(day - timedelta(days=1))
    if complete and previous and previous["points"] == previous["da_points"] == previous["rt_points"] == 96:
        delta = number(row["rt"]) - number(previous["rt"])
        facts.append(f"实时日均价较昨日{'增加' if delta >= 0 else '减少'} {abs(delta):,.2f} 元/MWh")
    return {"title": "电力现货", "status": "ready" if complete else "partial",
            "summary": f"当日已录入 {row['points']}/96 个时点，日前价格 {row['da_points']}/96，实时价格 {row['rt_points']}/96。", "facts": facts}


def read_dispatch(session, day):
    from .dispatch_reconciliation import device_key, reconcile_report
    row = session.execute(text("""
        SELECT biz_date, file_name, boiler_turbine_status, eqp_status_json, operations_and_tickets, log_items_json
        FROM dispatch_daily_reports WHERE project_key = :project AND biz_date = :day
    """), {"project": PROJECT_KEY, "day": day}).mappings().first()
    if row is None:
        return {"title": "生产调度", "status": "missing", "summary": "当日暂无调度日报。", "facts": []}
    report = reconcile_report({**row, "biz_date": day.isoformat()})
    events = report["operations_and_tickets"]
    current = [e for e in events if not e.get("event_date") or e["event_date"] == day.isoformat()]
    unresolved = [c for c in report["status_conflicts"] if not c.get("resolution")]
    facts = []
    for event in current:
        description = event.get("raw_description") or event.get("main_description") or ""
        if description:
            facts.append(" ".join(str(v) for v in (event.get("event_clock") or event.get("time"), event.get("responsible_org"), description) if v))
    summary = f"调度记录包含当日操作/工作票 {len(current)} 条。"
    if len(events) > len(current):
        summary += f"另有 {len(events) - len(current)} 条跨日记录，未计入当日。"
    if unresolved:
        summary += f"设备状态有 {len(unresolved)} 项待核对。"
    pending_keys = {item.get("device") for item in unresolved}
    equipment = []
    for facility in report.get("boiler_turbine_status", []):
        if not facility.get("unit_or_plant") or not (facility.get("standard_name") or facility.get("raw_name")):
            continue
        kind = "汽机" if facility.get("facility_type") == "汽机" else facility.get("boiler_type") or facility.get("facility_type")
        equipment.append({"key": device_key(facility), "kind": kind,
                          "status": facility.get("status"), "pending": device_key(facility) in pending_keys})
    overview_evidence = {"date": day.isoformat(), "equipment": equipment, "pending_count": len(unresolved),
                         "operations": [{"date": event.get("event_date") or day.isoformat(),
                                         "time": event.get("event_clock") or event.get("time") or "",
                                         "plant": event.get("responsible_org") or "",
                                         "description": event.get("raw_description") or event.get("main_description") or "",
                                         "is_ticket": bool(event.get("is_ticket"))}
                                        for event in current]}
    return {"title": "生产调度", "status": "partial" if unresolved else "ready", "summary": summary, "facts": facts,
            "source": row["file_name"], "overview_evidence": overview_evidence}


def read_inventory(session, day):
    """只汇总集团基层单位，输出总库存及在途、港口、厂内库存，不重复加总汇总行。"""
    rows = session.execute(text("""
        SELECT storage_type, SUM(value) AS value
        FROM coal_inventory_data
        WHERE date = :day AND company = ANY(:companies)
          AND storage_type IN ('coal_in_transit', 'coal_at_port', 'coal_at_plant')
        GROUP BY storage_type
    """), {"day": day, "companies": GROUP_COMPANIES}).mappings().all()
    if not rows:
        return {"title": "煤炭库存", "status": "missing", "summary": "当日暂无库存记录。", "facts": []}
    values = {r["storage_type"]: number(r["value"]) for r in rows}
    reported = [value for value in values.values() if value is not None]
    total = math.fsum(reported) if reported else None
    entries = [("全口径总库存", total)] + [(label, values.get(key)) for key, label in (
        ("coal_in_transit", "在途库存"), ("coal_at_port", "港口库存"), ("coal_at_plant", "厂内库存"),
    )]
    facts = [f"{label}：{value:,.2f} 吨" if value is not None else f"{label}：—" for label, value in entries]
    return {"title": "煤炭库存", "status": "ready" if reported else "missing", "summary": "", "facts": facts}


def build_daily_brief(session, day):
    """读取所选业务日；所有历史比较截止该日，不使用未来日数据生成走势。"""
    days = [day - timedelta(days=offset) for offset in range(6, -1, -1)]
    peer_days = [get_peer_date(d) for d in days]
    windows = get_season_windows(day)
    params = {"start": days[0], "end": day, "peer_start": min(peer_days), "peer_end": max(peer_days),
              "source_start": min(windows["biz_season_start"], windows["peer_season_start"])}
    raw = session.execute(text("""
        SELECT company, item, date,
          CASE WHEN COUNT(*) = COUNT(value) THEN SUM(value) ELSE NULL END AS value
        FROM daily_basic_data
        WHERE date BETWEEN :start AND :end OR date BETWEEN :peer_start AND :peer_end
        GROUP BY company, item, date
    """), params).mappings().all()
    periods = {get_season_windows(d)[f"{side}_period"] for d in days for side in ("biz", "peer")}
    expected = []
    # 每期分别识别曾有有效申报的字段：全期始终为空的辅材项属于不适用，不能当成每日漏报。
    for period in periods:
        anchors = [d for d in days + peer_days if get_season_period(d) == period]
        last = max(anchors)
        first = get_season_windows(last)["biz_season_start"]
        expected.extend(session.execute(text("""
            SELECT DISTINCT company, item, :period AS period FROM daily_basic_data
            WHERE date BETWEEN :first AND :last AND value IS NOT NULL
        """), {"period": period, "first": min(first, min(anchors)), "last": last}).mappings().all())
    # 常量数量小，统一读取再过滤期间；不重复查询每个主体和指标。
    constants = [r for r in session.execute(text("SELECT company, item, period, value FROM constant_data")).mappings().all() if r["period"] in periods]
    evidence = BriefEvidence(raw, expected, constants)
    engine = DailyDashboardEngine(session)
    metrics_by_day = {}
    for current_day in days:
        rows = engine.compute_all_metrics(current_day)
        metrics_by_day[current_day] = {(r["company"], r["item"]): r for r in rows}

    def subject(company):
        metrics = []
        for key, label, unit, digits in METRICS:
            points, failures_today, failures_peer = [], [], []
            for current_day, peer_day in zip(days, peer_days):
                row = metrics_by_day[current_day].get((company, key), {})
                failures = evidence.check(company, key, current_day)
                peer_failures = evidence.check(company, key, peer_day)
                if current_day == day:
                    failures_today, failures_peer = failures, peer_failures
                is_profit = key.startswith("eco_")
                valid = evidence.has_profit_source(company, current_day) if is_profit else not failures
                peer_valid = evidence.has_profit_source(company, peer_day) if is_profit else not peer_failures
                points.append({"date": current_day.isoformat(), "peer_date": peer_day.isoformat(),
                               "value": number(row.get("value_biz_date")) if valid else None,
                               "peer": number(row.get("value_peer_date")) if peer_valid else None})
            current, peer = points[-1]["value"], points[-1]["peer"]
            metrics.append({"key": key, "label": label, "unit": unit, "digits": digits,
                            "value": current, "peer": peer, "comparison": comparison(current, peer, digits),
                            "description": describe_change(label, current, peer, unit, digits),
                            "trend": trend_summary(points, label, unit, digits), "points": points,
                            "missing_current": failures_today, "missing_peer": failures_peer})
        return {"company": company, "name": COMPANIES[company], "metrics": metrics}

    subjects = {company: subject(company) for company in COMPANIES}
    # 每日固定五项、固定顺序；连续走势仅补充文字，缺值也保留该指标位置。
    highlights = []
    for metric in subjects["Group"]["metrics"][:5]:
        clauses = [metric["description"].removesuffix("。")]
        trend = metric["trend"]
        if trend["yoy_run"] >= 3:
            clauses.append(f"已连续{trend['yoy_run']}日{'高于' if trend['direction'] == 'up' else '低于'}同期")
        if trend["daily_run"] >= 3:
            # daily_run为日间比较次数，方向与同比分别表述。
            direction = comparison(metric["points"][-1]["value"], metric["points"][-2]["value"], metric["digits"])["direction"]
            clauses.append(f"较前日连续{trend['daily_run']}日{'增加' if direction == 'up' else '减少'}")
        highlights.append({"key": metric["key"], "text": "，".join(clauses) + "。", "detail": ""})
    temp = _optional(session, "气温背景", lambda: _temperature(engine, day, get_peer_date(day)))
    plan = _optional(session, "标煤计划", lambda: _plans(session, day))
    supplements = [_optional(session, "电力现货", lambda: read_spot(session, day)),
                   _optional(session, "生产调度", lambda: read_dispatch(session, day)),
                   _optional(session, "煤炭库存", lambda: read_inventory(session, day))]
    from .daily_brief_overview import build_brief_overview
    overview = build_brief_overview(day, subjects["Group"]["metrics"], temp, supplements[1])
    return {"ok": True, "date": day.isoformat(), "peer_date": get_peer_date(day).isoformat(),
            "generated_at": datetime.now(EAST_8).isoformat(), "highlights": highlights, "overview": overview, "weather": temp,
            "group": subjects["Group"], "main_city": subjects["ZhuChengQu"],
            "other_units": [subjects[c] for c in GROUP_COMPANIES if c not in ZHUCHENGQU_COMPANIES],
            "main_city_units": [subjects[c] for c in ZHUCHENGQU_COMPANIES], "plan": plan,
            "supplements": supplements}


def _temperature(engine, day, peer):
    current = engine.get_temperature_daily_avg_map(day, day).get(day.isoformat())
    previous = engine.get_temperature_daily_avg_map(peer, peer).get(peer.isoformat())
    return {"title": "气温背景", "status": "ready" if current is not None and previous is not None else "partial",
            "summary": describe_change("日均气温", current, previous, "℃", 1), "facts": [],
            "value": number(current), "peer": number(previous)}


def _plans(session, day):
    from .monthly_coal_progress import get_monthly_coal_progress
    from backend.services.dynamic_decomposition_service import get_coal_plan_comparison
    units = [{"company": c, "company_cn": n} for c, n in COMPANIES.items()]
    hierarchy = {"Group": GROUP_COMPANIES, "ZhuChengQu": ZHUCHENGQU_COMPANIES}
    monthly = get_monthly_coal_progress(session, day.isoformat(), units, hierarchy)
    dynamic = get_coal_plan_comparison("Group", day.isoformat(), session)
    return {"title": "标煤计划", "status": "ready", "monthly": monthly,
            "daily": dynamic.get("daily", {}), "daily_note": dynamic.get("reason") or dynamic.get("message") or "集团标煤动态日计划，仅列示数值与实际差额。"}
