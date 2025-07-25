"""应用配置设置."""

from typing import List
from functools import lru_cache


class Settings:
    """应用配置类."""
    
    # 应用基本信息
    app_name: str = "MarketStockMonitor API"
    app_description: str = "市场股票监控系统API，提供实时行情数据、交易时间表和市场状态查询功能"
    app_version: str = "1.0.0"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # CORS配置
    cors_origins: List[str] = ["*"]
    cors_methods: List[str] = ["*"]
    cors_headers: List[str] = ["*"]
    
    # 日志配置
    log_level: str = "INFO"
    
    # API配置
    api_prefix: str = "/api"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置单例."""
    return Settings()