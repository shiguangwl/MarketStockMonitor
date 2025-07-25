from datetime import datetime
import logging
from typing import List, Dict, Optional
from apscheduler.schedulers.background import BackgroundScheduler

from markt.ISourceStrategy import AbstractFetcher
from models.market_data import MarketDataType, MarketSourceInfo, MarketSymbol, MarketData
from wen_cai.price_data_point import SinaPriceDataPoint
from wen_cai.sina_realtime_quote_client import SinaRealtimeQuoteClient
from wen_cai.trading_hours_client import CurrentStatus, TradingDay, TradingHoursClient
from wen_cai.wen_cai_client import WenCaiClient

logger = logging.getLogger(__name__)


class WenCaiSource(AbstractFetcher):
    """问财数据源"""

    def __init__(self):
        super().__init__()
        self.mapping = {
            'rt_hkHSI': MarketSymbol.HSI.value,
            'gb_ixic': MarketSymbol.NASDAQ.value,
            '176_HSI': MarketSymbol.HSI.value,
            '88_IXIC': MarketSymbol.NASDAQ.value,
            '纳斯达克': MarketSymbol.NASDAQ.value,
            '恒生指数': MarketSymbol.HSI.value,
        }
        self.lastUpdateTime: Optional[datetime] = None

        # Clients
        self.wen_cai_client = WenCaiClient()
        self.trading_hours_client = TradingHoursClient()
        self.sina_realtime_quote_client = SinaRealtimeQuoteClient()

    def start(self) -> None:
        """启动数据源."""
        logger.info("启动数据源 %s", self.get_source_info())
        scheduler1 = BackgroundScheduler()
        scheduler1.add_job(self._tick_update_realtime, 'interval', seconds=2)
        scheduler1.start()

        scheduler2 = BackgroundScheduler()
        scheduler2.add_job(self._tick_update_kline, 'interval', seconds=15)
        scheduler2.start()

    def stop(self) -> None:
        """停止数据源."""
        logger.warning("停止问财数据源")

    def get_source_info(self) -> MarketSourceInfo:
        """获取数据源ID."""
        return MarketSourceInfo(
            source_id="wen_cai",
            source_name="问财",
            supported_markets=[MarketSymbol.HSI, MarketSymbol.NASDAQ]
        )

    def get_market_status(self, check_time: datetime, market: MarketSymbol) -> CurrentStatus:
        """获取指定时间的指定市场状态."""
        return self.trading_hours_client.get_current_trading_status(market.value)

    def get_trading_hours(self, market: MarketSymbol) -> List[TradingDay]:
        """获取指定市场交易时间表."""
        return self.trading_hours_client.get_all_trading_days(market.value)

    def get_latest_data(self, market: MarketSymbol, data_type: MarketDataType) -> SinaPriceDataPoint:
        """获取指定市场指定类型的最新数据."""
        if data_type not in [MarketDataType.REALTIME, MarketDataType.KLINE1M]:
            raise ValueError(f"不支持的数据类型: {data_type}")

        if data_type == MarketDataType.REALTIME:
            result = self._get_sina_realtime_quote([market])
            _, first_value = next(iter(result.items()))
            return self._mapping(first_value)
        else:
            if market == MarketSymbol.HSI:
                return self._mapping(self.wen_cai_client.get_hsi_kline()[-1])
            elif market == MarketSymbol.NASDAQ:
                return self._mapping(self.wen_cai_client.get_nasdaq_kline()[-1])

    def _get_sina_realtime_quote(self, markets: List[MarketSymbol]) -> Dict[str, SinaPriceDataPoint]:
        stock_codes_to_fetch = []
        for m in markets:
            if m == MarketSymbol.HSI:
                stock_codes_to_fetch.append('rt_hkHSI')
            elif m == MarketSymbol.NASDAQ:
                stock_codes_to_fetch.append('gb_ixic')
        return self.sina_realtime_quote_client.fetch_sina_quotes(stock_codes_to_fetch)

    def _mapping(self, data_point: SinaPriceDataPoint) -> SinaPriceDataPoint:
        data_point.name = self.mapping.get(data_point.name, data_point.name)
        return data_point

    def _tick_update_realtime(self) -> None:
        """实时数据更新"""
        now = datetime.now()
        if not self.get_market_status(now, MarketSymbol.HSI).is_open and \
                not self.get_market_status(now, MarketSymbol.NASDAQ).is_open:
            return

        results = self._get_sina_realtime_quote([MarketSymbol.HSI, MarketSymbol.NASDAQ])
        for key, value in results.items():
            symbol = self.mapping.get(key)
            if symbol:
                self.notify(MarketData(
                    source=self.get_source_info().source_id,
                    symbol=symbol,
                    type=MarketDataType.REALTIME,
                    price=value.price,
                    timestamp=value.time
                ))

    def _tick_update_kline(self) -> None:
        """K线数据更新"""
        hsi_kline = self.wen_cai_client.get_hsi_kline()
        nasdaq_kline = self.wen_cai_client.get_nasdaq_kline()

        all_data = [(MarketSymbol.HSI, hsi_kline), (MarketSymbol.NASDAQ, nasdaq_kline)]

        latest_time = self.lastUpdateTime
        new_latest_time = latest_time

        for symbol, kline_list in all_data:
            for item in kline_list:
                if latest_time is None or item.time > latest_time:
                    self.notify(MarketData(
                        source=self.get_source_info().source_id,
                        symbol=symbol,
                        type=MarketDataType.KLINE1M,
                        price=item.price,
                        timestamp=item.time
                    ))
                if new_latest_time is None or item.time > new_latest_time:
                    new_latest_time = item.time

        self.lastUpdateTime = new_latest_time
