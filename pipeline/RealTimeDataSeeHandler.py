from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData


class RealTimeDataSeeHandler(AbstractProcessingHandler):
    """实时数据的SSE推送"""
    
    def process(self, data: MarketData) -> None:
        pass