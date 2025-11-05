# 2025-11-09 单耗板块双期对比
- 时间：2025-11-09
- 变更文件：
  - `frontend/src/daily_report_25_26/pages/DashBoard.vue`
  - `configs/progress.md`
  - `frontend/README.md`
  - `backend/README.md`
- 摘要：单耗板块改为读取 `/dashboard` “4.供暖单耗”节点，新增 `unitSection`/`unitSeries` 计算属性并动态生成热/电/水单耗的本期与同期双柱图，tooltip/标签带上 `计量单位` 信息；保留 fallback 数据以防接口缺失。
- 验证：单耗图例包含“热/电/水单耗（本期/同期）”，柱顶标签显示两位小数并随业务日期更新，tooltip 展示对应单位。