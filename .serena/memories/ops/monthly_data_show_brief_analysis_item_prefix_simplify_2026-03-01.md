时间戳：2026-03-01
任务：简要分析中去掉指标层“指标：”前缀，仅显示指标名。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 分层分析生成逻辑中，field==='item' 时输出 group.key；
- 非 item 层级仍保留“口径：”等前缀。

结果：
- 指标行从“指标：耗标煤总量”变为“耗标煤总量”，文案更简洁。