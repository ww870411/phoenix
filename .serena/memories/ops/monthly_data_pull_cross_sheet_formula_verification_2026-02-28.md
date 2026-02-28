时间：2026-02-28
主题：累计公式核验增强为支持跨子工作表引用
触发：用户确认实际存在跨 sheet 公式，要求实现。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

实现摘要：
- 表达式解析新增 SHEET_CELL_REF_PATTERN，支持：
  - Sheet!H30
  - 'Sheet Name'!H30
- _evaluate_expr 增加 workbook 上下文，可替换跨 sheet 引用并求值。
- _extract_cell_refs/_collect_empty_refs 同步支持跨 sheet 引用，空源单元格检测覆盖跨 sheet。
- 月值/累计表达式及目标累计公式核验均接入跨 sheet 解析。

结果：
- 跨子工作表引用可参与累计一致性核验；
- 超出当前解析能力的函数/复杂公式仍会标记 formula_not_verifiable。