日期：2026-02-25
主题：用户分组与权限系统现状核对

结论摘要：
1) 账号来源：backend_data/shared/auth/账户信息.json，按组组织用户（username/password/unit）。
2) 权限来源：backend_data/shared/auth/permissions.json，按组定义 hierarchy/page_access/sheet_rules/units_access/actions。
3) 核心鉴权：backend/services/auth_manager.py（加载配置、登录、会话校验、单位范围解析、权限序列化）。
4) 会话机制：Bearer token；默认会话不过期（SESSION_TTL_SECONDS=None）；remember_me 持久化到 PostgreSQL auth_sessions（90天滚动）。
5) 前端消费：frontend/src/projects/daily_report_25_26/store/auth.js 根据 permissions 进行页面过滤、表单过滤、按钮显示控制。
6) 后端强校验：审批/撤销/发布等接口仍按 session.permissions.actions 与 session.allowed_units 二次校验。
7) 当前模型是页面/表单/单位/动作级，不包含通用项目级 project_access 字段。

本次改动文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

说明：本轮仅文档留痕与说明，无业务代码修改。