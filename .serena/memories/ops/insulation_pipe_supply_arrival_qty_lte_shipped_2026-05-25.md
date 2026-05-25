时间：2026-05-25
任务：确认并收口 `insulation_pipe_supply_2026` 中“确认到货量不能大于发货量”的业务规则。

结论：
- 后端原本已经具备两层约束：
  1. 服务层 `update_delivery_arrival_record()`：拒绝 `arrived_qty > shipped_qty`
  2. 初始化 SQL `chk_tube_delivery_arrived_qty_range`：要求 `arrived_qty <= shipped_qty`
- 本轮新增前端收口，文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
  - 到货确认输入框增加 `max=发货量`
  - 提交前增加显式校验，若 `arrivalConfirmQty > shippedQty` 则直接提示并阻止提交

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

当前状态：
- 这条规则已经形成前端输入限制、前端提交拦截、后端服务校验、数据库约束四层一致口径。
