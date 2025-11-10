2025-11-20：为 daily_report_25_26 数据填报链路补充“行内校验”能力。

- 后端：`backend/api/v1/daily_report_25_26.py` 将 `validation_rules/校验规则/数据校验` 归入 `DICT_KEY_GROUPS`，模板接口会将该字典与 `item_dict` 等一并返还，便于前端读取。
- 模板示例：`backend_data/数据结构_基本指标表.json` 中的 `BeiHai_co_generation_Sheet` 增加 `"校验规则"` 字段，包含对发电量/供热量/耗水量/外购电量的非负规则，以及“其中”行不大于主项的 `less_equal_than` 规则。
- 前端：`frontend/src/daily_report_25_26/pages/DataEntryView.vue` 新增校验状态与 `runFullValidation/validateRow`，在编辑、联动更新与提交前执行 `number_range`、`less_equal_than` 校验，UI 顶部出现“校验提醒”面板并阻止存在 error 的提交。
- 文档：`backend/README.md`、`frontend/README.md` 与 `configs/progress.md` 已记录用途、写法、回滚方式。