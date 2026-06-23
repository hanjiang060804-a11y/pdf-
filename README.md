# 墨流

在本机把 PDF 译成中文，尽量保留原版排版（公式、图表、目录）。

基于 [PDFMathTranslate](https://github.com/Byaidu/PDFMathTranslate) 与 [DeepSeek](https://www.deepseek.com/)，PDF 文件留在你的电脑上，只有待翻译的文字会发送到 API。

---

## 能做什么

- **文字版 PDF**：拖进去就能翻，自动识别源语言
- **扫描版 PDF**：先 OCR 再翻译（需额外安装 OCR 组件）
- **两种输出**：纯中文版，或中英对照版
- **网页或命令行**：习惯哪种用哪种

---

## 安装

**需要**：Windows 10/11、Python 3.10～3.12、[Poppler](https://github.com/oschwartz10612/poppler-windows/releases)、DeepSeek API Key。

```powershell
# 1. 克隆并进入项目
git clone https://github.com/hanjiang060804-a11y/pdf-.git
cd pdf-

# 2. 一键安装依赖（国内网络可用 setup-mirror.ps1）
.\scripts\setup.ps1

# 3. 配置 API Key
copy config.example.json config.json
notepad config.json
```

在 `config.json` 里把 `DEEPSEEK_API_KEY` 改成你的密钥（在 [DeepSeek 开放平台](https://platform.deepseek.com/) 申请）。

> 扫描版 PDF 还需安装 Tesseract、Ghostscript 等，步骤见 [安装指南](docs/安装指南.md)。

---

## 使用（网页，推荐）

```powershell
.\.venv\Scripts\Activate.ps1
python -m pdf_tra.web
```

浏览器打开 **http://127.0.0.1:7860**：

1. 拖入或点击选择本机 PDF  
2. 查看页数、语言、是否扫描版  
3. 点击「开始翻译」  
4. 完成后下载纯译文或对照版  

设置里可填写 API Key、选择排版引擎（一般保持默认即可）。

---

## 使用（命令行）

```powershell
.\.venv\Scripts\Activate.ps1

# 查看 PDF 信息（页数、能否翻译）
python -m pdf_tra inspect 论文.pdf

# 翻译文字版
python -m pdf_tra translate 论文.pdf -o output/

# 翻译扫描版
python -m pdf_tra translate 扫描件.pdf --ocr -o output/
```

结果在 `output/` 目录：`论文-mono.pdf`（纯中文）、`论文-dual.pdf`（对照）。

---

## 常见问题

| 问题 | 处理 |
|------|------|
| 提示找不到 `pdfinfo` | 安装 Poppler 并加入 PATH，见 [安装指南](docs/安装指南.md) |
| 提示找不到 `pdf2zh` | 确认已运行 `setup.ps1` 并激活 `.venv` |
| Python 3.13 装不上 pdf2zh | 请使用 Python 3.10～3.12 |
| 扫描版无法翻译 | 按安装指南补装 ocrmypdf、Tesseract、Ghostscript |
| 翻译失败 / 401 | 检查 `config.json` 中的 API Key 是否正确、有余额 |

---

## 隐私说明

- PDF 在本机读取与处理  
- 仅翻译所需的文本片段发送至 DeepSeek API  
- `config.json` 含 API Key，请勿分享或上传到公开仓库  

---

## 许可证

本项目编排代码许可证待定；[pdf2zh](https://github.com/Byaidu/PDFMathTranslate) 等上游工具遵循各自开源协议（pdf2zh 为 AGPL-3.0）。

安装与依赖说明见 [docs/安装指南.md](docs/安装指南.md)。
