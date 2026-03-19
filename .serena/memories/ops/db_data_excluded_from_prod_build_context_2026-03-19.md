时间：2026-03-19
主题：显式加固生产镜像构建上下文，排除本地数据库挂载目录 db_data

前置说明：
- 已确认项目根目录存在 `.dockerignore`，原本即包含 `db_data`。
- 用户要求修改 `lo1.ps1` 或相关配置，明确让该目录不参与生产镜像打包。

结论：
- `D:\编程项目\phoenix\db_data` 是开发环境 PostgreSQL 数据宿主机挂载目录。
- 它不应进入生产镜像 build context，也不应随镜像分发。
- 镜像本身不会直接覆盖目标环境数据库；真正影响数据的是运行时卷挂载和删卷行为。

本轮改动：
1. `.dockerignore`
- 将规则显式加固为：
  - `db_data`
  - `db_data/`
  - `**/db_data`
  - `**/db_data/**`
- 新增中文注释，说明其用途是排除本地 PostgreSQL 挂载目录。

2. `lo1.ps1`
- 构建前新增输出：`.dockerignore` 已排除 `db_data`，本地数据库挂载目录不会参与镜像打包。

3. `lo1_new_server.ps1`
- 同样新增上述构建前输出。

4. 文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

影响：
- 生产构建路径更明确，可减少误将数据库目录送入 Docker build context 的风险。
- 不改变业务功能，不影响前后端运行逻辑。