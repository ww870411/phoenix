时间：2026-05-25
任务：重构 `insulation_pipe_supply_2026` 库管页“选中记录处置”区域，使其从单条详情残留样式改为面向多选批量确认的汇总面板。

本轮修改：
- 文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- 原问题：
  - 处置区仍展示“首条供给主体 / 首条型号 / 首条状态”等单条详情字段
  - 与当前多选批量确认交互不匹配，信息价值低且易误导
- 当前改造为汇总面板，聚合展示：
  - 已选记录数
  - 可批量确认数
  - 车次数、单号数、站点数、型号数
  - 总发货长度、总到货长度、总接收长度
  - 平均在途时长、最长在途时长
  - 状态分布
  - 型号清单、车次清单、车牌清单（压缩为前几项 + 总项数）
- 聚合逻辑全部在前端基于当前已选台账记录计算，本轮未新增后端汇总接口。

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
