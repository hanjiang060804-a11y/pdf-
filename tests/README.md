# 测试目录说明
#
# tests/ 与 pdf_tra/ 源码分离，按分层镜像组织：
#
#   test_core/       错误码、模型、常量
#   test_adapters/   subprocess 适配器
#   test_config/     配置加载与校验（含边界用例 *_boundary.py）
#   test_steps/      各 Step 单元与边界测试
#   test_pipeline/   流水线注册与编排
#   test_cli/        CLI 入口与端到端 mock 流程
#   fixtures/        静态测试数据（JSON、pdfinfo 文本）
#
# 运行：pytest
# 原则：mock 外部 CLI，不调用真实 DeepSeek / pdf2zh
