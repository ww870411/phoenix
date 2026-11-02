"""从简报指标和当日调度证据组织综述，只描述可核对的变化与记录。"""
from __future__ import annotations

import math
import re

EQUIPMENT_KEYS = ("amount_turbine_running", "amount_boiler_steam_running",
                  "amount_boiler_water_running", "amount_boiler_room_running")


def _valid_count(value):
    """真实台数为非负整数，不能用四舍五入掩盖异常申报。"""
    return _finite(value) and value >= 0 and float(value).is_integer()


def _equipment_sentences(metrics):
    """使用日报集团汇总及完整性校验结果，不拿主城区调度设备清单替代全口径。"""
    clauses, used = [], []
    labels = ("汽轮机", "蒸汽锅炉", "水炉", "锅炉房锅炉")
    for key, label in zip(EQUIPMENT_KEYS, labels):
        metric = metrics.get(key, {})
        current, peer = metric.get("value"), metric.get("peer")
        if not _valid_count(current):
            clauses.append(f"{label}台数待补齐")
            continue
        used.append(key)
        clause = f"{label}{current:.0f}台"
        if _valid_count(peer):
            delta = current - peer
            clause += "（同比持平）" if delta == 0 else f"（同比{'增加' if delta > 0 else '减少'}{abs(delta):.0f}台）"
        else:
            clause += "（同期数据不足）"
        clauses.append(clause)
    sentences = ["当日集团全口径运行设备中，" + "、".join(clauses) + "。"]
    return sentences, used


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _comparable(metrics, key):
    metric = metrics.get(key, {})
    change = metric.get("comparison", {})
    if (_finite(metric.get("value")) and _finite(metric.get("peer"))
            and _finite(change.get("delta")) and change.get("direction") in {"up", "down", "flat"}):
        return metric
    return None


def _names(names):
    if len(names) < 2:
        return "".join(names)
    return "、".join(names[:-1]) + "与" + names[-1]


def _direction_sentence(metrics, keys):
    """同向指标合并表述，方向相反的指标分开，省去下方卡片已有的绝对值。"""
    groups = {"up": [], "down": [], "flat": []}
    used = []
    for key in keys:
        metric = _comparable(metrics, key)
        if metric:
            groups[metric["comparison"]["direction"]].append(metric["label"])
            used.append(key)
    verbs = {"up": "增加", "down": "减少", "flat": "持平"}
    clauses = [_names(names) + "同比" + verbs[direction] for direction, names in groups.items() if names]
    return "，".join(clauses) + "。" if clauses else "", used


def _weather_sentence(weather):
    current, peer = weather.get("value"), weather.get("peer")
    if not _finite(current):
        return ""
    text = f"当日日均气温{current:.1f}℃"
    if _finite(peer):
        delta = round(current - peer, 1)
        text += "，同比持平" if delta == 0 else f"，同比{'增加' if delta > 0 else '减少'}{abs(delta):.1f}℃"
    return text + "。"


def _profit_clause(metric):
    change = metric["comparison"]
    if change["direction"] == "flat":
        return metric["label"] + "同比持平"
    text = f"{metric['label']}同比{'增加' if change['direction'] == 'up' else '减少'}{abs(change['delta']):,.2f}万元"
    if metric["peer"] < 0 < metric["value"]:
        text += "（由亏转盈）"
    elif metric["peer"] > 0 > metric["value"]:
        text += "（由盈转亏）"
    return text


def _dispatch_paragraph(day, dispatch, metrics):
    sentences, used = _equipment_sentences(metrics)
    evidence = dispatch.get("overview_evidence", {})
    if evidence.get("date") != day.isoformat():
        sentences.append("当日暂无设备调度记录。")
        return {"key": "dispatch", "text": "".join(sentences), "metric_keys": used, "operations": []}

    equipment = {}
    ambiguous = set()
    for item in evidence.get("equipment", []):
        key = item.get("key")
        if not key:
            continue
        if key in equipment and equipment[key].get("status") != item.get("status"):
            ambiguous.add(key)
        equipment[key] = item
    pending = {key for key, item in equipment.items() if item.get("pending")} | ambiguous
    pending_count = max(int(evidence.get("pending_count") or 0), len(pending))

    operations = []
    seen = set()
    for record in evidence.get("operations", []):
        if record.get("date") != day.isoformat() or record.get("is_ticket"):
            continue
        description = str(record.get("description") or "").strip()
        if not description:
            continue
        identity = (record.get("plant"), record.get("time"), description)
        if identity in seen:
            continue
        seen.add(identity)
        operations.append(record)
    # 优先摘录设备/系统的故障、停启等记录，再恢复原记录次序；原文中的计划和否定不改写。
    priority = re.compile(r"泄漏|漏|跳闸|故障|停运|停炉|停机|灭火|检修|中断|启动|点火|并网|并汽")
    selected = sorted(sorted(enumerate(operations), key=lambda pair: (not bool(priority.search(pair[1]["description"])), pair[0]))[:3])
    excerpts = []
    for _, record in selected:
        attribution = " ".join(str(value) for value in (record.get("plant"), record.get("time")) if value)
        excerpts.append(attribution + "“" + record["description"].strip().rstrip("。；") + "”")
    if excerpts:
        # 台数及同比后直接承接调度事实，不重复概括增减、行为分类或运行意义。
        sentences.append("当日调度记录显示：" + "；".join(excerpts) + "。")
    if pending_count:
        sentences.append(f"另有{pending_count}项设备状态待核对。")
    if not operations:
        sentences.append("当日暂无设备操作记录。")
    return {"key": "dispatch", "text": "".join(sentences), "metric_keys": used,
            "operations": [record for _, record in selected]}


def build_brief_overview(day, metric_rows, weather, dispatch):
    """三个固定主题分别组织事实；不推断气温、设备动作与经营结果之间的因果。"""
    metrics = {metric["key"]: metric for metric in metric_rows}
    production = [_weather_sentence(weather)]
    production_keys = []
    for keys in (("amount_heat_supply", "amount_power_generation", "consumption_std_coal"),
                 ("rate_heat_per_10k_m2", "rate_water_per_10k_m2", "rate_power_per_10k_m2")):
        sentence, used = _direction_sentence(metrics, keys)
        production.append(sentence)
        production_keys.extend(used)
    coal = _comparable(metrics, "consumption_std_coal")
    if coal and coal.get("trend", {}).get("yoy_run", 0) >= 3:
        trend = coal["trend"]
        production.append(f"近七日内，标煤耗量已连续{trend['yoy_run']}日{'高于' if trend['direction'] == 'up' else '低于'}同期。")

    economics = []
    economics_keys = []
    profits = [metric for key in ("eco_comparable_marginal_profit", "eco_marginal_profit")
               if (metric := _comparable(metrics, key))]
    if profits:
        economics.append("，".join(_profit_clause(metric) for metric in profits) + "。")
        economics_keys.extend(metric["key"] for metric in profits)
        if len(profits) == 2 and {metric["comparison"]["direction"] for metric in profits} == {"up", "down"}:
            economics.append("两种利润口径同比方向不同。")
    sentence, used = _direction_sentence(metrics, ("amount_daily_service_complaints", "amount_daily_net_complaints"))
    economics.append(sentence)
    economics_keys.extend(used)
    return {"paragraphs": [
        {"key": "production", "text": "".join(production) or "当日生产指标暂无记录。", "metric_keys": production_keys},
        {"key": "economics", "text": "".join(economics) or "当日经营与投诉指标暂无记录。", "metric_keys": economics_keys},
        _dispatch_paragraph(day, dispatch, metrics),
    ]}
