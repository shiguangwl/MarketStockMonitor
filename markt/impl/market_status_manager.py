"""
市场状态管理模块
负责检查市场开市状态和管理延迟停止逻辑
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from models.market_data import MarketSymbol
from wen_cai.sina_trading_hours_client import CurrentStatus, TradingHoursClient
from utils.logger_config import setup_logger

logger = setup_logger("market_status_manager")


class MarketStatusManager:
    """市场状态管理器"""
    
    def __init__(self, delay_stop_minutes: int = 10):
        self.trading_hours_client = TradingHoursClient()
        self.delay_stop_minutes = delay_stop_minutes
        
        # 多市场状态跟踪
        self.market_states: Dict[MarketSymbol, Dict[str, Any]] = {}
        self.is_first_run: bool = True
        
        # 初始化所有支持的市场状态
        for market in [MarketSymbol.HSI, MarketSymbol.NASDAQ]:
            self.market_states[market] = {
                'last_market_status': None,
                'delay_stop_time': None,
                'is_active': True  # 是否应该继续抓取该市场的数据
            }
    
    def should_continue_fetching(self, market: MarketSymbol) -> bool:
        """
        判断指定市场当前是否应继续抓取数据（包括延迟停止时间段）
        
        Args:
            market: 市场符号
            check_time: 检查时间，默认为当前时间
            
        Returns:
            bool: 是否应该继续抓取该市场的数据
        """
        check_time = datetime.now()
        # 获取当前市场状态
        market_status = self.get_market_status(market)
        
        # 获取该市场的状态跟踪
        market_state = self.market_states[market]
        
        # 如果市场重新开市，取消延迟停止状态
        if market_status.is_open and market_state['delay_stop_time'] is not None:
            logger.info(f"📈 {market.value}市场重新开市，取消延迟停止状态")
            market_state['delay_stop_time'] = None
            market_state['is_active'] = True
        
        # 判断是否发生了状态切换：open -> close
        if market_state['last_market_status'] is True and not market_status.is_open:
            # 开始延迟停止计时
            market_state['delay_stop_time'] = check_time + timedelta(minutes=self.delay_stop_minutes)
            logger.info(f"🕒 {market.value}市场已关闭，将在{self.delay_stop_minutes}分钟后 ({market_state['delay_stop_time']}) 停止数据抓取")
        
        # 更新上一次状态
        market_state['last_market_status'] = market_status.is_open
        
        # 如果设置了 delay_stop_time，则检查是否已到达停止时间
        if market_state['delay_stop_time']:
            if check_time >= market_state['delay_stop_time']:
                logger.info(f"⏹️ {market.value}市场延迟时间已到，停止数据抓取")
                market_state['delay_stop_time'] = None  # 重置
                market_state['is_active'] = False
                return False
            else:
                logger.debug(f"⏳ {market.value}市场处于延迟停止阶段，继续抓取数据")
                return True
        
        # 正常情况下根据市场状态决定是否抓取
        should_continue = market_status.is_open
        market_state['is_active'] = should_continue
        return should_continue
    
    def get_active_markets(self, check_time: datetime = None) -> list[MarketSymbol]:
        """
        获取当前应该继续抓取数据的市场列表
        
        Args:
            check_time: 检查时间，默认为当前时间
            
        Returns:
            list[MarketSymbol]: 应该继续抓取数据的市场列表
        """

        active_markets = []
        for market in [MarketSymbol.HSI, MarketSymbol.NASDAQ]:
            if self.should_continue_fetching(market):
                active_markets.append(market)
        
        return active_markets
    
    def get_market_status(self, market: MarketSymbol, check_time: datetime = datetime.now()) -> CurrentStatus:
        """
        获取指定时间的指定市场状态
        
        Args:
            check_time: 检查时间
            market: 市场符号
            
        Returns:
            CurrentStatus: 当前市场状态
        """

        return self.trading_hours_client.get_status_at_time(market.value, check_time.strftime("%Y-%m-%d %H:%M:%S"), "Asia/Shanghai")
    
    def get_trading_hours(self, market: MarketSymbol) -> list:
        """
        获取指定市场交易时间表
        
        Args:
            market: 市场符号
            
        Returns:
            list: 交易时间表
        """
        return self.trading_hours_client.get_all_trading_days(market.value)
    
    def get_next_opening_time(self, market: MarketSymbol) -> object:
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
    
    def get_status_info(self) -> dict:
        """
        获取状态信息
        
        Returns:
            dict: 状态信息
        """
        status_info = {
            "is_first_run": self.is_first_run,
            "delay_stop_minutes": self.delay_stop_minutes,
            "markets": {}
        }
        
        for market, state in self.market_states.items():
            status_info["markets"][market.value] = {
                "last_market_status": state['last_market_status'],
                "delay_stop_time": state['delay_stop_time'],
                "is_active": state['is_active']
            }
        
        return status_info
