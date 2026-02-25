时间：2026-02-25
主题：项目可用性字段命名统一为 availability

变更文件：
1) backend_data/shared/项目列表.json
2) backend/api/v1/routes.py
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

内容：
- 项目配置键由“项目可用性”改为 availability。
- 春节项目白名单继续采用数组格式，即便单组：availability=["Global_admin"]。
- 后端读取优先级调整为 availability -> project_availability -> 项目可用性（兼容历史配置）。
- 权限语义不变：availability 为项目入口最高优先级，总闸通过后才进入 permissions.json 判定。