# 2025-12-11 数据分析默认选项优化
- 位置：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue
- 目的：满足“平均气温默认勾选、单位默认空选”的交互要求，并让趋势图/简报始终具备温度参照。
- 方案：
  1. 通过 `getTemperatureWeight` + `findDefaultTemperatureKeys`（遍历 metric_groups/metric_options/metric_dict）为温度指标打分，优先 `平均气温/平均温度`，其次“平均+气温/温度”，最后才回退其它温度项；`temperatureMetricKey` 与初始化逻辑都按新排序取首个候选。
  2. `loadSchema` 与 `resetSelections` 不再自动填充单位数组，`selectedUnits/activeUnit` 初值均为空，用户需显式勾选单位后才能运行分析。
  3. “重置”与首屏默认仅勾选首个温度指标，其它指标保持未选，表单校验沿用既有提示。
- 影响：仅前端逻辑/README/progress 发生变化，后端 API/Schema 无需改动。