时间：2026-03-04
问题：用户反馈模板设计器页面入口不可见。

根因：
- /api/v1/projects/{project_id}/pages 在 backend/api/v1/routes.py 中按 page_access 过滤页面；
- 某些账号虽具备 can_manage_modularization，但 page_access 漏配 template_designer，导致入口被隐藏。

修复：
- 在 list_project_pages 中加入可见性兜底：
  - 读取 session.get_project_action_flags(project_id)
  - 若 can_manage_modularization=true 且项目配置存在 template_designer 页面，则将 template_designer 加入 allowed_pages。

变更文件：
1) backend/api/v1/routes.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

结果：
- 具备模块化管理动作权限的账号，不再因 page_access 漏配而看不到模板设计器入口。