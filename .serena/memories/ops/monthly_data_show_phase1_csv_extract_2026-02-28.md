时间：2026-02-28
主题：monthly_data_show 第一阶段上线（上传月报 -> 复选 -> 提取CSV）

用户确认边界：
1) 先实现上传表格并提取 CSV（用于后续入库），暂不直接写库。
2) monthly_data_show 独立实现，不复用 monthly_data_pull。
3) 页面需提供口径与字段复选；已明确排除口径不展示（恒流/天然气炉/中水）。
4) 后续会建设查询分析页面，风格参考 daily_report_25_26/data_analysis。

已实现：
- 项目注册与权限：
  - backend_data/shared/项目列表.json 新增 monthly_data_show（中文名：月报入库工作台）
  - backend_data/shared/auth/permissions.json 为 Global_admin 增加 monthly_data_show 访问
- 后端模块：
  - backend/projects/monthly_data_show/api/router.py
  - backend/projects/monthly_data_show/api/workspace.py
  - backend/projects/monthly_data_show/services/extractor.py
  - backend/api/v1/project_router_registry.py 注册 monthly_data_show
- 后端接口：
  - POST /api/v1/projects/monthly_data_show/monthly-data-show/inspect
  - POST /api/v1/projects/monthly_data_show/monthly-data-show/extract-csv
- 提取规则：
  - 字段输出：company,item,unit,value,date,period,type
  - 指标清洗：去空格、去“其中：”、规则重命名
  - 指标过滤：剔除指标 + 计算指标不入库
  - 单位处理：米2/米² -> 平方米，千瓦时 -> 万千瓦时（值/10000）
  - 日期口径：按文件名 yy.m 推导（例如 26.1）
- 前端页面：
  - frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
  - 入口接线：ProjectEntryView、ProjectSelectView、API 封装新增 inspect/extract 函数
- 数据目录：
  - backend_data/projects/monthly_data_show/{uploads,outputs} + workspace_settings.json

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md

待后续阶段：
- CSV -> 数据库入库链路
- monthly_data_show 查询分析页面（参考 data_analysis 交互）