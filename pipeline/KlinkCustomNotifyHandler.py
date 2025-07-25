"""K线合并处理器."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData

logger = logging.getLogger(__name__)


class KlinkCustomNotifyHandler(AbstractProcessingHandler):
    """K线合并处理器，判断 MarketData 的时间戳是否满足特定K线周期."""

    async def process(self, data: MarketData) -> None:
        """处理数据，判断是否满足K线周期"""

