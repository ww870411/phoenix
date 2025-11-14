日期：2025-12-04（晚）
范围：backend/requirements.txt，configs/progress.md。
触发原因：AI 报告测试脚本切换到 google-generativeai SDK 后，需要在后端依赖列表中声明该包。
变更摘要：
- backend/requirements.txt 追加 google-generativeai>=0.7.0，确保后端环境安装官方 SDK。
- configs/progress.md 同步记录新增依赖的原因，使部署人员可追溯。
回滚方式：删除 requirements.txt 中该行并更新进度记录即可。