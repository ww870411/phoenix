时间：2026-02-28
需求：第3步将 CSV 提取与下载拆分为两个按钮。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
2) configs/progress.md
3) backend/README.md
4) frontend/README.md
实现摘要：
- 第3步按钮改为“提取 CSV”和“下载 CSV”。
- 提取按钮仅调用后端并缓存 File，不再自动触发下载。
- 下载按钮仅在存在缓存文件时可用，下载缓存结果。
- 提取后仍同步更新第4步可用文件，保持一键入库能力。
结果：
- 第3步交互更清晰，符合用户“提取/下载分离”要求。