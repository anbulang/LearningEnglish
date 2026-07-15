# 公网部署 Runbook（腾讯云轻量 + Caddy 免费 HTTPS + 本地盘）

把后端从「本地/局域网调试」推到「真实家庭用真机直接访问」的最小公网交付形态。形态：单台腾讯云
轻量应用服务器跑 `postgres + redis + api + worker + caddy`，Caddy 自动签发 Let's Encrypt 证书提供
HTTPS，录音/配图等用**本地盘**（不接 OSS），由 api 的 `/uploads` 对外服务。试点登录用**白名单**
（`IDENTITY_PROVIDER=pilot`），不接真微信/短信。

脚手架文件：`infra/docker-compose.prod.yml` · `infra/Caddyfile` · `infra/env/prod.example.env` ·
`make deploy-prod-up/-down/-logs`。

## 0. 前置（你需要开通）

- 一台**腾讯云轻量应用服务器**（建议 2C4G 起；镜像 Ubuntu 22.04 LTS）。
- 一个**域名** + 一条 **DNS A 记录**指向轻量实例的公网 IP。
- **DASHSCOPE_API_KEY**（阿里云 DashScope/百炼，AI+媒体+口语共用）。
- 试点家庭名单（每户一个登录 `code`，可附姓名/手机号）。
- 强密钥：`JWT_SECRET`（`openssl rand -hex 32`）、`POSTGRES_PASSWORD`、`ADMIN_API_TOKEN`。

> **ICP 备案**：腾讯云**境内**实例 + 境内解析域名需先完成 ICP 备案才能在 80/443 正常对外服务。
> 白名单试点不接微信/短信，因此也可先用**境外轻量实例 + 未备案域名**打通验证；后续若上真微信
> OAuth 需要备案域名。

## 1. 实例与网络

1. 创建实例，登录（`ssh ubuntu@<公网IP>`）。
2. 防火墙/安全组放行 **22 / 80 / 443**。
3. 安装 Docker + Compose 插件：
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER && newgrp docker
   docker compose version
   ```
4. 确认 DNS：`dig +short <你的域名>` 返回实例公网 IP（证书签发依赖它已生效）。

## 2. 拉代码 + 填 env

```bash
git clone <repo> learning-english && cd learning-english
cp infra/env/prod.example.env infra/env/prod.env
vi infra/env/prod.env   # 填「必填」项：PUBLIC_DOMAIN / POSTGRES_PASSWORD / JWT_SECRET /
                        # ADMIN_API_TOKEN / DASHSCOPE_API_KEY / PILOT_ALLOWLIST_JSON
```

`infra/env/prod.env` 含真实密钥，已被 `.gitignore` 忽略，**切勿提交**。`APP_ENV / PUBLIC_BASE_URL /
DATABASE_URL / STORAGE_BACKEND / LOCAL_STORAGE_PATH` 由 compose 自动注入，无需在 env 里设。

## 3. 起服务

```bash
make deploy-prod-up        # = docker compose --env-file infra/env/prod.env -f infra/docker-compose.prod.yml up -d --build
make deploy-prod-logs      # 跟随日志
```

- 数据库表由 api 启动时 `init_db()` 自动创建；如使用 Alembic 迁移为准，另跑 `make api-migrate`
  （`DATABASE_URL` 指向本机 postgres）。
- **生产守卫**：若 readiness 不通过（如缺 `DASHSCOPE_API_KEY`、`PUBLIC_BASE_URL` 非公网、
  `IDENTITY_PROVIDER` 仍是 `dev`），api **拒绝启动**并在日志打印缺失项——这是预期行为。

## 4. 验收

```bash
curl -s https://<域名>/healthz            # {"status":"ok"}
curl -s https://<域名>/readyz | jq        # ready=true，components 全 ready
```

- 故意把 `IDENTITY_PROVIDER=dev` 重启 → api 应拒绝启动（身份组件 not ready）。验毕改回 `pilot`。
- **白名单登录隔离**：用名单内 `code` 调 `POST /v1/auth/wechat/login` 应直接 `authenticated`；
  名单外 `code` 应返回 **403**；两个不同 `code` 得到不同账号、互不可见对方孩子。
- **媒体/口语冒烟**（对公网域名）：跑主链冒烟，确认配图/TTS 的 URL 形如 `https://<域名>/uploads/...`
  可公网拉取；口语评分不再因私网地址 fail-fast（DashScope 能拉到录音）。
  参考 `docs/harness/upload-recognition-loop.md` 与 `make harness-main-chain-smoke`。

## 5. App 指向

试点家庭的 App 在「设置 → 服务器地址」（`/settings/server`）填 `https://<域名>/v1`；或出包时用
`make mobile-ios-ipa IOS_API_BASE_URL=https://<域名>/v1`。

## 6. 运维注意

- **本地盘持久化**：上传与生成媒体存于命名卷 `uploads_data`、数据库存于 `postgres_data`。定期备份：
  ```bash
  docker run --rm -v infra_uploads_data:/d -v $PWD:/b alpine tar czf /b/uploads-backup.tgz -C /d .
  docker exec le-prod-postgres pg_dump -U learning_english learning_english > db-backup.sql
  ```
- 证书：Caddy 自动续期，证书存于 `caddy_data` 卷，勿随意清空。
- 升级：`git pull && make deploy-prod-up`（重建镜像、滚动重启）。
