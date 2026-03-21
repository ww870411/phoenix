时间：2026-03-21
任务：定位并修复 daily_report_25_26 数据看板“供暖期焦点指标详表（0.5 折叠表）”在缓存发布后内容失效的问题。
结论：问题不在前端展示，也不在赵丹数据，而在 section 编号解析。`backend/services/dashboard_expression.py` 使用的 `SECTION_PREFIX_PATTERN` 原为 `^(\d+)\.`，只能识别整数编号，导致 `0.5卡片详细信数据表（折叠）` 在并行发布的 `_extract_dashboard_subset()` 阶段被漏掉，缓存 detail.json 中保留的是原始模板字符串而不是计算结果。
变更文件：
1) backend/services/dashboard_expression.py
2) frontend/src/projects/daily_report_25_26/pages/DashBoard.vue
3) configs/progress.md
4) frontend/README.md
5) backend/README.md
修复摘要：
- 后端 section 索引正则改为支持小数编号：`^(\d+(?:\.\d+)?)`；
- 前端 sectionIndexMap 同步改为支持 `0.5`；
- 文档补充了本次根因与修复说明。
验证：
- `python -m py_compile backend/services/dashboard_expression.py` 通过；
- 运行 Python 校验 `_build_section_index_map(load_dashboard_config(...))` 已包含 `0.5`，且 `_extract_dashboard_subset(..., ['0.5','7','11'])` 会正确包含 `0.5卡片详细信数据表（折叠）`。
后续建议：
- 需要重新发布受影响日期的 dashboard cache，旧的 `dashboard_cache_v2/*/detail.json` 仍保留错误模板值，代码修复不会自动回填历史缓存。