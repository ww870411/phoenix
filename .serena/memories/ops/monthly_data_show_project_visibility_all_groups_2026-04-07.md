时间：2026-04-07
主题：放开 monthly_data_show 项目对全部现有用户组的项目列表可见性

变更摘要：
- backend_data/shared/项目列表.json：将 monthly_data_show.availability 从仅 Global_admin、Group_admin 扩展为全部现有用户组：Global_admin、Group_admin、ZhuChengQu_admin、Unit_admin、unit_filler、shoudian_filler、Group_viewer。
- 该修改只影响项目选择页/项目列表中的显示，不直接赋予项目页面访问权限；页面访问仍由 permissions.json 与 user_overrides 控制。
- configs/progress.md、frontend/README.md、backend/README.md 已同步。

验证证据：
- 使用 Python 解析 backend_data/shared/项目列表.json 成功。