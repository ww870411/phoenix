# 2025-10-30 运行时表达式帧函数参数修复
- 触发记录：`configs/10.30trace.md` 显示 `safe_expr` 生成 `value_biz_date("I("当日撤件后净投诉量"")")`，前端展示空值。
- 改动：`backend/services/runtime_expression.py::Evaluator._preprocess`
  - 项目名替换仍按非引号段执行；
  - 合并后新增 `frame_func_pattern`，一次性处理 `value_*/sum_*` 参数，支持 `I(...)` 含括号；
  - 多指标累加（`I()+I()`）拆分为多个 `value_*("指标")` 求和。
- 验证：临时脚本调用 `_preprocess`，确认 `value_biz_date(当日撤件后净投诉量)` → `value_biz_date("当日撤件后净投诉量")`。
- 文档：`configs/progress.md`、`backend/README.md`、`frontend/README.md` 已新增说明。