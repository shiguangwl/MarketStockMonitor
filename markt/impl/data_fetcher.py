"""
数据获取器模块
负责网络请求、超时处理和重试逻辑
"""

from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from models.market_data import MarketSymbol
from wen_cai.sina_realtime_quote_client import SinaRealtimeQuoteClient
from wen_cai.wen_cai_client import WenCaiClient
from wen_cai.price_data_point import SinaPriceDataPoint
from utils.logger_config import setup_logger

logger = setup_logger("data_fetcher")


class DataFetcher:
    """数据获取器"""
    
    def __init__(self, max_workers: int = 2, single_source_timeout: float = 3.0):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.single_source_timeout = single_source_timeout
        
        # 客户端实例
        self.sina_realtime_quote_client = SinaRealtimeQuoteClient()
        self.wen_cai_client = WenCaiClient()
    
    def fetch_realtime_quotes(self, markets: List[MarketSymbol]) -> Dict[str, SinaPriceDataPoint]:
        """
        获取实时行情数据
        
        Args:
            markets: 市场列表
            
        Returns:
            Dict[str, SinaPriceDataPoint]: 实时行情数据
        """
        stock_codes_to_fetch = []
        for market in markets:
            if market == MarketSymbol.HSI:
                stock_codes_to_fetch.append("rt_hkHSI")
            elif market == MarketSymbol.NASDAQ:
                stock_codes_to_fetch.append("gb_ixic")
        
        return self.sina_realtime_quote_client.fetch_sina_quotes(stock_codes_to_fetch)
    
    def fetch_kline_data(self, market: MarketSymbol) -> Optional[List[SinaPriceDataPoint]]:
        """
        获取K线数据
        
        Args:
            market: 市场符号
            
        Returns:
            Optional[List[SinaPriceDataPoint]]: K线数据列表
        """
        try:
            future = self.executor.submit(self._get_kline_fetcher(market))
            return future.result(timeout=self.single_source_timeout)
        except FutureTimeoutError:
            logger.error(f"⏰ 获取{market.value} K线数据超时")
            future.cancel()
            return None
        except ValueError as e:
            logger.error(f"❌ 不支持的市场: {market.value}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ 获取{market.value} K线数据失败: {e}")
            return None
    
    def _get_kline_fetcher(self, market: MarketSymbol) -> Callable:
        """
        获取K线数据获取函数
        
        Args:
            market: 市场符号
            
        Returns:
            Callable: 数据获取函数
        """
        if market == MarketSymbol.HSI:
            return self.wen_cai_client.get_hsi_kline
        elif market == MarketSymbol.NASDAQ:
            return self.wen_cai_client.get_nasdaq_kline
        else:
            raise ValueError(f"不支持的市场: {market}")
    
    def fetch_all_kline_data(self, markets: List[MarketSymbol]) -> Dict[MarketSymbol, Optional[List[SinaPriceDataPoint]]]:
        """
        批量获取K线数据
        
        Args:
            markets: 市场列表
            
        Returns:
            Dict[MarketSymbol, Optional[List[SinaPriceDataPoint]]]: 各市场的K线数据
        """
        results = {}
        for market in markets:
            results[market] = self.fetch_kline_data(market)
        return results
    
    def shutdown(self) -> None:
        """关闭线程池"""
        self.executor.shutdown(wait=False)
    
    def get_executor_status(self) -> Dict[str, Any]:
        """
        获取线程池状态
        
        Returns:
            Dict[str, Any]: 线程池状态信息
        """
        return {
            "max_workers": self.executor._max_workers,
            "thread_name_prefix": self.executor._thread_name_prefix,
            "shutdown": self.executor._shutdown,
        }


class DataFetchResult:
    """数据获取结果"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None, execution_time: float = 0.0):
        self.success = success
        self.data = data
        self.error = error
        self.execution_time = execution_time
    
    def __bool__(self) -> bool:
        return self.success
    
    def __str__(self) -> str:
        if self.success:
            return f"DataFetchResult(success=True, execution_time={self.execution_time:.2f}s)"
        else:
            return f"DataFetchResult(success=False, error='{self.error}', execution_time={self.execution_time:.2f}s)"
