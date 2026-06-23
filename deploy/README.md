# 墨流 2.0 云 API — 服务器部署

分支：`v2/wechat-miniprogram`

## 方式一：一键脚本（推荐 Ubuntu 22.04+）

```bash
curl -fsSL https://raw.githubusercontent.com/hanjiang060804-a11y/pdf-/v2/wechat-miniprogram/deploy/scripts/server-deploy.sh | sudo bash
```

或克隆后：

```bash
sudo bash deploy/scripts/server-deploy.sh
```

默认安装目录：`/opt/pdf-tra`

## 方式二：手动 Docker Compose

```bash
git clone -b v2/wechat-miniprogram https://github.com/hanjiang060804-a11y/pdf-.git /opt/pdf-tra
cd /opt/pdf-tra/deploy

mkdir -p data/uploads
cp ../config.example.json data/config.json   # 编辑 DEEPSEEK_API_KEY
cp .env.example .env                           # 编辑 WECHAT_*、JWT_SECRET

docker compose build
docker compose up -d
curl http://127.0.0.1:8787/health
```

## 目录结构（deploy/）

```
deploy/
├── Dockerfile
├── docker-compose.yml      # api + nginx
├── .env                    # 微信、JWT（勿提交）
├── data/
│   ├── config.json         # DeepSeek（勿提交）
│   └── uploads/            # 用户 PDF 临时目录
├── nginx/
│   ├── default.conf
│   └── ssl.conf.example
└── scripts/
    └── server-deploy.sh
```

## HTTPS 与域名

1. 域名 A 记录指向服务器 IP
2. 安装 certbot，申请证书
3. 参考 `nginx/ssl.conf.example` 启用 443
4. 微信小程序后台 → 开发管理 → 服务器域名：
   - request / uploadFile / downloadFile → `https://api.你的域名.com`

## 小程序指向服务器

编辑 `miniprogram/app.js`：

```javascript
globalData: {
  apiBase: "https://api.你的域名.com",
},
```

重新上传体验版。

## 运维命令

```bash
cd /opt/pdf-tra/deploy
docker compose logs -f api
docker compose restart api
docker compose pull && docker compose up -d --build   # 更新版本
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `WECHAT_APP_ID` / `WECHAT_APP_SECRET` | 小程序凭证 |
| `JWT_SECRET` | JWT 签名，≥32 字符 |
| `PDF_TRA_CLOUD_DEV` | 生产必须为 false 或未设置 |
| `PDF_TRA_CONFIG` | 容器内默认 `/data/config.json` |
| `PDF_TRA_UPLOAD_DIR` | 容器内默认 `/data/uploads` |

## 本地开发

见上文「方式二」或：

```powershell
$env:PDF_TRA_CLOUD_DEV = "true"
$env:JWT_SECRET = "dev-jwt-secret-key-32chars!!!!"
python -m pdf_tra.cloud
```

## 健康检查

`GET /health` → `{"status":"ok","service":"pdf-tra-cloud"}`
