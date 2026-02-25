时间：2026-02-25
主题：availability 旧键兼容移除

变更文件：
1) backend/api/v1/routes.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

实施内容：
- _is_project_enabled_for_group() 仅保留 availability 读取，缺省 true。
- 删除 project_availability 与 项目可用性 的回退兼容。

结果：
- 项目可用性配置已单键标准化，后续配置必须使用 availability。