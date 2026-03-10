时间：2026-03-09
问题：用户反馈生成的辽宁现货电价 JSON 过于啰嗦，`biz_date` 在每个点位大量重复。
处理：调整 backend/services/liaoning_spot_price_fetcher.py 的输出结构，删除顶层扁平 `points` 列表；删除 SpotPricePoint 中的 biz_date；改为仅在 `days[].biz_date` 保留日期，`days[].points[]` 内仅保留 `time_label`、`before_price`、`real_time_price`。同时同步调整 CSV 导出逻辑，从 days/points 分组结构展开。
验证：重新执行 `python backend/services/liaoning_spot_price_fetcher.py` 成功，产物文件 D:\编程项目\phoenix\backend_data\liaoning_spot_price_2026-01-01_2026-03-08.json 顶层键为 source/query/summary/days，不再包含顶层 points，点位内不再包含 biz_date。文件大小约 871454 字节，较之前明显下降。
留痕文件：configs/progress.md、frontend/README.md、backend/README.md。