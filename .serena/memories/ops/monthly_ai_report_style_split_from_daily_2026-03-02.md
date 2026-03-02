时间：2026-03-02
范围：backend/services/data_analysis_ai_report.py；configs/progress.md；backend/README.md；frontend/README.md。
变更摘要：确认月报 ai_mode_id 已正确传递为 monthly_analysis_v1；新增月报专用 HTML 渲染函数 _generate_monthly_report_html，并在 _generate_report_html 中按模式分流。月报不再复用日报卡片+趋势图主模板，改为正式简报版式（核心同比概览 + 四段正文 + 环比/计划附表 + 核对区）。
验证：python -m py_compile backend/services/data_analysis_ai_report.py 通过。