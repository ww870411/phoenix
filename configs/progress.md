
## 2025-12-09（仪表盘新增运行设备明细后端实现）

- **User Request:** 接入“各单位运行设备数量明细表”的后端数据逻辑。
- **Agent Action:**
  1. 在 `backend/services/dashboard_expression.py` 中新增 `_fill_device_status_section` 函数：
     - 从 `section` 配置中读取单位列表和指标列表。
     - 使用 `_fetch_metrics_from_view` 从 `sum_basic_data` 视图获取当日数据。
     - 将查询到的数值填充回 `section` 的 `本期` 桶中。
  2. 在 `evaluate_dashboard` 函数末尾（第 10 步之后）插入对 `_fill_device_status_section` 的调用，确保生成数据时执行该逻辑。
- **Result:** 后端现已支持处理序号为 `"11."` 的设备明细板块，与前端预埋逻辑对接。一旦配置文件中启用了该板块，API 即可返回真实数据。
