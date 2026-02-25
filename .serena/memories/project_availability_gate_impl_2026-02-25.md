时间：2026-02-25
主题：项目可用性最高优先级开关落地（项目列表.json + 后端统一鉴权）

变更文件：
1) backend_data/shared/项目列表.json
2) backend/api/v1/routes.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

核心实现：
- 在项目配置中引入字段：项目可用性（兼容 project_availability），支持 bool 或 string/list 白名单组。
- 判定顺序统一为：项目可用性 -> permissions.json 项目权限。
- /api/v1/projects 列表增加项目可用性过滤。
- /api/v1/projects/{project_id}/pages 增加项目可用性+权限总闸。
- 项目注册路由（private/public）统一挂载依赖，阻断绕过项目列表的直连访问。

当前配置：
- daily_report_25_26: 项目可用性=true
- daily_report_spring_festval_2026: 项目可用性=[Global_admin]

结果：
- 非白名单组对春节项目不可见且不可访问（403）。
- 白名单组仍需满足 permissions.json 才可访问。