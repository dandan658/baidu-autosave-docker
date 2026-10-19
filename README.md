# 百度网盘自动转存订阅（Docker）

基于 [kokojacket/baidu-autosave](https://github.com/kokojacket/baidu-autosave)，保留 AGPL-3.0 许可证。上游基线：`85203fda4bb027e926494acaeb3736b1df5a93c2`。

订阅指周期检查已添加的百度网盘分享链接，将新增文件转存到自己的网盘，使用上游的去重逻辑。不是 RSS 内容聚合或文件下载器。

## 直接拉取镜像（推荐）

镜像：`ghcr.io/dandan658/baidu-autosave-docker:latest`，支持 Linux amd64 和 arm64。公开后无需登录 GHCR。

```sh
docker pull ghcr.io/dandan658/baidu-autosave-docker:latest
docker run -d --name baidu-autosave --restart unless-stopped --init \
  -p 127.0.0.1:5000:5000 \
  -e TZ=Asia/Shanghai \
  -v baidu-autosave-config:/app/config \
  -v baidu-autosave-log:/app/log \
  ghcr.io/dandan658/baidu-autosave-docker:latest
docker logs baidu-autosave
```

以上多行命令适用于 Linux/macOS shell。PowerShell 可将 `docker run` 各行合并成一行。
默认只允许本机访问。要从局域网访问，将 `-p 127.0.0.1:5000:5000` 改成 `-p 5000:5000`。

也可克隆仓库后使用预构建版本的 Compose：

```sh
docker compose -f compose.prebuilt.yaml pull
docker compose -f compose.prebuilt.yaml up -d
docker compose -f compose.prebuilt.yaml logs --tail=100
```

升级时再次运行上述 `pull` 和 `up -d`，账号和任务保留在挂载目录中。源码构建版本与预构建版本任选其一，避免同时占用 5000 端口。

## 从源码构建启动

需要 Docker Engine / Docker Desktop 和 Docker Compose v2。

```sh
cp .env.example .env
docker compose up -d --build
docker compose logs baidu-autosave
```

PowerShell 用户将第一条命令替换为 `Copy-Item .env.example .env`。
打开 http://localhost:5000 。用户名默认 `admin`。首次启动前可在 `.env` 设置 `ADMIN_PASSWORD`；留空时随机生成，查看启动日志中的 `Initial admin password`。初始化后，环境变量不会覆盖现有账号，请在界面修改密码。

## 配置订阅

1. 登录百度网盘网页版，在浏览器开发者工具的网络请求中复制自己账号的 Cookie。
2. 在本服务的用户管理中添加百度账号，填入 Cookie 并验证。
3. 新建转存任务，填写分享链接、提取码、目标网盘目录，并选择账号。
4. 设置全局或单任务 Cron。例如 `*/30 * * * *` 为每 30 分钟；`0 10 * * *` 为每天 10 点。默认时区为上海。
5. 先手动执行一次，确认目标目录与日志，再保留定时任务运行。可继续配置文件过滤和通知。

Cookie 失效后需重新填写；分享失效、验证码、账号风控或容量不足会导致转存失败。实际转存需要用户自己的有效账号与分享链接。

## 持久化和维护

配置、账号凭据、任务保存在 `data/config`，日志在 `data/log`。备份这两个目录即可，勿提交到公开仓库。会话密钥也持久保存在配置目录，重启不会主动更换。

```sh
docker compose ps
docker compose logs -f --tail=100
docker compose down
docker compose up -d --build
```

默认只绑定本机。局域网部署可将 `.env` 的 `BIND_ADDRESS` 改为 `0.0.0.0`，通过服务器 IP 访问；远程使用建议经 HTTPS 反向代理。端口可通过 `WEB_PORT` 修改。

容器健康检查同时检查 Web 服务和调度器。单实例运行，避免多个调度器重复执行同一份任务。健康状态异常请检查日志；Docker 的 restart 策略只在进程退出时生效。

## 本版本修改

- 从源码构建 Vue 前端与 Python 3.10 后端。
- 首次启动生成管理密码与独立的持久化会话密钥。
- 持久化配置和日志，限制 Docker 日志大小。
- 新增 `/healthz` 调度器健康检查。
- 排除上游示例 Cookie、历史配置及无关文件。

## 自动构建发布

[GitHub Actions 构建记录](https://github.com/dandan658/baidu-autosave-docker/actions/workflows/docker-publish.yml)

- 推送到 `main`：分别在 amd64、arm64 原生运行器构建，完成启动、调度器健康、前端、登录和重启会话保留检查，均通过才合并发布 `latest`。
- 推送 `v*` 标签：发布原始标签及去掉 `v` 的版本标签，例如 `v1.0.0` 和 `1.0.0`；不会覆盖 `latest`。
- 每次成功构建还发布 `sha-<提交前12位>`，可用于固定版本及回滚。
- 支持在 Actions 页面手动运行。使用仓库的 `GITHUB_TOKEN`，无需设置个人令牌或 Docker Hub 密码。
- 本仓库 GHCR 包已确认为 Public。发布流程会使用空 Docker 配置验证匿名访问及两个架构的镜像清单；无需登录即可拉取。

镜像检查不使用真实百度凭据；百度账号端到端转存仍需用户自行验证。原项目说明见 `UPSTREAM_README.md`。
