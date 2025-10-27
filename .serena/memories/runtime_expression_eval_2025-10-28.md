新增运行时表达式求值模块 backend/services/expression_eval.py：
- 目标：按 configs/字典样例.json 的单表对象执行表达式/函数求值，替代二级 MV 的使用场景；
- 能力：value_* / sum_* 口径函数、date|month|ytd_diff_rate 差异率、四则运算与括号、c.<中文常量名> 引用（常量 period 规范化）、同列行间引用；
- 单位换算：除售电单价外，数量×单价统一 /10000 → 万元（与 calc_fill 保持一致）；
- 预取：批量预取涉及项目的各口径值 + 一次性读取常量；
- 输出：返回“数据已填满”的同结构对象；trace=True 输出 _trace.cells 供排障；
- 文档：backend/README.md、frontend/README.md 与 configs/progress.md 已补充说明；
- 回滚：删除 expression_eval.py 并移除 README 对应段落即可；不影响现有 API 与前端结构。