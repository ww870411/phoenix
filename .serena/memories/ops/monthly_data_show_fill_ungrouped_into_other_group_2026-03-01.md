时间：2026-03-01
需求：将页面未分组但配置未覆盖的指标，补入配置文件【其他指标】分组。
处理：
- 读取配置：backend_data/projects/monthly_data_show/indicator_config.json
- 参考 month_data_show 指标全集（通过 phoenix_backend 容器查询）
- 将缺失项追加至 basic_groups -> 【其他指标】 -> items
结果：配置覆盖更多基础指标，页面未分组项减少。
留痕：已更新 configs/progress.md、frontend/README.md、backend/README.md。