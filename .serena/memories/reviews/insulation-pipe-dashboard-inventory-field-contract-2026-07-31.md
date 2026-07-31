# 保温管全局看板库存为零根因：接口字段契约错配

日期：2026-07-31（Asia/Hong_Kong）；只读，无源码或数据改动。

## 已证实根因
- 当前 `GET /supply-management/demand-summary` 的 rows 返回字段为 `section_1_inventory_qty`（`workspace.py:990`），后端 metrics 也以该字段计算 `totalInv`（`:1030`），实际运行汇总返回 `totalInv=10.0`。
- `DashboardView.vue` 的顶部 KPI、透视表和图表全都读取 `row.station_inventory_qty`（例如 `:1028`）。该字段在当前汇总 rows 中不存在，JS 的 `undefined || 0` 因此变成 0。
- 同一个页面的 DOI 指标弹窗读取 `backendMetrics.totalInv`，所以会得到正确库存 10；顶部库存卡却显示 0，形成同页面自相矛盾。

## 影响
字段命名由旧的 `station_inventory_qty` 与当前的 `section_1_inventory_qty` 发生不兼容替换，造成顶部库存、透视表库存列、导出库存列、型号库存柱状图均为 0；后端业务计算与权限、HTTP 200 均正常。
