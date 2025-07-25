"""数据源服务层."""

from typing import List
from datetime import datetime
from models.market_data import MarketSymbol, MarketDataType
from app.models.responses import SourceInfoResponse
from app.utils.validators import find_source_by_id
from utils.logger_config import setup_logger

logger = setup_logger('source_service')


class SourceService:
    """数据源服务类."""
    
    def __init__(self, source_list: List):
        """初始化数据源服务.
        
        Args:
            source_list: 数据源列表
        """
        self.source_list = source_list
        logger.info(f"初始化数据源服务，共 {len(source_list)} 个数据源")
    
    def get_all_sources(self) -> List[SourceInfoResponse]:
        """获取所有数据源信息."""
        logger.info("获取所有数据源信息")
        
        sources = []
        for source in self.source_list:
            source_info = source.get_source_info()
            sources.append(SourceInfoResponse(
                source_id=source_info.source_id,
                source_name=source_info.source_name,
                supported_markets=[market.value for market in source_info.supported_markets]
            ))
        
        logger.info(f"返回 {len(sources)} 个数据源信息")
        return sources
    
    def get_source_by_id(self, source_id: str):
        """根据ID获取数据源."""
        logger.debug(f"查找数据源: {source_id}")
        return find_source_by_id(self.source_list, source_id)
    
    def get_sources_count(self) -> int:
        """获取数据源数量."""
        return len(self.source_list)