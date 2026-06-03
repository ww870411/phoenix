# Phoenix 项目 - 新服务器构建推送脚本 (适配 NPM)
# 文件名: lo1_new_server.ps1

# 设置 Docker Hub 用户名
$dockerhub_username = "ww870411"

# 定义服务
$services = @("backend", "web")

# 定义镜像名称
$backend_image = "phoenix-backend"
$web_image = "phoenix-web"

# 生成时间戳作为标签
$timestamp = (Get-Date -Format "yyyyMMddHHmmss")
Write-Output "INFO: 生成镜像标签: $timestamp"

Write-Output "INFO: Docker Hub 用户名设置为: $dockerhub_username"
Write-Output "INFO: 根目录 .dockerignore 已排除 db_data，本地数据库挂载目录不会参与镜像打包。"
Write-Output "INFO: 开始构建生产环境镜像 (HTTP ONLY 模式)..."

Write-Output "INFO: 开始构建生产环境 ARM64 镜像 (backend, web, HTTP ONLY 模式)..."

# 1. 构建后端服务镜像 (ARM64)
docker build --platform linux/arm64 -t "$dockerhub_username/${backend_image}:$timestamp" -f backend/Dockerfile.prod .

if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 构建 $backend_image 失败。"
    exit 1
}

# 2. 构建前端 Web 服务镜像 (ARM64, 强制开启 HTTP_ONLY)
$vite_api_base = if ($env:VITE_API_BASE) { $env:VITE_API_BASE } else { "/api/v1" }
docker build --platform linux/arm64 --build-arg HTTP_ONLY=true --build-arg VITE_API_BASE=$vite_api_base -t "$dockerhub_username/${web_image}:$timestamp" -f deploy/Dockerfile.web .

if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 构建 $web_image 失败。"
    exit 1
}

Write-Output "SUCCESS: 镜像构建成功。"
Write-Output "INFO: 开始推送镜像到 Docker Hub..."

# 推送后端镜像
docker push "$dockerhub_username/${backend_image}:$timestamp"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 推送 $backend_image 失败。"
    exit 1
}

# 推送前端 Web 镜像
docker push "$dockerhub_username/${web_image}:$timestamp"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 推送 $web_image 失败。"
    exit 1
}

Write-Output "SUCCESS: 所有镜像（ARM64 / HTTP ONLY）已成功推送到 Docker Hub!"
Write-Output "--------------------------------------------------------"
Write-Output "请使用以下时间戳更新您的 lo1_new_server.yml 文件中的镜像标签: $timestamp"
Write-Output "下一步: 请在服务器上执行 'docker-compose -f lo1_new_server.yml up -d'。"
