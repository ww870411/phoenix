日期：2026-02-08
主题：项目模块化第十步（数据看板接口下沉到项目目录）

新增文件：
- backend/projects/daily_report_25_26/api/dashboard.py
  - 包含 /dashboard 公开接口与缓存/导入相关管理接口。

改动文件：
1) backend/projects/daily_report_25_26/api/router.py
- 组合路由新增 `dashboard_router`。
- public_router 改为组合 legacy_public_router + dashboard_public_router。

2) backend/api/v1/daily_report_25_26.py
- 删除已迁移的 dashboard 相关接口与辅助函数。
- 删除对应无用导入（dashboard_cache/evaluate_dashboard/load_default_push_date/cache_publish_job_manager/weather_importer 相关）。

兼容性：
- 对外 URL 不变，前端无需修改。
- 实现位置迁移至项目目录，旧大文件进一步瘦身。

文档留痕：
- configs/progress.md 追加第十步
- backend/README.md 与 frontend/README.md 同步更新