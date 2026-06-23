# 墨流 2.0 · 微信小程序

> **产品版本**：2.0（与 1.x 本机 Web/CLI 分离）  
> **状态**：规划中  
> **主分支开发**：`v2/wechat-miniprogram`

---

## 1.x 与 2.0 的区别

| | **1.x（当前 main）** | **2.0（本目录）** |
|---|---------------------|-------------------|
| 形态 | 本机 Web + CLI | 微信小程序 + 云端 API |
| PDF 处理 | 本地 `pdf_tra` 流水线 | 服务器跑同一套 `service` |
| 文件来源 | 电脑拖拽/选择 | 微信聊天 / 本地文件上传 |
| API Key | 用户本机 `config.json` | 服务端托管（+ 配额） |
| 隐私 | 文件不出本机 | 需上传 PDF，用户协议说明 |

**共用**：`pdf_tra/` 核心包（pipeline、steps、service）——不 fork 两套翻译逻辑。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [项目概述.md](./项目概述.md) | 目标、范围、里程碑 |
| [分支与协作.md](./分支与协作.md) | Git 分支、合并、发布策略 |
| [技术方案.md](./技术方案.md) | 云 API、鉴权、存储、部署 |
| [小程序设计.md](./小程序设计.md) | 页面、流程、微信 API |
| [hanjianglab.com.md](./hanjianglab.com.md) | **122.152.207.51** 生产部署步骤 |

---

## 代码规划（尚未创建）

```
pdf-tra/
├── pdf_tra/              # 共用核心（main 与 v2 同步修复）
├── miniprogram/          # v2：微信小程序
├── deploy/                 # v2：云部署（Docker / 腾讯云）
└── docs/v2/              # v2 文档（本目录）
```

---

## 快速命令

```powershell
# 切换到 v2 开发分支
git checkout v2/wechat-miniprogram

# 从 main 同步核心修复
git checkout v2/wechat-miniprogram
git merge main
```
