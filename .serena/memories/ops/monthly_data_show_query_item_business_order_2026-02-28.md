时间：2026-02-28
需求：指标排序按业务逻辑重排（19个计算指标后置，基本+半计算前置，产量/销售量/消耗量/其他顺序，相似指标总在前）。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 前端新增 CALCULATED_ITEM_SET（19个计算指标）。
- 新增指标排序函数，排序键为：
  1) 是否计算指标（基础/半计算前，计算后）
  2) 主分组（产量->销售量->消耗量->其他）
  3) 消耗量子分组（煤->油->水->电->气->其他）
  4) 相似名“总”优先
  5) 原始顺序兜底
结果：
- 指标勾选列表已按业务导向排序，符合用户描述。