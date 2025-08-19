"""
数据处理器模块
负责数据映射、转换和增量处理
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from models.market_data import MarketSymbol, MarketData, MarketDataType, MarketSourceInfo
from wen_cai.price_data_point import SinaPriceDataPoint
from utils.logger_config import setup_logger

logger = setup_logger("data_processor")


class DataProcessor:
    """数据处理器"""
    
    def __init__(self, symbol_mapping: Dict[str, str]):
        self.symbol_mapping = symbol_mapping
    
    def map_symbol(self, original_symbol: str) -> str:
        """
        映射符号名称
        
        Args:
            original_symbol: 原始符号名称
            
        Returns:
            str: 映射后的符号名称
        """
        return self.symbol_mapping.get(original_symbol, original_symbol)
    
    def process_realtime_data(
        self, 
        raw_data: Dict[str, SinaPriceDataPoint], 
        source_id: str
    ) -> List[MarketData]:
        """
        处理实时数据
        
        Args:
            raw_data: 原始实时数据
            source_id: 数据源ID
            
        Returns:
            List[MarketData]: 处理后的市场数据列表
        """
        processed_data = []
        
        for key, value in raw_data.items():
            symbol_str = self.map_symbol(key)
            if symbol_str:
                try:
                    symbol_enum = MarketSymbol(symbol_str)
                    market_data = MarketData(
                        source=source_id,
                        symbol=symbol_enum,
                        type=MarketDataType.REALTIME,
                        price=value.price,
                        timestamp=value.time,
                    )
                    processed_data.append(market_data)
                except ValueError as e:
                    logger.warning(f"⚠️ 无效的符号映射: {key} -> {symbol_str}, 错误: {e}")
        
        return processed_data
    
    def process_kline_data(
        self, 
        kline_data: Dict[MarketSymbol, List[SinaPriceDataPoint]], 
        source_id: str,
        last_update_time: Optional[datetime] = None
    ) -> Tuple[List[MarketData], Optional[datetime], int]:
        """
        处理K线数据
        
        Args:
            kline_data: K线数据字典
            source_id: 数据源ID
            last_update_time: 上次更新时间
            
        Returns:
            Tuple[List[MarketData], Optional[datetime], int]: 
            (处理后的数据列表, 最新数据时间, 处理的数据条数)
        """
        processed_data = []
        max_data_time = last_update_time
        total_processed = 0
        
        for symbol, kline_list in kline_data.items():
            if not kline_list:
                continue
            
            # 获取增量数据
            new_items = [
                item for item in kline_list 
                if last_update_time is None or item.time > last_update_time
            ]
            
            # 处理新数据
            for item in new_items:
                market_data = MarketData(
                    source=source_id,
                    symbol=symbol,
                    type=MarketDataType.KLINE1M,
                    price=item.price,
                    timestamp=item.time,
                )
                processed_data.append(market_data)
                
                # 更新最新数据时间
                if max_data_time is None or (item.time and item.time > max_data_time):
                    max_data_time = item.time
            
            total_processed += len(new_items)
            
            if new_items:
                logger.info(f"📊 处理了 {symbol.value} 的 {len(new_items)} 条新K线数据")
        
        return processed_data, max_data_time, total_processed
    
    def validate_data_point(self, data_point: SinaPriceDataPoint) -> bool:
        """
        验证数据点有效性
        
        Args:
            data_point: 数据点
            
        Returns:
            bool: 数据点是否有效
        """
        if not data_point:
            return False
        
        if not hasattr(data_point, 'price') or data_point.price is None:
            return False
        
        if not hasattr(data_point, 'time') or data_point.time is None:
            return False
        
        return True
    
    def filter_valid_data(self, data_list: List[SinaPriceDataPoint]) -> List[SinaPriceDataPoint]:
        """
        过滤有效数据
        
        Args:
            data_list: 数据列表
            
        Returns:
            List[SinaPriceDataPoint]: 有效数据列表
        """
        valid_data = []
        invalid_count = 0
        
        for item in data_list:
            if self.validate_data_point(item):
                valid_data.append(item)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            logger.warning(f"⚠️ 过滤掉 {invalid_count} 条无效数据")
        
        return valid_data
    
    def get_processing_stats(self, original_count: int, processed_count: int) -> Dict[str, int]:
        """
        获取处理统计信息
        
        Args:
            original_count: 原始数据条数
            processed_count: 处理后数据条数
            
        Returns:
            Dict[str, int]: 统计信息
        """
        return {
            "original_count": original_count,
            "processed_count": processed_count,
            "filtered_count": original_count - processed_count,
            "filter_rate": round((original_count - processed_count) / original_count * 100, 2) if original_count > 0 else 0
        }
