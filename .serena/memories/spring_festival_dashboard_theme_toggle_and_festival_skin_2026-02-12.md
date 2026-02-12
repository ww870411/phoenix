时间：2026-02-12
需求：新增界面风格切换开关，保留默认风格并增加春节氛围模板。
实现：
1) SpringFestivalDashboardView.vue 新增 themeMode（default/festival）和 THEME_STORAGE_KEY。
2) 工具栏新增“风格”下拉选择；根容器改为按 themeMode 动态 class。
3) onMounted 读取 localStorage；watch(themeMode) 持久化保存。
4) 新增春节主题样式：暖色渐变背景、光斑纹理、卡片/按钮/选择框/表头暖色皮肤。
5) 默认主题保持原样。
涉及文件：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue，configs/progress.md，frontend/README.md，backend/README.md。
验证：未在本条内执行命令行构建，建议本地运行 npm run build 或页面实测。