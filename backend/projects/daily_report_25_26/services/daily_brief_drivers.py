"""每日经营差异归因：只解释已有数据和计算公式能支持的变化。"""

from math import isclose

from backend.services.heating_metrics.season_utils import get_peer_date, get_season_period


# 集团口径不包括内部售热及内部购热；电量的单位为万千瓦时。
DRIVERS = (
    ("eco_power_supply_income", "售电收入", (("amount_power_sales", "售电量", "万千瓦时", "price_power_sales", 1),)),
    ("eco_hot_water_supply_income", "售高温水收入", (("amount_hot_water_sales", "高温水销量", "GJ", "price_hot_water_sales", 0.0001),)),
    ("eco_steam_supply_income", "售汽收入", (("amount_steam_sales", "售汽量", "吨", "price_steam_sales", 0.0001),)),
    ("eco_coal_cost", "煤成本", (("consumption_std_coal", "标煤耗量", "吨", "price_std_coal", 0.0001),)),
    ("eco_natural_gas_cost", "天然气成本", (("consumption_natural_gas", "天然气耗量", "立方米", "price_natural_gas", 0.0001),)),
    ("eco_purchased_power_cost", "外购电成本", (("consumption_purchased_power", "外购电量", "万千瓦时", "price_purchased_power", 1),)),
    ("eco_purchased_water_cost", "购水成本", (("consumption_water", "购水量", "吨", "price_purchased_water", 0.0001),)),
    ("eco_outer_heat_cost", "外购热成本", (("consumption_outer_purchased_heat", "外购热量", "GJ", "price_outer_purchased_heat", 0.0001),)),
    ("eco_measurable_auxiliary_materials", "可计量辅材成本", tuple(
        (f"consumption_{key}", label, "吨", price, 0.0001) for key, label, price in (
            ("acid", "耗酸量", "price_acid"), ("alkali", "耗碱量", "price_alkali"),
            ("oil", "耗油量", "price_oil"), ("ammonia_water", "耗氨水量", "price_n_ammonia_water"),
            ("limestone", "石灰石耗量", "price_limestone"), ("limestone_powder", "石灰石粉耗量", "price_limestone_powder"),
            ("magnesium_oxide", "氧化镁耗量", "price_magnesium_oxide"), ("denitration_agent", "脱硝剂耗量", "price_denitration_agent"),
        )
    )),
)


def build_cost_drivers(day, rows, evidence, companies, names):
    """筛选日同比差额，按单位和基础量价对称分解；缺失时不伪造归因。"""
    peer = get_peer_date(day)
    periods = (get_season_period(day), get_season_period(peer))
    stories, incomplete = [], []
    heating = rows.get(("Group", "eco_heating_supply_income"))
    if heating:
        current, previous = heating.get("value_biz_date"), heating.get("value_peer_date")
        if current is not None and previous is not None:
            delta = current - previous
            if abs(delta) >= 1 and (abs(previous) < 1 or abs(delta / previous) >= 0.1):
                parts, complete = [], True
                for company in companies:
                    row = rows.get((company, "eco_heating_supply_income"), {})
                    value, old = row.get("value_biz_date"), row.get("value_peer_date")
                    if value is None or old is None:
                        complete = False
                        continue
                    if any(evidence.constants.get((company, "eco_season_heating_income", period)) is None
                           for period, amount in zip(periods, (value, old)) if amount != 0):
                        complete = False
                    if (value - old) * delta > 0 and abs(value - old) >= 0.01:
                        parts.append({"company": company, "name": names[company], "factor": "暖收入分摊额",
                                      "unit": "万元", "current": value, "peer": old, "delta": value - old})
                if complete and isclose(sum(rows.get((c, "eco_heating_supply_income"), {}).get("value_biz_date", 0) -
                                           rows.get((c, "eco_heating_supply_income"), {}).get("value_peer_date", 0)
                                           for c in companies), delta, abs_tol=0.02) and parts:
                    parts.sort(key=lambda part: abs(part["delta"]), reverse=True)
                    stories.append({"key": "eco_heating_supply_income", "label": "暖收入", "current": current,
                                    "peer": previous, "delta": delta,
                                    "percent": delta / previous * 100 if previous > 0 and current >= 0 else None,
                                    "drivers": parts[:3]})
                else:
                    incomplete.append("暖收入")
    for metric, label, factors in DRIVERS:
        group = rows.get(("Group", metric))
        if not group:
            continue
        current, previous = group.get("value_biz_date"), group.get("value_peer_date")
        if current is None or previous is None:
            continue
        delta = current - previous
        # 兼顾绝对差额和同比比例；零基数只使用绝对差额。
        if abs(delta) < 1 or (abs(previous) >= 1 and abs(delta / previous) < 0.1):
            continue
        contributions, missing = [], False
        for company in companies:
            for item, factor_label, unit, price, scale in factors:
                # 供热公司售汽与高温水收入直接填报金额，不适合套用销量乘单价。
                if company == "GongRe" and metric in {"eco_hot_water_supply_income", "eco_steam_supply_income"}:
                    known_amount = [metric in evidence.expected.get((company, period), set()) for period in periods]
                    if any(known_amount):
                        amounts = [evidence.raw.get((company, metric, date)) for date in (day, peer)]
                        if any(value is None for value in amounts):
                            missing = True
                        else:
                            contributions.append({"company": company, "name": names[company], "factor": "填报收入",
                                                  "unit": "万元", "current": amounts[0], "peer": amounts[1],
                                                  "delta": amounts[0] - amounts[1]})
                    continue
                known = [item in evidence.expected.get((company, period), set()) for period in periods]
                if not any(known):
                    continue
                quantities = [evidence.raw.get((company, item, date)) for date in (day, peer)]
                if any(value is None for value in quantities):
                    missing = True
                    continue
                prices = [evidence.constants.get((company, price, period)) for period in periods]
                if any(p is None and q != 0 for p, q in zip(prices, quantities)):
                    missing = True
                    continue
                # 无消耗一侧缺价格时，以另一侧价格作为参照，不虚构价格影响。
                prices = [p if p is not None else (prices[1 - i] or 0) for i, p in enumerate(prices)]
                q, q0 = quantities
                p, p0 = prices
                quantity_effect = (q - q0) * (p + p0) / 2 * scale
                price_effect = (p - p0) * (q + q0) / 2 * scale
                contributions.append({"company": company, "name": names[company], "factor": factor_label,
                                      "unit": unit, "current": q, "peer": q0,
                                      "quantity_effect": quantity_effect, "price_effect": price_effect,
                                      "delta": quantity_effect + price_effect})
        # 聚合值必须与底层贡献闭合，避免遗漏填报金额或被算法补零的项目。
        if missing or not isclose(sum(x["delta"] for x in contributions), delta, abs_tol=0.02):
            incomplete.append(label)
            continue
        aligned = [x for x in contributions if x["delta"] * delta > 0 and abs(x["delta"]) >= 0.01]
        aligned.sort(key=lambda x: abs(x["delta"]), reverse=True)
        if not aligned:
            continue
        stories.append({"key": metric, "label": label, "current": current, "peer": previous,
                        "delta": delta, "percent": delta / previous * 100 if previous > 0 and current >= 0 else None,
                        "drivers": aligned[:3]})
    stories.sort(key=lambda story: abs(story["delta"]), reverse=True)
    return {"stories": stories[:5], "incomplete": incomplete}
