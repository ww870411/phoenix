时间：2026-03-17
主题：monthly_data_show 半计算规则新增公式能力，并添加“煤折标煤耗量补齐”配置

前置说明：
- 用户明确要求本轮只实现功能和配置，不更新 configs/progress.md、frontend/README.md、backend/README.md。
- 本轮未使用 apply_patch；基于当前环境此前 apply_patch 异常，直接按仓库允许降级路径使用 desktop-commander 做文件编辑。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json

实现内容：
1. extractor.py
   - 新增半计算公式支持，兼容 `="耗标煤总量"-"耗油量"*1.4571` 这类写法。
   - 规则执行优先级调整为：若 rule 含 `formula`，则优先走公式分支；否则沿用原 `copy/sum/subtract`。
   - 公式内部会把双引号/单引号包裹的指标名转换为 `{{指标名}}` 令牌，再复用 indicator_config.py 的 evaluate_formula 安全求值。
   - 默认行为：公式引用指标缺失时不生成目标项；可为后续微调保留扩展空间。
   - get_extraction_rule_options() 的半计算规则描述增加公式展示支持。
2. monthly_data_show_extraction_rules.json
   - 在 semi_calculated_rules 最后一项新增：
     - name: 煤折标煤耗量补齐
     - companies: [金普, 庄河]
     - target_item: 煤折标煤耗量
     - target_unit: 吨
     - formula: ="耗标煤总量"-"耗油量"*1.4571

当前假设：
- 新规则公司范围先沿用“煤折标煤量补齐”的口径，即金普、庄河。
- 目标单位暂按吨处理。

本地验证：
- get_extraction_rule_options() 已能返回“煤折标煤耗量补齐”。
- 构造样例：金普 / 耗标煤总量=100 / 耗油量=10。
- _apply_semicalculated_completion_rules(rows) 后新增：煤折标煤耗量=85.429，且 item_transform_note 为 `{{耗标煤总量}}-{{耗油量}}*1.4571→煤折标煤耗量`。
- 配置文件最后一项已正确写入 formula 规则。

后续可微调点：
- 公式缺项时是否允许按 0 参与计算。
- 规则适用口径范围是否扩大或缩小。
- transform_note 是否保留原始带引号公式文本。