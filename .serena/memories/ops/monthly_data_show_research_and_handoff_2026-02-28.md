时间：2026-02-28
主题：monthly_data_show 模块新增前置调研与接入点梳理

会话目标：用户要求在已上线 monthly_data_pull 后新增 monthly_data_show，先了解外部需求与文件。

已完成调研：
1) Serena 接入校验：activate_project 成功；check_onboarding_performed=已完成。
2) 外部需求文件：
   - 路径：外部导入项目-月报表导入数据库/2.28 月报数据库化配置文件.txt
   - 结论：存在明确的指标清洗、单位处理、字段映射、入库范围、实时计算指标、多月聚合和多口径聚合规则。
3) 外部样例文件：
   - 路径：外部导入项目-月报表导入数据库/综合表26.1.xlsx
   - 结论：17个子表；核心列含“本年计划/本月计划/上年同期/本月实际/本年累计”；需剔除子表“恒流/天然气炉/中水”。
4) 现有复用骨架确认：
   - 后端：backend/api/v1/project_router_registry.py + backend/projects/monthly_data_pull/*
   - 前端：frontend/src/pages/ProjectEntryView.vue + ProjectSelectView.vue + monthly_data_pull 页面
   - 权限与项目：backend_data/shared/项目列表.json + backend_data/shared/auth/permissions.json

本轮代码变更：
- configs/progress.md：新增“2026-02-28（monthly_data_show 需求预研与接入点梳理）”。
- backend/README.md：新增“结构同步（2026-02-28 monthly_data_show 预研）”。
- frontend/README.md：新增“结构同步（2026-02-28 monthly_data_show 预研）”。

偏差与降级：
- 无 Serena 编辑受阻；无降级 shell 编辑；未进行业务代码实现，仅文档留痕。

后续建议落地顺序：
1. 新增项目注册与权限（project list + permissions）；
2. 创建 backend/projects/monthly_data_show 路由与服务骨架；
3. 创建 frontend/src/projects/monthly_data_show 页面与 API 封装；
4. 再按规则分阶段实现：基础指标查询 -> 多月聚合 -> 计算指标实时计算 -> 多口径聚合。