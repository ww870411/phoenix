时间：2026-02-28
需求：指标选择区改为“当前指标 -> 常量指标 -> 计算指标”三栏分段。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现：
- 指标列表改为三段 sections 渲染：current/constant/calculated。
- 常量指标集合：发电设备容量、锅炉设备容量，并按固定顺序展示。
- 计算指标集合使用固定顺序清单。
- 各段保留勾选与顺序数字徽标显示。
结果：
- 指标区层次更清晰，常量与计算指标不再“混在列表里不明显”。