from dataclasses import dataclass
from datetime import datetime

@dataclass
class PriceDataPoint:
    """
    用于存储单个时间点价格信息的数据类。

    Attributes:
        timestamp (datetime): 日期和时间信息。
        price (float): 该时间点的价格。
    """
    timestamp: datetime
    price: float

    def __repr__(self):
        return f"PriceDataPoint(timestamp='{self.timestamp.strftime('%Y-%m-%d %H:%M')}', price={self.price})"



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