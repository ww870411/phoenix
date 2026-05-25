# 2026-05-25 insulation_pipe_supply_2026 库管页零值数量显示为横杠

## 背景
用户要求库管页台账中的“到货量”“接收量”在值为 0 时显示为横杠，而不是数字 0。

## 实施
文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`

- 表格列：
  - `arrived_qty` 从 `formatAmount(...)` 改为 `formatOptionalAmount(...)`
  - `received_qty` 从 `formatAmount(...)` 改为 `formatOptionalAmount(...)`
- 新增函数 `formatOptionalAmount(value)`：
  - 非法数值或 `0` => `—`
  - 正数 => 沿用原有数字格式

## 结果
- 库管页列表中的零值到货量、接收量不再显示为 `0`，而是显示为 `—`。
- 本轮仅调整前端显示口径，不影响后端真实数据与接口返回值。