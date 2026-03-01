时间戳：2026-03-01
任务：简要分析中若缺失上期值，省略整段环比描述。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 末级描述句由固定模板改为 segments 动态拼接。
- 当 row.momValue == null 时，不拼接“上期...环比...”段。
- 本期、同比、计划比段保持输出。

结果：
- 不再出现“上期—，环比0，差异率—”等无意义文案。