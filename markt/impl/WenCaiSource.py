from datetime import datetime
import logging
from typing import List, Dict
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
            'rt_hkHSI': MarketSymbol.HSI,
            'gb_ixic': MarketSymbol.NASDAQ,
            '88_HSI': MarketSymbol.HSI,
            '88_IXIC': MarketSymbol.NASDAQ,
        }
        # 问财K线数据
        self.lastUpdateTime = None
        self.wen_cai_client = WenCaiClient()
        # 新浪交易时间数据
        self.trading_hours_client = TradingHoursClient()
        # 新浪实时价格数据
        self.sina_realtime_quote_client = SinaRealtimeQuoteClient()
        # 最后一次抓取
    
    def start(self) -> None:
        """启动数据源."""
        logger.info("启动数据源" + str(self.get_source_info()))
        # 实时数据抓取
        scheduler1 = BackgroundScheduler()
        scheduler1.add_job(self._tick_update_realtime, 'interval', seconds=2)
        scheduler1.start()
        # K线数据抓取
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
            supported_markets=[
                MarketSymbol.HSI,
                MarketSymbol.NASDAQ
            ]
        )
    
    def get_market_status(self, check_time: datetime, market: MarketSymbol) -> CurrentStatus:
        """获取指定时间的指定市场状态."""
        return self.trading_hours_client.get_current_trading_status(market.value)
    
    def get_trading_hours(self, market: MarketSymbol) -> List[TradingDay]:
        """获取指定市场交易时间表."""
        return self.trading_hours_client.get_all_trading_days(market.value)
    
    def get_latest_data(self, market: MarketSymbol, type: MarketDataType) -> SinaPriceDataPoint:
        """获取指定市场指定类型的最新数据."""
        if type not in [MarketDataType.REALTIME, MarketDataType.KLINE1M]:
            raise ValueError(f"不支持的数据类型: {type}")

        if type == MarketDataType.REALTIME:
            # 实时数据
            temp_result = self._get_sina_realtime_quote([market])
            _, first_value = temp_result.popitem()
            return self._mapping(first_value)
        else:
            # K线级别数据
            if market == MarketSymbol.HSI:
                return self._mapping(self.wen_cai_client.get_hsi_kline()[-1])
            elif market == MarketSymbol.NASDAQ:
                return self._mapping(self.wen_cai_client.get_nasdaq_kline()[-1])

    def _get_sina_realtime_quote(self, market: List[MarketSymbol]) -> Dict[str, SinaPriceDataPoint]:
        stock_codes_to_fetch = []
        if market == MarketSymbol.HSI:
            stock_codes_to_fetch.append('rt_hkHSI')
        elif market == MarketSymbol.NASDAQ:
            stock_codes_to_fetch.append('gb_ixic')
        result = self.sina_realtime_quote_client.fetch_sina_quotes(stock_codes_to_fetch)
        return result

    def _mapping(self, market: SinaPriceDataPoint) -> SinaPriceDataPoint:
        market.name = self.mapping.get(market.name, market.name)
        return market

    def _tick_update_realtime(self) -> None:
        """实时数据"""
        # 如果为收盘状态则不更新
        if not self.get_market_status(datetime.now(), MarketSymbol.HSI).is_open:
            return
        if not self.get_market_status(datetime.now(), MarketSymbol.NASDAQ).is_open:
            return

        result_dict = self._get_sina_realtime_quote([MarketSymbol.HSI,MarketSymbol.NASDAQ])
        for key, value in result_dict.items():
            symbol = self.mapping[key]
            self.notify(
                MarketData(
                    source = self.get_source_info().source_id,
                    symbol=symbol,
                    type=MarketDataType.REALTIME,
                    price=value.price,
                    timestamp=value.time
                )
            )

    def _tick_update_kline(self) -> None:
        """K线数据"""
        hsi_kline = self.wen_cai_client.get_hsi_kline();
        nasdaq_kline = self.wen_cai_client.get_nasdaq_kline();
        # 只筛选时间在self.lastUpdateTime之后的数据
        if self.lastUpdateTime is None:
            # 上一次时间为空则通知所有数据
            for hsi_item in hsi_kline:
                self.notify(
                    MarketData(
                        source = self.get_source_info().source_id,
                        symbol=MarketSymbol.HSI,
                        type=MarketDataType.KLINE1M,
                        price=hsi_item.price,
                        timestamp=hsi_item.time
                    )
                )
            for nasdaq_item in nasdaq_kline:
                self.notify(
                    MarketData(
                        source = self.get_source_info().source_id,
                        symbol=MarketSymbol.NASDAQ,
                        type=MarketDataType.KLINE1M,
                        price=nasdaq_item.price,
                        timestamp=nasdaq_item.time
                    )
                )
        else:
            # 上一次时间不为空则只通知时间在self.lastUpdateTime之后的数据
            for hsi_item in hsi_kline:
                if hsi_item.time > self.lastUpdateTime:
                    self.notify(
                        MarketData(
                            source = self.get_source_info().source_id,
                            symbol=MarketSymbol.HSI,
                            type=MarketDataType.KLINE1M,
                            price=hsi_item.price,
                            timestamp=hsi_item.time
                        )
                    )
            for nasdaq_item in nasdaq_kline:
                if nasdaq_item.time > self.lastUpdateTime:
                    self.notify(
                        MarketData(
                            source = self.get_source_info().source_id,
                            symbol=MarketSymbol.NASDAQ,
                            type=MarketDataType.KLINE1M,
                            price=nasdaq_item.price,
                            timestamp=nasdaq_item.time
                        )
                    )
        self.lastUpdateTime = datetime.now()