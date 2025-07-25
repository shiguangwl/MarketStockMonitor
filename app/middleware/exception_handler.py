"""异常处理中间件."""

from datetime import datetime
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from app.models.responses import ErrorResponse
from app.utils.exceptions import MarketDataError, SourceNotFoundError, InvalidParameterError, DataFetchError
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()


def setup_exception_handlers(app: FastAPI) -> None:
    """设置异常处理器."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """HTTP异常处理器."""
        api_logger.warning(f"❌ HTTP异常: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                detail=exc.detail,
                error_code=f"HTTP_{exc.status_code}"
            ).dict()
        )
    
    @app.exception_handler(SourceNotFoundError)
    async def source_not_found_handler(request, exc):
        """数据源未找到异常处理器."""
        api_logger.warning(f"❌ 数据源未找到: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                detail=str(exc),
                error_code="SOURCE_NOT_FOUND"
            ).dict()
        )
    
    @app.exception_handler(InvalidParameterError)
    async def invalid_parameter_handler(request, exc):
        """无效参数异常处理器."""
        api_logger.warning(f"❌ 无效参数: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail=str(exc),
                error_code="INVALID_PARAMETER"
            ).dict()
        )
    
    @app.exception_handler(DataFetchError)
    async def data_fetch_error_handler(request, exc):
        """数据获取异常处理器."""
        api_logger.error(f"❌ 数据获取失败: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail=str(exc),
                error_code="DATA_FETCH_ERROR"
            ).dict()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """通用异常处理器."""
        api_logger.error(f"❌ 未处理的异常: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "服务器内部错误",
                "error_code": "INTERNAL_SERVER_ERROR",
                "timestamp": datetime.now().isoformat()
            }
        )
