## 2025-11-06 售电煤炭库存表权限放行
- 更新 backend_data/auth/permissions.json，将 unit_filler 组 data_entry 规则添加 sheets=["Coal_inventory_Sheet"]，刷新 updated_at。
- 前端 auth store 的 by_unit 模式现在会读取 sheets 白名单，在 sheetMatchesUnit 之外放行显式授权表单，售电账号 shoudian_filler 可访问 Coal_inventory_Sheet。
- 配套文档 progress.md、backend/README.md、frontend/README.md 已记录本次变更与回滚方式。