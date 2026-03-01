时间：2026-03-01
需求：业务月份止默认也为上个月。
实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- loadOptions()：新增 previousMonth 变量，dateMonthFrom/dateMonthTo 均设为 previousMonth
- resetFilters()：起止月份重置均为 previousMonth
结果：页面首次进入与重置后，业务月份起止都默认上个月（例如 2026-03 当月时默认 2026-02）。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。