"""
市场状态管理模块
负责检查市场开市状态和管理延迟停止逻辑
"""

from datetime import datetime, timedelta
from typing import Optional
from models.market_data import MarketSymbol
from wen_cai.sina_trading_hours_client import CurrentStatus, TradingHoursClient
from utils.logger_config import setup_logger

logger = setup_logger("market_status_manager")


class MarketStatusManager:
    """市场状态管理器"""
    
    def __init__(self, delay_stop_minutes: int = 10):
        self.trading_hours_client = TradingHoursClient()
        self.delay_stop_minutes = delay_stop_minutes
        
        # 状态跟踪
        self.last_market_status: Optional[bool] = None
        self.delay_stop_time: Optional[datetime] = None
        self.is_first_run: bool = True
    
    def should_continue_fetching(self, check_time: datetime = None) -> bool:
        """
        判断当前是否应继续抓取数据（包括延迟停止时间段）
        
        Args:
            check_time: 检查时间，默认为当前时间
            
        Returns:
            bool: 是否应该继续抓取数据
        """
        if check_time is None:
            check_time = datetime.now()
        
        # 获取当前市场状态
        market_status = self._get_market_status(check_time)
        
        # 如果市场重新开市，取消延迟停止状态
        if market_status.is_open and self.delay_stop_time is not None:
            logger.info("📈 市场重新开市，取消延迟停止状态")
            self.delay_stop_time = None
        
        # 判断是否发生了状态切换：open -> close
        if self.last_market_status is True and not market_status.is_open:
            # 开始延迟停止计时
            self.delay_stop_time = check_time + timedelta(minutes=self.delay_stop_minutes)
            logger.info(f"🕒 市场已关闭，将在{self.delay_stop_minutes}分钟后 ({self.delay_stop_time}) 停止数据抓取")
        
        # 更新上一次状态
        self.last_market_status = market_status.is_open
        
        # 如果设置了 delay_stop_time，则检查是否已到达停止时间
        if self.delay_stop_time:
            if check_time >= self.delay_stop_time:
                logger.info("⏹️ 延迟时间已到，停止数据抓取")
                self.delay_stop_time = None  # 重置
                return False
            else:
                logger.debug("⏳ 处于延迟停止阶段，继续抓取数据")
                return True
        
        # 正常情况下根据市场状态决定是否抓取
        return market_status.is_open
    
    def _get_market_status(self, check_time: datetime) -> CurrentStatus:
        """
        获取指定时间的市场状态
        
        Args:
            check_time: 检查时间
            
        Returns:
            CurrentStatus: 当前市场状态
        """
        return self.trading_hours_client.get_current_trading_status(MarketSymbol.HSI.value)
    
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
        return {
            "last_market_status": self.last_market_status,
            "delay_stop_time": self.delay_stop_time,
            "is_first_run": self.is_first_run,
            "delay_stop_minutes": self.delay_stop_minutes,
        }
