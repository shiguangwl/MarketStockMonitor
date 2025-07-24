from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SinaPriceDataPoint:
    """
    用于存储单个时间点价格信息的数据类。
    """
    # 名称
    name: str
    # 时间戳
    time: datetime
    # 价格
    price: float

    def __repr__(self):
        return f"PriceDataPoint(name='{self.name}', time='{self.time.strftime('%Y-%m-%d %H:%M')}', price={self.price})"


@dataclass
class ParsedTradingRule:
    """从API解析出的原始交易规则"""
    date_pattern: str
    start_time: str
    end_time: str
    description: str

@dataclass
class TradingDay:
    """特殊交易日信息（如节假日、半天交易日）"""
    start: datetime
    end: datetime
    text: str
    
    def __str__(self):
        return f"TradingDay(start={self.start.strftime('%Y-%m-%d %H:%M:%S')}, end={self.end.strftime('%Y-%m-%d %H:%M:%S')}, text={self.text})"


@dataclass
class CurrentStatus:
    """封装市场的交易状态"""
    is_open: bool
    status_text: str
    market_time: datetime
    matched_rule: Optional[ParsedTradingRule]
