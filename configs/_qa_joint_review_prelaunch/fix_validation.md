# 联合会审剩余问题修复与验证

最后验证日期：2026-10-09。输入：本机当前源码、当前数据库结构、已登录 Chrome 页面。对应最初检查报告 `review.md`。

## 修复结果

| 问题 | 实现模块/函数 | 处理结果 |
|---|---|---|
| JR-01 标段权限 | create_joint_review / _check_user_can_vote_entity | 发起及表决核对角色与标段责任集合；厂家复用供货归属；公开台账阅读范围不变 |
| JR-02 明细归属 | _validate_patch | 提请、生效均拒绝重复ID和冻结集合外明细，单号取数据库原值 |
| JR-03 冻结恢复 | original_snapshot._review_rows / _lock_review_rows / _restore_rows | 存每行原值和实际冻结ID；按行恢复前状态、清除pre_review_status、保留各自备注；不修改同车其他阶段、标段或厂家的明细 |
| JR-04 并发提请 | create_joint_review | 相同订单/车次先取得事务咨询锁，再按ID顺序行锁和检查；同车不同主明细也不能重复提请 |
| JR-05 数量 | _validate_patch / 提请弹窗 | 按实际NUMERIC(18,2)校验有限正数、范围和精度；文本提前校验数据库长度。保留用户允许到货量超过更正发货量的规则；提请和最终生效重复校验 |
| JR-06 字段未生效 | _restore_rows / InitiateJointReviewModal | 联系人、电话、车牌、备注及明细字段均执行；备注更正后附决议。补充备注输入、比对及载荷，其他节点明细禁改 |
| JR-07 待办计数分页 | list_joint_reviews / loadStats | 先按资格筛出所有本人未签议案，再计算总数和分页；全局KPI不被列表筛选结果覆盖 |
| JR-08 改票入口 | 会审大厅 action-group / vote_joint_review | 在审且有资格者仍可再次表决；审计记录前次签署意见及此次决定，包括最后一票触发生效的情形 |
| JR-09 隐藏筛选 | loadReviews | 只有all标签提交会审状态筛选 |
| JR-10 异步响应 | loadReviews / loadStats | 请求序号限定仅最新响应能提交列表、统计、错误提示及loading |
| JR-11 通知收件目标 | AuthManager.list_user_identities / create_joint_review | 从真实账号身份按同一表决资格解析收件人，写用户名消息；不再生成厂家ENTITY不可见目标或向其他标段主管广播 |
| 通知定位 | get_joint_review_detail / focusedReviewId | 详情复用列表资格元数据；URL的review_id直接获取详情并自动展开，显示定位提示及返回列表入口 |
| 裁决冒充全票 | approval_type / 大厅格式化函数 | 区分SYSTEM_CONSENSUS和终局裁决，按实际赞成主体计票；统计卡片统一称“已通过更正” |
| 多明细原始快照 | original_snapshot.items / 明细对照表 | 保存并显示每项原品类、规格、数量；历史缺少快照时明确提示不补造 |
| 初始化异常 | ensure_joint_review_tables / _ensure_status_constraints | 多进程DDL事务锁；异常向上抛出，不能在表/约束未就绪时继续业务；补齐差异待审核状态证据 |

## 验证与证据

- 真实 PostgreSQL 回归10/10通过，`backend/projects/insulation_pipe_supply_2026/tests/test_joint_review_postgres.py`。AST加载真实函数、真实SQL事务，独立随机`jr_test_<UUID>` schema克隆当前表的约束；通知/审计捕获接口不发送实际消息。结束后测试schema数量为0。
- 生命周期用例涵盖直管/管件的待到货、待接收、差异待审核、待库管四状态，各自全票通过（先异议再改票）、撤回、强制通过、强制驳回，共32组合；核对订单量、恢复状态、清除冻结标记及终态重复表决拒绝。
- 两事务覆盖同直管订单、同管件订单、同车不同明细提请；均只有一单成功，其余409。最后一票与撤回竞争只有一个终态成功。
- 混合状态车次校验：同节点两项参加，其余完成、撤销、其他节点订单整行保持原值；逐行备注保留。覆盖外来ID、重复ID、跨标段、非法数量、字段长度及最终冻结状态变化拒绝并回滚投票。
- 前端真实SFC/Vue渲染回归10/10通过：展开、改票入口、裁决票数、独立KPI、隐藏筛选、旧响应隔离、通知定位、备注提交及非法数量。
- 原机械性修复回归3/3通过；轻量探针7项symptom均false；Python语法检查通过；Vite构建通过（原有大包体积提示）；git diff --check无内容错误。
- 已登录本机Chrome验证：台账3笔；筛选已通过列表2笔而全网总数仍3；单次展开显示比对与签署；通知URL review_id=3直接展开已办结旧议案；无需该议案仍在个人待办。
- 页面证据截图：`hall_verified.png`，包含通知定位提示、返回列表入口、独立KPI及自动展开的旧议案。
- 执行期间本机数据库曾缺少之前存在的pre_review_status及会审状态，原因未证实。已调用现有初始化函数补齐两表字段及状态CHECK，验证约束均convalidated=true；未修改真实订单记录、真实议案或表决。

## 迁移、回滚与验证边界

- 用户自行执行的直管到货量非负约束已同步`backend/sql/tube_schema_init.sql`；其他环境可执行`backend/sql/migrate_tube_joint_review_arrived_qty.sql`，本轮不重复修改该数量约束。
- 新会审在既有JSONB快照字段内增加逐行冻结记录，无新增业务表字段迁移。历史在审议案无逐行快照时仅恢复同标段、厂家、前状态的挂起记录，发现同车重叠会审则拒绝自动处理。历史已办结记录不重写。
- 回滚代码可还原本轮补丁；已生成的新快照继续保留。恢复旧到货上界前必须检查到货量超过发货量的数据，不能强行恢复旧约束。
- 待我联审在服务端加载匹配状态候选并按资格筛选后分页，保证正确计数；大规模活动议案的容量/压力测试未执行。
- 实际业务数据库未创建测试订单；真实厂家/施工/库管账号的写入与收件箱人工验收、库存看板和生产部署尚未执行。通知资格与载荷已测试，真实投递依赖现有消息服务运行。
- 当前容器没有coverage组件，未声称达到90%覆盖率或完成依赖CVE审计；本次测试通过不代表上述上线门槛已全部认证。

## 本地复现命令

```text
docker exec phoenix_backend python -m unittest backend.projects.insulation_pipe_supply_2026.tests.test_joint_review_postgres -v
node --test frontend/tests/joint-review-hall.test.mjs
python configs/_qa_joint_review_prelaunch/test_mechanical_fixes.py
python configs/_qa_joint_review_prelaunch/audit_probe.py
npm --prefix frontend run build
```

文件读写使用原生工具，文本编辑使用apply_patch；三份项目文档同步，关键结论登记Serena。
