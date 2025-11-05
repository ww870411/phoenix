## 2025-11-08 仪表盘气温模块联调
- 背景：DashBoard.vue 仍使用静态温度数组，需要改为读取 `/dashboard` 的“1.逐小时气温”数据。
- 变更：增加 `temperatureSection`、`temperatureSeries` 计算属性，对本期/同期数据按日期排序并计算均值；`tempOpt`、`temperatureTableData`、`averageTemp` 改为依赖这些计算，卡片直接读取 `push_date` 对应的 24 小时列表求算术平均（两位小数），若缺失则显示“—”；图表与表格统一使用两位小数。
- 效果：切换 `show_date` 时气温折线图、表格及平均温度会随接口数据更新，展示结果与后端算法保持一致，为其他模块接入提供模板。