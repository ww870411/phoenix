时间：2026-03-09
主题：Docker 自定义网络在容器停止后仍保留的判断

用户现象：
- `docker ps` 为空，没有运行容器。
- `docker network ls` 仍可见 `25-26_phoenix_net`。

判断：
- 这属于 Docker 正常行为。
- compose 创建的用户自定义 bridge 网络，不会因为容器停止而自动删除。
- 只有以下情况才会删除：
  1) `docker compose down`
  2) 显式 `docker network rm <network>`

后续排查顺序：
1. 先用 `docker ps -a` 检查是否有已停止但未删除的容器仍挂在该网络；
2. 用 `docker network inspect 25-26_phoenix_net` 查看是否仍有 Containers/Endpoints；
3. 若无占用则可直接删除该网络；
4. 若删除后重建仍异常，再进入 Docker daemon 级网络重置或改 subnet。