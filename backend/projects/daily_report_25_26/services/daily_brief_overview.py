"""从简报指标和当日调度证据组织综述，只描述可核对的变化与记录。"""
from __future__ import annotations

import math
import re
from collections import Counter


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


def _dispatch_paragraph(day, dispatch):
    evidence = dispatch.get("overview_evidence", {})
    if evidence.get("date") != day.isoformat():
        return {"key": "dispatch", "text": "当日暂无设备调度记录。", "metric_keys": [], "operations": []}

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
    sentences = []
    # 存在状态争议时不汇总运行台数，以免将尚待确认的状态写成结论。
    if equipment and not pending_count:
        for state, label in (("运行", "运行"), ("检修", "检修")):
            counts = Counter(item.get("kind") for item in equipment.values()
                             if item.get("status") == state and item.get("kind"))
            if counts:
                kinds = [kind for kind in ("汽机", "汽炉", "水炉", "燃气炉", "锅炉") if kind in counts]
                kinds += sorted(set(counts) - set(kinds))
                sentences.append("调度状态表列示" + label + "设备：" + "、".join(f"{kind}{counts[kind]}台" for kind in kinds) + "。")
        if not sentences:
            standby = sum(item.get("status") == "备用" for item in equipment.values())
            if standby:
                sentences.append(f"调度状态表列示备用设备{standby}台。")

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
        sentences.append("操作日志记载：" + "；".join(excerpts) + "。")
    if pending_count:
        sentences.append(f"有{pending_count}项设备状态待核对。")
    if not sentences:
        sentences.append("当日调度日报已记录。")
    return {"key": "dispatch", "text": "".join(sentences), "metric_keys": [],
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
        _dispatch_paragraph(day, dispatch),
    ]}
