时间：2026-02-28
主题：修复源文件批量确认无响应（.xls 兼容 + 错误可见）
现象：源文件批量识别后点击确认无反应，目标底表正常。
根因：源文件含 .xls，后端仅 openpyxl 读取；确认阶段报错且前端步骤2未显式展示错误。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) backend/requirements.txt
3) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
4) configs/progress.md
5) backend/README.md
6) frontend/README.md

实现摘要：
- 后端增加 xlrd 适配：
  - get_sheet_names 支持 .xls；
  - execute_mapping 源工作簿加载按后缀分流（.xls -> xlrd 适配器，其他 -> openpyxl）。
- 新增依赖 xlrd>=2.0.1。
- 前端步骤2新增 errorMessage 可见展示，批量确认异常时弹窗提示。

结果：
- 源文件 .xls 批量确认可正常处理；
- 后续失败能即时看到错误，不再表现为“没反应”。