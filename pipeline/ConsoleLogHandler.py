"""控制台日志处理器."""

import json
from typing import Any
from datetime import datetime

from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData
from utils.logger_config import setup_pipeline_logger

logger = setup_pipeline_logger()


class ConsoleLogHandler(AbstractProcessingHandler):
    """控制台日志处理器，打印数据到控制台，用于调试."""

    def __init__(self, format_type: str = 'simple') -> None:
        """初始化控制台日志处理器
        
        Args:
            format_type: 输出格式类型 ('simple', 'detailed', 'json')
        """
        self.format_type = format_type

    def process(self, data: MarketData) -> Any:
        """处理数据，打印数据到控制台.
        
        Args:
            data: MarketData 对象
            
        Returns:
            处理结果
        """
        try:
            if self.format_type == 'simple':
                # 简化格式：时间 市场 类型 价格
                message = data.to_simple_string()
            elif self.format_type == 'detailed':
                # 详细格式：使用自定义的__str__方法
                message = str(data)
            elif self.format_type == 'json':
                # JSON格式：使用to_json方法
                message = f"市场数据更新:\n{data.to_json()}"
            else:
                message = data.to_simple_string()
            
            logger.info(f"📈 {message}")
            
        except Exception as e:
            logger.error(f"处理市场数据失败: {e}")
            logger.debug(f"原始数据: {data}")
            return None
        
        return data
