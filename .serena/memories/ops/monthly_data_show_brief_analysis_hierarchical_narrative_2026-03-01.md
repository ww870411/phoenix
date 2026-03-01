时间戳：2026-03-01
任务：将“简要分析”改为按层次顺序的逐项报告式叙述（非分组编号技术描述）。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 重写 analysisInsights：
  - 根据 filters.orderFields 动态构建层次（口径/指标/期间/类型）；
  - 逐层输出标题；
  - 在末级输出完整业务句式：
    本期、同期同比（增减+差值+差异率）、上期环比（增减+差值+差异率）、计划比（较计划增减+差值+差异率）。
- 保留风险提示与数据完整性总结，形成报告收尾。

结果：
- 分析区文本结构更接近真实分析报告，可按所选层次顺序阅读。