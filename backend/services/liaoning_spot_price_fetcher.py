from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence
from urllib import error, request


GET_LIST_DATA_URL = "https://fgw.ln.gov.cn/indexview/api/getListData"
DEFAULT_START_DATE = date(2026, 1, 1)
DEFAULT_END_DATE = date(2026, 3, 8)
DEFAULT_TIMEOUT = 20.0
DEFAULT_OUTPUT_JSON = (
    Path(__file__).resolve().parents[2]
    / "backend_data"
    / "liaoning_spot_price_2026-01-01_2026-03-08.json"
)


class LiaoningSpotPriceFetchError(RuntimeError):
    """辽宁现货电价抓取过程中的通用错误。"""


@dataclass
class SpotPricePoint:
    """单个 15 分钟点位。"""

    time_label: str
    before_price: str
    real_time_price: str


@dataclass
class DailySpotPrice:
    """单日抓取结果。"""

    biz_date: str
    published: bool
    total_points: int
    non_empty_value_count: int
    points: List[SpotPricePoint]


def _time_sort_key(time_label: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = time_label.split(":", 1)
        return int(hour_text), int(minute_text)
    except (ValueError, AttributeError) as exc:
        raise LiaoningSpotPriceFetchError(f"无法解析时刻字段：{time_label}") from exc


def _parse_iso_date(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"日期格式错误，需为 YYYY-MM-DD：{raw}") from exc


def _iter_dates(start_date: date, end_date: date) -> Sequence[date]:
    current = start_date
    all_dates: List[date] = []
    while current <= end_date:
        all_dates.append(current)
        current += timedelta(days=1)
    return all_dates


def _request_with_retry(biz_date: str, timeout: float) -> Dict[str, object]:
    payload = json.dumps({"date": biz_date}).encode("utf-8")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "phoenix-liaoning-spot-price-fetcher/1.0",
    }
    last_error: Optional[Exception] = None

    for attempt in range(2):
        req = request.Request(
            GET_LIST_DATA_URL,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                status_code = getattr(response, "status", None) or response.getcode()
                raw_body = response.read().decode("utf-8")
                if status_code == 429:
                    if attempt == 0:
                        time.sleep(20)
                        continue
                    raise LiaoningSpotPriceFetchError(f"{biz_date} 请求被限流，状态码 429")
                if status_code >= 500:
                    if attempt == 0:
                        time.sleep(2)
                        continue
                    raise LiaoningSpotPriceFetchError(
                        f"{biz_date} 服务端异常，状态码 {status_code}"
                    )
                return json.loads(raw_body)
        except error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt == 0:
                time.sleep(20)
                continue
            if exc.code >= 500 and attempt == 0:
                time.sleep(2)
                continue
            break
        except (error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2)
                continue
            break

    raise LiaoningSpotPriceFetchError(f"{biz_date} 抓取失败：{last_error}") from last_error


def _normalize_day_payload(biz_date: str, payload: Dict[str, object]) -> DailySpotPrice:
    if payload.get("CODE") != "200":
        raise LiaoningSpotPriceFetchError(
            f"{biz_date} 接口返回异常：CODE={payload.get('CODE')} MESSAGE={payload.get('MESSAGE')}"
        )

    raw_rows = payload.get("data")
    if not isinstance(raw_rows, list):
        raise LiaoningSpotPriceFetchError(f"{biz_date} 接口 data 结构异常，预期为 list")

    points: List[SpotPricePoint] = []
    non_empty_value_count = 0

    for row_index, row in enumerate(raw_rows, start=1):
        if not isinstance(row, dict):
            raise LiaoningSpotPriceFetchError(f"{biz_date} 第 {row_index} 行结构异常，预期为 dict")

        for group_index in range(1, 5):
            time_label = str(row.get(f"name{group_index}", "")).strip()
            before_price = str(row.get(f"beforeTime{group_index}", "")).strip()
            real_time_price = str(row.get(f"realTime{group_index}", "")).strip()

            if not time_label:
                raise LiaoningSpotPriceFetchError(
                    f"{biz_date} 第 {row_index} 行第 {group_index} 组缺少时刻字段"
                )

            if before_price:
                non_empty_value_count += 1
            if real_time_price:
                non_empty_value_count += 1

            points.append(
                SpotPricePoint(
                    time_label=time_label,
                    before_price=before_price,
                    real_time_price=real_time_price,
                )
            )

    return DailySpotPrice(
        biz_date=biz_date,
        published=non_empty_value_count > 0,
        total_points=len(points),
        non_empty_value_count=non_empty_value_count,
        points=sorted(points, key=lambda item: _time_sort_key(item.time_label)),
    )


def fetch_spot_prices(
    start_date: date,
    end_date: date,
    include_empty_days: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    pause_seconds: float = 0.0,
) -> Dict[str, object]:
    """
    抓取辽宁省发改委现货电价数据。

    - 默认过滤全空日；
    - 返回值同时保留摘要与逐日明细，便于落库或二次处理。
    - JSON 采用按天分组结构，避免在每个点位重复写 `biz_date`。
    """

    if end_date < start_date:
        raise LiaoningSpotPriceFetchError("结束日期不能早于开始日期")

    dates = _iter_dates(start_date, end_date)
    daily_results: List[DailySpotPrice] = []

    for current_date in dates:
        biz_date = current_date.isoformat()
        payload = _request_with_retry(biz_date, timeout)
        daily_result = _normalize_day_payload(biz_date, payload)
        if include_empty_days or daily_result.published:
            daily_results.append(daily_result)
        if pause_seconds > 0:
            time.sleep(pause_seconds)

    return {
        "source": {
            "provider": "liaoning-development-and-reform-commission",
            "page_url": "https://fgw.ln.gov.cn/fgw/xxgk/xhdj/index.shtml",
            "data_url": "https://fgw.ln.gov.cn/indexview",
            "api_url": GET_LIST_DATA_URL,
        },
        "query": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "include_empty_days": include_empty_days,
            "timeout": timeout,
            "pause_seconds": pause_seconds,
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
        },
        "summary": {
            "requested_days": len(dates),
            "returned_days": len(daily_results),
            "published_days": sum(1 for day in daily_results if day.published),
            "empty_days": sum(1 for day in daily_results if not day.published),
            "total_points": sum(day.total_points for day in daily_results),
        },
        "days": [
            {
                "biz_date": day.biz_date,
                "published": day.published,
                "total_points": day.total_points,
                "non_empty_value_count": day.non_empty_value_count,
                "points": [asdict(point) for point in day.points],
            }
            for day in daily_results
        ],
    }


def _write_json(output_path: Path, payload: Dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_csv(output_path: Path, payload: Dict[str, object]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["biz_date", "time_label", "before_price", "real_time_price"],
        )
        writer.writeheader()
        days = payload.get("days")
        if not isinstance(days, list):
            raise LiaoningSpotPriceFetchError("导出 CSV 失败：days 结构异常")
        for day in days:
            if not isinstance(day, dict):
                continue
            biz_date = str(day.get("biz_date", "")).strip()
            points = day.get("points")
            if not isinstance(points, list):
                continue
            for point in points:
                if not isinstance(point, dict):
                    continue
                writer.writerow(
                    {
                        "biz_date": biz_date,
                        "time_label": point.get("time_label", ""),
                        "before_price": point.get("before_price", ""),
                        "real_time_price": point.get("real_time_price", ""),
                    }
                )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓取辽宁省发改委现货电价 getListData 数据。",
    )
    parser.add_argument(
        "--start-date",
        type=_parse_iso_date,
        default=DEFAULT_START_DATE,
        help="开始日期，格式 YYYY-MM-DD，默认 2026-01-01",
    )
    parser.add_argument(
        "--end-date",
        type=_parse_iso_date,
        default=DEFAULT_END_DATE,
        help="结束日期，格式 YYYY-MM-DD，默认 2026-03-08",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=DEFAULT_OUTPUT_JSON,
        help="输出 JSON 文件路径，默认写入 backend_data/liaoning_spot_price_2026-01-01_2026-03-08.json",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        help="输出 CSV 文件路径",
    )
    parser.add_argument(
        "--include-empty-days",
        action="store_true",
        help="包含全空占位日；默认仅保留已发布的有效日期",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="HTTP 超时时间（秒），默认 20",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.0,
        help="每个日期请求后的停顿秒数，默认 0",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        payload = fetch_spot_prices(
            start_date=args.start_date,
            end_date=args.end_date,
            include_empty_days=args.include_empty_days,
            timeout=args.timeout,
            pause_seconds=args.pause_seconds,
        )
    except LiaoningSpotPriceFetchError as exc:
        print(f"抓取失败：{exc}")
        return 1

    if args.output_json:
        _write_json(args.output_json, payload)
        print(f"已输出 JSON：{args.output_json}")

    if args.output_csv:
        _write_csv(args.output_csv, payload)
        print(f"已输出 CSV：{args.output_csv}")

    summary = payload["summary"]
    query = payload["query"]
    print(
        "抓取完成："
        f"请求 {summary['requested_days']} 天，"
        f"返回 {summary['returned_days']} 天，"
        f"有效发布 {summary['published_days']} 天，"
        f"全空日 {summary['empty_days']} 天。"
    )
    print(
        f"时间范围：{query['start_date']} 至 {query['end_date']}，"
        f"包含空日：{query['include_empty_days']}。"
    )
    if args.output_json:
        print("默认执行会生成整合后的单个 JSON 文件，可直接用于后续导入或分析。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
