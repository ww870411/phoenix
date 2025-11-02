时间：2025-11-02
主题：常量金额字段带千分位导致写库为 NULL
现象：company_cn=庄河环海、item_cn=采暖期供暖收入 的提交一直保持 NULL，其他指标可更新。
原因：前端可能录入带千位分隔符或包含空格的金额，后端 `_parse_decimal_value` 对 "1,234" 等格式解析失败并返回 None，upsert 覆盖为 NULL。
处理：
- backend/api/v1/daily_report_25_26.py `_parse_decimal_value` 现会清除 `,`、`，`、空格，并过滤 `--/N/A` 等占位符后再调用 Decimal。
- 对应记录重提后即可写入数值。
备注：若日后仍需兼容额外格式（如 `%`、`万元`），可在同函数继续扩展清洗规则。