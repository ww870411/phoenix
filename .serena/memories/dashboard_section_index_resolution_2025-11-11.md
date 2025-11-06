# 数据看板段名序号化解析（2025-11-11）

- **背景**：`backend_data/数据结构_数据看板.json` 中“6.当日省市平台投诉量”改名后，原本写死段名的后端/前端逻辑无法匹配，展示卡片数据丢失。
- **后端**：`services/dashboard_expression.py` 新增 `_build_section_index_map` 与 `get_section_by_index`，`evaluate_dashboard` 按段落编号（`1.`~`8.`）检索各模块，投诉板块继续复用 `_fill_complaint_section`；段名可自由调整但需保留编号。
- **前端**：`DashBoard.vue` 引入 `sectionIndexMap`/`resolveSection`，所有 `dashboardData.sections[...]` 调用改为序号解析；投诉卡片的排序与标题映射同时兼容“省市平台投诉量/服务投诉量”等命名。
- **验证建议**：修改配置段名后刷新 `/dashboard` 接口与仪表盘页面，应仍能看到投诉、边际利润等数据；如移除编号则需补充新的匹配策略。