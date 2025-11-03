## 2025-11-06 DashBoard 图表依赖调整
- 取消 npm 依赖 `vue-echarts/echarts`，避免安装失败；改为在 `frontend/index.html` 通过 CDN 注入 `echarts.min.js`。
- `DashBoard.vue` 定义本地 `EChart` 包装组件（使用 `window.echarts`）并维持卡片样式，路由跳转逻辑不变。
- 如需回滚，可移除 CDN 脚本并恢复旧版页面/路由；若未来切换至真实接口，可直接在 `EChart` 组件中调用。