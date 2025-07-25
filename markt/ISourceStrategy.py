"""数据获取相关接口."""

import abc
from datetime import datetime
from typing import Any, List, Callable

from models.market_data import MarketData, MarketDataType, MarketSourceInfo, MarketSymbol
from wen_cai.price_data_point import ParsedTradingRule
from wen_cai.trading_hours_client import CurrentStatus, TradingDay


class ISourceStrategy(abc.ABC):
    """数据获取策略抽象基类."""

    @abc.abstractmethod
    async def start(self) -> None:
        """启动数据获取策略."""
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        """停止数据获取策略."""
        pass

    @abc.abstractmethod
    def attach(self, observer: Any) -> None:
        """添加观察者.

        Args:
            observer: 观察者对象
        """
        pass

    @abc.abstractmethod
    def detach(self, observer: Any) -> None:
        """移除观察者.

        Args:
            observer: 观察者对象
        """
        pass

    @abc.abstractmethod
    def notify(self, data: Any) -> None:
        """通知所有观察者.

        Args:
            data: 通知的数据
        """
        pass
    
    @abc.abstractmethod
    def get_source_info(self) -> MarketSourceInfo:
        """获取数据源ID.
        """
        pass
    

    @abc.abstractmethod
    def get_market_status(self, check_time: datetime,market: MarketSymbol) -> CurrentStatus:
        """获取指定时间的指定市场状态.

        Args:
            check_time: 需要检查的时间点

        Returns:
            市场状态信息
        """
        pass

    @abc.abstractmethod
    def get_trading_hours(self, market: MarketSymbol) -> List[TradingDay]:
        """获取指定市场交易时间表.
        """
        pass
    
    @abc.abstractmethod
    def get_latest_data(self, market: MarketSymbol, type: MarketDataType) -> MarketData:
        """获取指定市场的最新数据.
        """
        pass
    
    @abc.abstractmethod
    def get_next_opening_time(self, market: MarketSymbol) -> ParsedTradingRule:
        """获取指定市场的下一个开盘时间.
        """
        pass


class AbstractFetcher(ISourceStrategy):
    """抽象数据获取器，实现观察者模式."""

    def __init__(self) -> None:
        self._observers: List[Callable[[MarketData], None]] = []

    def attach(self, observer: Callable[[MarketData], None]) -> None:
        self._observers.append(observer)

    def detach(self, observer: Callable[[MarketData], None]) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, data: MarketData) -> None:
        for observer in self._observers:
            observer(data)
