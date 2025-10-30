# 2025-10-30 运行时表达式跨公司常量支持
- 痛点：审批/展示模板中的 `万平方米省市净投诉量` 需要 `c.GongRe.挂网面积` 等跨 company 常量；旧版求值仅从当前 company 常量缓存读取，导致分母为 0。
- 改动：
  - `render_spec` 解析 `单位标识`、表达式中的 `c.<company>.<常量>`，预取对应 company 的常量缓存。
  - `Evaluator._value_of_const` 若命中 `.<company>.` 语法，则从全局常量缓存读取指定 company 的值，并兼容中文公司名。
- 佐证：重新执行 `render_spec(..., trace=True)` 更新 `configs/10.30trace.md`，`used_consts` 中 `GongRe.挂网面积` 返回 183.2000/229.0000 等实际数值。
- 受影响文件：`backend/services/runtime_expression.py`、`configs/10.30trace.md`、`backend_data/数据结构_全口径展示表.json`、`config/progress.md`、`backend/README.md`。