日期：2026-03-18
主题：展示页首屏剖析接入后 runtime 路由 404 回归修复

背景：在为 `daily_report_25_26` 展示页接入 `profile: true` 分段计时后，用户刷新页面时收到 `{"detail":"Not Found"}`。

根因：编辑 `backend/projects/daily_report_25_26/api/legacy_full.py` 的 `runtime_eval` 与 `runtime_eval_batch` 函数体时，函数上方的 `@router.post(...)` 装饰器被意外移除，导致函数存在但路由未注册。

修复：
1. 恢复 `runtime_eval` 装饰器：`@router.post("/runtime/spec/eval", ...)`
2. 恢复 `runtime_eval_batch` 装饰器：`@router.post("/runtime/spec/eval-batch", ...)`
3. 三份文档已同步补记本次回归与修复。

验证：
- `python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py backend/services/runtime_expression.py` 通过。

影响边界：
- 不改变任何计算逻辑，仅恢复后端路由注册。
- 前端请求路径无需变更。