"""市场数据控制器."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Path, Query, Depends
from app.models.responses import (
    LatestPriceResponse, TradingHoursResponse, 
    MarketStatusResponse, NextOpeningTimeResponse
)
from app.services import MarketService
from app.utils.validators import validate_market_symbol, validate_data_type, convert_exceptions_to_http
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()

market_router = APIRouter(prefix="/sources", tags=["市场数据"])


def get_market_service() -> MarketService:
    """依赖注入：获取市场数据服务."""
    return None  # 将通过dependency_overrides设置


@market_router.get(
    "/{source_id}/latest/{market}/{data_type}",
    response_model=LatestPriceResponse,
    summary="获取最新价格数据",
    description="获取指定数据源的指定市场的最新价格数据"
)
def get_latest_price(
    source_id: str = Path(..., description="数据源ID，如: wen_cai"),
    market: str = Path(..., description="市场代码，如: HSI, NASDAQ"),
    data_type: str = Path(..., description="数据类型，如: realtime, kline1m"),
    market_service: MarketService = Depends(get_market_service)
):
    """获取指定数据源的指定类型的最新价格数据."""
    try:
        # 验证参数
        market_symbol = validate_market_symbol(market)
        market_data_type = validate_data_type(data_type)
        
        return market_service.get_latest_price(source_id, market_symbol, market_data_type)
    except Exception as e:
        api_logger.error(f"❌ 获取最新价格失败: {str(e)}")
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@market_router.get(
    "/{source_id}/trading-hours/{market}",
    response_model=TradingHoursResponse,
    summary="获取交易时间表",
    description="获取指定市场的特殊交易时间表（包括节假日安排等）"
)
def get_trading_hours(
    source_id: str = Path(..., description="数据源ID，如: wen_cai"),
    market: str = Path(..., description="市场代码，如: HSI, NASDAQ"),
    market_service: MarketService = Depends(get_market_service)
):
    """获取特殊交易时间表."""
    try:
        # 验证市场代码
        market_symbol = validate_market_symbol(market)
        
        return market_service.get_trading_hours(source_id, market_symbol)
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@market_router.get(
    "/{source_id}/market-status/{market}",
    response_model=MarketStatusResponse,
    summary="获取市场状态",
    description="获取指定市场在特定时间的开盘状态"
)
def get_market_status(
    source_id: str = Path(..., description="数据源ID，如: wen_cai"),
    market: str = Path(..., description="市场代码，如: HSI, NASDAQ"),
    check_time: Optional[str] = Query(None, description="检查时间 (ISO格式，可选，默认为当前时间)"),
    market_service: MarketService = Depends(get_market_service)
):
    """获取指定源的指定市场的状态."""
    try:
        # 验证市场代码
        market_symbol = validate_market_symbol(market)
        
        # 处理检查时间
        check_datetime = None
        if check_time:
            try:
                check_datetime = datetime.fromisoformat(check_time.replace('Z', '+00:00'))
            except ValueError:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的时间格式: {check_time}。请使用ISO格式，如: 2024-01-15T09:00:00"
                )
        
        return market_service.get_market_status(source_id, market_symbol, check_datetime)
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@market_router.get(
    "/{source_id}/next-opening-time/{market}",
    response_model=NextOpeningTimeResponse,
    summary="获取下一个开盘时间",
    description="获取指定市场的下一个开盘时间信息"
)
def get_next_opening_time(
    source_id: str = Path(..., description="数据源ID，如: wen_cai"),
    market: str = Path(..., description="市场代码，如: HSI, NASDAQ"),
    market_service: MarketService = Depends(get_market_service)
):
    """获取指定市场的下一个开盘时间."""
    try:
        # 验证市场代码
        market_symbol = validate_market_symbol(market)
        
        return market_service.get_next_opening_time(source_id, market_symbol)
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
