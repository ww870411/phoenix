## 2025-11-06 DashBoard 页面样式与依赖补齐
- 降级原因：Serena 暂不支持 `.vue`/`.js` 文件符号级编辑，使用 `apply_patch` 更新 `DashBoard.vue` 样式与 `main.js` 组件注册。
- 主要改动：
  - `DashBoard.vue` 替换 Tailwind 类名为自定义样式类并内联 CSS，复现设计稿配色、阴影与网格布局；表格/卡片组件同步调整。
  - `main.js` 引入 `vue-echarts` 与 `echarts`，注册 `<v-chart>` 并预加载折线、柱状图所需组件；提示执行 `npm install vue-echarts echarts`。
  - `PageSelectView.vue` 及路由先前改动保持生效，使“数据看板”卡片直达仪表盘。
- 回滚思路：恢复上述文件至 2025-11-06 前版本并卸载新增依赖即可还原旧页面。