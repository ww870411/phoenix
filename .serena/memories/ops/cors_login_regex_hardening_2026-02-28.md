时间：2026-02-28
主题：登录 CORS 二次加固

背景：用户反馈在首轮修复后仍出现 localhost:5173 -> 127.0.0.1:8000 登录预检拦截。

处理：
- 文件：backend/main.py
- 在 CORSMiddleware 中新增：
  allow_origin_regex = ^https?://(localhost|127\.0\.0\.1)(:\d+)?$
- 保留显式 allow_origins 白名单。

结果：
- 本机调试端口变化（如 5173/4173/3000）场景下，预检兼容性提升。