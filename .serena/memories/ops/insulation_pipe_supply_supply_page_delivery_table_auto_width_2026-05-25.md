# 2026-05-25 insulation_pipe_supply_2026 供给页发货记录表自动宽度分配优化

## 背景
用户反馈供给页发货记录表中“状态”和“备注”部分内容出现挤压重叠，并询问是否可以根据内容自动适应宽度。

## 结论
可以做“有限自动适应”，但不宜完全放任浏览器自由分列，否则 14 列台账会重新失衡。当前采用的是：
- 表格改为 `table-layout: auto`
- 关键列保留 `min-width`
- `状态 / 备注 / 操作` 允许在剩余空间中更自然伸缩

## 实施文件
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

## 具体调整
- `delivery-record-table` 从固定布局改为自动布局。
- 订单号、车次号、车牌号、数量、时间等列增加 `min-width`，避免被过度压缩。
- `状态` 列最小宽度提高到 `180px`。
- `备注` 列改为 `width: auto` 且 `min-width: 240px`。
- `操作` 列最小宽度提高到 `170px`。
- 状态单元格继续单行展示，避免标签自身换行。

## 结果
- 表格列宽不再是完全死板的固定分配。
- 当前更接近“按内容自适应，但受底线约束”的排版方式。
- 后端接口和业务逻辑不受影响。