时间：2026-02-28
主题：登录接口 CORS 预检失败修复

问题现象：
- 浏览器从 http://localhost:5173 访问 http://127.0.0.1:8000/api/v1/auth/login 报错：
  No 'Access-Control-Allow-Origin' header is present on the requested resource.

根因：
- backend/main.py 中 CORS 配置为 allow_credentials=True + allow_origins=['*']。
- 该组合在浏览器预检场景下不兼容，导致跨域失败。

修复：
- 文件：backend/main.py
- 改为默认显式白名单：
  - http://localhost:5173
  - http://127.0.0.1:5173
  - http://localhost:4173
  - http://127.0.0.1:4173
  - http://localhost:3000
  - http://127.0.0.1:3000
- 保留 PHOENIX_CORS_ORIGINS 环境变量覆盖能力。

影响：
- 本地开发前端登录预检恢复正常。
- 不改变业务接口契约。