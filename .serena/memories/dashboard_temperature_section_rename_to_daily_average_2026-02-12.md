时间：2026-02-12
需求：将主看板“逐小时气温”改为“日均气温”，并确保来源为 calc_temperature_data 视图。
改动：
1) backend/services/dashboard_expression.py：第1节改为“日均气温”提示与注释；section 解析改为 get_section_by_index("1", "1.日均气温", "1.逐小时气温")。
2) backend_data/projects/daily_report_25_26/config/数据结构_数据看板.json：section 键改为 1.日均气温，数据来源改为 calc_temperature_data。
3) backend_data/projects/daily_report_25_26/config/dashboard_frontend_config.json：key/title/source_section/contract_notes/description 同步更新为日均气温与视图来源。
4) frontend/src/projects/daily_report_25_26/pages/DashBoard.vue：temperatureSection 解析别名改为优先 1.日均气温，兼容 1.逐小时气温。
验证：frontend npm run build 通过；python -m py_compile backend/services/dashboard_expression.py 通过。