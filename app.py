"""MarketStockMonitor 应用启动入口."""

import uvicorn
from app.main import app, settings

if __name__ == "__main__":
    print("🚀 启动 MarketStockMonitor API 服务")
    print(f"📍 服务地址: http://{settings.host}:{settings.port}")
    print(f"📚 API文档: http://{settings.host}:{settings.port}{settings.docs_url}")
    print(f"🔧 配置信息: {settings.app_name} v{settings.app_version}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        access_log=True
    )
