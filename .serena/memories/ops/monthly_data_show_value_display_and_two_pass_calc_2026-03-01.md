时间：2026-03-01
主题：monthly_data_show 数值展示规则 + 计算指标两轮计算

用户诉求：
1) 单位为 % 的值按百分数显示（0.65 -> 65%）；
2) 小数部分不为 0 的值统一保留 2 位小数；
3) 计算指标存在依赖链，要求连续两轮计算后显示。

改动文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

后端实现：
- 新增 _compute_calculated_two_pass(metric_values, selected_calc_items, day_count)
  - 固定两轮计算；第二轮以上一轮结果作为输入之一。
- query 与 query-comparison 均切换到两轮计算。
- 依赖取值顺序：缓存 -> 已计算值 -> 递归计算。

前端实现：
- 新增 formatValue(value, unit)
  - unit 为 % 时转为 value*100 后附加 %。
- formatNumber 统一规则：
  - 整值不带小数；
  - 非整值保留 2 位小数。
- 主表 value、对比表 current/yoy/mom 值均改为 formatValue 渲染。

结果：
- 百分比指标展示符合业务阅读习惯；
- 数值展示小数位一致；
- 计算指标依赖链按两轮计算输出更稳定。