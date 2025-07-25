"""参数验证工具."""

from typing import List
from fastapi import HTTPException, status
from models.market_data import MarketSymbol, MarketDataType
from app.utils.exceptions import SourceNotFoundError, InvalidParameterError


def validate_market_symbol(market: str) -> MarketSymbol:
    """验证并转换市场代码."""
    try:
        return MarketSymbol(market.upper())
    except ValueError:
        valid_markets = [symbol.value for symbol in MarketSymbol]
        raise InvalidParameterError(
            f"无效的市场代码: {market}。支持的市场: {', '.join(valid_markets)}"
        )


def validate_data_type(data_type: str) -> MarketDataType:
    """验证并转换数据类型."""
    try:
        return MarketDataType(data_type.lower())
    except ValueError:
        valid_types = [dt.value for dt in MarketDataType]
        raise InvalidParameterError(
            f"无效的数据类型: {data_type}。支持的类型: {', '.join(valid_types)}"
        )


def find_source_by_id(source_list: List, source_id: str):
    """根据source_id查找数据源."""
    for source in source_list:
        if source.get_source_info().source_id == source_id:
            return source
    raise SourceNotFoundError(f"数据源 {source_id} 未找到")


def convert_exceptions_to_http(func):
    """装饰器：将自定义异常转换为HTTP异常."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SourceNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except InvalidParameterError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"服务器内部错误: {str(e)}"
            )
    return wrapper