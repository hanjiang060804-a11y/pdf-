# 1Panel 部署墨流 2.0 云 API

文件已在 `/opt/pdf-tra` 时，按此文档操作（**不要用** compose 里的 nginx，避免和 1Panel 抢 80 端口）。

---

## 1. 准备配置

在 **1Panel 终端** 或 SSH：

```bash
cd /opt/pdf-tra/deploy
mkdir -p data/uploads

# 若还没有 config
cp ../config.example.json data/config.json
cp .env.example .env

nano data/config.json   # 填 DEEPSEEK_API_KEY
nano .env               # WECHAT_APP_ID, WECHAT_APP_SECRET, JWT_SECRET（≥32 字符）
```

`.env` **不要** 设置 `PDF_TRA_CLOUD_DEV`（生产环境）。

---

## 2. 启动（启动脚本）

```bash
cd /opt/pdf-tra/deploy
docker compose -f docker-compose.1panel.yml up -d --build
```

| 操作 | 命令 |
|------|------|
| 启动 | `docker compose -f docker-compose.1panel.yml up -d` |
| 重启 | `docker compose -f docker-compose.1panel.yml restart` |
| 停止 | `docker compose -f docker-compose.1panel.yml down` |
| 日志 | `docker compose -f docker-compose.1panel.yml logs -f api` |
| 更新重建 | `docker compose -f docker-compose.1panel.yml up -d --build` |

验证：

```bash
curl http://127.0.0.1:8787/health
# {"status":"ok","service":"pdf-tra-cloud"}
```

---

## 3. 1Panel 图形界面（编排）

1. **容器** → **编排** → **创建编排**
2. 名称：`pdf-tra`
3. 路径：`/opt/pdf-tra/deploy/docker-compose.1panel.yml`
4. 保存并 **启动**

或在 **终端** 里执行上面第 2 节命令即可。

---

## 4. 1Panel 反代 + HTTPS

1. **网站** → **创建网站** → **反向代理**
2. 主域名：`api.hanjianglab.com`（DNS A 记录 → 服务器 IP）
3. 代理地址：`http://127.0.0.1:8787`
4. **SSL** → 申请 Let's Encrypt 证书并开启 HTTPS
5. 高级：上传/请求体大小建议 **25MB**（PDF 上传）

微信小程序后台 → 服务器域名 → 三项都填：`https://api.hanjianglab.com`

---

## 5. 目录说明

```
/opt/pdf-tra/
├── pdf_tra/              # 源码
├── deploy/
│   ├── docker-compose.1panel.yml   ← 1Panel 用这个
│   ├── .env                        # 微信 + JWT
│   └── data/
│       ├── config.json             # DeepSeek
│       └── uploads/                # 用户 PDF（临时）
└── miniprogram/                    # 小程序源码（不在服务器跑）
```

---

## 6. 常见问题

| 问题 | 处理 |
|------|------|
| 80 端口冲突 | 只用 `docker-compose.1panel.yml`，别启动自带 nginx |
| build 很慢 | 首次需拉 Python 镜像 + pip 装 pdf2zh，约 5–15 分钟 |
| 8787 不通 | `docker compose logs api` 看报错；检查 `data/config.json` |
| 小程序连不上 | 1Panel 是否已 HTTPS；域名是否在微信合法域名里 |
