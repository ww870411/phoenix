# 日报供暖期整改
最后验证：2026-10-21，本机。
用户在审计后明确授权修复：独立气温起点默认11月1日、日报统计起止、历史常量错位、旧视图回退、仅发布当前期缓存且保留旧缓存、审批主体隔离；常量以后输入，全局业务日期名称和展示日行为不改，第5点只解释，不单独修改预供热收入规则。用户进一步确认：当日明细保留，7日/月/期累计均与统计区间求交，开始前0、结束后不加，本期同期各用自己设置。因此累计天数自然不负，每日暖收入156分母保持。
实现：heating_season_service新增temperature_start_date/seasons/peer_settings，旧start_date/end_date用作统计区间；season_utils统一窗口；daily_engine与analysis_engine裁剪累计、区分单日明细和仅一天的累计模式；手填净投诉累计作末值减基线，遵循原月初/11月1日重置边界，不能减10月快照。正式数据未改。
runtime_expression常量与列头按查询日推期，不再跟全局active。日报/分析/库存失败不回退旧视图，错误显式传播。dashboard_expression气温起算日分期，缺气温显示—，同比安全移年。缓存发布/刷新限当前期统计区间，禁用只停用不删文件；版本3口径签名防旧新期缓存命中。workflow主体来自本项目基本指标模板，显示批准撤销均求交，旧快照留存。
实际UI保存：26-27统计2026-11-01~2027-04-05、气温2026-11-01；同期2025-11-01~2026-04-05、气温2025-11-01。11月5日仅示例测试，未实际设定。登录Chrome验证刷新后设置保持、审批仅9日报主体、看板当日和期均气温显示—、净投诉同期58、缓存当前期选项。未提交真实日报/常量、审批或批量缓存发布。旧缓存保留，路由不改。
验证：npm run build通过751模块13.47秒；12项unittest通过（PG临时表最终rollback，正式库不变），覆盖边界/历史常量/失败不回退/单日累计/净投诉重置/缓存保留/审批隔离。git diff --check通过。测试命令docker exec -e PHOENIX_TEST_POSTGRES=1 phoenix_backend python -m unittest backend.projects.daily_report_25_26.tests.test_season_rollover -v。目标服务器未部署未验收。
文档：configs/26-27供暖期生产日报整改说明_2026-10-21.md，原审计顶部加整改链接；configs/progress.md及前后端README已同步。工具：Serena检索，按用户要求apply_patch编辑；新tests目录DC创建；progress.md误判binary经原生Node确认UTF8后保留原文更新。Docker管道沙箱访问拒绝后获授权测试。撤销仅本轮代码/season_config差异，勿回退并行保温管改动及历史缓存。
