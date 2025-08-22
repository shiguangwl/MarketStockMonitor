"""
市场状态管理模块
负责检查市场开市状态和管理延迟停止逻辑
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models.market_data import MarketSymbol
from wen_cai.price_data_point import ParsedTradingRule
from wen_cai.sina_trading_hours_client import CurrentStatus, TradingHoursClient
from utils.logger_config import setup_logger

logger = setup_logger("market_status_manager")


class MarketStatusManager:
    """市场状态管理器"""

    def __init__(self, delay_stop_minutes: int = 10, delay_start_minutes: int = 10):
        self.trading_hours_client = TradingHoursClient()
        self.delay_stop_minutes = delay_stop_minutes
        self.delay_start_minutes = delay_start_minutes

        # 多市场状态跟踪
        self.market_states: Dict[MarketSymbol, Dict[str, Any]] = {}
        self.is_first_run: bool = True

        # 初始化所有支持的市场状态
        for market in [MarketSymbol.HSI, MarketSymbol.NASDAQ]:
            self.market_states[market] = {
                "last_market_status": None,
                "delay_stop_time": None,
                "delay_start_time": None,  # 开市延迟确认时间
                "is_active": True,  # 是否应该继续抓取该市场的数据
            }

    def should_continue_fetching(
        self, market: MarketSymbol, check_time: Optional[datetime] = None
    ) -> bool:
        """
        判断指定市场当前是否应继续抓取数据（包括延迟停止和延迟开始时间段）

        Args:
            market: 市场符号
            check_time: 检查时间，默认为当前时间

        Returns:
            bool: 是否应该继续抓取该市场的数据
        """
        if check_time is None:
            check_time = datetime.now()

        market_status = self.get_market_status(market, check_time)
        market_state = self.market_states[market]
        last_status_is_open = market_state.get("last_market_status")

        # --- 状态切换检测 ---
        # 从 休市 -> 开市
        if last_status_is_open is False and market_status.is_open:
            # 如果当前正处于延迟停止状态，说明市场在缓冲期内恢复，应立即恢复抓取
            if market_state["delay_stop_time"] is not None:
                logger.info(f"📈 {market.value}市场在延迟停止期间重新开市，立即恢复抓取")
                market_state["delay_stop_time"] = None
            elif market_state["delay_start_time"] is None:
                market_state["delay_start_time"] = check_time + timedelta(
                    minutes=self.delay_start_minutes
                )
                logger.info(
                    f"🔄 {market.value}市场变为开市，启动 {self.delay_start_minutes} 分钟延迟确认..."
                )

        # 从 开市 -> 休市
        elif last_status_is_open is True and not market_status.is_open:
            if market_state["delay_stop_time"] is None:
                market_state["delay_stop_time"] = check_time + timedelta(
                    minutes=self.delay_stop_minutes
                )
                logger.info(
                    f"🕒 {market.value}市场已关闭，将在 {self.delay_stop_minutes} 分钟后停止抓取"
                )
            if market_state["delay_start_time"] is not None:
                logger.info(f"📉 {market.value}市场在开市确认期间关闭，取消延迟确认")
                market_state["delay_start_time"] = None

        # --- 延迟状态处理 ---
        # 1. 处理开市延迟
        if market_state["delay_start_time"] is not None:
            if not market_status.is_open:
                logger.info(f"📉 {market.value}市场在开市确认期间再次关闭，取消延迟")
                market_state["delay_start_time"] = None
            elif check_time < market_state["delay_start_time"]:
                logger.debug(f"⏳ {market.value}市场处于开市延迟确认阶段，暂不抓取")
                market_state["last_market_status"] = market_status.is_open
                return False
            else:
                logger.info(f"✅ {market.value}市场开市状态已确认，开始数据抓取")
                market_state["delay_start_time"] = None
                market_state["is_active"] = True
                market_state["last_market_status"] = market_status.is_open
                return True

        # 2. 处理休市延迟
        if market_state["delay_stop_time"] is not None:
            if check_time < market_state["delay_stop_time"]:
                logger.debug(f"⏳ {market.value}市场处于延迟停止阶段，继续抓取数据")
                market_state["last_market_status"] = market_status.is_open
                return True
            else:
                logger.info(f"⏹️ {market.value}市场延迟时间已到，停止数据抓取")
                market_state["delay_stop_time"] = None
                market_state["is_active"] = False
                market_state["last_market_status"] = market_status.is_open
                return False

        # --- 默认情况 (无延迟状态) ---
        market_state["last_market_status"] = market_status.is_open
        market_state["is_active"] = market_status.is_open
        return market_status.is_open

    def get_active_markets(
        self, check_time: Optional[datetime] = None
    ) -> list[MarketSymbol]:
        """
        获取当前应该继续抓取数据的市场列表

        Args:
            check_time: 检查时间，默认为当前时间

        Returns:
            list[MarketSymbol]: 应该继续抓取数据的市场列表
        """
        if check_time is None:
            check_time = datetime.now()

        active_markets = []
        for market in [MarketSymbol.HSI, MarketSymbol.NASDAQ]:
            if self.should_continue_fetching(market, check_time):
                active_markets.append(market)

        return active_markets

    def get_market_status(
        self, market: MarketSymbol, check_time: datetime = datetime.now()
    ) -> CurrentStatus:
        """
        获取指定时间的指定市场状态

        Args:
            check_time: 检查时间
            market: 市场符号

        Returns:
            CurrentStatus: 当前市场状态
        """

        return self.trading_hours_client.get_status_at_time(
            market.value, check_time.strftime("%Y-%m-%d %H:%M:%S"), "Asia/Shanghai"
        )

    def get_trading_hours(self, market: MarketSymbol) -> list[Any]:
        """
        获取指定市场交易时间表

        Args:
            market: 市场符号

        Returns:
            list: 交易时间表
        """
        return self.trading_hours_client.get_all_trading_days(market.value)

    def get_next_opening_time(self, market: MarketSymbol) -> ParsedTradingRule:
        """
        获取指定市场的下一个开盘时间

        Args:
            market: 市场符号

        Returns:
            下一个开盘时间信息
        """
        return self.trading_hours_client.get_next_opening_time(market.value)

    def reset_first_run_flag(self) -> None:
        """重置首次运行标志"""
        self.is_first_run = False

    def is_first_run_flag(self) -> bool:
        """获取首次运行标志"""
        return self.is_first_run

    def get_status_info(self) -> dict[str, Any]:
        """
        获取状态信息

        Returns:
            dict: 状态信息
        """
        markets_info: dict[str, Any] = {}
        for market, state in self.market_states.items():
            markets_info[market.value] = {
                "last_market_status": state.get("last_market_status"),
                "delay_stop_time": state.get("delay_stop_time"),
                "delay_start_time": state.get("delay_start_time"),
                "is_active": state.get("is_active"),
            }

        status_info: dict[str, Any] = {
            "is_first_run": self.is_first_run,
            "delay_stop_minutes": self.delay_stop_minutes,
            "delay_start_minutes": self.delay_start_minutes,
            "markets": markets_info,
        }
        return status_info
