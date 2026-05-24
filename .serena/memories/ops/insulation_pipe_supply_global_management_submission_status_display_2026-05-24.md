时间：2026-05-24
主题：为 insulation_pipe_supply_2026 全局管理页补充换热站提交状态显示。

处理原因：
- 用户指出全局管理入口中看不到各换热站提交状态。

本次修改：
1. 后端
- `backend/projects/insulation_pipe_supply_2026/services/config_service.py`
  - 新增 `SUBMISSION_STATUS_PATH`
  - 新增 `load_station_submission_status()`，读取 `station_submission_status.json`
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
  - `get_global_management_config()` 已返回：
    - `submission_status_path`
    - `submission_status.latest_submissions`
    - `submission_status.history_submissions`

2. 前端
- `frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`
  - 新增“换热站提交状态”卡片
  - 展示字段：
    - 换热站
    - 当前状态（已提交 / 未提交）
    - 最新提交日期
    - 最新提交时间
    - 最新提交人
  - 判定规则：`data_submit_date == plan_start_date` 记为“已提交”，否则“未提交”
  - 顶部汇总显示：已提交数、未提交数、历史记录数

3. 文档同步
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

验证：
- 前端 `npm run build` 通过。

当前边界：
- 仅实现只读显示
- 暂未接入写入逻辑、提交前置校验与历史滚动更新逻辑