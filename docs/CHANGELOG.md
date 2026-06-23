# 变更日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 文档

- `web_server.md`：补充用户流程边缘情况表与 HTTP 状态映射

### 代码

- Web API：`PdfTraError` 统一转 HTTP 响应；上传文件名消毒；翻译前路径校验
- 前端：非 PDF 拦截、422 错误解析、按 `has_mono`/`has_dual` 显示下载按钮
- 新增 `tests/test_web/test_api_boundary.py`（20 项边界用例）

## [0.2.0] - 2026-06-23

### 新增

- Phase 3：扫描版 OCR（ocrmypdf、实时页码进度、`pdftotext_post`）
- Phase 4：BabelDOC 默认排版引擎、classic 回退、`PolishStep` 译后溢出修正
- Web：`pdf_tra/web/` FastAPI + PaperFlow SPA（7860）
- 服务层：`pdf_tra/service.py`（CLI/Web 共用 inspect/translate）
- 自动语言识别（`core/lang.py`）
- 翻译 prompt 模板（`prompts/`）

### 变更

- Web 导入收敛为仅本机拖拽/选择（移除微信/QQ/浏览 API）
- subprocess 适配器增强 venv `Scripts` PATH 解析
- 英译中 prompt：不再压字数，保留特殊字体占位符
- 重写 `README.md`；更新 `docs/项目结构.md` v1.1

### 文档

- `layout_engine.md`、`scanned_ocr.md`、`file_import.md` v0.3
- 前端设计、service/web 规格同步

### 测试

- 158+ pytest 用例

## [0.1.0] - 2026-06-23

### 文档

- 初始化项目文档 v0.1.0
  - `docs/项目概述.md`：项目目标、功能范围、里程碑、待确认事项
  - `docs/开发流程.md`：文档驱动开发流程、Git 提交规范、审核检查清单
  - `docs/技术设计.md`：架构、目录结构、CLI、配置、模块设计
  - `README.md`：项目入口与文档索引

---

## 版本说明

- **文档版本**与**代码版本**在发布时对齐
- 当前文档版本：**v0.2.0（已审核）**
- 当前代码版本：**v0.2.0**
