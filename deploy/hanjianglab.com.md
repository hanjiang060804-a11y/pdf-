# 墨流 2.0 · hanjianglab.com 服务器部署

> 服务器：`122.152.207.51`  
> 建议 API 域名：`https://api.hanjianglab.com`

---

## 1. DNS

在域名控制台添加 **A 记录**：

| 主机记录 | 类型 | 值 |
|----------|------|-----|
| `api` | A | `122.152.207.51` |

验证：`ping api.hanjianglab.com` 应解析到 `122.152.207.51`

---

## 2. 服务器部署（SSH 登录 122.152.207.51 后）

### 2.0 配置 GitHub SSH（首次必做）

私有仓库 **不能 curl 脚本**（404），也 **不能无公钥 git clone**。

```bash
# 以 ubuntu 用户执行（不要 sudo）
ssh-keygen -t ed25519 -C "hanjianglab-vm" -f ~/.ssh/id_ed25519 -N ""

cat ~/.ssh/id_ed25519.pub
```

复制输出 → GitHub → **Settings → SSH and GPG keys → New SSH key**（或仓库 **Settings → Deploy keys** 只读即可）

测试：

```bash
ssh -T git@github.com
# 应看到 Hi hanjiang060804-a11y!
```

> ⚠️ 不要用 `sudo git clone`，否则用的是 root 的 `~/.ssh`，容易 Permission denied。

### 2.1 克隆与部署

```bash
# 不要用 sudo clone
git clone -b v2/wechat-miniprogram git@github.com:hanjiang060804-a11y/pdf-.git /tmp/pdf-tra
sudo mv /tmp/pdf-tra /opt/pdf-tra
sudo chown -R ubuntu:ubuntu /opt/pdf-tra

sudo bash /opt/pdf-tra/deploy/scripts/server-deploy.sh
```

---

## 3. 配置

```bash
# DeepSeek
sudo nano /opt/pdf-tra/deploy/data/config.json

# 微信 + JWT（生产勿开 PDF_TRA_CLOUD_DEV）
sudo nano /opt/pdf-tra/deploy/.env
```

`.env` 示例：

```bash
WECHAT_APP_ID=wx你的AppID
WECHAT_APP_SECRET=你的Secret
JWT_SECRET=请用至少32位随机字符串
```

---

## 4. HTTPS（Let's Encrypt）

```bash
sudo apt-get install -y certbot

# 先确保 80 端口可访问（docker compose 已启动 nginx）
cd /opt/pdf-tra/deploy
sudo docker compose up -d

# 申请证书（按提示填 api.hanjianglab.com）
sudo certbot certonly --standalone -d api.hanjianglab.com --pre-hook "docker compose stop nginx" --post-hook "docker compose start nginx"
```

启用 HTTPS：编辑 `deploy/nginx/default.conf`，或挂载 `ssl.conf.example` 并改为：

- 证书路径：`/etc/letsencrypt/live/api.hanjianglab.com/`
- `server_name api.hanjianglab.com;`

`docker-compose.yml` 中 nginx 增加卷：

```yaml
- /etc/letsencrypt:/etc/letsencrypt:ro
```

然后：

```bash
cd /opt/pdf-tra/deploy
sudo docker compose up -d --force-recreate
curl https://api.hanjianglab.com/health
```

---

## 5. 微信小程序

1. [微信公众平台](https://mp.weixin.qq.com/) → 开发管理 → 服务器域名  
2. **request / uploadFile / downloadFile** 均填：`https://api.hanjianglab.com`  
3. 修改小程序 `miniprogram/app.js`：

```javascript
globalData: {
  apiBase: "https://api.hanjianglab.com",
},
```

4. 重新上传体验版

---

## 6. 防火墙

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 7. 运维

```bash
cd /opt/pdf-tra/deploy
sudo docker compose logs -f api
sudo docker compose restart
git -C /opt/pdf-tra pull && sudo docker compose up -d --build
```

健康检查：`curl https://api.hanjianglab.com/health`
