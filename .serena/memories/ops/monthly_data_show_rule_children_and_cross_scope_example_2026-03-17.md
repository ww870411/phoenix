时间：2026-03-17
主题：monthly_data_show 规则选择改为父项展开子项 + 主城区取供热公司耗水量示例

前置说明：
- 用户指出上一版实现不符合预期：需要在“规则执行选择”中按父项展开到每个具体子规则，而不是只做大类分组。
- 本轮仍未更新 configs/progress.md、frontend/README.md、backend/README.md。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json

实现内容：
1. 规则选择接口改为父子结构
   - get_extraction_rule_options() 现在返回 4 个父项：
     - 指标剔除：children 展开 item_exclude_set 每一项
     - 指标重命名：children 展开 item_rename_rules 每一项
     - 半计算规则：children 展开 semi_calculated_rules 每一项
     - 特殊修正：children 展开特殊修正规则（当前含金普面积扣减）
2. 前端规则选择弹窗
   - 改为父项折叠/展开。
   - 展开后可逐项勾选具体子规则。
   - 每个父项支持“本项全选/本项全不选”。
   - 默认全部子项勾选，顶部仍保留全局全选/全不选。
3. 后端执行粒度改为子规则级
   - item_exclude_set：按选中的具体剔除项生效。
   - item_rename_rules：按选中的具体重命名规则生效。
   - semi_calculated_rules：继续按各自 rule id 生效。
   - 兼容旧的父项 id 传入：若前端仍传 item_exclude / item_rename / semi_calculated / special_adjustments，会自动展开成该父项下全部子项。
4. 配置示例
   - 用户要求的“主城区的热网耗水量 = 供热公司的耗水量”未写入 item_rename_rules，因为该配置只适合名称映射，不适合跨口径赋值。
   - 已按正确语义写入 semi_calculated_rules 示例：
     - name: 主城区热网耗水量取供热公司耗水量
     - companies: [主城区]
     - target_item: 热网耗水量
     - target_unit: 吨
     - formula: ="供热公司::耗水量"

验证：
- get_extraction_rule_options() 返回父项名称：指标剔除、指标重命名、半计算规则、特殊修正。
- 指标剔除子项数量为 19；指标重命名已逐条展开；半计算规则末尾包含：
  - 主城区热网耗水量取供热公司耗水量
  - 煤折标煤量补齐
- 最小样例验证：当窗口内存在 `供热公司/耗水量=55` 时，半计算可生成 `主城区/热网耗水量=55`。
- Python 语法检查通过。
- 前端 `npm run build` 通过。

说明：
- 当前示例是“真实生效”的半计算规则，不是注释示例。若用户只想保留样例不生效，后续需再改为文档说明或增加 enabled 字段支持。