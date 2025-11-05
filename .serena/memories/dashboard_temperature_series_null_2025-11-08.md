## 2025-11-08 气温序列缺测处理
- 背景：/dashboard 气温模块平均值偏低，原因是 `_fetch_temperature_series` 对缺失小时默认填 0，导致前端算术平均被拉低。
- 变更：`backend/services/dashboard_expression.py` 现在对缺失小时返回 `None`；前端 `calcAverageFromList` 仅统计真实 `number`，并维持两位小数显示。
- 效果：push_date 当日的平均温度与手工计算一致，缺测数据不会误判为 0℃，图表和卡片展示更准确。