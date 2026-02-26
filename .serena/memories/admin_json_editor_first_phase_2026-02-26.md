时间：2026-02-26
任务：后台弹窗编辑器提供按类型的专用编辑能力，先落地 JSON。
实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminFileEditorWindow.vue
- 功能：
  1) 通过路径后缀识别 .json 文件（isJsonFile）
  2) 对 JSON 内容实时 JSON.parse 校验（jsonValidation）
  3) 从错误信息中提取 position 并换算行列显示
  4) JSON 非法时禁用保存并给出提示
  5) 新增“格式化 JSON”按钮，输出 2 空格缩进且末尾换行
结果：
- JSON 文件编辑可见结构、可校验、可阻断错误提交；
- 非 JSON 文件维持原文本编辑流程。