日期：2026-02-08
主题：项目模块化第十四步（全局项目选择页剥离）

改动：
1) 页面迁移
- frontend/src/daily_report_25_26/pages/ProjectSelectView.vue
-> frontend/src/pages/ProjectSelectView.vue

2) 依赖路径修正
- 新文件中 theme/components/composables 改为引用 ../daily_report_25_26/... 路径。

3) 路由更新
- frontend/src/router/index.js
- /projects 组件改为 import('../pages/ProjectSelectView.vue')

结果：
- /projects 页面归属从“项目目录”修复为“全局目录”；
- 功能与路径保持一致，无需后端或接口变更。