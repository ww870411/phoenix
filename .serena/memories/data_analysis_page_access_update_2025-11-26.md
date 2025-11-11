## 2025-11-26 数据分析页面权限补丁
- `backend_data/auth/permissions.json` 把 `data_analysis` 加入 Global_admin / Group_admin / ZhuChengQu_admin / Unit_admin / unit_filler / Group_viewer 的 page_access，确保任意角色登录后都能在 PageSelectView 看到“数据分析页面”入口卡片。
- backend/README.md 与 frontend/README.md 均补记此调整；configs/progress.md 记录降级原因与验证方式（重新登录刷新权限即可）。