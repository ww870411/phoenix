时间：2026-02-28
主题：研究院多 sheet 自动匹配完善 + 累计值对照日志落地

需求：
1) 研究院源文件有三个有效子工作表，默认映射不应全指向第一张；
2) 累计值对照功能确认与实现。

改动文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) backend/projects/monthly_data_pull/services/engine.py
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

实现摘要：
- 前端：新增 pickBestSheetName(ruleSheet, actualSheets)，对规则 sheet 与实际 sheet 做归一化匹配（完全/包含），作为默认映射。
- 后端：累计处理增加对照日志字段：acc_compare_status、acc_compare_diff、tgt_acc_before；并在 execution_log 增加 acc_compare_stats 汇总。
- 状态语义：ok / mismatch / skipped_target_formula / non_numeric。

结果：
- 多 sheet 的默认匹配更准确，不再全选第一张；
- 累计值对照能力已可在 execution_log_*.json 中逐行与汇总查看。