时间：2026-02-12
需求：清理“项目模块化管理”板块。
前端改动：
1) PageSelectView.vue 移除模块化管理卡片与 openModularization 逻辑。
2) router/index.js 移除 /projects/:projectKey/modularization 路由。
3) services/api.js 删除 getProjectModularizationStatus/ bootstrapProjectModularization。
4) 删除 pages/ProjectModularizationView.vue。
后端改动：
1) backend/projects/daily_report_25_26/api/router.py 移除 modularization_router 挂载。
2) 删除 backend/projects/daily_report_25_26/api/modularization.py。
验证：frontend npm run build 通过；python -m py_compile backend/projects/daily_report_25_26/api/router.py backend/api/v1/routes.py 通过。
说明：保留 backend/api/v1/routes.py 的通用 modularization 接口（无前端入口，不影响当前页面）。