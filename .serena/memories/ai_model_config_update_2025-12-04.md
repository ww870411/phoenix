日期：2025-12-04（晚）
范围：backend_data/api_key.json，configs/ai_test.py，configs/progress.md，backend/README.md，frontend/README.md。
触发原因：用户要求将模型设定与密钥一并写入 backend_data/api_key.json，并让脚本按该配置加载。
变更摘要：
- backend_data/api_key.json 现在包含 gemini_api_key 与 gemini_model。
- configs/ai_test.py 的 load_api_config() 会按“环境变量 → JSON 文件”顺序同时读取 API Key 与模型名，调用 genai.GenerativeModel(model_name)。
- configs/progress.md、后端/前端 README 均同步说明新配置方式。
回滚方式：删除模型字段并恢复脚本与文档即可。