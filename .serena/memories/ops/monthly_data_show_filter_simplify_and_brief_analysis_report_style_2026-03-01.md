时间戳：2026-03-01
任务：去除查询筛选中的来源月份起止，并将“专业分析要点”改写为报告式“简要分析”。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 筛选区：移除“来源月份起/来源月份止”输入。
- 数据结构：filters 移除 reportMonthFrom/reportMonthTo。
- 请求构造：report_month_from/report_month_to 固定为 null。
- 分析区：标题由“专业分析要点”改为“简要分析”。
- 文案重写：analysisInsights 改为“ 一、二、三...”的报告式顺序表达，避免“分组1（口径=...）”技术描述。

结果：
- 页面筛选区更简洁；
- 分析文案更符合业务汇报场景。