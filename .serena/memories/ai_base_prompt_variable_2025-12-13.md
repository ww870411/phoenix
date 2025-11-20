# 2025-12-13 更新：AI 测试脚本基础提示词变量

## 变更概述
- 位置：configs/ai_test.py
- 新增 BASE_SYSTEM_PROMPT 常量，默认值“你是凤凰计划的数据填报辅助助手，请用中文简洁回答，避免编造或虚构数据。”
- send_message() 会自动把 BASE_SYSTEM_PROMPT（以及 extra_instruction）附加到用户提问之后，统一约束模型回答风格。

## 文件触及
- configs/ai_test.py
- backend/README.md（会话小结新增说明）
- frontend/README.md（会话小结新增说明）
- configs/progress.md（记录前置说明与动作）

## 验证
- 运行 python configs/ai_test.py，观察回复应遵循默认提示词；将 BASE_SYSTEM_PROMPT 置空字符串即可恢复无提示模式。

## 回滚
- 恢复上述文件到本次改动前版本，删除 BASE_SYSTEM_PROMPT 并还原 README/progress 对应段落。