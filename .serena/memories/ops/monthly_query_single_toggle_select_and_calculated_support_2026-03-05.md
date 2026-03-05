时间：2026-03-05
需求：月报查询页把“全选/全不选”改为单按钮切换，同时让“计算指标”也加入该功能。

实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
1) 顶部按钮调整：
- 口径与指标两个区域的双按钮改为单按钮“全选/取消”切换。
2) 指标分类按钮：
- 在每个指标大类标题右侧新增单按钮“全选/取消”（含计算指标分类）。
3) 逻辑新增：
- areAllSelected
- allIndicatorItems（computed）
- isAllCompaniesSelected / isAllItemsSelected（computed）
- isSectionItemsAllSelected / toggleSectionItems
4) 保留能力：
- 基础指标分组级“全选/取消”按钮继续保留。

验证：
- frontend 执行 npm run build 通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md