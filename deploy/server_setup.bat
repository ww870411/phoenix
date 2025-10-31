@echo off
REM 凤凰计划生产部署批处理
REM 作用：在 Windows 服务器上快速构建 / 更新容器集群

setlocal enabledelayedexpansion

REM 1) 切换到仓库根目录
cd /d %~dp0..

REM 2) 预检查 Docker / Compose
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop 或 Docker Engine。
    exit /b 1
)
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [错误] 当前 Docker 未启用 compose 插件，请升级到支持 version 2 的版本。
    exit /b 1
)

REM 3) 预创建数据目录（避免首次挂载失败）
if not exist db_data (
    echo 创建数据目录 db_data...
    mkdir db_data
)
if not exist backend_data (
    echo 创建数据目录 backend_data...
    mkdir backend_data
)

REM 4) 可选：导入环境变量文件（优先 .env.prod，没有则退回 .env）
set ENV_FILE=.env.prod
if not exist %ENV_FILE% (
    set ENV_FILE=.env
)
if exist %ENV_FILE% (
    echo 使用环境变量文件 %ENV_FILE%
    set COMPOSE_ENV_FILE=--env-file %ENV_FILE%
) else (
    set COMPOSE_ENV_FILE=
)

REM 5) 构建并启动生产集群
set COMPOSE_FILE=docker-compose.prod.yml
echo 开始构建镜像并启动服务...
docker compose %COMPOSE_ENV_FILE% -f %COMPOSE_FILE% build --pull
if errorlevel 1 (
    echo [错误] 构建镜像失败，请检查日志。
    exit /b 1
)
docker compose %COMPOSE_ENV_FILE% -f %COMPOSE_FILE% up -d
if errorlevel 1 (
    echo [错误] 启动容器失败，请检查日志。
    exit /b 1
)

REM 6) 清理悬挂镜像（可选）
docker image prune -f >nul

echo 部署完成，可通过 http://服务器IP:%FRONTEND_PORT% 访问前端。
echo 后端健康检查：curl http://服务器IP:%BACKEND_PORT%/healthz

endlocal
