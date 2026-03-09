时间：2026-03-09
主题：Phoenix 脏状态 bridge 网络已成功移除

用户回传：
- `docker network inspect 25-26_phoenix_net` 显示：
  - `Containers: {}`
  - 但 `IPsInUse: 3`
- 随后用户成功执行：
  - `docker network rm 25-26_phoenix_net`
- 删除后 `docker network ls` 中该网络已消失。

判断：
- 这证明先前 Phoenix bridge 网络确实存在脏 IPAM 状态。
- 当前最合理的下一步是重新通过 `lo1_new_server.yml` 拉起 Phoenix，让 Docker 创建一张全新的网络并重新验证 `web -> backend`。