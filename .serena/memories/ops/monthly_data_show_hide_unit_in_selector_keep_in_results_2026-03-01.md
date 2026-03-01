时间：2026-03-01
需求：指标选择区域不显示计量单位，单位仅用于查询结果表格与简要分析。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 移除指标选择区域（基本分组/计算分组）中的 unit-tag 渲染；
- 删除 itemUnitMap 计算属性；
- 删除 .unit-tag 样式。
2) configs/progress.md
- 追加本次变更记录。
3) frontend/README.md
- 追加结构同步：指标选区隐藏计量单位。
4) backend/README.md
- 追加联动说明：后端单位下发保持不变。
结果：前端选区仅展示指标名；单位配置仍保留并继续在查询结果与分析链路中使用。