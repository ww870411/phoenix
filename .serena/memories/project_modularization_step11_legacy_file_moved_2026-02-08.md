日期：2026-02-08
主题：项目模块化第十一步（旧大文件整体迁入项目目录）

关键改动：
1) 文件迁移
- 将 `backend/api/v1/daily_report_25_26.py` 整体迁移为
  `backend/projects/daily_report_25_26/api/legacy_full.py`。

2) 兼容层保留
- 在旧路径 `backend/api/v1/daily_report_25_26.py` 新建兼容层：
  - 仅 `from backend.projects.daily_report_25_26.api.legacy_full import *`
  - 保持历史导入兼容。

3) 项目路由入口更新
- `backend/projects/daily_report_25_26/api/router.py` 改为直接从 `.legacy_full` 导入 legacy 路由。

影响与收益：
- 代码物理位置更符合“按项目目录组织”；
- 运行时接口路径不变，前端无感；
- 为后续继续拆分 `legacy_full.py` 奠定基础。