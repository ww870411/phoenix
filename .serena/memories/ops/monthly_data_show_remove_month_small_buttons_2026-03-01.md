时间：2026-03-01
问题：月份筛选行仍存在按钮压住日期选框的现象。
处理：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 移除月份小按钮：本月、上月、同起始月
- 删除对应方法：setBusinessMonthFromCurrent、setBusinessMonthFromPrevious、setBusinessMonthToCurrent、syncBusinessMonthToFrom
- 清理 month-quick-actions 样式，月份行改为纯输入框布局
结果：月份行空间更宽敞，日期选框不再被小按钮挤压。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。