日期：2025-12-04（晚）
范围：backend_data/api_key.json，configs/ai_test.py，configs/progress.md，backend/README.md，frontend/README.md。
触发原因：用户要求将 Gemini API Key 保存在仓库内的 backend_data/api_key.json，并让测试脚本优先从该文件读取。
变更摘要：
- 新增 backend_data/api_key.json，字段 gemini_api_key 默认含当前测试 Key。
- configs/ai_test.py 引入 load_api_key()，按“环境变量 → JSON 文件”顺序读取密钥，并使用 genai SDK。
- configs/progress.md 记录新增文件与加载顺序，说明继续降级编辑的原因。
- backend/README.md 与 frontend/README.md 的 2025-12-04 会话小结补充密钥存储方式。
回滚方式：删除 api_key.json 并恢复上述文件即可。