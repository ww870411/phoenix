时间：2026-03-01
需求：移除月份区域“快捷区间”。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 删除模板中的快捷区间块（近3/6/12个月、本年）
- 删除方法 setBusinessMonthRangeRecent / setBusinessMonthRangeCurrentYear
- 删除 month-preset-field / month-presets 相关样式与媒体查询样式
结果：月份筛选区仅保留业务月份起止输入框，更简洁且无挤压。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。