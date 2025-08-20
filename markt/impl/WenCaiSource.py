"""
问财数据源 - 重构版本
使用模块化架构，提高代码质量和可维护性
"""

import time
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from markt.ISourceStrategy import AbstractFetcher
from markt.ticker_scheduler import get_global_scheduler
from markt.impl.wen_cai_config import WenCaiConfig, DEFAULT_CONFIG
from markt.impl.market_status_manager import MarketStatusManager
from markt.impl.data_fetcher import DataFetcher
from markt.impl.data_processor import DataProcessor
from models.market_data import (
    MarketDataType,
    MarketSourceInfo,
    MarketSymbol,
    MarketData,
)
from wen_cai.price_data_point import ParsedTradingRule, SinaPriceDataPoint
from wen_cai.sina_trading_hours_client import CurrentStatus, TradingDay
from utils.logger_config import setup_logger

logger = setup_logger("wen_cai_source")


class WenCaiSource(AbstractFetcher):
    """问财数据源"""

    def __init__(self, config: WenCaiConfig = None):
        super().__init__()
        
        # 使用配置
        self.config = config or DEFAULT_CONFIG
        
        # 初始化组件
        self.market_status_manager = MarketStatusManager(
            delay_stop_minutes=self.config.delay_stop_minutes
        )
        self.data_fetcher = DataFetcher(
            max_workers=self.config.max_workers,
            single_source_timeout=self.config.single_source_timeout
        )
        self.data_processor = DataProcessor(self.config.symbol_mapping)
        
        # 状态管理
        self.last_update_time: Optional[datetime] = None
        self.last_notification_count = 0
        
        # 线程池用于超时控制
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)

    def start(self) -> None:
        """启动数据源"""
        source_info = self.get_source_info()
        logger.info(
            f"🚀 启动数据源: {source_info.source_name} ({source_info.source_id})"
        )

        # 重置状态
        self.last_update_time = None
        self.last_notification_count = 0
        self.is_first_run_flag = True

        # 获取全局调度器
        scheduler = get_global_scheduler()
        scheduler.start()

        # 添加数据更新任务
        scheduler.add_interval_job(
            job_id="wen_cai_data_update_realtime",
            func=self._update_realtime_data,
            seconds=self.config.realtime_update_interval,
            description="问财数据更新-实时数据",
        )
        
        scheduler.add_interval_job(
            job_id="wen_cai_data_update_kline",
            func=self._update_kline_data,
            seconds=self.config.kline_update_interval,
            description="问财数据更新-K线数据",
        )

    def stop(self) -> None:
        """停止数据源"""
        logger.warning("🛑 停止问财数据源")

        # 移除定时任务
        scheduler = get_global_scheduler()
        scheduler.remove_job("wen_cai_data_update_realtime")
        scheduler.remove_job("wen_cai_data_update_kline")
        
        # 关闭线程池
        self.executor.shutdown(wait=False)
        self.data_fetcher.shutdown()

        # 保存最后更新时间
        if self.last_update_time:
            logger.info(
                f"📝 保存最后更新时间: {self.last_update_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def get_source_info(self) -> MarketSourceInfo:
        """获取数据源信息"""
        return MarketSourceInfo(
            source_id="wen_cai",
            source_name="问财",
            supported_markets=[MarketSymbol.NASDAQ, MarketSymbol.HSI],
        )

    def get_market_status(self, market: MarketSymbol, check_time: datetime = datetime.now()) -> CurrentStatus:
        """获取当前时间的指定市场状态"""
        return self.market_status_manager.get_market_status(market, check_time)

    def get_trading_hours(self, market: MarketSymbol) -> List[TradingDay]:
        """获取指定市场交易时间表"""
        return self.market_status_manager.get_trading_hours(market)

    def get_latest_data(
        self, market: MarketSymbol, data_type: MarketDataType
    ) -> SinaPriceDataPoint:
        """获取指定市场指定类型的最新数据"""
        if data_type not in [MarketDataType.REALTIME, MarketDataType.KLINE1M]:
            raise ValueError(f"不支持的数据类型: {data_type}")

        if data_type == MarketDataType.REALTIME:
            result = self.data_fetcher.fetch_realtime_quotes([market])
            _, first_value = next(iter(result.items()))
            return self._apply_mapping(first_value)
        else:
            kline_data = self.data_fetcher.fetch_kline_data(market)
            if kline_data:
                return self._apply_mapping(kline_data[-1])
            raise ValueError(f"无法获取{market.value}的K线数据")

    def get_next_opening_time(self, market: MarketSymbol) -> ParsedTradingRule:
        """获取指定市场的下一个开盘时间"""
        return self.market_status_manager.get_next_opening_time(market)

    def _apply_mapping(self, data_point: SinaPriceDataPoint) -> SinaPriceDataPoint:
        """应用符号映射"""
        data_point.name = self.config.get_mapping(data_point.name, data_point.name)
        return data_point

    def _update_realtime_data(self) -> None:
        """实时数据更新"""
        # 获取当前应该继续抓取数据的市场列表
        active_markets = self.market_status_manager.get_active_markets(datetime.now())
        
        if not active_markets:
            logger.debug("📊 当前没有活跃的市场，跳过实时数据更新")
            return

        try:
            # 只获取活跃市场的实时数据
            raw_data = self.data_fetcher.fetch_realtime_quotes(active_markets)
            
            # 处理数据
            processed_data = self.data_processor.process_realtime_data(
                raw_data, self.get_source_info().source_id
            )
            
            # 通知数据更新
            for market_data in processed_data:
                self.notify(market_data)
                
        except Exception as e:
            logger.error(f"❌ 实时数据更新时出错: {e}")

    def _update_kline_data(self) -> None:
        """K线数据更新 - 优化版本"""
        start_time = time.time()
        
        try:
            # 获取当前应该继续抓取数据的市场列表
            active_markets = self.market_status_manager.get_active_markets(datetime.now())
            
            # 首次运行时即使市场关闭也要执行一次
            if self.is_first_run_flag:
                # 首次运行获取所有市场数据
                active_markets = [MarketSymbol.NASDAQ, MarketSymbol.HSI]  
                self.is_first_run_flag = False
            elif not active_markets:
                logger.debug("📊 当前没有活跃的市场，跳过K线数据更新")
                return

            # 使用超时机制执行数据获取
            future = self.executor.submit(self._fetch_kline_data, active_markets)
            try:
                result = future.result(timeout=self.config.kline_fetch_timeout)
                if result is not None:
                    max_data_time, processed_count = result
                    if max_data_time is not None:
                        if self.last_update_time is None:
                            logger.info(
                                f"📝 首次记录增量数据时间: {max_data_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            )
                        self.last_update_time = max_data_time
                        
                    execution_time = time.time() - start_time
                    if processed_count > 0:
                        logger.info(f"📊 K线数据更新完成，处理{processed_count}条数据，耗时{execution_time:.2f}秒")
                    
            except FutureTimeoutError:
                logger.error("⏰ K线数据更新超时，跳过本次更新")
                future.cancel()
                
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ K线数据更新异常，耗时{execution_time:.2f}秒: {e}")
        finally:
            execution_time = time.time() - start_time
            if execution_time > self.config.execution_time_warning_threshold:
                logger.warning(f"⚠️ K线数据更新耗时较长: {execution_time:.2f}秒")

    def _fetch_kline_data(self, markets: list[MarketSymbol]) -> Optional[tuple]:
        """实际执行K线数据获取的方法"""
        kline_data = self.data_fetcher.fetch_all_kline_data(markets)
        
        # 过滤有效数据
        valid_kline_data = {}
        for market, data_list in kline_data.items():
            if data_list:
                valid_data = self.data_processor.filter_valid_data(data_list)
                if valid_data:
                    valid_kline_data[market] = valid_data
        
        # 处理数据
        processed_data, max_data_time, total_processed = self.data_processor.process_kline_data(
            valid_kline_data, 
            self.get_source_info().source_id,
            self.last_update_time
        )
        
        # 通知数据更新
        for market_data in processed_data:
            self.notify(market_data)
        
        return max_data_time, total_processed

    def get_status_info(self) -> dict:
        """获取状态信息"""
        return {
            "last_update_time": self.last_update_time,
            "last_notification_count": self.last_notification_count,
            "market_status": self.market_status_manager.get_status_info(),
            "config": self.config.to_dict(),
            "executor_status": self.data_fetcher.get_executor_status(),
        }
