日期：2026-02-25
主题：permissions.json 去重，仅保留 projects 子树

变更内容：
1) 文件 backend_data/shared/auth/permissions.json 已重建为“groups -> hierarchy + projects”结构。
2) 删除了组级平铺字段：page_access/sheet_rules/units_access/actions。
3) 每个项目节点保留完整权限四元组，作为唯一权限来源。

影响评估：
- 由于 auth_manager 已支持项目化解析，配置去重后可正常生效。
- 旧平铺字段仍被代码兼容读取（如后续需回滚，可补回字段）。

同步文档：
- configs/progress.md
- backend/README.md
- frontend/README.md