# MarketStockMonitor API 使用指南

## 概述

MarketStockMonitor 是一个重构后的市场股票监控系统，采用模块化架构设计，提供完整的REST API端点用于获取市场数据、交易时间表和市场状态信息。

## 🚀 快速开始

### 启动服务
```bash
python app.py
```

### 访问地址
- **主页**: http://localhost:8000/
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 📋 API 端点

### 1. 健康检查

**端点**: `GET /health`

**描述**: 检查API服务健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00.123456",
  "uptime": "0:05:30.123456",
  "sources_count": 1
}
```

**使用示例**:
```bash
curl http://localhost:8000/health
```

### 2. 获取数据源列表

**端点**: `GET /api/sources`

**描述**: 获取系统中所有可用的数据源列表及其支持的市场

**响应示例**:
```json
[
  {
    "source_id": "wen_cai",
    "source_name": "问财",
    "supported_markets": ["HSI", "NASDAQ"]
  }
]
```

**使用示例**:
```bash
curl http://localhost:8000/api/sources
```

### 3. 获取最新价格数据

**端点**: `GET /api/sources/{source_id}/latest/{market}/{data_type}`

**描述**: 获取指定数据源的指定市场的最新价格数据

**参数**:
- `source_id`: 数据源ID (如: wen_cai)
- `market`: 市场代码 (HSI, NASDAQ)
- `data_type`: 数据类型 (realtime, kline1m)

**响应示例**:
```json
{
  "source_id": "wen_cai",
  "market": "HSI",
  "data_type": "realtime",
  "data": {
    "name": "恒生指数",
    "time": "2024-01-15T14:30:00",
    "price": 16250.5,
    "volume": 1234567,
    "change": -125.3,
    "change_percent": -0.76
  }
}
```

**使用示例**:
```bash
# 获取HSI实时价格
curl http://localhost:8000/api/sources/wen_cai/latest/HSI/realtime

# 获取NASDAQ K线数据
curl http://localhost:8000/api/sources/wen_cai/latest/NASDAQ/kline1m
```

### 4. 获取交易时间表

**端点**: `GET /api/sources/{source_id}/trading-hours/{market}`

**描述**: 获取指定市场的特殊交易时间表（包括节假日安排等）

**参数**:
- `source_id`: 数据源ID (如: wen_cai)
- `market`: 市场代码 (HSI, NASDAQ)

**响应示例**:
```json
{
  "source_id": "wen_cai",
  "market": "HSI",
  "trading_hours": [
    {
      "start": "2024-12-26T00:00:00+08:00",
      "end": "2024-12-27T00:00:00+08:00",
      "text": "圣诞节翌日"
    },
    {
      "start": "2024-12-31T12:00:00+08:00",
      "end": "2025-01-01T00:00:00+08:00",
      "text": "新年前夕休市半日"
    },
    {
      "start": "2025-04-04T00:00:00+08:00",
      "end": "2025-04-05T00:00:00+08:00",
      "text": "清明节休市"
    }
  ]
}
```

**使用示例**:
```bash
# 获取HSI交易时间表
curl http://localhost:8000/api/sources/wen_cai/trading-hours/HSI

# 获取NASDAQ交易时间表
curl http://localhost:8000/api/sources/wen_cai/trading-hours/NASDAQ
```

### 5. 获取市场状态

**端点**: `GET /api/sources/{source_id}/market-status/{market}`

**描述**: 获取指定市场在特定时间的开盘状态

**参数**:
- `source_id`: 数据源ID (如: wen_cai)
- `market`: 市场代码 (HSI, NASDAQ)
- `check_time`: 检查时间 (可选，ISO格式，默认为当前时间)

**响应示例**:
```json
{
  "source_id": "wen_cai",
  "market": "HSI",
  "check_time": "2025-01-15T16:22:30.449375",
  "status": {
    "is_open": false,
    "status_text": "已收盘",
    "market_time": "2025-01-15T16:22:30.449385+08:00",
    "matched_rule": {
      "date_pattern": "*",
      "start_time": "16:10:00",
      "end_time": "24:00:00",
      "description": "已收盘"
    }
  }
}
```

**使用示例**:
```bash
# 获取HSI当前市场状态
curl http://localhost:8000/api/sources/wen_cai/market-status/HSI

# 获取NASDAQ指定时间的市场状态
curl "http://localhost:8000/api/sources/wen_cai/market-status/NASDAQ?check_time=2024-01-15T09:00:00"
```

### 6. 获取下一个开盘时间

**端点**: `GET /api/sources/{source_id}/next-opening-time/{market}`

**描述**: 获取指定市场的下一个开盘时间信息

**参数**:
- `source_id`: 数据源ID (如: wen_cai)
- `market`: 市场代码 (HSI, NASDAQ)

**响应示例**:
```json
{
  "source_id": "wen_cai",
  "market": "HSI",
  "next_opening_time": "2024-01-16",
  "start_time": "09:30:00",
  "end_time": "16:00:00",
  "description": "正常交易日"
}
```

**使用示例**:
```bash
# 获取HSI下一个开盘时间
curl http://localhost:8000/api/sources/wen_cai/next-opening-time/HSI

# 获取NASDAQ下一个开盘时间
curl http://localhost:8000/api/sources/wen_cai/next-opening-time/NASDAQ
```

## 🚨 错误响应

重构后的API提供了统一的错误处理机制，会根据不同的错误情况返回相应的HTTP状态码：

### 错误状态码
- `400 Bad Request`: 参数错误（如无效的市场代码或数据类型）
- `404 Not Found`: 数据源不存在
- `500 Internal Server Error`: 服务器内部错误或数据获取失败

### 错误响应格式
```json
{
  "detail": "错误详情描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T14:30:00.123456"
}
```

### 常见错误示例
```json
// 数据源未找到
{
  "detail": "数据源 invalid_source 未找到",
  "error_code": "SOURCE_NOT_FOUND",
  "timestamp": "2024-01-15T14:30:00.123456"
}

// 无效参数
{
  "detail": "无效的市场代码: INVALID。支持的市场: HSI, NASDAQ",
  "error_code": "INVALID_PARAMETER",
  "timestamp": "2024-01-15T14:30:00.123456"
}

// 数据获取失败
{
  "detail": "获取最新价格失败: 网络连接超时",
  "error_code": "DATA_FETCH_ERROR",
  "timestamp": "2024-01-15T14:30:00.123456"
}
```

## 📊 支持的市场和数据类型

### 市场代码
- `HSI`: 香港恒生指数
- `NASDAQ`: 纳斯达克综合指数

### 数据类型
- `realtime`: 实时数据
- `kline1m`: 1分钟K线数据

## 🏗️ 架构特性

### 重构后的优势
- **模块化设计**: 清晰的分层架构
- **统一异常处理**: 标准化的错误响应
- **参数验证**: 自动参数校验和转换
- **依赖注入**: 提高代码可测试性
- **配置管理**: 集中化配置

### 性能优化
- **服务层缓存**: 减少重复数据查询
- **异步处理**: 提高并发性能
- **错误恢复**: 完善的重试机制

## 📖 交互式文档

访问 http://localhost:8000/docs 可以查看完整的交互式API文档，支持：
- 📋 完整的API规范
- 🧪 在线测试功能
- 📝 详细的参数说明
- 💡 示例代码生成

## 🔧 开发集成

### Python 示例
```python
import requests

# 获取数据源列表
response = requests.get("http://localhost:8000/api/sources")
sources = response.json()

# 获取HSI实时价格
response = requests.get("http://localhost:8000/api/sources/wen_cai/latest/HSI/realtime")
price_data = response.json()

# 检查市场状态
response = requests.get("http://localhost:8000/api/sources/wen_cai/market-status/HSI")
market_status = response.json()
```
