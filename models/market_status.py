"""市场状态枚举."""

from enum import Enum


class MarketStatus(Enum):
    """市场状态枚举."""
    # 开盘
    OPEN = "OPEN"
    # 休市
    CLOSED = "CLOSED"