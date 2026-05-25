# 2026-05-25 insulation_pipe_supply_2026 供给页发货记录状态/操作列单行横排

## 背景
用户要求供给页发货记录表中“状态”“操作”两个字段内的内容放在同一行左右安放，不要在单元格内换行堆叠。

## 实施
文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`

- `status-chip-group`
  - `flex-wrap: wrap` 改为 `flex-wrap: nowrap`
  - 增加 `white-space: nowrap`
- `action-stack`
  - `flex-direction: column` 改为 `row`
  - `align-items` 改为 `center`
  - 增加 `flex-wrap: nowrap`

## 结果
- 状态标签在单元格内保持单行横向排列。
- 操作按钮与“不可撤销”提示在单元格内保持单行横向排列。
- 本轮仅为前端样式收口，不涉及后端接口与业务逻辑。