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
Write-Output "INFO: 开始构建生产环境镜像 (backend, web)..."

# 使用 docker-compose.server.yml 构建指定服务的镜像
docker-compose -f docker-compose.server.yml build $services

# 检查构建是否成功
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 镜像构建失败，请检查 docker-compose 输出。"
    exit 1
}

Write-Output "SUCCESS: 镜像构建成功。"
Write-Output "INFO: 开始为镜像添加标签..."

# 为镜像打上 Docker Hub 标签
docker tag $backend_image "$dockerhub_username/${backend_image}:$timestamp"
docker tag $web_image "$dockerhub_username/${web_image}:$timestamp"

Write-Output "SUCCESS: 标签添加成功。"
Write-Output "  - $dockerhub_username/${backend_image}:$timestamp"
Write-Output "  - $dockerhub_username/${web_image}:$timestamp"

Write-Output "INFO: 开始推送镜像到 Docker Hub..."

# 推送镜像
docker push "$dockerhub_username/${backend_image}:$timestamp"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 推送 $backend_image 失败。"
    exit 1
}

docker push "$dockerhub_username/${web_image}:$timestamp"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ERROR: 推送 $web_image 失败。"
    exit 1
}

Write-Output "SUCCESS: 所有镜像已成功推送到 Docker Hub!"
Write-Output "请使用以下时间戳更新您的 lo1.yml 文件中的镜像标签: $timestamp"
Write-Output "下一步: 请将更新后的 'lo1.yml' 文件上传到您的服务器，并执行 'docker-compose -f lo1.yml up -d'。"
