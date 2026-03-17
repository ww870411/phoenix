时间：2026-03-17
任务：开始将 daily_report_25_26 数据看板缓存从单文件 dashboard_cache.json 迁移为按日期目录拆分的 dashboard_cache_v2 结构。
当前设计：根目录含 index.json、shared.json；每个日期一个子目录，内含 meta.json、summary.json、detail.json、trend.json。
多日复用：共享的 口径别名 / 项目字典 / 单位字典 抽到 shared.json，减少跨日期重复存储。
兼容策略：首次访问缓存时自动把旧版 dashboard_cache.json 迁移到新结构，并备份为 dashboard_cache.legacy.json。