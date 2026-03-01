时间戳：2026-03-01
任务：查询结果隐藏period/type，月份按钮横向排列，起始月份默认上个月。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 查询结果表：移除 period/type 两列。
- 导出“查询结果”sheet：同步移除“期间/类型”列。
- 月份控件：month-input-wrap 横向排列并允许换行，去除小屏纵向堆叠规则。
- 默认值：loadOptions/resetFilters 中 dateMonthFrom 设为上个月。

结果：
- 查询结果更精简；月份筛选更易操作；起始月份默认符合“上个月”要求。