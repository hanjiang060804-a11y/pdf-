#!/usr/bin/env bash
# Ubuntu 22.04+ 服务器部署（root 或 sudo）
# 私有仓库：先 git clone，再 sudo bash deploy/scripts/server-deploy.sh
set -euo pipefail

REPO_URL="${REPO_URL:-git@github.com:hanjiang060804-a11y/pdf-.git}"
BRANCH="${BRANCH:-v2/wechat-miniprogram}"
INSTALL_DIR="${INSTALL_DIR:-/opt/pdf-tra}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    return
  fi
  echo "==> 安装 Docker"
  apt-get update
  apt-get install -y ca-certificates curl git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
}

if [ -f "$DEPLOY_DIR/docker-compose.yml" ]; then
  INSTALL_DIR="$(cd "$DEPLOY_DIR/.." && pwd)"
  cd "$DEPLOY_DIR"
  echo "==> 使用已克隆仓库: $INSTALL_DIR"
  install_docker
else
  install_docker
  echo "==> 拉取代码 → $INSTALL_DIR"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
  else
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR"
  fi
  cd "$INSTALL_DIR/deploy"
fi

echo "==> 准备配置"
mkdir -p data/uploads
if [ ! -f data/config.json ]; then
  cp ../config.example.json data/config.json
  echo "请编辑 deploy/data/config.json 填入 DEEPSEEK_API_KEY"
fi
if [ ! -f .env ]; then
  cp .env.example .env
  echo "请编辑 deploy/.env 填入 WECHAT_* 与 JWT_SECRET"
fi

echo "==> 构建并启动"
docker compose build --pull
docker compose up -d

echo ""
echo "==> 健康检查"
sleep 5
curl -sf "http://127.0.0.1:8787/health" && echo " OK" || echo " 等待 API 启动…"

echo ""
echo "完成。下一步："
echo "  1. 编辑 $INSTALL_DIR/deploy/data/config.json（DeepSeek Key）"
echo "  2. 编辑 $INSTALL_DIR/deploy/.env（微信 + JWT）"
echo "  3. cd $INSTALL_DIR/deploy && docker compose restart"
echo "  4. 配置域名 HTTPS，微信后台合法域名"
echo "  5. 小程序 app.js apiBase 改为 https://你的域名"
