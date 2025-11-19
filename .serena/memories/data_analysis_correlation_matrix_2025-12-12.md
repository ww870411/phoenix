# 2025-12-12 数据简报相关矩阵
- 位置：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue
- 变更：`correlationMatrixState` 对所有勾选且含逐日数据的指标构建皮尔逊相关矩阵，Matrix 结果显示在“数据简报”卡片中；摘要内的【相关性】段落也依据此状态提示“矩阵已生成/样本不足”。
- 特性：
  1. 指标两两对照，与“平均气温”无绑定要求；正/负/缺失通过不同颜色在矩阵单元格呈现。
  2. 若仅部分指标具备逐日数据或不同指标缺少共同日期，矩阵底部与摘要中会提示具体原因。
  3. 当无法生成矩阵时，摘要显示“请选择至少两个指标/样本不足”的提醒，维持用户引导。
- 文档：frontend/README.md、backend/README.md、configs/progress.md 均已更新说明。