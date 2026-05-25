时间：2026-05-25
任务：温习 `configs/5.24_tube项目建设方案_v5.2_物流链管理版.md` 与 `configs/5.24_tube项目完整构建流程计划_v5.2执行版.md`，为后续继续开发 `insulation_pipe_supply_2026` 建立统一基线。

前置说明：
- 已读取 Serena 手册并在项目 `D:\编程项目\phoenix` 上下文下工作。
- 本轮未发现可调用的 `check_onboarding_performed` 工具，因此未执行该校验；已以 `initial_instructions` 返回结果作为项目激活与可用记忆列表的依据。
- 本轮仅做文档/记忆回顾，无代码修改。

方案层确认：
- 该子项目已从“扩需求”转入“规则收口 + dashboard 补尾 + 提交治理”的阶段。
- `tube_config.json` 是唯一运行配置主源，关键字段包括：`show_date`、`plan_start_date`、`plan_editable_days`、`construction_units.station_ids`、`baseline_presets`。
- 日期语义已拆为两层：
  - `plan_start_date`：控制三日计划录入窗口与实际使用采集日期（默认 `plan_start_date - 1`）。
  - `show_date`：控制 dashboard 与展示层的汇总/库存/累计/滚动三日计划展示窗口。
- 当前关键业务口径：
  - 库存 = 总到货 - 总使用量
  - 净缺口只扣减 `pending_arrival`
  - 到货/使用汇总推进到 `show_date - 1`
  - 在途时长截止于确认到货，`cancelled` 不展示
  - `tube.tube_baseline_quantity` 已退出运行链路，基准量主数据以 `baseline_presets` 为准

执行计划确认：
- 已落地页面：`dashboard`、`global_management`、`supply_management`、`demand_management`、`warehouse_management`。
- 主流程闭环已基本打通：三日计划、发货登记、到货确认、施工接收、库管确认、实际使用、供需汇总。
- 最近新增的治理方向：
  - 独立提交状态文件 `station_submission_status.json`
  - 需求侧提交动作与全局管理页提交状态展示
  - `auto_update_plan_start_date` 开关
- 当前最大未完成块仍是 `dashboard` 正式汇总展示；其次是提交前置条件、`show_date` 推进校验和全链路边界回归。

建议作为后续开发主线：
1. 先补提交治理闭环：提交前置条件、站点维度完成性校验、`show_date` 推进判断。
2. 再补 dashboard：正式汇总卡片、风险提示、图形展示，全部复用后端统一口径。
3. 最后做主流程与异常边界回归，重点校验角色权限、日期切换、库存/缺口、撤销与状态机。
