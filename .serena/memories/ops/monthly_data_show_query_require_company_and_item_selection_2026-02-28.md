时间：2026-02-28
需求：口径或指标未选择时不能点击查询。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) backend/projects/monthly_data_show/api/workspace.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 前端查询按钮禁用条件扩展为 companies/items/periods/types 任一为空即禁用。
- 提示文案同步更新为“四项均需至少各选1项”。
- 后端查询接口增加对应保护，任一为空返回空结果。
结果：
- 口径为空或指标为空均无法触发查询。