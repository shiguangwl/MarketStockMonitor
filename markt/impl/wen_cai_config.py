"""
问财数据源配置管理
"""

from dataclasses import dataclass
from typing import Dict, Any
from models.market_data import MarketSymbol


@dataclass
class WenCaiConfig:
    """问财数据源配置"""
    
    # 调度配置
    realtime_update_interval: int = 5  # 实时数据更新间隔（秒）
    kline_update_interval: int = 10      # K线数据更新间隔（秒）
    
    # 超时配置
    kline_fetch_timeout: float = 8.0     # K线数据获取超时时间（秒）
    single_source_timeout: float = 3.0   # 单个数据源超时时间（秒）
    
    # 线程池配置
    max_workers: int = 2                 # 线程池最大工作线程数
    
    # 延迟停止配置
    delay_stop_minutes: int = 10         # 市场关闭后延迟停止时间（分钟）
    
    # 性能监控配置
    execution_time_warning_threshold: float = 5.0  # 执行时间警告阈值（秒）
    
    # 符号映射配置
    symbol_mapping: Dict[str, str] = None
    
    def __post_init__(self):
        """初始化默认符号映射"""
        if self.symbol_mapping is None:
            self.symbol_mapping = {
                "rt_hkHSI": MarketSymbol.HSI.value,
                "gb_ixic": MarketSymbol.NASDAQ.value,
                "176_HSI": MarketSymbol.HSI.value,
                "88_IXIC": MarketSymbol.NASDAQ.value,
                "纳斯达克": MarketSymbol.NASDAQ.value,
                "恒生指数": MarketSymbol.HSI.value,
            }
    
    def get_mapping(self, key: str, default: str = None) -> str:
        """获取符号映射"""
        return self.symbol_mapping.get(key, default or key)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "realtime_update_interval": self.realtime_update_interval,
            "kline_update_interval": self.kline_update_interval,
            "kline_fetch_timeout": self.kline_fetch_timeout,
            "single_source_timeout": self.single_source_timeout,
            "max_workers": self.max_workers,
            "delay_stop_minutes": self.delay_stop_minutes,
            "execution_time_warning_threshold": self.execution_time_warning_threshold,
            "symbol_mapping": self.symbol_mapping,
        }


# 默认配置实例
DEFAULT_CONFIG = WenCaiConfig()
