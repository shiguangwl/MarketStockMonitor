"""健康检查控制器."""

from datetime import datetime
from fastapi import APIRouter, Depends
from app.models.responses import HealthResponse
from app.services import SourceService
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()

health_router = APIRouter(tags=["健康检查"])

# 启动时间记录
startup_time = datetime.now()


def get_source_service() -> SourceService:
    """依赖注入：获取数据源服务."""
    return None  # 将通过dependency_overrides设置


@health_router.get(
    "/",
    summary="根路径",
    description="API根路径，返回基本信息"
)
def read_root():
    """根路径端点."""
    return {
        "message": "MarketStockMonitor API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查",
    description="检查API服务健康状态"
)
def health_check(source_service: SourceService = Depends(get_source_service)):
    """健康检查端点."""
    uptime = datetime.now() - startup_time
    api_logger.info("🔍 健康检查请求")
    
    return HealthResponse(
        status="healthy",
        uptime=str(uptime),
        sources_count=source_service.get_sources_count()
    )