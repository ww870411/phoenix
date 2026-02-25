日期：2026-02-25
主题：修复 unit_filler 全员可见 Coal_inventory_Sheet

问题：
- `unit_filler` 组的 data_entry 规则含显式 sheets: [Coal_inventory_Sheet]，导致该组所有填报员都可见该表。

修复方案：
1) 账号分组拆分
- 文件：backend_data/shared/auth/账户信息.json
- 将 shoudian_filler 从 unit_filler 列表移到新组 shoudian_filler。

2) 权限配置收敛
- 文件：backend_data/shared/auth/permissions.json
- unit_filler: data_entry 仅保留 mode=by_unit（移除 Coal_inventory_Sheet 显式授权）。
- 新增 shoudian_filler 组：data_entry 保留 sheets=[Coal_inventory_Sheet] 显式授权。

结果：
- Coal_inventory_Sheet 的额外显式权限仅对 shoudian_filler 生效；其余 unit_filler 不再可见该表。

本次同步文档：
- configs/progress.md
- backend/README.md
- frontend/README.md