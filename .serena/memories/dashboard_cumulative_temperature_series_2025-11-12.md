# 2025-11-12 数据看板累计卡片气温序列
- 位置：backend/services/dashboard_expression.py
- 新增 `_fetch_daily_average_temperature_map`，将 `calc_temperature_data` 区间内的日均气温补全为连续日期字典（缺口返回 None）。
- `_fill_cumulative_cards` 现将“供暖期平均气温”填写为 `[{"date": "YYYY-MM-DD", "value": <float|null>}, ...]`，同步生成同期序列；`_fetch_average_temperature_between` 改为基于该映射求整体均值。
- 其他累计指标（标煤耗量、可比煤价边际利润、省市平台投诉量）仍从 `groups` 视图读取 `sum_ytd_*` 字段。
- 前端 README 已提示新数据结构，后续接入折线/柱图时直接使用即可。