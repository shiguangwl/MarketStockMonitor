# """控制台日志处理器."""

# import json
# import logging
# from typing import Any
# from datetime import datetime

# from app.interfaces.IProcessingHandler import AbstractProcessingHandler
# from app.models.market_data import MarketData

# logger = logging.getLogger(__name__)


# class ConsoleLogHandler(AbstractProcessingHandler):
#     """控制台日志处理器，打印数据到控制台，用于调试."""
    
#     def __init__(self, pretty_print: bool = False) -> None:
#         """初始化控制台日志处理器.
        
#         Args:
#             pretty_print: 是否格式化打印
#         """
#         super().__init__()
#         self.pretty_print = pretty_print
    
#     async def _process(self, request: Any) -> Any:
#         """处理数据，打印数据到控制台.
        
#         Args:
#             request: MarketData 对象
            
#         Returns:
#             处理结果
#         """
#         if not isinstance(request, MarketData):
#             logger.warning(f"ConsoleLogHandler received non-MarketData object: {type(request)}")
#             return None
        
#         try:
#             # 将MarketData转换为字典格式
#             payload = request.model_dump()
#             # 添加时间戳
#             payload["log_time"] = datetime.now().isoformat()
            
#             # 打印数据到控制台
#             if self.pretty_print:
#                 log_message = json.dumps(payload, indent=2, ensure_ascii=False)
#             else:
#                 log_message = json.dumps(payload, ensure_ascii=False)
            
#             print(f"[MARKET_DATA] {log_message}")
#             logger.info(f"Market data logged to console for symbol: {request.symbol}")
#             return request
#         except Exception as e:
#             logger.error(f"Failed to log data to console: {e}")
#             return None