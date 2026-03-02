时间：2026-03-01
主题：全局管理后台新增数据库表在线编辑

用户目标：在“全局管理后台 -> 后台文件编辑”中直接编辑数据库表（先支持 monthly_data_show，并可扩展其他表）。

后端改动：backend/api/v1/admin_console.py
1) 新增 DB 元数据与安全工具函数：
- _is_safe_identifier / _quote_identifier（限制标识符）
- _load_table_meta（读取字段与主键）
- _to_json_value（Decimal/日期类型序列化）
2) 新增接口：
- GET /api/v1/admin/db/tables
- POST /api/v1/admin/db/table/query
- POST /api/v1/admin/db/table/batch-update
3) 保存规则：
- 仅支持含主键表更新；
- 按主键定位，批量提交 changes 字段；
- 忽略主键字段修改。

前端改动：
1) API 层 frontend/src/projects/daily_report_25_26/services/api.js
- listAdminDbTables
- queryAdminDbTable
- batchUpdateAdminDbTable
2) 页面 frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 在 files tab 新增“数据库表在线编辑”模块：
  - 表选择、limit/offset、加载、保存
  - 表格行内编辑
  - PK 字段只读且标记
  - 仅提交差异字段

验证：
- python -m py_compile backend/api/v1/admin_console.py 通过。

备注：
- 本轮未执行前端全量构建，仅完成代码级自检与后端语法检查。