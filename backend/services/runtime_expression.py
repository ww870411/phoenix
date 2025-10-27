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
from typing import Any, Dict, List, Optional, Tuple
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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
def _fetch_metrics_from_matview(session: Session, company: str) -> Dict[str, Dict[str, Decimal]]:
    """
    从物化视图按 company 维度一次性拉取所有 item 的 6 个窗口值。
    返回结构：{ item: {field_name: Decimal, ...}, ... }
    """
    sql = text(
        """
        SELECT item, item_cn, unit,
               value_biz_date, value_peer_date,
               sum_month_biz, sum_month_peer,
               sum_ytd_biz, sum_ytd_peer
          FROM sum_basic_data
         WHERE company = :company
        """
    )
    rows = session.execute(sql, {"company": company}).mappings().all()
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
    sql = text(f"SELECT item AS name, period, value FROM {table_name} WHERE company = :company")
    rows = session.execute(sql, {"company": company}).mappings().all()
    out: Dict[str, Dict[str, Decimal]] = {}
    for r in rows:
        name = r["name"]
        period = r["period"]
        out.setdefault(name, {})[period] = _to_decimal(r["value"])
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
                 column_frame_map: Dict[int, str]):
        self.ctx = ctx
        self.metrics = metrics_cache
        self.consts = const_cache
        self.column_frames = column_frame_map

        self.item_cn_to_item = ctx.item_cn_to_item  # CN → en

        # 构建替换器
        const_aliases = list(ctx.const_alias_map.keys()) if ctx.const_alias_map else ["c"]
        self.alias_patterns, self.item_pairs = _build_replacers(list(self.item_cn_to_item.keys()), const_aliases)

    # ---- 值提取 ----
    def _value_of_item(self, item_cn: str, frame: str) -> Decimal:
        item_en = self.item_cn_to_item.get(item_cn)
        if not item_en:
            return Decimal(0)
        fields = self.metrics.get(item_en) or {}
        field_name = FRAME_FIELDS[frame]
        return fields.get(field_name, Decimal(0))

    def _value_of_const(self, name_cn: str, frame: str, alias: Optional[str] = None) -> Decimal:
        """
        常量读取规则：
        - 表中 key 为英文 item（如 price_power_sales），表达式里使用中文（如 售电单价）
        - 先用项目字典反查中文→英文；若找不到，再用中文原值兜底
        """
        period = FRAME_TO_PERIOD[frame]
        target_alias = alias or "c"
        # cn -> en
        key_en = self.item_cn_to_item.get(name_cn, name_cn)
        data_by_alias = self.consts.get(target_alias) if isinstance(self.consts, dict) else None
        if not isinstance(data_by_alias, dict):
            return Decimal(0)
        # 优先英文 key
        bucket = data_by_alias.get(key_en)
        if not isinstance(bucket, dict):
            # 兜底：尝试中文 key
            bucket = data_by_alias.get(name_cn)
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
        """
        s = expr.strip()
        # 1) 先处理别名常量
        for pat, repl in self.alias_patterns:
            s = pat.sub(repl, s)
        # 2) 仅在非引号区域替换项目名
        #    按双引号切分，偶数索引为未被引号包裹的区域
        parts = re.split(r'(".*?")', s)
        for i in range(0, len(parts), 2):
            seg = parts[i]
            if not seg:
                continue
            for name, repl in self.item_pairs:
                seg = seg.replace(name, repl)
            parts[i] = seg
        return "".join(parts)

    def _safe_eval(self, safe_expr: str, frame: str, current_item_cn: Optional[str], trace_sink: Optional[Dict[str, Any]] = None) -> Optional[Decimal]:
        """
        简化求值：将 I/C 转为回调，再通过 Python 受限 eval 环境计算。
        - 禁止内建与 import
        - 仅暴露 I、C 与部分无参函数（针对当前行项目）
        """
        def I(name_cn: str) -> Decimal:
            v = self._value_of_item(name_cn, frame)
            if trace_sink is not None:
                trace_sink.setdefault("used_items", []).append({"name": name_cn, "frame": frame, "value": str(v)})
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

        def _cur(frame_key: str) -> Decimal:
            if not current_item_cn:
                return Decimal(0)
            return self._value_of_item(current_item_cn, frame_key)

        env = {
            "I": I,
            "C": C,
            "CA": CA,
            # 针对当前行项目的便捷函数
            "value_biz_date": lambda: _cur("biz_date"),
            "value_peer_date": lambda: _cur("peer_date"),
            "sum_month_biz": lambda: _cur("sum_month_biz"),
            "sum_month_peer": lambda: _cur("sum_month_peer"),
            "sum_ytd_biz": lambda: _cur("sum_ytd_biz"),
            "sum_ytd_peer": lambda: _cur("sum_ytd_peer"),
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
    company = (primary_key or {}).get("company")
    if not company:
        raise ValueError("primary_key 需包含 company 键")

    # 反查：项目中文名 → 英文 item
    item_dict = spec.get("项目字典") or {}
    # item_dict: {en: cn}
    item_cn_to_item = {cn: en for (en, cn) in item_dict.items()}

    ctx = EvalContext(
        project_key=project_key,
        primary_key=primary_key,
        main_table=main_table,
        const_alias_map=alias_map,
        item_cn_to_item=item_cn_to_item,
        context=context,
    )

    # --- 2. 预取缓存 ---
    with next(get_session()) as session:  # type: ignore
        # 指标
        metrics: Dict[str, Dict[str, Decimal]]
        if context and isinstance(context.get("biz_date"), str) and context["biz_date"] != "regular":
            metrics = _fetch_metrics_dynamic_by_date(session, company, context["biz_date"])
        else:
            metrics = _fetch_metrics_from_matview(session, company)
        # 常量（多别名预留）
        consts_by_alias: Dict[str, Dict[str, Dict[str, Decimal]]] = {}
        for alias, table_name in (alias_map or {}).items():
            try:
                consts_by_alias[alias] = _fetch_constants_for_table(session, table_name, company)
            except Exception:
                consts_by_alias[alias] = {}

    columns: List[str] = spec.get("列名") or []
    rows: List[List[Any]] = spec.get("数据") or []
    col_frames = map_columns_to_frames(columns)

    evaluator = Evaluator(ctx, metrics, consts_by_alias, col_frames)

    # 用于 diff_rate 计算：按（日、月、供暖期）分组，先算出 biz/peer 值
    def _pair_for_group(group: str) -> Tuple[str, str]:
        if group == "day":
            return "biz_date", "peer_date"
        if group == "month":
            return "sum_month_biz", "sum_month_peer"
        if group == "ytd":
            return "sum_ytd_biz", "sum_ytd_peer"
        raise ValueError("unknown group")

    # 返回对象
    out = dict(spec)  # 浅拷贝基础字段
    out_rows: List[List[Any]] = []
    all_traces: List[List[Dict[str, Any]]] = []

    for r in rows:
        if not isinstance(r, list) or len(r) < 2:
            out_rows.append(r)
            all_traces.append([])
            continue
        row_label = r[0]  # 项目中文名
        unit_label = r[1]
        # 当前行项目是否可映射为基础指标
        current_item_cn = row_label if row_label in evaluator.item_cn_to_item else None

        # 先逐列计算普通值，临时保存以便 diff_rate 使用
        row_vals: List[Optional[Decimal]] = []
        row_traces: List[Dict[str, Any]] = []
        for ci, cell in enumerate(r):
            if ci < 2:
                row_vals.append(None)
                row_traces.append({"raw": cell})
                continue
            expr = str(cell or "").strip()
            frame = col_frames.get(ci)  # None 表示差异列
            expr_key = expr.replace(" ", "")
            if expr_key.startswith("date_diff_rate"):
                # 先占位，稍后统一计算
                row_vals.append(None)
                row_traces.append({"raw": expr, "deferred": True})
                continue
            if expr_key.startswith("month_diff_rate"):
                row_vals.append(None)
                row_traces.append({"raw": expr, "deferred": True})
                continue
            if expr_key.startswith("ytd_diff_rate"):
                row_vals.append(None)
                row_traces.append({"raw": expr, "deferred": True})
                continue
            val, t = evaluator.eval_cell(expr, frame, current_item_cn)
            row_vals.append(val)
            row_traces.append(t)

        # 计算三类差异列：按列名判断所在组
        def _find_indices_by_group(group: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
            # 返回 (biz_idx, peer_idx, diff_idx)
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
            return biz_idx, peer_idx, diff_idx

        for grp in ("day", "month", "ytd"):
            biz_idx, peer_idx, diff_idx = _find_indices_by_group(grp)
            if diff_idx is None:
                continue
            # 差异列原始表达式应为 *_diff_rate()
            diff_expr = str(r[diff_idx] or "")
            # 若对应 biz/peer 列表达式为空，则跳过
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
            # 写回
            row_vals[diff_idx] = out_val
            row_traces[diff_idx] = {**row_traces[diff_idx], "raw": diff_expr, "formatted": out_fmt}

        # 组装最终显示行：将差异列格式化为百分比，其余为原始数值（Decimal→float）
        display_row: List[Any] = []
        # 判断是否“全厂热效率”行
        item_en = evaluator.item_cn_to_item.get(row_label) if current_item_cn else None
        is_efficiency_row = (row_label == "全厂热效率") or (item_en == "rate_overall_efficiency")

        for ci, cell in enumerate(r):
            if ci < 2:
                display_row.append(cell)
                continue
            label = _normalize_col_label(columns[ci]) if ci < len(columns) else ""
            is_diff = any(k in label for k in ("日差异", "月差异", "供暖期差异", "供暖期差"))
            v = row_vals[ci]
            if is_diff:
                # 已在 trace 中给出 formatted
                fmt = row_traces[ci].get("formatted")
                display_row.append(fmt if fmt is not None else "-")
            else:
                # 其他列返回数值（保留四位小数）
                if v is None:
                    display_row.append("-" if is_efficiency_row else "")
                else:
                    if is_efficiency_row:
                        # 效率指标也按百分比字符串输出，保留两位
                        display_row.append(_percent(v))
                    else:
                        display_row.append(float(v.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)))
        out_rows.append(display_row)
        all_traces.append(row_traces)

    out["数据"] = out_rows
    if trace:
        out["_trace"] = all_traces
    return out
