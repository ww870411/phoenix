# 2025-11-19 Dashboard 净投诉量多窗口取值
- 背景：0.5 折叠表与 9 号累计卡片的“净投诉量”月累计/供暖期累计数据错误，需改为使用专门指标。
- 实施：
  1. `_build_group_summary_metrics` 引入 `SUMMARY_PERIOD_ITEM_OVERRIDES`，令“净投诉量”三列分别映射到“当日净投诉量 / 本月累计净投诉量 / 本供暖期累计净投诉量”。
  2. `_fill_cumulative_cards` 将“集团汇总净投诉量”改用 `sum_season_total_net_complaints` 并读 `value_biz_date/value_peer_date`，防止重复累计。
- 验证：调用 `/dashboard` 确认 `0.5` 节点“净投诉量（件）”三列与 9 号卡片的本期/同期数值均与数据库专用指标一致。