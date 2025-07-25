"""市场数据服务层."""

from datetime import datetime
from typing import Optional
from models.market_data import MarketSymbol, MarketDataType
from app.models.responses import (
    LatestPriceResponse, PriceData, TradingHoursResponse, TradingHour,
    MarketStatusResponse, MarketStatusInfo, MatchedRule, NextOpeningTimeResponse
)
from app.utils.exceptions import DataFetchError
from utils.logger_config import setup_logger

logger = setup_logger('market_service')


class MarketService:
    """市场数据服务类."""
    
    def __init__(self, source_service):
        """初始化市场数据服务.
        
        Args:
            source_service: 数据源服务实例
        """
        self.source_service = source_service
        logger.info("初始化市场数据服务")
    
    def get_latest_price(self, source_id: str, market: MarketSymbol, 
                        data_type: MarketDataType) -> LatestPriceResponse:
        """获取最新价格数据."""
        logger.info(f"获取最新价格: {source_id}/{market.value}/{data_type.value}")
        
        try:
            source = self.source_service.get_source_by_id(source_id)
            latest_data = source.get_latest_data(market, data_type)
            
            logger.info(f"成功获取 {market.value} 最新价格: {latest_data.price}")
            
            # 安全处理时间字段
            time_str = latest_data.time.isoformat() if hasattr(latest_data.time, 'isoformat') else str(latest_data.time)
            
            return LatestPriceResponse(
                source_id=source_id,
                market=market.value,
                data_type=data_type.value,
                data=PriceData(
                    name=getattr(latest_data, 'name', f"{market.value}"),
                    time=time_str,
                    price=getattr(latest_data, 'price', 0.0),
                    volume=getattr(latest_data, 'volume', None),
                    change=getattr(latest_data, 'change', None),
                    change_percent=getattr(latest_data, 'change_percent', None)
                )
            )
        except Exception as e:
            logger.error(f"获取最新价格失败: {str(e)}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            raise DataFetchError(f"获取最新价格失败: {str(e)}")
    
    def get_trading_hours(self, source_id: str, market: MarketSymbol) -> TradingHoursResponse:
        """获取交易时间表."""
        logger.info(f"获取交易时间表: {source_id}/{market.value}")
        
        try:
            source = self.source_service.get_source_by_id(source_id)
            trading_hours = source.get_trading_hours(market)
            
            logger.info(f"成功获取 {market.value} 交易时间表: {len(trading_hours)} 条记录")
            
            return TradingHoursResponse(
                source_id=source_id,
                market=market.value,
                trading_hours=[
                    TradingHour(
                        start=th.start.isoformat(),
                        end=th.end.isoformat(),
                        text=th.text
                    )
                    for th in trading_hours
                ]
            )
        except Exception as e:
            logger.error(f"获取交易时间表失败: {str(e)}")
            raise DataFetchError(f"获取交易时间表失败: {str(e)}")
    
    def get_market_status(self, source_id: str, market: MarketSymbol, 
                         check_time: Optional[datetime] = None) -> MarketStatusResponse:
        """获取市场状态."""
        if check_time is None:
            check_time = datetime.now()
            
        time_info = f" 时间: {check_time.isoformat()}" if check_time else " (当前时间)"
        logger.info(f"获取市场状态: {source_id}/{market.value}{time_info}")
        
        try:
            source = self.source_service.get_source_by_id(source_id)
            status_info = source.get_market_status(check_time, market)
            
            status_emoji = "🟢" if status_info.is_open else "🔴"
            logger.info(f"成功获取 {market.value} 市场状态: {status_emoji} {status_info.status_text}")
            
            return MarketStatusResponse(
                source_id=source_id,
                market=market.value,
                check_time=check_time.isoformat(),
                status=MarketStatusInfo(
                    is_open=status_info.is_open,
                    status_text=status_info.status_text,
                    market_time=status_info.market_time.isoformat() if status_info.market_time else None,
                    matched_rule=MatchedRule(
                        date_pattern=status_info.matched_rule.date_pattern,
                        start_time=status_info.matched_rule.start_time,
                        end_time=status_info.matched_rule.end_time,
                        description=status_info.matched_rule.description
                    ) if status_info.matched_rule else None
                )
            )
        except Exception as e:
            logger.error(f"获取市场状态失败: {str(e)}")
            raise DataFetchError(f"获取市场状态失败: {str(e)}")
    
    def get_next_opening_time(self, source_id: str, market: MarketSymbol) -> NextOpeningTimeResponse:
        """获取下一个开盘时间."""
        logger.info(f"获取下一个开盘时间: {source_id}/{market.value}")
        
        try:
            source = self.source_service.get_source_by_id(source_id)
            next_opening_time = source.get_next_opening_time(market)
            
            logger.info(f"成功获取 {market.value} 下一个开盘时间: {next_opening_time.date_pattern} {next_opening_time.start_time} - {next_opening_time.end_time}")
            
            return NextOpeningTimeResponse(
                source_id=source_id,
                market=market.value,
                next_opening_time=next_opening_time.date_pattern,
                start_time=next_opening_time.start_time,
                end_time=next_opening_time.end_time,
                description=next_opening_time.description
            )
        except Exception as e:
            logger.error(f"获取下一个开盘时间失败: {str(e)}")
            raise DataFetchError(f"获取下一个开盘时间失败: {str(e)}")