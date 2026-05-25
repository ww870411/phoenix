# 2026-05-25 insulation_pipe_supply_2026 数量差异文案细化与发货页数量显示修复

## 背景
用户要求把数量差异异常说得更具体，并反馈供给侧发货页没有正确显示到货量、接收量。

## 结论
- 供给侧发货页数量未正确显示的直接原因在前端 `SupplyManagementView.vue`：表格使用 `arrivedQty / receivedQty`，但历史数据映射未把接口返回的 `arrived_qty / received_qty` 转为对应前端字段。
- 当前已收口为：
  - 发货页正确显示 `到货量 / 接收量`
  - 差异异常按类型显示，不再统一写“异常”
    - `arrived_qty < shipped_qty` => `少到货`
    - `received_qty < arrived_qty` => `少接收`

## 变更文件
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
  - 补齐 `arrivedQty`、`receivedQty` 映射
  - 新增 `formatNullableNumber`
  - 状态旁异常文案改为 `getAbnormalLabel(row)`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
  - 状态旁异常文案改为 `getAbnormalLabel(row)`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
  - 状态旁异常文案改为 `getAbnormalLabel(row)`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

## 业务口径
- 状态机仍只表示流程阶段，不新增“异常状态”
- 数量差异继续用 `abnormal_flag` 承载
- 页面文案层只负责把异常类型显式化，便于一线判断问题发生在“到货”还是“接收”阶段

## 备注
- 本轮未新增后端字段或状态值。
- 自动验证命令再次遇到本地统一执行进程启动失败（非代码业务报错），因此本轮以代码静态核对和最小片段检视为主。