"""数据源控制器."""

from typing import List
from fastapi import APIRouter, Depends
from app.models.responses import SourceInfoResponse
from app.services import SourceService
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()

sources_router = APIRouter(prefix="/sources", tags=["数据源"])


def get_source_service() -> SourceService:
    """依赖注入：获取数据源服务."""
    return None  # 将通过dependency_overrides设置


@sources_router.get(
    "/",
    response_model=List[SourceInfoResponse],
    summary="获取数据源列表",
    description="获取系统中所有可用的数据源列表及其支持的市场"
)
def get_data_sources(source_service: SourceService = Depends(get_source_service)):
    """获取数据源列表."""
    api_logger.info("🔍 请求获取数据源列表")
    
    sources = source_service.get_all_sources()
    api_logger.info(f"✅ 返回 {len(sources)} 个数据源")
    
    return sources