时间：2026-02-28
主题：异常清单细化 + 累计表达式支持 + 空源单元格异常

需求：
1) 异常清单标题固定显示“异常清单”；
2) 源键/目标键显示去括号简写；
3) 累计源表达式（如 H30+H62）可计算；
4) 源单元格为空纳入异常。

改动文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) backend/projects/monthly_data_pull/services/engine.py
3) configs/progress.md
4) frontend/README.md
5) backend/README.md

实现摘要：
- 前端：
  - 异常清单标题改为固定“异常清单”；
  - 异常表源键/目标键通过 normalizeReferenceName 去括号展示；
  - 异常筛选新增 warn_source_empty / warn_month_expr_invalid / warn_acc_expr_invalid。
- 后端：
  - src_acc 支持表达式求值（非单坐标走 _evaluate_expr）；
  - 新增 _extract_cell_refs / _collect_empty_refs 空源单元格检测；
  - 空源引用写入 empty_source_refs_month/acc 并标记 warn_source_empty；
  - 无效表达式标记 warn_month_expr_invalid / warn_acc_expr_invalid。

结果：
- “H30+H62 is not a valid coordinate”问题被消除；
- 源空单元格将进入异常清单。