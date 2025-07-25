"""控制台日志处理器."""

import json
import logging
from typing import Any
from datetime import datetime

from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData

logger = logging.getLogger(__name__)


class ConsoleLogHandler(AbstractProcessingHandler):
    """控制台日志处理器，打印数据到控制台，用于调试."""

    def __init__(self) -> None:
        """初始化控制台日志处理器"""
        self.pretty_print = True

    def process(self, data: MarketData) -> Any:
        """处理数据，打印数据到控制台.
        
        Args:
            data: MarketData 对象
            
        Returns:
            处理结果
        """

        try:

            # 打印数据到控制台
            if self.pretty_print:
                log_message = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                log_message = json.dumps(data, ensure_ascii=False)

            print(f"[MARKET_DATA] {log_message}")
        except Exception as e:
            logger.error(f"Failed to log data to console: {e}")
            return None
