# 保温管核心日期自动更新现状

- 时间：2026-08-09。
- 用户问题：全局管理页“核心控制参数”中的三个日期和“起始日期是否自动随今天变化”当前实际实现什么效果。
- 核对范围：线上 `https://platform.smartview.top/projects/insulation_pipe_supply_2026/pages/global_management`、前端 `GlobalManagementView.vue`、后端 `config_service.py` 与 `workspace.py`；全程只读。
- 线上当前值：`show_date=2026-08-08`、`usage_collection_date=2026-08-08`、`plan_start_date=2026-08-09`，自动开关为“否”。
- 自动模式后端规则：`plan_start_date=北京时间当天`；`usage_collection_date=北京时间当天-1天`。计算发生在接口请求时，无定时任务、无每日配置文件回写。
- `show_date` 不受开关控制，非空时继续使用手动值；只有缺失时才回退为 `plan_start_date-1天`，而正常分区保存要求日期非空。
- 前端规则：开启自动后禁用 `usage_collection_date` 和 `plan_start_date` 输入框，并在切换及保存时把 `plan_start_date` 设置为浏览器当天；`show_date` 仍可编辑。
- 影响范围：需求侧三日计划窗口、实际使用采集日期、严格流程校验、供给/库管页面计划起点、提交状态日期和全局管理返回值。
- 已识别边界1：前端 `getTodayDateString()` 使用 `new Date().toISOString().slice(0, 10)`，北京时间00:00至07:59切换时可能短暂显示UTC前一天，保存返回后由后端北京时间动态值纠正。
- 已识别边界2：`loadConfig()` 重新加载时覆盖动态 `plan_start_date`，但未用顶层动态响应覆盖 `usage_collection_date`；自动模式下全局管理页可能显示旧的消耗采集日期，业务接口仍按动态前一天计算。
- 已识别边界3：自动运行期间配置中的日期不会每天前推；关闭开关后会恢复读取已保存日期，人工接管前需重新核对并保存。
- 结论：当前实现是“两项动态、一项手动”，并非三个日期整体自动联动。
- 平台影响：未修改业务代码、配置或数据库。
- 最后验证日期：2026-08-09。