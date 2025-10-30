# -*- coding: utf-8 -*-
"""
运行时表达式求值服务（首版）
目标：
- 在不继续扩张二级视图的前提下，基于物化视图 sum_basic_data 与基础表，按“字典样例.json”的表达式规则，
  对模板中的单元格进行计算与替换，返回可直接渲染的 rows-only 数据对象。

重要约束与约定（来自用户回复 D:/编程项目/phoenix/configs/回复.md）：
- 差异列（date/month/ytd）均为“增长率”：(biz - peer) / abs(peer)，分母为 0 时返回 "-"
- 常量 period 映射：
  - value_biz_date / sum_month_biz / sum_ytd_biz → "25-26"
  - value_peer_date / sum_month_peer / sum_ytd_peer → "24-25"
- “项目名”按 spec["项目字典"] 反向查询得到英文 item 作为准确查询键
- 统一使用 company 维度（正在取消 center），主数据域以 spec['查询数据源']['主表'] 指定（目前以 sum_basic_data 为主）
- biz_date 可覆盖：
  - 若 context['biz_date']=="regular" 或未提供：使用物化视图
  - 若 context['biz_date']=="YYYY-MM-DD"：按该日期走基础表动态聚合（等价于视图定义的参数化版本）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date as _date, datetime as _datetime, timedelta as _timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.database_daily_report_25_26 import get_session

# ------------------------
# 帧与 period 映射
# ------------------------
FRAME_FIELDS = {
    "biz_date": "value_biz_date",
    "peer_date": "value_peer_date",
    "sum_month_biz": "sum_month_biz",
    "sum_month_peer": "sum_month_peer",
    "sum_ytd_biz": "sum_ytd_biz",
    "sum_ytd_peer": "sum_ytd_peer",
}

FRAME_TO_PERIOD = {
    "biz_date": "25-26",
    "sum_month_biz": "25-26",
    "sum_ytd_biz": "25-26",
    "peer_date": "24-25",
    "sum_month_peer": "24-25",
    "sum_ytd_peer": "24-25",
}


@dataclass
class EvalContext:
    project_key: str
    primary_key: Dict[str, Any]  # 目前必须含 company
    main_table: str              # 期望为 "sum_basic_data"
    const_alias_map: Dict[str, str]  # 如 {"c": "constant_data"}
    item_cn_to_item: Dict[str, str]  # 由 "项目字典" 反查得到：CN → en
    item_en_to_cn: Optional[Dict[str, str]] = None
    unit_cn_to_en: Optional[Dict[str, str]] = None
    unit_en_to_cn: Optional[Dict[str, str]] = None
    # 可选覆盖：{"biz_date": "regular" | "YYYY-MM-DD"}
    context: Optional[Dict[str, Any]] = None


# ------------------------
# 列名到帧映射
# ------------------------
def _normalize_col_label(label: str) -> str:
    return re.sub(r"\s+", "", label or "")


def map_columns_to_frames(columns: List[str]) -> Dict[int, str]:
    """
    将模板列标题映射为帧类型，返回 {col_index: frame_key}
    支持：本期日/同期日/日差异、本期月/同期月/月差异、本供暖期/同供暖期/供暖期差异
    """
    frames: Dict[int, str] = {}
    for idx, col in enumerate(columns):
        c = _normalize_col_label(col)
        if "本期日" in c:
            frames[idx] = "biz_date"
        elif "同期日" in c:
            frames[idx] = "peer_date"
        elif "本期月" in c:
            frames[idx] = "sum_month_biz"
        elif "同期月" in c:
            frames[idx] = "sum_month_peer"
        elif "本供暖期" in c:
            frames[idx] = "sum_ytd_biz"
        elif "同供暖期" in c:
            frames[idx] = "sum_ytd_peer"
        # 差异列不直接映射帧，由调用方使用同组帧计算 diff_rate
    return frames


# ------------------------
# 数据预取：指标与常量
# ------------------------
def _fetch_metrics_from_view(session: Session, table: str, company: str) -> Dict[str, Dict[str, Decimal]]:
    """
    从视图按 company 维度一次性拉取所有 item 的 6 个窗口值。
    允许表名为白名单：sum_basic_data | groups
    返回结构：{ item: {field_name: Decimal, ...}, ... }
    """
    table_whitelist = {"sum_basic_data", "groups"}
    target = table if table in table_whitelist else "sum_basic_data"
    sql = text(
        f"""
        SELECT item, item_cn, unit,
               value_biz_date, value_peer_date,
               sum_month_biz, sum_month_peer,
               sum_ytd_biz, sum_ytd_peer
          FROM {target}
         WHERE company = :company
        """
    )
    rows = session.execute(sql, {"company": company}).mappings().all()
    out: Dict[str, Dict[str, Decimal]] = {}
    for r in rows:
        item = r["item"]
        bucket = {
            "value_biz_date": _to_decimal(r.get("value_biz_date")),
            "value_peer_date": _to_decimal(r.get("value_peer_date")),
            "sum_month_biz": _to_decimal(r.get("sum_month_biz")),
            "sum_month_peer": _to_decimal(r.get("sum_month_peer")),
            "sum_ytd_biz": _to_decimal(r.get("sum_ytd_biz")),
            "sum_ytd_peer": _to_decimal(r.get("sum_ytd_peer")),
        }
        out[item] = bucket
        # 兼容：允许用中文项目名直接取值（当模板或字典未提供映射时）
        if r.get("item_cn"):
            cn_key = str(r.get("item_cn")).strip()
            if cn_key and cn_key not in out:
                out[cn_key] = bucket
    return out


def _fetch_metrics_dynamic_by_date(session: Session, company: str, biz_date: str) -> Dict[str, Dict[str, Decimal]]:
    """
    动态日期路径：按传入 biz_date 复用视图定义的窗口口径，在基础表 daily_basic_data 上计算聚合。
    """
    sql = text(
        """
        WITH anchor_dates AS (
          SELECT
            CAST(:biz_date AS date) AS biz_date,
            (CAST(:biz_date AS date) - INTERVAL '1 year')::date AS peer_date
        ),
        window_defs AS (
          SELECT
            biz_date, peer_date,
            biz_date - INTERVAL '6 day' AS biz_7d_start,
            peer_date - INTERVAL '6 day' AS peer_7d_start,
            date_trunc('month', biz_date)::date AS biz_month_start,
            date_trunc('month', peer_date)::date AS peer_month_start,
            DATE '2025-10-01' AS biz_ytd_start,
            DATE '2024-10-01' AS peer_ytd_start
          FROM anchor_dates
        )
        SELECT
          d.item,
          COALESCE(SUM(d.value) FILTER (WHERE d.date = w.biz_date), 0) AS value_biz_date,
          COALESCE(SUM(d.value) FILTER (WHERE d.date = w.peer_date), 0) AS value_peer_date,
          COALESCE(SUM(d.value) FILTER (WHERE d.date BETWEEN w.biz_month_start AND w.biz_date), 0) AS sum_month_biz,
          COALESCE(SUM(d.value) FILTER (WHERE d.date BETWEEN w.peer_month_start AND w.peer_date), 0) AS sum_month_peer,
          COALESCE(SUM(d.value) FILTER (WHERE d.date BETWEEN w.biz_ytd_start AND w.biz_date), 0) AS sum_ytd_biz,
          COALESCE(SUM(d.value) FILTER (WHERE d.date BETWEEN w.peer_ytd_start AND w.peer_date), 0) AS sum_ytd_peer
        FROM daily_basic_data d
        CROSS JOIN window_defs w
        WHERE d.company = :company
          AND d.date BETWEEN w.peer_ytd_start AND w.biz_date
        GROUP BY d.item;
        """
    )
    rows = session.execute(sql, {"company": company, "biz_date": biz_date}).mappings().all()
    out: Dict[str, Dict[str, Decimal]] = {}
    for r in rows:
        item = r["item"]
        out[item] = {
            "value_biz_date": _to_decimal(r["value_biz_date"]),
            "value_peer_date": _to_decimal(r["value_peer_date"]),
            "sum_month_biz": _to_decimal(r["sum_month_biz"]),
            "sum_month_peer": _to_decimal(r["sum_month_peer"]),
            "sum_ytd_biz": _to_decimal(r["sum_ytd_biz"]),
            "sum_ytd_peer": _to_decimal(r["sum_ytd_peer"]),
        }
    return out


def _fetch_constants_for_table(session: Session, table_name: str, company: str) -> Dict[str, Dict[str, Decimal]]:
    """
    通用常量表取值缓存（表结构需包含 item, period, value, company）
    返回：{ const_name: {period: Decimal}, ...}
    """
    # 为提高命中率，同时索引 item 与 item_cn 两个名字（中文/英文都可用）
    sql = text(f"SELECT item, item_cn, period, value FROM {table_name} WHERE company = :company")
    rows = session.execute(sql, {"company": company}).mappings().all()
    out: Dict[str, Dict[str, Decimal]] = {}
    for r in rows:
        keys = []
        if r.get("item"):
            keys.append(str(r["item"]).strip())
        if r.get("item_cn"):
            keys.append(str(r["item_cn"]).strip())
        period_raw = str(r["period"]).strip() if r.get("period") is not None else ""
        period = _normalize_period_key(period_raw)
        val = _to_decimal(r.get("value"))
        for k in keys:
            if not k:
                continue
            out.setdefault(k, {})[period] = val
    return out


def _fetch_sum_coal_inventory_constants(session: Session, company: str) -> Dict[str, Dict[str, Decimal]]:
    """
    针对 sum_coal_inventory_data 视图的取值逻辑：
    - 仅关注最新日期、storage_type='all_sites' 的汇总行
    - 支持两种 company 取值：原始 company（如 JinZhou）及附加后缀 _sum（如 JinZhou_sum）
    - 返回形如 { 'JinZhou_sum': {'25-26': value, '24-25': value} }
    """
    sql = text(
        """
        SELECT company, storage_type, value
        FROM sum_coal_inventory_data
        WHERE company = :company
        """
    )
    candidates: List[str] = []
    if company:
        candidates.append(company)
        if not company.endswith("_sum"):
            candidates.append(f"{company}_sum")
        else:
            base = company[:-4]
            if base:
                candidates.append(base)
    seen: Set[str] = set()
    rows: List[Dict[str, Any]] = []
    for cand in candidates:
        key = cand.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        part = session.execute(sql, {"company": key}).mappings().all()
        if part:
            rows.extend(part)
    if not rows:
        return {}
    out: Dict[str, Dict[str, Decimal]] = {}
    for r in rows:
        comp_raw = str(r.get("company") or "").strip()
        storage_type = str(r.get("storage_type") or "").strip()
        val = _to_decimal(r.get("value"))
        if not comp_raw:
            continue
        if storage_type == "all_sites":
            if comp_raw.endswith("_sum"):
                key = comp_raw
            else:
                key = f"{comp_raw}_sum"
        elif storage_type:
            key = f"{comp_raw}_{storage_type}"
        else:
            key = comp_raw
        out[key] = {
            FRAME_TO_PERIOD["biz_date"]: val,
            FRAME_TO_PERIOD["peer_date"]: val,
        }
    return out


def _to_decimal(v: Any) -> Decimal:
    if v is None:
        return Decimal(0)
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal(0)

def _normalize_period_key(label: Optional[str]) -> str:
    """
    归一化常量 period 标签：
    - 去除空白/括号
    - 去除结尾的 'period'/'供暖期' 等词
    - 主要用于将 '25-26period'、'（25-26）'、'25-26供暖期' → '25-26'
    """
    s = (label or "").strip()
    if not s:
        return ""
    s = re.sub(r"[()（）\s]", "", s)
    s = re.sub(r"(供暖期|本供暖期|同供暖期|period)$", "", s, flags=re.IGNORECASE)
    return s


# ------------------------
# 表达式求值（受限）
# ------------------------
_OPS = set("+-*/()")


def _build_replacers(item_names_cn: List[str], const_aliases: List[str]) -> Tuple[List[Tuple[re.Pattern, str]], List[Tuple[str, str]]]:
    """
    生成两类替换器：
    - 常量别名点号：如 c.售电单价 → C("售电单价")
    - 项目名：如 售电量 → I("售电量")
    先替换别名点号，再替换项目名，避免二次替换。
    """
    alias_patterns: List[Tuple[re.Pattern, str]] = []
    for alias in const_aliases:
        # <alias>.<中文名> → CA("alias","中文名")
        # 中文名允许包含全角字符，匹配到运算符或括号前
        pat = re.compile(rf"{re.escape(alias)}\.([^\+\-\*\/\(\)]+)")
        alias_patterns.append((pat, f'CA("{alias}","' + r'\1' + '")'))

    # 项目名按长度倒序，避免子串误替换
    sorted_items = sorted(item_names_cn, key=len, reverse=True)
    item_pairs: List[Tuple[str, str]] = []
    for name in sorted_items:
        item_pairs.append((name, f'I("{name}")'))
    return alias_patterns, item_pairs


def _percent(v: Optional[Decimal]) -> str:
    if v is None:
        return "-"
    try:
        pct = (v * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{pct}%"
    except Exception:
        return "-"


class Evaluator:
    """
    受限求值器：
    - 只允许 + - * / ( ) 与数字
    - 允许函数：I("项目中文名")、C("常量中文名")
    - 允许无参函数：value_*() / sum_*() 针对“当前行项目”；diff_rate() 由外部按已算值处理
    """

    def __init__(self, ctx: EvalContext, metrics_cache: Dict[str, Dict[str, Decimal]], const_cache: Dict[str, Dict[str, Decimal]],
                 column_frame_map: Dict[int, str], row_cache: Optional[Dict[str, Dict[str, Decimal]]] = None,
                 all_const_cache: Optional[Dict[str, Dict[str, Dict[str, Decimal]]]] = None,
                 all_metrics_cache: Optional[Dict[str, Dict[str, Dict[str, Decimal]]]] = None,
                 company_code: Optional[str] = None):
        self.ctx = ctx
        self.metrics = metrics_cache
        self.consts = const_cache
        self.consts_all = all_const_cache if isinstance(all_const_cache, dict) else {}
        self.metrics_all = all_metrics_cache if isinstance(all_metrics_cache, dict) else {}
        self.company_code = company_code or str(ctx.primary_key.get("company", ""))
        self.column_frames = column_frame_map
        self.row_cache: Dict[str, Dict[str, Decimal]] = row_cache if isinstance(row_cache, dict) else {}

        self.item_cn_to_item = ctx.item_cn_to_item  # CN → en
        self.item_en_to_cn = ctx.item_en_to_cn or {}
        self.unit_cn_to_en = ctx.unit_cn_to_en or {}
        self.unit_en_to_cn = ctx.unit_en_to_cn or {}
        self.company_codes: Set[str] = set()
        if self.unit_en_to_cn:
            self.company_codes.update(k for k in self.unit_en_to_cn.keys() if isinstance(k, str))
        if self.unit_cn_to_en:
            self.company_codes.update(v for v in self.unit_cn_to_en.values() if isinstance(v, str))
        if self.company_code:
            self.company_codes.add(self.company_code)
        if self.metrics_all:
            self.company_codes.update(k for k in self.metrics_all.keys() if isinstance(k, str))

        # 构建替换器
        const_aliases = list(ctx.const_alias_map.keys()) if ctx.const_alias_map else ["c"]
        self.const_aliases = set(const_aliases)
        self.alias_patterns, self.item_pairs = _build_replacers(list(self.item_cn_to_item.keys()), const_aliases)

    # ---- 值提取 ----
    def _value_of_item(self, item_cn: str, frame: str, company_hint: Optional[str] = None) -> Decimal:
        target_company = company_hint or self.company_code
        use_cache = (not company_hint) or target_company == self.company_code
        if use_cache:
            cached = (self.row_cache.get(item_cn) or {}).get(frame)
            if isinstance(cached, Decimal):
                return cached

        metrics_bucket: Dict[str, Dict[str, Decimal]] = {}
        if target_company == self.company_code or not target_company:
            metrics_bucket = self.metrics or {}
        if (not metrics_bucket) and target_company and self.metrics_all:
            metrics_bucket = self.metrics_all.get(target_company, {}) or {}

        item_en = self.item_cn_to_item.get(item_cn)
        fields: Dict[str, Decimal] = {}
        if item_en and isinstance(metrics_bucket.get(item_en), dict):
            fields = metrics_bucket.get(item_en) or {}
        if not fields and isinstance(metrics_bucket.get(item_cn), dict):
            fields = metrics_bucket.get(item_cn) or {}

        field_name = FRAME_FIELDS[frame]
        if item_en:
            if item_en.startswith("sum_month_"):
                if frame in ("biz_date", "sum_month_biz"):
                    field_name = "sum_month_biz"
                elif frame in ("peer_date", "sum_month_peer"):
                    field_name = "sum_month_peer"
            elif item_en.startswith(("sum_season_", "sum_heating_", "sum_ytd_", "sum_period_", "sum_winter_")):
                if frame in ("biz_date", "sum_ytd_biz"):
                    field_name = "sum_ytd_biz"
                elif frame in ("peer_date", "sum_ytd_peer"):
                    field_name = "sum_ytd_peer"
        return fields.get(field_name, Decimal(0))

    def _normalize_company_code(self, raw: Any) -> Optional[str]:
        if raw is None:
            return None
        try:
            token = str(raw).strip()
        except Exception:
            return None
        if not token:
            return None
        if token in self.company_codes:
            return token
        if token in self.unit_cn_to_en:
            mapped = self.unit_cn_to_en[token]
            if mapped:
                self.company_codes.add(mapped)
                return mapped
        if self.metrics_all and token in self.metrics_all:
            self.company_codes.add(token)
            return token
        return None

    def _resolve_company_item(
        self,
        name_input: Optional[str],
        fallback_item_cn: Optional[str],
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if name_input is None:
            return self.company_code, fallback_item_cn, None
        token = str(name_input) if not isinstance(name_input, str) else name_input
        token = token.strip()
        if not token:
            return self.company_code, fallback_item_cn, None

        alias_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\.(.+)$", token)
        if alias_match:
            alias_candidate, remainder = alias_match.groups()
            if alias_candidate in self.const_aliases:
                return self.company_code, remainder.strip(), alias_candidate

        if "." in token:
            prefix, suffix = token.split(".", 1)
            company_code = self._normalize_company_code(prefix)
            if company_code:
                suffix = suffix.strip()
                return company_code, (suffix if suffix else fallback_item_cn), None

        company_code = self._normalize_company_code(token)
        if company_code:
            return company_code, fallback_item_cn, None

        # 尝试按“英文.项目英文”拆分，用于支持 company.item_en 写法
        dotted_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$", token)
        if dotted_match:
            company_candidate, item_en = dotted_match.groups()
            company_code = self._normalize_company_code(company_candidate)
            if company_code:
                item_cn = self.item_en_to_cn.get(item_en) if isinstance(self.item_en_to_cn, dict) else None
                if item_cn:
                    return company_code, item_cn, None
                return company_code, item_en, None

        return self.company_code, token, None

    def _value_of_const(self, name_cn: str, frame: str, alias: Optional[str] = None) -> Decimal:
        """
        常量读取规则：
        - 表中 key 为英文 item（如 price_power_sales），表达式里使用中文（如 售电单价）
        - 先用项目字典反查中文→英文；若找不到，再用中文原值兜底
        """
        period = _normalize_period_key(FRAME_TO_PERIOD[frame])
        target_alias = alias or "c"
        # cn -> en
        key_en = self.item_cn_to_item.get(name_cn, name_cn)
        data_by_alias = self.consts.get(target_alias) if isinstance(self.consts, dict) else None

        def _locate_bucket(source: Optional[Dict[str, Dict[str, Decimal]]], keys: List[str]) -> Optional[Dict[str, Decimal]]:
            if not isinstance(source, dict):
                return None
            for k in keys:
                candidate = source.get(k)
                if isinstance(candidate, dict):
                    return candidate
            return None

        bucket = _locate_bucket(data_by_alias, [key_en, name_cn])

        # 支持 c.<company>.<常量名> 写法，跨公司读取常量
        if not isinstance(bucket, dict) and "." in name_cn and isinstance(self.consts_all, dict):
            company_hint, inner = name_cn.split(".", 1)
            company_candidates: List[str] = []
            if company_hint:
                company_hint = company_hint.strip()
                if company_hint:
                    company_candidates.append(company_hint)
                    if self.ctx.unit_cn_to_en and company_hint in self.ctx.unit_cn_to_en:
                        mapped = self.ctx.unit_cn_to_en[company_hint]
                        if mapped and mapped not in company_candidates:
                            company_candidates.insert(0, mapped)
            inner = inner.strip()
            key_inner_en = self.item_cn_to_item.get(inner, inner)
            for comp_code in company_candidates:
                alias_maps = self.consts_all.get(comp_code)
                if not isinstance(alias_maps, dict):
                    continue
                cross_alias = alias_maps.get(target_alias)
                bucket = _locate_bucket(cross_alias, [key_inner_en, inner])
                if isinstance(bucket, dict):
                    break
            # 若找到跨公司常量，后续 period 直接使用

        if not isinstance(bucket, dict):
            return Decimal(0)

        return bucket.get(period, Decimal(0))

    # ---- 表达式转换与计算 ----
    def _preprocess(self, expr: str) -> str:
        """
        预处理顺序：
        1) 别名常量：a.常量名 → CA("a","常量名")
        2) 项目名替换：仅在非引号区域替换 中文项目名 → I("中文项目名")
           这样不会把 CA("a","售电单价") 误改为 CA("a","I("售电单价")")
        3) 数字字面量统一转 Decimal：未被引号包裹的 123 / 123.45 → D("123.45")
        """
        s = expr.strip()

        def _normalize_expr_text(s0: str) -> str:
            table = {"（": "(", "）": ")", "＋": "+"}
            for k, v in table.items():
                s0 = s0.replace(k, v)
            s0 = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", s0)
            return s0

        s = _normalize_expr_text(s)

        for pat, repl in self.alias_patterns:
            s = pat.sub(repl, s)

        parts = re.split(r"(\".*?\")", s)
        for i in range(0, len(parts), 2):
            seg = parts[i]
            if not seg:
                continue
            for name, repl in self.item_pairs:
                seg = seg.replace(name, repl)
            seg = re.sub(r'(?<![\w\"])\b\d+(?:\.\d+)?\b', lambda m: f'D("{m.group(0)}")', seg)
            parts[i] = seg

        s = "".join(parts)

        frame_func_pattern = re.compile(
            r'\b(value_biz_date|value_peer_date|sum_month_biz|sum_month_peer|sum_ytd_biz|sum_ytd_peer)\(\s*((?:[^)(]+|\([^)(]*\))*)\s*\)'
        )

        def _wrap_unknown_args(m: re.Match) -> str:
            func = m.group(1)
            inner = (m.group(2) or '').strip()
            if not inner:
                return m.group(0)
            tokens = [t.strip() for t in re.split(r'[+＋]', inner)]
            wrapped: List[str] = []
            for token in tokens:
                if not token:
                    continue
                ts = token.strip()
                m_direct = re.match(r'^I\("([^\"]+)"\)$', ts)
                if m_direct:
                    wrapped.append(f'"{m_direct.group(1)}"')
                    continue
                m_qwrapped = re.match(r'^"I\("([^\"]+)"\)"$', ts)
                if m_qwrapped:
                    wrapped.append(f'"{m_qwrapped.group(1)}"')
                    continue
                m_company_item = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\.I\("([^\"]+)"\)$', ts)
                if m_company_item:
                    wrapped.append(f'"{m_company_item.group(1)}.{m_company_item.group(2)}"')
                    continue
                if ts.startswith('"') and ts.endswith('"'):
                    wrapped.append(ts)
                else:
                    wrapped.append(f'"{ts}"')
            if not wrapped:
                return m.group(0)
            return f"{func}(" + ' + '.join(wrapped) + ")"

        s = frame_func_pattern.sub(_wrap_unknown_args, s)

        def _split_multi_args(m: re.Match) -> str:
            func = m.group(1)
            inner = (m.group(2) or '').strip()
            if '+' not in inner and '＋' not in inner:
                return m.group(0)
            tokens = [t.strip() for t in re.split(r'[+＋]', inner)]
            names: List[str] = []
            for token in tokens:
                if not token:
                    continue
                if token.startswith('"') and token.endswith('"'):
                    names.append(token[1:-1])
                else:
                    return m.group(0)
            if len(names) <= 1:
                return m.group(0)
            return ' + '.join(f'{func}("{name}")' for name in names)

        s = frame_func_pattern.sub(_split_multi_args, s)

        return s

    def _safe_eval(self, safe_expr: str, frame: str, current_item_cn: Optional[str], trace_sink: Optional[Dict[str, Any]] = None) -> Optional[Decimal]:
        """
        简化求值：将 I/C 转为回调，再通过 Python 受限 eval 环境计算。
        - 禁止内建与 import
        - 仅暴露 I、C 与部分无参函数（针对当前行项目）
        """
        def I(name_cn: str) -> Decimal:
            # 判定来源（行缓存优先）
            src = "metrics"
            if (self.row_cache.get(name_cn) or {}).get(frame) is not None:
                src = "row_cache"
            v = self._value_of_item(name_cn, frame)
            if trace_sink is not None:
                trace_sink.setdefault("used_items", []).append({"name": name_cn, "frame": frame, "value": str(v), "source": src})
            return v

        def C(name_cn: str) -> Decimal:
            # 默认别名 c
            v = self._value_of_const(name_cn, frame, alias="c")
            if trace_sink is not None:
                trace_sink.setdefault("used_consts", []).append({"alias": "c", "name": name_cn, "frame": frame, "value": str(v)})
            return v

        def CA(alias: str, name_cn: str) -> Decimal:
            v = self._value_of_const(name_cn, frame, alias=alias)
            if trace_sink is not None:
                trace_sink.setdefault("used_consts", []).append({"alias": alias, "name": name_cn, "frame": frame, "value": str(v)})
            return v

        def _cur(frame_key: str, name_cn: Optional[str] = None) -> Decimal:
            company_hint, item_hint, const_alias = self._resolve_company_item(name_cn, current_item_cn)
            if const_alias:
                target_name = item_hint or ""
                return self._value_of_const(target_name, frame_key, alias=const_alias)
            target_cn = item_hint or current_item_cn
            if not target_cn:
                return Decimal(0)
            return self._value_of_item(target_cn, frame_key, company_hint)

        def _call(frame_key: str, name: Optional[str]):
            if trace_sink is not None:
                trace_sink.setdefault("func_calls", []).append({"func": frame_key, "arg": name})
            return _cur(frame_key, name)

        def value_biz_date(name=None): return _call("biz_date", name)
        def value_peer_date(name=None): return _call("peer_date", name)
        def sum_month_biz(name=None): return _call("sum_month_biz", name)
        def sum_month_peer(name=None): return _call("sum_month_peer", name)
        def sum_ytd_biz(name=None): return _call("sum_ytd_biz", name)
        def sum_ytd_peer(name=None): return _call("sum_ytd_peer", name)

        env = {
            "I": I,
            "C": C,
            "CA": CA,
            "D": Decimal,
            # 帧函数：支持可选中文项目名参数
            "value_biz_date": value_biz_date,
            "value_peer_date": value_peer_date,
            "sum_month_biz": sum_month_biz,
            "sum_month_peer": sum_month_peer,
            "sum_ytd_biz": sum_ytd_biz,
            "sum_ytd_peer": sum_ytd_peer,
        }
        try:
            # eval 安全限制：不提供 __builtins__
            val = eval(safe_expr, {"__builtins__": {}}, env)  # noqa: S307 (受控环境)
            return _to_decimal(val)
        except ZeroDivisionError:
            return None
        except Exception as e:
            # 由外层记录错误详情
            raise e

    # ---- 对外：按列表达式计算一个单元格 ----
    def eval_cell(self, expr: str, frame: Optional[str], current_item_cn: Optional[str]) -> Tuple[Optional[Decimal], Dict[str, Any]]:
        """
        返回 (值, 调试信息)
        - frame: 本列的帧；diff_rate 列传入 None，外部统一处理
        """
        trace: Dict[str, Any] = {"raw": expr}
        if not expr:
            return None, trace
        safe_expr = self._preprocess(expr)
        trace["safe_expr"] = safe_expr
        if frame is None:
            # 差异列由外部处理
            return None, trace
        try:
            val = self._safe_eval(safe_expr, frame, current_item_cn, trace_sink=trace)
            trace["value"] = str(val) if val is not None else None
        except Exception as e:
            trace["error"] = str(e)
            val = None
        return val, trace


# ------------------------
# 对外主函数
# ------------------------
def render_spec(spec: Dict[str, Any], project_key: str, primary_key: Dict[str, Any], *, trace: bool = False,
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行步骤：
    1) 解析查询数据源（主表、主键、常量别名）
    2) 预取指标与常量缓存
    3) 逐行逐列替换表达式
    返回：新对象（深拷贝），其中 数据 的表达式已替换为数值/文本；如 trace=True，附加 _trace
    """
    # --- 1. 解析上下文 ---
    qsrc = spec.get("查询数据源") or {}
    main_table = qsrc.get("主表", "sum_basic_data")
    alias_map = qsrc.get("缩写") or {"c": "constant_data"}
    # 行级 company 解析：通过主键中的 column_index 指定用于区分 company 的列（如“中心”或其它）
    try:
        discriminator_index = int((qsrc.get("主键") or {}).get("column_index", -1))
    except Exception:
        discriminator_index = -1
    company = (primary_key or {}).get("company")
    if not company:
        raise ValueError("primary_key 需包含 company 键")

    # 反查：项目中文名 → 英文 item
    item_dict = spec.get("项目字典") or {}
    # item_dict: {en: cn}
    item_cn_to_item = {cn: en for (en, cn) in item_dict.items()}

    # 单位字典（仅使用当前 spec 下发的字典，优先中文→英文反查）
    unit_dict = spec.get("单位字典") or {}
    unit_en_to_cn: Dict[str, str] = {}
    unit_cn_to_en: Dict[str, str] = {}
    if isinstance(unit_dict, dict):
        for en, cn in unit_dict.items():
            if isinstance(en, str) and isinstance(cn, str):
                unit_en_to_cn[en.strip()] = cn.strip()
                unit_cn_to_en[cn.strip()] = en.strip()

    ctx = EvalContext(
        project_key=project_key,
        primary_key=primary_key,
        main_table=main_table,
        const_alias_map=alias_map,
        item_cn_to_item=item_cn_to_item,
        item_en_to_cn=item_dict if item_dict else None,
        unit_cn_to_en=unit_cn_to_en if unit_cn_to_en else None,
        unit_en_to_cn=unit_en_to_cn if unit_en_to_cn else None,
        context=context,
    )

    # --- 2. 预取缓存（支持多 company） ---
    raw_columns: List[str] = spec.get("列名") or []
    rows: List[List[Any]] = spec.get("数据") or []
    is_crosstab = spec.get("类型") == "crosstab"
    header_levels: List[List[str]] = []
    column_companies: Dict[int, Optional[str]] = {}
    column_groups_meta: List[Dict[str, Any]] = []

    known_company_codes: Set[str] = set()
    if company:
        known_company_codes.add(str(company))
    if unit_en_to_cn:
        known_company_codes.update(k for k in unit_en_to_cn.keys() if isinstance(k, str))
    if unit_cn_to_en:
        known_company_codes.update(v for v in unit_cn_to_en.values() if isinstance(v, str))

    def _normalize_company(raw: Any) -> Optional[str]:
        if raw is None:
            return None
        try:
            token = str(raw).strip()
        except Exception:
            return None
        if not token:
            return None
        if unit_cn_to_en and token in unit_cn_to_en:
            mapped = unit_cn_to_en[token]
            if mapped:
                known_company_codes.add(mapped)
                return mapped
        if token in known_company_codes:
            return token
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", token):
            known_company_codes.add(token)
            return token
        return None

    if is_crosstab:
        header_level1 = spec.get("列名1") or []
        header_level2 = spec.get("列名2") or []
        max_len = max(len(header_level1), len(header_level2))

        def _ensure_len(src, length):
            if not isinstance(src, list):
                return [""] * length
            result = []
            for idx in range(length):
                val = src[idx] if idx < len(src) else ""
                result.append("" if val is None else str(val))
            return result

        header_level1 = _ensure_len(header_level1, max_len)
        header_level2 = _ensure_len(header_level2, max_len)
        header_levels = [header_level1, header_level2]
        columns: List[str] = []
        for idx in range(max_len):
            top = header_level1[idx] or ""
            bottom = header_level2[idx] or ""
            top = str(top)
            bottom = str(bottom)
            if bottom:
                columns.append(f"{top}\n{bottom}" if top else bottom)
            else:
                columns.append(top)
            if idx >= 2 and top:
                normalized_top = top.strip()
                column_companies[idx] = unit_cn_to_en.get(normalized_top, normalized_top)
            else:
                column_companies[idx] = None

        if max_len:
            idx = 0
            while idx < max_len:
                top_clean = str(header_level1[idx] or "").strip()
                if idx < 2 or not top_clean:
                    title = top_clean or str(header_level2[idx] or "") or str(columns[idx] or "")
                    column_groups_meta.append({"start": idx, "span": 1, "title": title})
                    idx += 1
                    continue
                span = 0
                while idx + span < max_len:
                    cur = str(header_level1[idx + span] or "").strip()
                    if cur != top_clean:
                        break
                    span += 1
                column_groups_meta.append({"start": idx, "span": span or 1, "title": top_clean})
                idx += span or 1
    else:
        columns = raw_columns

    companies_needed: Set[str] = set()
    primary_company = _normalize_company(company) or (str(company) if company else "")
    if primary_company:
        known_company_codes.add(primary_company)
        companies_needed.add(primary_company)
    unit_identifiers = spec.get("单位标识")
    if isinstance(unit_identifiers, str):
        for token in re.split(r"[\\/|,;]", unit_identifiers):
            token = token.strip()
            if token:
                normalized = _normalize_company(token)
                if normalized:
                    companies_needed.add(normalized)
    if column_companies:
        for comp_hint in column_companies.values():
            if comp_hint:
                normalized = _normalize_company(comp_hint)
                if normalized:
                    companies_needed.add(normalized)
    const_company_pattern = re.compile(r"c\.([^.]+)\.")
    frame_company_pattern = re.compile(
        r"\b(?:value_biz_date|value_peer_date|sum_month_biz|sum_month_peer|sum_ytd_biz|sum_ytd_peer)\s*\(\s*((?:[^)(]+|\([^)(]*\))*)\s*\)"
    )
    for r in rows:
        if not isinstance(r, list):
            continue
        for cell in r:
            if not isinstance(cell, str):
                try:
                    cell = str(cell)
                except Exception:
                    continue
            for match in frame_company_pattern.finditer(cell):
                inner = (match.group(1) or "").strip()
                if not inner:
                    continue
                for token in re.split(r"[+\uff0b]", inner):
                    candidate = token.strip().strip('"').strip("'")
                    if not candidate:
                        continue
                    if candidate.startswith("c."):
                        continue
                    company_part = candidate.split(".", 1)[0]
                    normalized = _normalize_company(company_part)
                    if normalized:
                        companies_needed.add(normalized)
            for comp_hint in const_company_pattern.findall(cell):
                comp_hint = comp_hint.strip()
                if comp_hint:
                    normalized = _normalize_company(comp_hint)
                    if normalized:
                        companies_needed.add(normalized)
    if isinstance(discriminator_index, int) and discriminator_index >= 0:
        for r in rows:
            if isinstance(r, list) and len(r) > discriminator_index:
                c = _normalize_company(r[discriminator_index])
                if c:
                    companies_needed.add(c)

    with next(get_session()) as session:  # type: ignore
        metrics_by_company: Dict[str, Dict[str, Dict[str, Decimal]]] = {}
        consts_by_company: Dict[str, Dict[str, Dict[str, Dict[str, Decimal]]]] = {}
        # 解析主表路由（支持两种写法：顶层“主表路由”，或 qsrc['主表'] 为对象）
        route_cfg = spec.get("主表路由") if isinstance(spec, dict) else None
        if (not isinstance(route_cfg, dict)) and isinstance(qsrc, dict):
            _mb = qsrc.get("主表")
            if isinstance(_mb, dict) and ("groups" in _mb or "default" in _mb):
                route_cfg = _mb
        _groups_set: Set[str] = set()
        _default_table = str(main_table)
        if isinstance(route_cfg, dict):
            try:
                _groups_set = set(route_cfg.get("groups") or [])
                _default_table = route_cfg.get("default") or _default_table
            except Exception:
                pass
        for comp in companies_needed:
            try:
                if context and isinstance(context.get("biz_date"), str) and context["biz_date"] != "regular":
                    metrics_by_company[comp] = _fetch_metrics_dynamic_by_date(session, comp, context["biz_date"])
                else:
                    # 按公司动态选择主表（comp 在 groups 列表 → groups，否则 default）
                    _per_table = "groups" if comp in _groups_set else _default_table
                    metrics_by_company[comp] = _fetch_metrics_from_view(session, _per_table, comp)
            except Exception:
                metrics_by_company[comp] = {}
            consts_by_company[comp] = {}
            for alias, table_name in (alias_map or {}).items():
                try:
                    if isinstance(table_name, str) and table_name == "sum_coal_inventory_data":
                        consts_by_company[comp][alias] = _fetch_sum_coal_inventory_constants(session, comp)
                    else:
                        consts_by_company[comp][alias] = _fetch_constants_for_table(session, table_name, comp)
                except Exception:
                    consts_by_company[comp][alias] = {}

    col_frames = map_columns_to_frames(columns)
    # 动态确定回填起点：以首个“本期日”所在列为准（data_start_idx）
    # 在此之前（ci < data_start_idx）的列原样保留（如 项目/中心/计量单位 等）
    data_start_idx = 2  # 兜底：标准两列表头时从第3列开始
    try:
        biz_cols = [idx for idx, frame in col_frames.items() if frame == "biz_date"]
        if biz_cols:
            data_start_idx = min(biz_cols)
    except Exception:
        pass
    readonly_limit = max(0, data_start_idx - 1)

    # 识别“项目”列索引（若存在），以便当前行默认项目从该列取值
    item_col_index: int = -1
    try:
        for idx, cname in enumerate(columns or []):
            label = _normalize_col_label(str(cname) if cname is not None else "")
            if label in ("项目", "项目名称", "项目名"):
                item_col_index = idx
                break
    except Exception:
        item_col_index = -1

    # 允许多轮求值以解决行间/前后顺序依赖（默认 2 轮，可通过 context.passes 覆盖）
    max_passes = 2
    if context and isinstance(context.get("passes"), int) and context["passes"] >= 1:
        max_passes = int(context["passes"])

    # 用于 diff_rate 计算：按（日、月、供暖期）分组，先算出 biz/peer 值
    def _pair_for_group(group: str) -> Tuple[str, str]:
        if group == "day":
            return "biz_date", "peer_date"
        if group == "month":
            return "sum_month_biz", "sum_month_peer"
        if group == "ytd":
            return "sum_ytd_biz", "sum_ytd_peer"
        raise ValueError("unknown group")

    def _normalize_accuracy_key(val: Any) -> str:
        try:
            return str(val).strip()
        except Exception:
            return ""

    def _clamp_accuracy(val: Any) -> Optional[int]:
        try:
            n = int(val)
        except Exception:
            return None
        if n < 0:
            return 0
        if n > 8:
            return 8
        return n

    # 精度（accuracy）：除差异列外，按模板设置的小数位进行格式化；支持默认值与分项覆盖
    accuracy_default: int = 2
    accuracy_overrides: Dict[str, int] = {}
    try:
        acc_raw = spec.get("accuracy") if isinstance(spec, dict) else None
        if isinstance(acc_raw, dict):
            default_val = _clamp_accuracy(acc_raw.get("default"))
            if default_val is not None:
                accuracy_default = default_val
            for key, raw_val in acc_raw.items():
                if key == "default":
                    continue
                clamp_val = _clamp_accuracy(raw_val)
                if clamp_val is not None:
                    norm_key = _normalize_accuracy_key(key)
                    if norm_key:
                        accuracy_overrides[norm_key] = clamp_val
        else:
            clamp_val = _clamp_accuracy(acc_raw)
            if clamp_val is not None:
                accuracy_default = clamp_val
    except Exception:
        accuracy_default = 2
        accuracy_overrides = {}

    # 返回对象（在最后一轮填充）
    out = dict(spec)  # 浅拷贝基础字段
    out["accuracy"] = accuracy_default
    if accuracy_overrides:
        out["accuracy_map"] = dict(accuracy_overrides)
    # 透传 number_format，便于前端做分组/本地化格式化
    if isinstance(spec, dict) and isinstance(spec.get("number_format"), dict):
        out["number_format"] = dict(spec.get("number_format"))
    final_rows: List[List[Any]] = []
    final_traces: List[List[Dict[str, Any]]] = []
    # 跨轮共享的行缓存（用于前后顺序依赖）——按 company 分片，避免串扰
    shared_row_cache_by_company: Dict[str, Dict[str, Dict[str, Decimal]]] = {}

    for pass_idx in range(max_passes):
        last_pass = (pass_idx == max_passes - 1)
        # 每一轮的临时输出
        out_rows: List[List[Any]] = []
        all_traces: List[List[Dict[str, Any]]] = []

        for r in rows:
            if not isinstance(r, list) or len(r) < 2:
                if last_pass:
                    out_rows.append(r)
                    all_traces.append([])
                # 非最后一轮无需记录显示
                continue
            row_label = r[0]  # 传统模板：项目中文名；本模板可能为“经营单位”
            unit_label = r[1] if len(r) > 1 else ""
            # 默认 company：优先行内 discriminator，其次 primary_key.company
            row_company_default = str(company)
            if isinstance(discriminator_index, int) and discriminator_index >= 0 and len(r) > discriminator_index:
                rc = _normalize_company(r[discriminator_index])
                if rc:
                    row_company_default = rc

            evaluator_cache: Dict[str, Evaluator] = {}
            row_cache_map: Dict[str, Dict[str, Dict[str, Decimal]]] = shared_row_cache_by_company

            def _get_evaluator(comp_hint: Optional[str]) -> Tuple[str, Evaluator]:
                target = str(comp_hint or row_company_default)
                if target not in evaluator_cache:
                    metrics = metrics_by_company.get(target, {})
                    consts_alias = consts_by_company.get(target, {})
                    row_cache_local = row_cache_map.setdefault(target, {})
                    evaluator_cache[target] = Evaluator(
                        ctx,
                        metrics,
                        consts_alias,
                        col_frames,
                        row_cache=row_cache_local,
                        all_const_cache=consts_by_company,
                        all_metrics_cache=metrics_by_company,
                        company_code=target,
                    )
                return target, evaluator_cache[target]

            # 当前行项目是否可映射为基础指标（仅依赖项目字典即可）
            current_item_cn = None
            try:
                if item_col_index >= 0 and len(r) > item_col_index:
                    item_cell = r[item_col_index]
                    item_cn_candidate = str(item_cell).strip() if item_cell is not None else ""
                    if item_cn_candidate and item_cn_candidate in ctx.item_cn_to_item:
                        current_item_cn = item_cn_candidate
                if current_item_cn is None and row_label in ctx.item_cn_to_item:
                    current_item_cn = row_label
            except Exception:
                current_item_cn = row_label if row_label in ctx.item_cn_to_item else None

            FRAME_TO_GROUP = {
                "biz_date": "day",
                "peer_date": "day",
                "sum_month_biz": "month",
                "sum_month_peer": "month",
                "sum_ytd_biz": "ytd",
                "sum_ytd_peer": "ytd",
            }

            row_vals: List[Optional[Decimal]] = []
            row_traces: List[Dict[str, Any]] = []
            per_company_group_indices: Dict[str, Dict[str, Dict[str, Optional[int]]]] = {}
            per_company_frames: Dict[str, Dict[str, Decimal]] = {}

            for ci, cell in enumerate(r):
                if ci <= readonly_limit:
                    row_vals.append(None)
                    if last_pass:
                        row_traces.append({"raw": cell})
                    continue
                expr = str(cell or "").strip()
                frame = col_frames.get(ci)
                expr_key = expr.replace(" ", "")
                comp_hint = column_companies.get(ci) if column_companies else None
                comp_code, evaluator = _get_evaluator(comp_hint)
                group_name = FRAME_TO_GROUP.get(frame) if frame else None

                if expr_key.startswith("date_diff_rate"):
                    per_company_group_indices.setdefault(comp_code, {}).setdefault("day", {})["diff"] = ci
                    row_vals.append(None)
                    if last_pass:
                        row_traces.append({"raw": expr, "deferred": True})
                    continue
                if expr_key.startswith("month_diff_rate"):
                    per_company_group_indices.setdefault(comp_code, {}).setdefault("month", {})["diff"] = ci
                    row_vals.append(None)
                    if last_pass:
                        row_traces.append({"raw": expr, "deferred": True})
                    continue
                if expr_key.startswith("ytd_diff_rate"):
                    per_company_group_indices.setdefault(comp_code, {}).setdefault("ytd", {})["diff"] = ci
                    row_vals.append(None)
                    if last_pass:
                        row_traces.append({"raw": expr, "deferred": True})
                    continue

                val, t = evaluator.eval_cell(expr, frame, current_item_cn)
                row_vals.append(val)
                if last_pass:
                    row_traces.append(t)

                if frame and isinstance(val, Decimal):
                    per_company_frames.setdefault(comp_code, {})[frame] = val
                    if group_name:
                        if frame in ("biz_date", "sum_month_biz", "sum_ytd_biz"):
                            key = "biz"
                        elif frame in ("peer_date", "sum_month_peer", "sum_ytd_peer"):
                            key = "peer"
                        else:
                            key = None
                        if key:
                            per_company_group_indices.setdefault(comp_code, {}).setdefault(group_name, {})[key] = ci

            if is_crosstab and per_company_group_indices:
                for comp_code, groups in per_company_group_indices.items():
                    for grp_name, idxs in groups.items():
                        diff_idx = idxs.get("diff")
                        if diff_idx is None:
                            continue
                        diff_expr = str(r[diff_idx] or "")
                        biz_idx = idxs.get("biz")
                        peer_idx = idxs.get("peer")
                        if biz_idx is None or peer_idx is None:
                            out_val = None
                            out_fmt = "-"
                        else:
                            biz_val = row_vals[biz_idx]
                            peer_val = row_vals[peer_idx]
                            if biz_val is None or peer_val is None:
                                out_val, out_fmt = None, "-"
                            else:
                                try:
                                    denom = abs(peer_val)
                                    if denom == 0:
                                        out_val, out_fmt = None, "-"
                                    else:
                                        rate = (biz_val - peer_val) / denom
                                        out_val, out_fmt = rate, _percent(rate)
                                except Exception:
                                    out_val, out_fmt = None, "-"
                        row_vals[diff_idx] = out_val
                        if last_pass:
                            base = {"raw": diff_expr, "formatted": out_fmt}
                            if len(row_traces) > diff_idx and isinstance(row_traces[diff_idx], dict):
                                row_traces[diff_idx] = {**row_traces[diff_idx], **base}
                            else:
                                if diff_idx >= len(row_traces):
                                    row_traces.extend([{}] * (diff_idx - len(row_traces) + 1))
                                row_traces[diff_idx] = base
            else:
                def _find_indices_by_group(group: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
                    biz_frame, peer_frame = _pair_for_group(group)
                    biz_idx = peer_idx = diff_idx = None
                    for ci in range(len(r)):
                        f = col_frames.get(ci)
                        if f == biz_frame:
                            biz_idx = ci
                        elif f == peer_frame:
                            peer_idx = ci
                        else:
                            label = _normalize_col_label(columns[ci]) if ci < len(columns) else ""
                            if group == "day" and "日差异" in label:
                                diff_idx = ci
                            elif group == "month" and "月差异" in label:
                                diff_idx = ci
                            elif group == "ytd" and ("供暖期差异" in label or "供暖期差" in label):
                                diff_idx = ci
                    if diff_idx is not None:
                        raw_expr = str(r[diff_idx] or "").strip()
                        if not raw_expr or "diff_rate" not in raw_expr:
                            diff_idx = None
                    return biz_idx, peer_idx, diff_idx

                for grp in ("day", "month", "ytd"):
                    biz_idx, peer_idx, diff_idx = _find_indices_by_group(grp)
                    if diff_idx is None:
                        continue
                    diff_expr = str(r[diff_idx] or "")
                    if biz_idx is None or peer_idx is None:
                        out_val = None
                        out_fmt = "-"
                    else:
                        biz_val = row_vals[biz_idx]
                        peer_val = row_vals[peer_idx]
                        if biz_val is None or peer_val is None:
                            out_val = None
                            out_fmt = "-"
                        else:
                            try:
                                denom = abs(peer_val)
                                if denom == 0:
                                    out_val = None
                                    out_fmt = "-"
                                else:
                                    rate = (biz_val - peer_val) / denom
                                    out_val = rate
                                    out_fmt = _percent(rate)
                            except Exception:
                                out_val, out_fmt = None, "-"
                    row_vals[diff_idx] = out_val
                    if last_pass:
                        base = {"raw": diff_expr, "formatted": out_fmt}
                        if len(row_traces) > diff_idx and isinstance(row_traces[diff_idx], dict):
                            row_traces[diff_idx] = {**row_traces[diff_idx], **base}
                        else:
                            if diff_idx >= len(row_traces):
                                row_traces.extend([{}] * (diff_idx - len(row_traces) + 1))
                            row_traces[diff_idx] = base

            # 将本行可用数值写入共享行缓存
            for comp_code, frame_map in per_company_frames.items():
                if not frame_map:
                    continue
                row_store = row_cache_map.setdefault(comp_code, {})
                existing = row_store.get(row_label) or {}
                for frame_key, value in frame_map.items():
                    if isinstance(value, Decimal):
                        existing[frame_key] = value
                row_store[row_label] = existing

            if last_pass:
                # 组装显示行
                display_row: List[Any] = []
                item_en = evaluator.item_cn_to_item.get(row_label) if current_item_cn else None
                is_efficiency_row = (row_label == "全厂热效率") or (item_en == "rate_overall_efficiency")
                # 行级精度：优先使用 accuracy_map 中的覆盖
                row_accuracy_key = _normalize_accuracy_key(row_label)
                row_accuracy = accuracy_overrides.get(row_accuracy_key, accuracy_default)
                if row_accuracy is None or not isinstance(row_accuracy, int):
                    row_accuracy = accuracy_default
                # 占位符策略：仅将单字符 '-' 识别为占位符
                def _is_placeholder(s: str) -> bool:
                    return (s or "").strip() == "-"

                for ci, cell in enumerate(r):
                    if ci <= readonly_limit:
                        display_row.append(cell)
                        continue
                    label = _normalize_col_label(columns[ci]) if ci < len(columns) else ""
                    is_diff = any(k in label for k in ("日差异", "月差异", "供暖期差异", "供暖期差"))
                    v = row_vals[ci]
                    raw_cell = str(cell) if cell is not None else ""
                    if is_diff:
                        raw_trim = raw_cell.strip()
                        if raw_trim:
                            fmt = row_traces[ci].get("formatted") if ci < len(row_traces) and isinstance(row_traces[ci], dict) else None
                            display_row.append(fmt if fmt is not None else "-")
                        else:
                            if v is None:
                                display_row.append("")
                            else:
                                display_row.append(v)
                    else:
                        if v is None:
                            # 仅对标准占位符 '-' 进行占位显示；其余文本保持原规则
                            if _is_placeholder(raw_cell):
                                display_row.append("-")
                            else:
                                display_row.append("-" if is_efficiency_row else "")
                        else:
                            if is_efficiency_row:
                                display_row.append(_percent(v))
                            else:
                                # 按 accuracy 控制小数位
                                if row_accuracy == 0:
                                    q = Decimal("1")
                                else:
                                    q = Decimal("1").scaleb(-row_accuracy)  # 等价于 10**(-accuracy)
                                display_row.append(float(v.quantize(q, rounding=ROUND_HALF_UP)))
                out_rows.append(display_row)
                all_traces.append(row_traces)

        if last_pass:
            final_rows = out_rows
            final_traces = all_traces
        # 下一轮继续，使用已累积的 shared_row_cache

    out["数据"] = final_rows
    if trace:
        out["_trace"] = final_traces

    # --- 4. 列头占位替换（便于前端直观显示） ---
    # 规则：
    # (本期日) → biz_date（YYYY-MM-DD）
    # (同期日) → peer_date（YYYY-MM-DD）
    # (本期月) → month_biz（YYYY-MM）
    # (同期月) → month_peer（YYYY-MM）
    # (本供暖期) → ytd_biz（如 25-26）
    # (同供暖期) → ytd_peer（如 24-25）
    try:
        # 1) 解析锚点日期：优先 context.biz_date（YYYY-MM-DD），否则使用“今日-1”
        anchor: Optional[_date] = None
        if context and isinstance(context.get("biz_date"), str) and context["biz_date"] != "regular":
            try:
                anchor = _date.fromisoformat(context["biz_date"])
            except Exception:
                anchor = None
        if anchor is None:
            anchor = _project_today() - _timedelta(days=1)
        # 2) 同期为去年同日（闰日回退到 2/28）
        try:
            peer = anchor.replace(year=anchor.year - 1)
        except ValueError:
            # 2/29 → 2/28
            peer = anchor.replace(year=anchor.year - 1, day=28)
        # 3) 月份标签
        month_biz = f"{anchor.year:04d}-{anchor.month:02d}"
        month_peer = f"{peer.year:04d}-{peer.month:02d}"
        # 4) 供暖期标签采用帧到 period 的映射（已在常量读取中统一归一化）
        ytd_biz = FRAME_TO_PERIOD["sum_ytd_biz"]
        ytd_peer = FRAME_TO_PERIOD["sum_ytd_peer"]
        # 5) 执行替换
        cols_in = list(columns) if isinstance(columns, list) else []
        cols_out: List[str] = []
        for c in cols_in:
            s = str(c) if c is not None else ""
            s = s.replace("(本期日)", anchor.isoformat())
            s = s.replace("(同期日)", peer.isoformat())
            s = s.replace("(本期月)", month_biz)
            s = s.replace("(同期月)", month_peer)
            s = s.replace("(本供暖期)", ytd_biz)
            s = s.replace("(同供暖期)", ytd_peer)
            cols_out.append(s)
        if cols_out:
            out["列名"] = cols_out
            # 兼容：若调用方直接读取 columns 字段
            out["columns"] = cols_out
            if header_levels:
                level0 = list(header_levels[0]) if len(header_levels) > 0 else [""] * len(cols_out)
                level1 = list(header_levels[1]) if len(header_levels) > 1 else [""] * len(cols_out)
                if len(level0) < len(cols_out):
                    level0.extend([""] * (len(cols_out) - len(level0)))
                if len(level1) < len(cols_out):
                    level1.extend([""] * (len(cols_out) - len(level1)))
                for idx, col_name in enumerate(cols_out):
                    parts = str(col_name or "").split("\n", 1)
                    if parts:
                        if idx < len(level0):
                            level0[idx] = parts[0]
                        if len(parts) > 1 and idx < len(level1):
                            level1[idx] = parts[1]
                header_levels_out = [level0, level1]
                out["column_headers"] = header_levels_out
    except Exception:
        # 列头替换失败不影响主体数据返回
        pass

    if header_levels and "column_headers" not in out:
        out["column_headers"] = header_levels
    if column_groups_meta:
        out["column_groups"] = column_groups_meta

    return out
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
except ImportError:  # pragma: no cover - fallback for older Python
    _ZoneInfo = None

# ------------------------
# 时间工具
# ------------------------
def _project_today() -> _date:
    """
    返回项目默认时区（Asia/Shanghai）的“今天”日期。
    若运行环境不支持 zoneinfo，则回退到本地日期。
    """
    if _ZoneInfo is not None:
        try:
            return _datetime.now(_ZoneInfo("Asia/Shanghai")).date()
        except Exception:
            pass
    return _date.today()
