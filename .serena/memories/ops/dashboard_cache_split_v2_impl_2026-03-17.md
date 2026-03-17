时间：2026-03-17
任务：完成 daily_report_25_26 数据看板缓存从单文件迁移到按日期目录拆分结构，并验证兼容读写。
变更文件：backend/services/dashboard_cache.py
新结构：backend_data/projects/daily_report_25_26/runtime/dashboard_cache_v2/index.json、shared.json、<date>/meta.json、summary.json、detail.json、trend.json。
多日复用：共享的 口径别名 / 项目字典 / 单位字典 抽取到 shared.json。
兼容迁移：首次读取缓存时自动将旧版 dashboard_cache.json 拆分迁移，并备份为项目 runtime 下的 dashboard_cache.legacy.json。
路径修正：新结构不再走旧平铺根目录回退，固定写入项目 runtime；若曾错误生成到 backend_data/dashboard_cache_v2，会自动搬迁到项目 runtime。
验证结果：
1) `python -m py_compile backend/services/dashboard_cache.py` 通过；
2) `get_cache_status('daily_report_25_26')` 可正常返回 18 个缓存日期；
3) `get_cached_payload('daily_report_25_26', '2026-03-16')` 可正常重组 payload；
4) 与旧备份对比，2026-03-16 的顶层 key 和 data key 顺序保持一致；
5) `update_cache_entry` 原样写回验证通过；
6) 旧单文件 1360637 bytes，新拆分结构总量 1048344 bytes，减少约 312293 bytes。