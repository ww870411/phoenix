时间：2026-03-01
问题：前端 SFC 编译报错 `Identifier 'current' has already been declared`。
原因：itemSections 计算属性里存在重复 `const current` 声明。
处理：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 删除早期无效的 `const current = []`，保留后续有效声明。
结果：重复声明错误消除，页面可继续编译。