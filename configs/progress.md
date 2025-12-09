## 2025-12-09（仪表盘新增运行设备明细）

- **User Request:** 在数据看板页面增加“11.各单位运行设备数量明细表”展示板块。
- **Agent Action:**
  1. 读取 `backend_data/数据结构_数据看板.json` 理解数据结构。
  2. 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue`：
     - 新增 `deviceStatusSection` 等 computed 属性用于解析数据。
     - 在 Template 中添加 `Card` 和 `Table` 组件展示数据。
     - 添加 CSS 样式使该板块在桌面端全宽显示。
- **Result:** 数据看板现已包含“各单位运行设备数量明细表”板块，位于煤炭库存与趋势图之间。目前前端已就绪，等待后端 API 返回对应数据即可自动渲染。