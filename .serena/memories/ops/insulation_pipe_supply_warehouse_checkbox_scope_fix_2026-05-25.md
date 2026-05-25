时间：2026-05-25
任务：修正 `insulation_pipe_supply_2026` 库管页多选交互，使复选框只出现在 `pending_warehouse`（已接收待库管）记录前。

本轮修改：
- 文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- 调整内容：
  - 台账首列复选框改为 `v-if="row.status === 'pending_warehouse'"`
  - 非 `pending_warehouse` 记录显示占位符 `—`
- 目的：避免对不可执行库管确认的记录展示可误解为“可选中批量确认”的复选框。

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
