# MarketStockMonitor

股票/指数数据抓取通知服务

## 项目简介

MarketStockMonitor 是一个基于 Python 异步生态的金融数据服务系统，用于实时抓取股票/指数数据并在满足特定条件时发送通知。系统采用显式代码构建服务关系，处理流程高度可定制，稳定可靠。

核心功能：
- 实时抓取股票/指数数据
- 根据交易时间动态判断市场状态
- 通过 Webhook 和 SSE 推送数据通知
- 支持数据处理管道和责任链模式
- 具备重试机制和死信队列保障数据可靠性

## 技术栈

- **Web 框架**: FastAPI
- **异步 HTTP 客户端**: HTTPX
- **数据结构与校验**: Pydantic
- **定时任务**: APScheduler (AsyncIOScheduler)
- **日志**: Loguru
- **数据库 (用于DLQ)**: MySQL + SQLAlchemy (Asyncio Extension)
- **SSE 推送**: sse-starlette

## 目录结构

```
app/
├── core/          # 核心组件
├── models/        # 数据模型
├── schemas/       # 数据模式定义
├── api/           # API 接口
├── services/      # 业务服务
└── utils/         # 工具函数
tests/             # 测试文件
wen_cai/           # 问财数据抓取模块
docs/              # 文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基本使用

1. 配置环境变量和数据库连接
2. 启动服务：
   ```bash
   python main.py
   ```
3. 服务将根据配置的策略自动抓取数据并推送通知

## 开发规范

项目遵循谷歌Python开发规范，确保代码质量和一致性。