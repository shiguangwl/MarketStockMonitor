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
from wen_cai.trading_hours_client import CurrentStatus, TradingDay, TradingHoursClient
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
        # 收盘后延续抓取的时间（分钟）
        self.post_close_duration_minutes = 5
        # 记录各市场的收盘时间
        self.market_close_times: Dict[MarketSymbol, Optional[datetime]] = {
            MarketSymbol.HSI: None,
            MarketSymbol.NASDAQ: None,
        }
        # 记录上次通知的数据数量
        self.last_notification_count = 0

        self.wen_cai_client = WenCaiClient()
        self.trading_hours_client = TradingHoursClient()
        self.sina_realtime_quote_client = SinaRealtimeQuoteClient()

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

        # 添加实时数据更新任务
        scheduler.add_interval_job(
            job_id="wen_cai_realtime",
            func=self._tick_update_realtime,
            seconds=1.5,
            description="问财实时数据更新",
        )

        # 添加K线数据更新任务
        scheduler.add_interval_job(
            job_id="wen_cai_kline",
            func=self._tick_update_kline,
            seconds=15,
            description="问财K线数据更新",
        )

    def stop(self) -> None:
        """停止数据源"""
        logger.warning("🛑 停止问财数据源")

        # 移除定时任务
        scheduler = get_global_scheduler()
        scheduler.remove_job("wen_cai_realtime")
        scheduler.remove_job("wen_cai_kline")

        # 重置收盘时间记录
        self.market_close_times = {MarketSymbol.HSI: None, MarketSymbol.NASDAQ: None}

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

    def _tick_update_realtime(self) -> None:
        """实时数据更新"""
        now = datetime.now()

        # 检查是否应该继续抓取数据
        if not self._should_continue_fetching(now):
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

    def _tick_update_kline(self) -> None:
        """K线数据更新"""
        now = datetime.now()

        # 检查是否应该继续抓取数据
        if not self._should_continue_fetching(now):
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

                # 筛选出新数据（时间大于上次更新时间的数据）
                new_items = []
                if self.lastUpdateTime is not None:
                    new_items = [
                        item for item in kline_list if item.time > self.lastUpdateTime
                    ]
                else:
                    new_items = kline_list

                # 通知新数据
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

                    # 更新最大数据时间
                    if max_data_time is None or (
                        item.time and item.time > max_data_time
                    ):
                        max_data_time = item.time

                if new_items:
                    logger.info(
                        f"📊 更新了 {symbol.value} 的 {len(new_items)} 条新K线数据"
                    )

            except Exception as e:
                fetch_status = False
                logger.error(f"❌ 更新 {symbol.value} K线数据时出错: {e}")

        # 只有在成功获取数据且有新的最大时间时才更新lastUpdateTime
        if fetch_status and max_data_time is not None:
            if self.lastUpdateTime is None:
                logger.info(
                    f"📝 首次记录增量数据时间: {max_data_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                logger.info(
                    f"📝 增量更新数据时间: {self.lastUpdateTime.strftime('%Y-%m-%d %H:%M:%S')} -> {max_data_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            self.lastUpdateTime = max_data_time

    def _should_continue_fetching(self, current_time: datetime) -> bool:
        """
        判断是否应该继续抓取数据

        逻辑：
        1. 如果任一市场正在交易，继续抓取
        2. 如果所有市场都已收盘，检查是否在收盘后5分钟内
        3. 超过5分钟后停止抓取

        Args:
            current_time: 当前时间

        Returns:
            bool: True表示继续抓取，False表示停止抓取
        """
        try:
            # 获取各市场当前状态
            hsi_status = self.get_market_status(current_time, MarketSymbol.HSI)
            nasdaq_status = self.get_market_status(current_time, MarketSymbol.NASDAQ)

            # 如果任一市场正在交易，继续抓取
            if hsi_status.is_open or nasdaq_status.is_open:
                # 重置收盘时间记录（因为市场还在交易）
                if hsi_status.is_open:
                    self.market_close_times[MarketSymbol.HSI] = None
                if nasdaq_status.is_open:
                    self.market_close_times[MarketSymbol.NASDAQ] = None
                return True

            # 所有市场都已收盘，检查收盘后延续抓取逻辑
            return self._check_post_close_fetching(
                current_time, hsi_status, nasdaq_status
            )

        except Exception as e:
            logger.error(f"❌ 检查抓取状态时出错: {e}")
            # 出错时保守处理，继续抓取
            return True

    def _check_post_close_fetching(
        self,
        current_time: datetime,
        hsi_status: CurrentStatus,
        nasdaq_status: CurrentStatus,
    ) -> bool:
        """
        检查收盘后是否应该继续抓取数据

        Args:
            current_time: 当前时间
            hsi_status: 恒生指数市场状态
            nasdaq_status: 纳斯达克市场状态

        Returns:
            bool: True表示继续抓取，False表示停止抓取
        """
        should_continue = False

        # 检查恒生指数收盘后延续抓取
        if not hsi_status.is_open:
            should_continue_hsi = self._check_market_post_close_fetching(
                MarketSymbol.HSI, current_time
            )
            should_continue = should_continue or should_continue_hsi

        # 检查纳斯达克收盘后延续抓取
        if not nasdaq_status.is_open:
            should_continue_nasdaq = self._check_market_post_close_fetching(
                MarketSymbol.NASDAQ, current_time
            )
            should_continue = should_continue or should_continue_nasdaq

        return should_continue

    def _check_market_post_close_fetching(
        self, market: MarketSymbol, current_time: datetime
    ) -> bool:
        """
        检查单个市场收盘后是否应该继续抓取

        Args:
            market: 市场符号
            current_time: 当前时间

        Returns:
            bool: True表示继续抓取，False表示停止抓取
        """
        # 如果还没有记录收盘时间，记录当前时间作为收盘时间
        if self.market_close_times[market] is None:
            self.market_close_times[market] = current_time
            logger.info(
                f"📝 记录 {market.value} 收盘时间: {current_time.strftime('%H:%M:%S')}"
            )
            return True  # 刚收盘，继续抓取

        # 计算收盘后经过的时间
        close_time = self.market_close_times[market]
        elapsed_minutes = (current_time - close_time).total_seconds() / 60

        if elapsed_minutes <= self.post_close_duration_minutes:
            # 收盘后5分钟内，继续抓取
            remaining_minutes = self.post_close_duration_minutes - elapsed_minutes
            if int(elapsed_minutes) != int(elapsed_minutes - 0.1):  # 每分钟只记录一次
                logger.info(
                    f"⏰ {market.value} 收盘后延续抓取中，剩余 {remaining_minutes:.1f} 分钟"
                )
            return True
        else:
            # 超过5分钟，停止抓取
            if (
                elapsed_minutes <= self.post_close_duration_minutes + 0.1
            ):  # 只在刚超时时记录一次
                logger.info(f"⏹️ {market.value} 收盘后延续抓取结束")
            return False
