"""市场数据模型."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json

class MarketDataType(Enum):
    """市场数据类型."""
    REALTIME = "realtime"
    KLINE1M = "kline1m"
    KLINE5M = "kline5m"
    KLINE15M = "kline15m"
    KLINE30M = "kline30m"
    KLINE1H = "kline1h"
    KLINE4H = "kline4h"
    KLINE1D = "kline1d"
    KLINE1W = "kline1w"
    KLINE1MM = "kline1m"
    KLINE3MM = "kline3m"
    KLINE6MM = "kline6m"
    KLINE1Y = "kline1y"

class MarketSymbol(Enum):
    HSI = "HSI"
    NASDAQ = "NASDAQ"

@dataclass
class MarketData():
    """市场数据模型."""
    # 数据源
    source: str
    # 市场代码
    symbol: MarketSymbol
    # 类型
    type: MarketDataType
    # 价格
    price: float
    # 时间戳
    timestamp: datetime
    # 成交量
    volume: Optional[int] = None
    # 开盘价
    open_price: Optional[float] = None
    # 最高价
    high_price: Optional[float] = None
    # 最低价
    low_price: Optional[float] = None
    # 收盘价
    close_price: Optional[float] = None
    # 涨跌额
    change: Optional[float] = None
    # 涨跌幅
    change_percent: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于JSON序列化."""
        data = asdict(self)
        # 转换枚举值
        data['symbol'] = self.symbol.value
        data['type'] = self.type.value
        # 格式化时间戳
        data['timestamp'] = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return data
    
    def to_json(self) -> str:
        """转换为JSON字符串."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def __str__(self) -> str:
        """字符串表示，用于日志输出."""
        return (f"MarketData(source={self.source}, symbol={self.symbol.value}, "
                f"type={self.type.value}, price={self.price}, "
                f"timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")
    
    def to_simple_string(self) -> str:
        """简化的字符串表示."""
        return (f"[{self.timestamp.strftime('%H:%M:%S')}] {self.symbol.value} "
                f"({self.type.value}) -> ¥{self.price:.2f}")


@dataclass
class MarketSourceInfo():
    """市场数据源信息模型."""
    # 数据源ID
    source_id: str
    # 数据源名称
    source_name: str
    # 支持的市场
    supported_markets: List[MarketSymbol]