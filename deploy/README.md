# 墨流 2.0 云 API 部署

## 环境变量

复制 `.env.example` 为 `.env` 并填写。

## 本地开发

```powershell
$env:PDF_TRA_CLOUD_DEV = "true"
$env:JWT_SECRET = "dev-jwt-secret-change-me-32c"
.\.venv\Scripts\python.exe -m pdf_tra.cloud
# http://127.0.0.1:8787
```

小程序 `miniprogram/app.js` 中 `apiBase` 指向上述地址；开发者工具勾选「不校验合法域名」。

开发登录：小程序 `wx.login` 后服务端在 dev 模式下 `code=dev` 可用手动测试；真机联调需配置微信 AppID/Secret。

## 生产

1. Linux 服务器安装 Poppler、pdf2zh（同 1.x 安装指南）
2. `config.json` 配置 DeepSeek API Key（勿提交 Git）
3. 设置 `WECHAT_APP_ID`、`WECHAT_APP_SECRET`、`JWT_SECRET`
4. `uvicorn pdf_tra.cloud.app:create_cloud_app --factory --host 0.0.0.0 --port 8787`
5. Nginx 反代 + HTTPS，域名填入微信后台合法域名

## 健康检查

`GET /health` → `{"status":"ok"}`
