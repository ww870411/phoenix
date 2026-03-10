时间：2026-03-09
问题：用户反馈紧凑化后的辽宁现货电价 JSON 中，time_label 仍未按时间排序。根因是接口原始返回顺序来自页面四栏展示顺序，而非真实时间顺序。
处理：在 backend/services/liaoning_spot_price_fetcher.py 中新增 _time_sort_key，按 HH:MM 对 days[].points[] 进行排序。
验证：重新执行 `python backend/services/liaoning_spot_price_fetcher.py` 成功。校验首日 points 的前 10 个 time_label 为 00:15, 00:30, 00:45, 01:00, 01:15, 01:30, 01:45, 02:00, 02:15, 02:30；末尾 5 个为 23:00, 23:15, 23:30, 23:45, 24:00；is_sorted=True。
留痕文件：configs/progress.md、frontend/README.md、backend/README.md。