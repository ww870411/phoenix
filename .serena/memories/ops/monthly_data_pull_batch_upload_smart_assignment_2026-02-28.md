时间：2026-02-28
主题：monthly_data_pull 支持批量上传并按文件名智能归位
需求：批量上传文件，自动识别归属到源文件/底表槽位。

改动文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 在步骤2新增两个批量按钮：
  - 批量上传源文件并识别
  - 批量上传底表并识别
- 新增多选输入与处理函数 handleBatchPick(type, event)。
- 新增匹配算法：
  - normalizeMatchToken(name)：去扩展名、去括号内容、去符号并小写归一；
  - findBestSlotKey(filename, keys)：按完全命中/包含命中打分；并列最高分则不自动匹配。
- 新增 applyUploadedFile(...) 复用单文件上传后的状态写入逻辑，保持 sheet 自动映射规则一致。
- 批量处理后通过弹窗回显已匹配与未匹配文件。

后端联动：
- 未新增接口；复用 existing get-sheets 接口逐个上传解析。

行为说明：
- 自动归位是预填充，不影响后续人工改选；
- 对不确定归属的文件不强行匹配，避免误配。