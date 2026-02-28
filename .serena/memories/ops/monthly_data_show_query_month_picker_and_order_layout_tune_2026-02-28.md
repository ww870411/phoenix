时间：2026-02-28
反馈：查询页过于紧凑；希望日历按月选择，并先选业务日期再选来源月份。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 时间筛选改为 month picker：业务月份起/止、来源月份起/止。
- 展示顺序改为业务优先、来源其次。
- 前端将 YYYY-MM 转换为查询所需日期范围：from=月初、to=月末。
- 布局从过紧回调到适中：列宽170->190，列表/分段高度与间距上调。
结果：
- 筛选交互符合“先业务后来源”的按月筛选诉求，页面密度更均衡。