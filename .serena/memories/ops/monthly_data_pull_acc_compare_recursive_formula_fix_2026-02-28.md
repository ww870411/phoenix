时间：2026-02-28
主题：累计一致性核验再修复（递归公式求值）
触发：用户复现 26.2 累计应翻倍但未检出 mismatch。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

根因：
- 目标累计公式引用的单元格中仍含公式时，旧逻辑将二级公式按 0 处理，导致比对失真。

实现摘要：
- _cell_value_as_number 增加递归公式求值；
- _evaluate_expr/_sheet_value_by_name 传递 workbook 上下文 + 递归状态；
- 增加递归深度限制与循环引用保护。

结果：
- 链式公式（公式引用公式）可展开计算；
- 26.2 这类累计翻倍场景可正确落为 acc_compare_status=mismatch 并进入异常清单。