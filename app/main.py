"""重构后的应用主入口文件."""

import asyncio
import uvicorn
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config.settings import get_settings
from app.middleware.cors import setup_cors
from app.middleware.exception_handler import setup_exception_handlers
from app.controllers import health_router, sources_router, market_router
from app.services import SourceService, MarketService

# 导入原有的数据源和处理器
from markt.impl.WenCaiSource import WenCaiSource
from pipeline.ConsoleLogHandler import ConsoleLogHandler
from models.market_data import MarketData
from utils.logger_config import setup_market_data_logger, setup_api_logger

# 设置日志器
market_logger = setup_market_data_logger()
api_logger = setup_api_logger()

# 获取配置
settings = get_settings()

# 数据源列表
source_list = [
    WenCaiSource(),
]

# 数据分发链
pipelines = [
    ConsoleLogHandler(format_type='detailed'),
    # RealTimeDataSeeHandler(),
    # KlinkCustomNotifyHandler(),
]

# 服务实例
source_service = SourceService(source_list)
market_service = MarketService(source_service)


def data_handler(data: MarketData) -> None:
    """数据处理回调函数."""
    try:
        for pipeline in pipelines:
            pipeline.process(data)
    except Exception as e:
        market_logger.error(f"❌ 数据处理失败: {str(e)}")


def init_data_core() -> None:
    """初始化市场数据核心系统."""
    market_logger.info("🚀 初始化市场数据核心系统")
    
    # 注册回调
    for source in source_list:
        market_logger.info(f"注册数据源: {source.get_source_info().source_name}")
        source.attach(data_handler)
    
    # 启动数据源
    for source in source_list:
        market_logger.info(f"启动数据源: {source.get_source_info().source_name}")
        source.start()
    
    market_logger.info("✅ 市场数据核心系统初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    # 启动时执行
    try:
        init_data_core()
        api_logger.info("🚀 MarketStockMonitor API 服务启动成功")
    except Exception as e:
        api_logger.error(f"❌ 启动失败: {str(e)}")
        raise
    
    yield
    
    # 关闭时执行清理工作
    try:
        api_logger.info("🛑 MarketStockMonitor API 服务正在关闭...")
        # 在这里添加清理逻辑，如停止定时任务、关闭连接等
    except Exception as e:
        api_logger.error(f"❌ 关闭时出现错误: {str(e)}")


def create_app() -> FastAPI:
    """创建FastAPI应用实例."""
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url
    )
    
    # 设置中间件
    setup_cors(app, settings)
    setup_exception_handlers(app)
    
    # 注册路由
    app.include_router(health_router)
    app.include_router(sources_router, prefix=settings.api_prefix)
    app.include_router(market_router, prefix=settings.api_prefix)
    
    return app


# 依赖注入设置
def get_source_service():
    """获取数据源服务实例."""
    return source_service


def get_market_service():
    """获取市场数据服务实例."""
    return market_service


# 创建应用实例
app = create_app()

# 导入依赖注入函数
from app.controllers.health import get_source_service as health_get_source_service
from app.controllers.sources import get_source_service as sources_get_source_service  
from app.controllers.market import get_market_service as market_get_market_service

# 使用FastAPI的依赖注入覆盖
app.dependency_overrides[health_get_source_service] = lambda: source_service
app.dependency_overrides[sources_get_source_service] = lambda: source_service
app.dependency_overrides[market_get_market_service] = lambda: market_service


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        access_log=True
    )