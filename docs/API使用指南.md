# MarketStockMonitor API 使用指南

## 概述

MarketStockMonitor 提供了4个主要的REST API端点，用于获取市场数据、交易时间表和市场状态信息。

## API 端点

### 1. 获取数据源列表

**端点**: `GET /api/sources`

**描述**: 获取系统中所有可用的数据源列表

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

### 2. 获取最新价格数据

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
    "name": "HSI",
    "time": "2024-01-15T14:30:00",
    "price": 16250.5
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

### 3. 获取交易时间表

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
        ......
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

### 4. 获取市场状态

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
  "check_time": "2025-07-25T16:22:30.449375",
  "status": {
      "is_open": false,
      "status_text": "已收盘",
      "market_time": "2025-07-25T16:22:30.449385+08:00",
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

## 错误响应

API会根据不同的错误情况返回相应的HTTP状态码：

- `400 Bad Request`: 参数错误（如无效的市场代码或数据类型）
- `404 Not Found`: 数据源不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应示例：
```json
{
  "detail": "数据源 invalid_source 未找到"
}
```

## 支持的市场和数据类型

### 市场代码
- `HSI`: 香港恒生指数
- `NASDAQ`: 纳斯达克指数

### 数据类型
- `realtime`: 实时数据
- `kline1m`: 1分钟K线数据

## 注意事项

1. 所有时间格式都使用ISO 8601标准格式