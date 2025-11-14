日期：2025-12-04（晚）
范围：configs/ai_test.py，configs/progress.md，backend/README.md，frontend/README.md。
触发原因：根据用户要求改用官方 google-generativeai 模块（genai）完成 Gemini 2.5 Flash 调用。
变更摘要：
- `configs/ai_test.py` 现基于 genai SDK，实现 `ensure_model()` 复用 `GenerativeModel`、支持缺少 SDK/密钥的提示，并捕获 `GoogleAPIError`。
- `configs/progress.md` 在 2025-12-04 记录中补充“切换 genai SDK”说明及继续降级使用 apply_patch 的原因。
- 后端与前端 README 同步更新该会话小结，说明测试脚本现在依赖官方 SDK，后续 DashBoard AI 报告将基于同一方式。
回滚方式：恢复上述文件到切换前版本即可重新使用 requests 方案。