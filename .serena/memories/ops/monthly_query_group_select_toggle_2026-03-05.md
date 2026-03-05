时间：2026-03-05
需求：在 monthly_data_show 查询页“指标（可多选）”中，为每个分类（如主要产销指标、主要消耗指标）增加“全选/取消”按钮，且仅控制本分类。

实现：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
1) 模板层：
- 每个 basic-group 标题右侧新增“全选/取消”按钮。
2) 逻辑层：
- 新增函数 toggleGroupItems(groupItems, checked)
  - checked=true：仅将该分组指标追加为选中，不影响其他分组
  - checked=false：仅取消该分组指标，不影响其他分组
3) 样式层：
- 新增 basic-group-title-row、basic-group-actions 布局样式。

验证：
- frontend 执行 npm run build 通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md