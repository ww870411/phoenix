# -*- coding: utf-8 -*-
"""
monthly_data_show 指标配置加载与公式计算服务。
"""

from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

_ROOT = Path(__file__).resolve().parents[4]
CONFIG_CANDIDATES = [
    _ROOT / "data" / "projects" / "monthly_data_show" / "indicator_config.json",
    _ROOT / "backend_data" / "projects" / "monthly_data_show" / "indicator_config.json",
]
TOKEN_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

DEFAULT_BASIC_SECTION_TITLE = "基本指标"
DEFAULT_CALCULATED_SECTION_TITLE = "计算指标（0项）"
DEFAULT_CATEGORY_PLACEHOLDER = "【待配置分类】"


def _safe_str(value: object) -> str:
    return str(value or "").strip()


def _to_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _normalize_calc_value(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(round(value, 8))


def _read_raw_config() -> dict:
    target_path: Optional[Path] = None
    for candidate in CONFIG_CANDIDATES:
        if candidate.exists():
            target_path = candidate
            break
    if target_path is None:
        target_path = CONFIG_CANDIDATES[-1]
    if not target_path.exists():
        return {}
    try:
        return json.loads(target_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize_basic_items(raw_items: object, placeholder: str) -> List[dict]:
    rows: List[dict] = []
    seen: Set[str] = set()
    for raw in raw_items or []:
        if isinstance(raw, str):
            name = _safe_str(raw)
            category = placeholder
            unit = ""
        elif isinstance(raw, dict):
            name = _safe_str(raw.get("name"))
            category = _safe_str(raw.get("category")) or placeholder
            unit = _safe_str(raw.get("unit"))
        else:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({"name": name, "category": category, "unit": unit})
    return rows


def _normalize_basic_groups(raw_groups: object, placeholder: str) -> List[dict]:
    groups: List[dict] = []
    used_names: Set[str] = set()
    seen_group_names: Set[str] = set()
    for raw_group in raw_groups or []:
        if not isinstance(raw_group, dict):
            continue
        group_name = _safe_str(raw_group.get("name")) or "未命名分组"
        if group_name in seen_group_names:
            continue
        seen_group_names.add(group_name)
        normalized_items: List[dict] = []
        for raw_item in raw_group.get("items") or []:
            if isinstance(raw_item, str):
                item_name = _safe_str(raw_item)
                unit = ""
            elif isinstance(raw_item, dict):
                item_name = _safe_str(raw_item.get("name"))
                unit = _safe_str(raw_item.get("unit"))
            else:
                continue
            if not item_name or item_name in used_names:
                continue
            used_names.add(item_name)
            normalized_items.append({"name": item_name, "category": group_name or placeholder, "unit": unit})
        groups.append({"name": group_name, "items": normalized_items})
    return groups


def _extract_formula_tokens(formula: str) -> List[str]:
    tokens: List[str] = []
    seen: Set[str] = set()
    for matched in TOKEN_PATTERN.findall(formula or ""):
        token = _safe_str(matched)
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _normalize_calculated_items(raw_items: object) -> List[dict]:
    rows: List[dict] = []
    seen: Set[str] = set()
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        name = _safe_str(raw.get("name"))
        if not name or name in seen:
            continue
        seen.add(name)
        formula = _safe_str(raw.get("formula"))
        rows.append(
            {
                "name": name,
                "unit": _safe_str(raw.get("unit")),
                "formula": formula,
                "dependencies": _extract_formula_tokens(formula),
            }
        )
    return rows


def load_indicator_runtime_config() -> dict:
    raw = _read_raw_config()
    basic_section = raw.get("basic_section") if isinstance(raw, dict) else {}
    calc_section = raw.get("calculated_section") if isinstance(raw, dict) else {}
    category_placeholder = _safe_str((basic_section or {}).get("category_placeholder")) or DEFAULT_CATEGORY_PLACEHOLDER
    basic_groups = _normalize_basic_groups((raw or {}).get("basic_groups"), category_placeholder)
    basic_items = []
    if basic_groups:
        for group in basic_groups:
            basic_items.extend(group.get("items") or [])
    else:
        basic_items = _normalize_basic_items((raw or {}).get("basic_items"), category_placeholder)
    calculated_items = _normalize_calculated_items((raw or {}).get("calculated_items"))
    calculated_item_names = [x["name"] for x in calculated_items]
    calculated_item_set = set(calculated_item_names)
    calculated_item_units = {x["name"]: _safe_str(x.get("unit")) for x in calculated_items}
    calculated_item_formulas = {x["name"]: _safe_str(x.get("formula")) for x in calculated_items}
    dependency_map: Dict[str, Set[str]] = {}
    for item in calculated_items:
        name = item["name"]
        dependency_map[name] = set(item.get("dependencies") or [])
    return {
        "basic_section_title": _safe_str((basic_section or {}).get("title")) or DEFAULT_BASIC_SECTION_TITLE,
        "calculated_section_title": _safe_str((calc_section or {}).get("title"))
        or f"计算指标（{len(calculated_items)}项）"
        or DEFAULT_CALCULATED_SECTION_TITLE,
        "category_placeholder": category_placeholder,
        "basic_groups": basic_groups,
        "basic_items": basic_items,
        "calculated_items": [
            {
                "name": x["name"],
                "unit": _safe_str(x.get("unit")),
                "formula": _safe_str(x.get("formula")),
            }
            for x in calculated_items
        ],
        "calculated_item_names": calculated_item_names,
        "calculated_item_set": calculated_item_set,
        "calculated_item_units": calculated_item_units,
        "calculated_item_formulas": calculated_item_formulas,
        "calculated_dependency_map": dependency_map,
    }


def order_items_by_config(all_items: List[str], runtime_cfg: dict) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    basic_names = [_safe_str(x.get("name")) for x in runtime_cfg.get("basic_items") or []]
    calc_names = [_safe_str(x.get("name")) for x in runtime_cfg.get("calculated_items") or []]
    for name in [*basic_names, *calc_names]:
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    for name in all_items or []:
        item = _safe_str(name)
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def build_indicator_config_payload(runtime_cfg: dict) -> dict:
    return {
        "basic_section_title": runtime_cfg.get("basic_section_title") or DEFAULT_BASIC_SECTION_TITLE,
        "calculated_section_title": runtime_cfg.get("calculated_section_title") or DEFAULT_CALCULATED_SECTION_TITLE,
        "category_placeholder": runtime_cfg.get("category_placeholder") or DEFAULT_CATEGORY_PLACEHOLDER,
        "basic_groups": runtime_cfg.get("basic_groups") or [],
        "basic_items": runtime_cfg.get("basic_items") or [],
        "calculated_items": runtime_cfg.get("calculated_items") or [],
    }


def safe_eval_expression(expression: str) -> float:
    try:
        node = ast.parse(expression, mode="eval")
    except Exception:
        return 0.0

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant):
            if isinstance(n.value, (int, float)):
                return float(n.value)
            return 0.0
        if isinstance(n, ast.Num):  # pragma: no cover
            return float(n.n)
        if isinstance(n, ast.UnaryOp):
            value = _eval(n.operand)
            if isinstance(n.op, ast.UAdd):
                return value
            if isinstance(n.op, ast.USub):
                return -value
            return 0.0
        if isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                if right == 0:
                    return 0.0
                return left / right
            if isinstance(n.op, ast.Mod):
                if right == 0:
                    return 0.0
                return left % right
            if isinstance(n.op, ast.Pow):
                return left**right
            if isinstance(n.op, ast.FloorDiv):
                if right == 0:
                    return 0.0
                return left // right
            return 0.0
        return 0.0

    try:
        return _normalize_calc_value(_eval(node))
    except Exception:
        return 0.0


def evaluate_formula(formula: str, context: Dict[str, float]) -> float:
    source = str(formula or "")

    def _replace(match: re.Match) -> str:
        token = _safe_str(match.group(1))
        return str(_to_float(context.get(token)))

    expression = TOKEN_PATTERN.sub(_replace, source)
    return safe_eval_expression(expression)
