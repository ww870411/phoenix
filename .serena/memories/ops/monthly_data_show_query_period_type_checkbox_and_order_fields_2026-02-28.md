时间：2026-02-28
需求：期间/类型改为勾选并有顺序数字；数据层次顺序改为“口径/指标/期间/类型”有序勾选。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) backend/projects/monthly_data_show/api/workspace.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 前端：
  - 期间/类型从多选下拉改为复选列表（全选/全不选 + 顺序数字徽标）。
  - 新增层次顺序勾选区（company/item/period/type）与默认重置。
  - 查询 payload 新增 order_fields。
- 后端：
  - QueryRequest 新增 order_fields。
  - 按白名单动态拼接排序字段，聚合模式自动忽略 company。
结果：
- 筛选体验统一为勾选式，展示层次可由有序勾选精细控制且后端真实生效。