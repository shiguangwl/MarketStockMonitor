from typing import List
from models.market_data import MarketData


class AbstractProcessingHandler:
    def process(self, data: MarketData) -> None:
        pass