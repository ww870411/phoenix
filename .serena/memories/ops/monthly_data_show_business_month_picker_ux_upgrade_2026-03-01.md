时间戳：2026-03-01
任务：优化“业务月份起/止”日期选框的美观度与操作便利性。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 业务月份输入区视觉优化：卡片化、统一尺寸、聚焦高亮。
- 快捷操作：
  - 起月：本月、上月
  - 止月：本月、同起月
  - 快捷区间：近3/6/12个月、本年
- 新增范围顺序保护：起月晚于止月时自动修正。
- 移动端适配：月份输入与快捷按钮在窄屏自动换行。

结果：
- 日期筛选更易操作，常用时间范围一键可达，视觉统一性提升。