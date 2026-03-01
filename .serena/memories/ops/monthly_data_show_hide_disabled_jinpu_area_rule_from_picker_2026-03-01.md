时间：2026-03-01
用户反馈：金普面积扣减规则已取消，但规则弹窗仍显示。
修复：
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 逻辑：get_extraction_rule_options 仅在 ENABLE_JINPU_HEATING_AREA_ADJUSTMENT=True 时下发“jinpu_area_adjust”规则。
结果：当前开关关闭时，前端规则弹窗不再显示该规则。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。