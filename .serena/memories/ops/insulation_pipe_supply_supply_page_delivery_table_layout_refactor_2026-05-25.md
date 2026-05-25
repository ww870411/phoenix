# 2026-05-25 insulation_pipe_supply_2026 供给页发货记录表排版重组

## 背景
用户反馈 `SupplyManagementView.vue` 中“发货记录”板块表格排版混乱，横向列数过多，阅读不顺。

## 实施
本轮仅调整前端模板与样式，不改后端接口和业务逻辑。

### 文件
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

### 具体调整
- 原 14 列平铺改为 8 列分组：
  - `单号/车次`
  - `供给去向`
  - `型号`
  - `数量`
  - `发货/时效`
  - `状态`
  - `备注`
  - `操作`
- 将 `订单号 / 运输车次号 / 车牌号` 合并为同一信息块。
- 将 `供给主体 / 换热站` 合并展示。
- 将 `发货量 / 到货量 / 接收量` 改为纵向指标堆叠，减少横向跳读。
- 将 `发货时间 / 在途时长` 合并展示。
- 将“继续该车次 / 撤销发货”改为纵向按钮栈，避免按钮挤压备注和状态列。
- 增加专属样式类：`delivery-record-table`、`cell-stack`、`metric-stack`、`action-stack` 等。

## 结果
- 发货记录表在不改业务口径的前提下，阅读路径从“横向扫很多列”改为“按信息组块纵向浏览”。
- 当前仅是界面结构优化，不影响 `shipment_no` 复用、撤销发货、数量差异显示等现有逻辑。

## 备注
- 本轮未做自动构建验证；此前统一执行器存在启动失败问题，因此当前以静态代码核对为主。