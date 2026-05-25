# 2026-05-25 insulation_pipe_supply_2026 审计报告复核

## 背景
用户要求复核 `configs/5.25 审计（agy）.md`，判断其内容是否成立。

## 总体结论
该审计报告不能整份照单全收。当前更准确的结论是：
- 有一批问题仍然成立
- 有一批问题已经被当前代码修复，报告属于过时结论
- 有一批问题方向有依据，但危害描述和适用范围明显夸大

## 复核后仍成立的代表项
1. `order_no` 唯一索引与初始插入空字符串的并发冲突风险
   - 证据：`backend/sql/tube_schema_init.sql` 仍为全局唯一索引；`workspace.py` 仍先以空 `order_no` 调用 `create_delivery_record(...)` 再回写正式编号。
2. `DemandManagementView.vue` 中 `normalizePendingRows` 与确认函数对 `0` 使用 `||` 的 falsy 覆盖问题
3. 施工接收前端缺少 `received_qty <= arrived_qty` 的显式提交前拦截
4. `/workspace/config-summary` 位于 `public_router` 且返回 `config_path` 与全量配置列表

## 复核后不成立或已过时的代表项
1. “供给侧滚动三日计划量不应按 `show_date` 统计”不成立
   - 当前实现与执行版计划文档一致：展示层滚动三日计划量按 `show_date ~ show_date+2` 汇总。
2. “库管页在途时长确认后仍无限增长”已过时
   - 当前后端已统一输出 `delivery_elapsed_label`，前端展示优先使用该字段；Warehouse 页原始行对象也具备 `arrived_confirm_at`。

## 复核后需降级看待的代表项
1. `username` 缺失导致普通角色“恒为空白”
   - 当前配置确未普遍维护 `username`，但权限解析还会匹配 `manager_id / manager_name / entity_id / entity_name`，因此属于条件性风险，不是无条件必现。
2. JSON 文件并发写回无锁
   - 工程稳健性隐患成立，但更接近并发一致性风险，不宜直接表述为当前高频已复现业务故障。
3. 供给页 watcher 死循环
   - 现有 watcher 间存在重复触发和维护复杂度问题，但“极易死循环导致页面瘫痪”的表述缺乏当前代码层直接证据。

## 结果
该审计报告可作为问题线索清单使用，但不能作为当前真实状态的权威基线，必须逐条复核后再纳入修复排期。