时间戳：2026-03-01
任务：若某指标本期/同期/上期/计划值全为0，则跳过该指标分析内容。

变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 简要分析新增 shouldSkipAnalysisRow(row)：四个值均为0时返回true。
- 末级描述行生成时跳过 shouldSkipAnalysisRow=true 的条目。
- 分层分组阶段同步过滤无有效数据分组，避免空标题。

结果：
- 全零指标不再输出分析内容，文本更聚焦。