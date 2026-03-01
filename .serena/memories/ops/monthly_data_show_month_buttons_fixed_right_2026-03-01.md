时间戳：2026-03-01
任务：将日期快捷按钮固定在日期选框右侧。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- month-input-wrap: flex-wrap 改为 nowrap。
- month-quick-actions: flex-wrap 改为 nowrap，新增 margin-left:auto。

结果：
- 日期输入与快捷按钮固定同一行，按钮在右侧显示。