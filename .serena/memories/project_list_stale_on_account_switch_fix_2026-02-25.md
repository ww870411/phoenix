时间：2026-02-25
主题：切换账号后项目列表残留旧账号数据修复

变更文件：
1) frontend/src/projects/daily_report_25_26/composables/useProjects.js
2) frontend/src/projects/daily_report_25_26/store/auth.js
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

根因：
- 项目列表使用全局 ref（useProjects.js），会话切换时未同步清空，导致刷新前短暂显示旧账号项目。

修复：
- 新增 resetProjectsState() 清空 projects/projectsLoading/projectsError。
- clearSession() 调用 resetProjectsState()。
- login() 成功后也调用 resetProjectsState()，保证账号切换先清空旧列表。

结果：
- 切换账号后不再残留旧账号项目卡片；列表将按当前账号重新加载。