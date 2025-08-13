from datetime import datetime, timedelta
from typing import List, Dict, Optional

from markt.ISourceStrategy import AbstractFetcher
from markt.ticker_scheduler import get_global_scheduler
from models.market_data import (
    MarketDataType,
    MarketSourceInfo,
    MarketSymbol,
    MarketData,
)
from wen_cai.price_data_point import ParsedTradingRule, SinaPriceDataPoint
from wen_cai.sina_realtime_quote_client import SinaRealtimeQuoteClient
from wen_cai.sina_trading_hours_client import CurrentStatus, TradingDay, TradingHoursClient
from wen_cai.wen_cai_client import WenCaiClient
from utils.logger_config import setup_logger

logger = setup_logger("wen_cai_source")


class WenCaiSource(AbstractFetcher):
    """问财数据源"""

    def __init__(self):
        super().__init__()
        self.mapping = {
            "rt_hkHSI": MarketSymbol.HSI.value,
            "gb_ixic": MarketSymbol.NASDAQ.value,
            "176_HSI": MarketSymbol.HSI.value,
            "88_IXIC": MarketSymbol.NASDAQ.value,
            "纳斯达克": MarketSymbol.NASDAQ.value,
            "恒生指数": MarketSymbol.HSI.value,
        }
        self.lastUpdateTime: Optional[datetime] = None
        # 记录上次通知的数据数量
        self.last_notification_count = 0

        self.wen_cai_client = WenCaiClient()
        self.trading_hours_client = TradingHoursClient()
        self.sina_realtime_quote_client = SinaRealtimeQuoteClient()
        
        self.last_market_status = None   # 上一次市场开市状态
        self.delay_stop_time = None      # 延迟停止时间
        self.is_first_run = True        # 是否是第一次运行

    def start(self) -> None:
        """启动数据源"""
        source_info = self.get_source_info()
        logger.info(
            f"🚀 启动数据源: {source_info.source_name} ({source_info.source_id})"
        )

        # 重置最后更新时间
        self.lastUpdateTime = None
        self.last_notification_count = 0

        # 获取全局调度器
        scheduler = get_global_scheduler()
        scheduler.start()

        # 添加数据更新任务，每5秒执行一次
        scheduler.add_interval_job(
            job_id="wen_cai_data_update_realtime",
            func=self._update_realtime_data,
            seconds=1.5,
            description="问财数据更新-实时数据",
        )
        
        scheduler.add_interval_job(
            job_id="wen_cai_data_update_kline",
            func=self._update_kline_data,
            seconds=5,
            description="问财数据更新-K线数据",
        )
        

    def stop(self) -> None:
        """停止数据源"""
        logger.warning("🛑 停止问财数据源")

        # 移除定时任务
        scheduler = get_global_scheduler()
        scheduler.remove_job("wen_cai_data_update_realtime")
        scheduler.remove_job("wen_cai_data_update_kline")

        # 保存最后更新时间，以便下次启动时可以继续增量抓取
        if self.lastUpdateTime:
            logger.info(
                f"📝 保存最后更新时间: {self.lastUpdateTime.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def get_source_info(self) -> MarketSourceInfo:
        """获取数据源信息"""
        return MarketSourceInfo(
            source_id="wen_cai",
            source_name="问财",
            supported_markets=[MarketSymbol.HSI, MarketSymbol.NASDAQ],
        )

    def get_market_status(
        self, check_time: datetime, market: MarketSymbol
    ) -> CurrentStatus:
        """获取指定时间的指定市场状态."""
        return self.trading_hours_client.get_current_trading_status(market.value)

    def get_trading_hours(self, market: MarketSymbol) -> List[TradingDay]:
        """获取指定市场交易时间表."""
        return self.trading_hours_client.get_all_trading_days(market.value)

    def get_latest_data(
        self, market: MarketSymbol, data_type: MarketDataType
    ) -> SinaPriceDataPoint:
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

    def get_next_opening_time(self, market: MarketSymbol) -> ParsedTradingRule:
        """获取指定市场的下一个开盘时间."""
        return self.trading_hours_client.get_next_opening_time(market.value)

    def _get_sina_realtime_quote(
        self, markets: List[MarketSymbol]
    ) -> Dict[str, SinaPriceDataPoint]:
        stock_codes_to_fetch = []
        for m in markets:
            if m == MarketSymbol.HSI:
                stock_codes_to_fetch.append("rt_hkHSI")
            elif m == MarketSymbol.NASDAQ:
                stock_codes_to_fetch.append("gb_ixic")
        return self.sina_realtime_quote_client.fetch_sina_quotes(stock_codes_to_fetch)

    def _mapping(self, data_point: SinaPriceDataPoint) -> SinaPriceDataPoint:
        data_point.name = self.mapping.get(data_point.name, data_point.name)
        return data_point


    def _should_continue_fetching(self) -> bool:
        """判断当前是否应继续抓取数据（包括延迟停止时间段）"""
        now = datetime.now()
        
        # 获取当前市场状态
        market_status = self.get_market_status(now, MarketSymbol.HSI)
        # 如果市场重新开市，取消延迟停止状态
        if market_status.is_open and self.delay_stop_time is not None:
            logger.info("📈 市场重新开市，取消延迟停止状态")
            self.delay_stop_time = None
        # 判断是否发生了状态切换：open -> close
        if self.last_market_status is True and not market_status.is_open:
            # 开始延迟停止计时（10分钟后）
            self.delay_stop_time = now + timedelta(minutes=10)
            logger.info(f"🕒 市场已关闭，将在10分钟后 ({self.delay_stop_time}) 停止数据抓取")
        # 更新上一次状态
        self.last_market_status = market_status.is_open
        # 如果设置了 delay_stop_time，则检查是否已到达停止时间
        if self.delay_stop_time:
            if now >= self.delay_stop_time:
                logger.info("⏹️ 延迟时间已到，停止数据抓取")
                self.delay_stop_time = None  # 重置
                return False
            else:
                logger.debug("⏳ 处于延迟停止阶段，继续抓取数据")
                return True
        # 正常情况下根据市场状态决定是否抓取
        return market_status.is_open



    def _update_realtime_data(self) -> None:
        """实时数据更新"""
        if not self._should_continue_fetching():
            return

        try:
            results = self._get_sina_realtime_quote(
                [MarketSymbol.HSI, MarketSymbol.NASDAQ]
            )
            for key, value in results.items():
                symbol_str = self.mapping.get(key)
                if symbol_str:
                    symbol_enum = MarketSymbol(symbol_str)
                    self.notify(
                        MarketData(
                            source=self.get_source_info().source_id,
                            symbol=symbol_enum,
                            type=MarketDataType.REALTIME,
                            price=value.price,
                            timestamp=value.time,
                        )
                    )
        except Exception as e:
            logger.error(f"❌ 实时数据更新时出错: {e}")


    def _update_kline_data(self) -> None:
        """K线数据更新"""
        
        # 检查是否应该继续抓取数据
        should_continue = self._should_continue_fetching()
        
        # 首次运行时即使市场关闭也要执行一次
        if self.is_first_run:
            self.is_first_run = False
        elif not should_continue:
            return

        all_data_sources = {
            MarketSymbol.HSI: self.wen_cai_client.get_hsi_kline,
            MarketSymbol.NASDAQ: self.wen_cai_client.get_nasdaq_kline,
        }

        fetch_status = True
        max_data_time = self.lastUpdateTime

        for symbol, data_fetcher in all_data_sources.items():
            try:
                kline_list = data_fetcher()
                if not kline_list:
                    continue

                new_items = [
                    item for item in kline_list if self.lastUpdateTime is None or item.time > self.lastUpdateTime
                ]

                for item in new_items:
                    self.notify(
                        MarketData(
                            source=self.get_source_info().source_id,
                            symbol=symbol,
                            type=MarketDataType.KLINE1M,
                            price=item.price,
                            timestamp=item.time,
                        )
                    )

                    if max_data_time is None or (item.time and item.time > max_data_time):
                        max_data_time = item.time

                if new_items:
                    logger.info(
                        f"📊 更新了 {symbol.value} 的 {len(new_items)} 条新K线数据"
                    )

            except Exception as e:
                fetch_status = False
                logger.error(f"❌ 更新 {symbol.value} K线数据时出错: {e}")

        if fetch_status and max_data_time is not None:
            if self.lastUpdateTime is None:
                logger.info(
                    f"📝 首次记录增量数据时间: {max_data_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            self.lastUpdateTime = max_data_time
