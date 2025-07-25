# MarketStockMonitor

市场股票监控系统 - 实时获取港股恒生指数和美股纳斯达克指数数据

## 🎯 项目特性

- 🔄 实时数据获取：支持港股恒生指数(HSI)和美股纳斯达克指数(NASDAQ)
- 📊 多数据源支持：集成问财、新浪财经等数据源
- ⏰ 交易时间管理：智能识别交易时间，避免非交易时段的无效请求
- 🔔 多种通知方式：支持控制台输出、自定义通知等
- 🌐 RESTful API：提供完整的HTTP API接口
- 📈 数据处理管道：灵活的数据处理和分发机制
- 🏗️ 模块化架构：重构后的分层设计，提高可维护性

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 使用重构后的应用启动
python app.py
```

服务启动后，访问以下地址：

- 🏠 主页：http://localhost:8000/
- 📚 API文档：http://localhost:8000/docs
- 🔍 健康检查：http://localhost:8000/health
- 📊 数据源列表：http://localhost:8000/api/sources

## 📋 API接口

### 获取数据源列表
```
GET /api/sources
```

### 获取最新价格
```
GET /api/sources/{source_id}/latest/{market}/{data_type}
```

### 获取交易时间表
```
GET /api/sources/{source_id}/trading-hours/{market}
```

### 获取市场状态
```
GET /api/sources/{source_id}/market-status/{market}
```

### 获取下一个开盘时间
```
GET /api/sources/{source_id}/next-opening-time/{market}
```

## 🏪 支持的市场

- **HSI**: 港股恒生指数
- **NASDAQ**: 美股纳斯达克综合指数

## 📈 支持的数据类型

- **realtime**: 实时数据
- **kline1m**: 1分钟K线数据

## ⚙️ 配置说明

系统支持通过环境变量或`.env`文件进行配置：

```env
APP_NAME=MarketStockMonitor API
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

## 🏗️ 项目架构

### 重构后的项目结构

```
MarketStockMonitor/
├── app.py                  # 应用启动入口
├── app/                    # 重构后的应用模块
│   ├── config/            # 配置管理
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务层
│   ├── controllers/       # API控制器
│   ├── middleware/        # 中间件
│   └── utils/            # 工具函数
├── models/                # 原始数据模型
├── markt/                 # 市场数据核心
├── pipeline/              # 数据处理管道
├── wen_cai/              # 问财数据源
├── utils/                # 工具类
└── test/                 # 测试文件
```

### 架构优势

- **分层设计**: 清晰的职责分离
- **模块化**: 便于维护和扩展
- **依赖注入**: 提高代码可测试性
- **统一异常处理**: 标准化错误响应
- **配置管理**: 集中化配置

## 🔧 开发指南

### 添加新数据源

1. 继承 `AbstractFetcher` 类
2. 实现必要的接口方法
3. 在 `app/main.py` 中注册新数据源

### 添加新的API端点

1. 在 `app/controllers/` 中创建新的控制器
2. 在 `app/services/` 中添加业务逻辑
3. 在 `app/main.py` 中注册路由

### 添加新的数据处理器

1. 继承 `IProcessingHandler` 接口
2. 实现 `process` 方法
3. 在处理管道中注册

## 🧪 测试

```bash
# 运行对比测试
python test/refactor_comparison_test.py

# 运行API测试
python test/api_test.py
```

## 📖 文档

- [重构架构说明](docs/重构架构说明.md)
- [API使用指南](docs/API使用指南.md)

## 🎉 重构亮点

- ✅ 将500+行单文件拆分为模块化架构
- ✅ 实现分层设计和职责分离
- ✅ 统一异常处理和参数验证
- ✅ 提高代码可维护性和可扩展性
- ✅ 保持API完全兼容

## 📄 许可证

MIT License