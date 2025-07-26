"""KlinkCustomNotifyHandler 测试示例."""

from datetime import datetime
from models.market_data import MarketData, MarketSymbol, MarketDataType
from pipeline.KlinkCustomNotifyHandler import KlinkCustomNotifyHandler
from utils.logger_config import setup_pipeline_logger

# 使用项目的日志系统
logger = setup_pipeline_logger()

def test_klink_notify_handler():
    """测试KlinkCustomNotifyHandler"""
    
    logger.info("🧪 开始测试KlinkCustomNotifyHandler")
    
    # 创建处理器实例
    handler = KlinkCustomNotifyHandler(
        notify_url="http://your-api.com/api/draw/openDraw",
        secret_key="your_secret_key_here",
        request_timeout=15
    )
    
    # 创建测试数据 - 15分钟整数倍时间
    test_data = MarketData(
        source="test_source",
        symbol=MarketSymbol.HSI,
        type=MarketDataType.KLINE1M,
        price=25000.50,
        timestamp=datetime(2024, 1, 1, 10, 15, 0),  # 10:15:00 - 15分钟整数倍
        volume=1000,
        open_price=25000.00,
        high_price=25100.00,
        low_price=24900.00,
        close_price=25000.50
    )
    
    logger.info(f"📊 测试数据: {test_data}")
    logger.info(f"⏰ 是否为15分钟整数倍: {handler._is_quarter_minute(test_data)}")
    
    # 测试签名生成
    test_params = {
        "type": "test_source",
        "drawTime": "2024-01-01 10:15:00",
        "drawIndex": "25000.5"
    }
    
    try:
        sign = handler._generate_sign(test_params)
        logger.info(f"🔐 生成的签名: {sign}")
        
        # 测试数据准备
        notify_data = handler._prepare_notify_data(test_data)
        logger.info(f"📤 通知数据: {notify_data}")
        
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
    
    finally:
        # 关闭资源
        handler.close()
        logger.info("🔒 测试完成，资源已释放")

def test_with_context_manager():
    """使用上下文管理器测试"""
    
    logger.info("🧪 开始上下文管理器测试")
    
    # 创建非15分钟整数倍的测试数据
    test_data = MarketData(
        source="test_source",
        symbol=MarketSymbol.NASDAQ,
        type=MarketDataType.KLINE1M,
        price=15000.25,
        timestamp=datetime(2024, 1, 1, 10, 17, 0),  # 10:17:00 - 不是15分钟整数倍
        volume=500
    )
    
    with KlinkCustomNotifyHandler() as handler:
        logger.info(f"📊 测试数据: {test_data}")
        logger.info(f"⏰ 是否为15分钟整数倍: {handler._is_quarter_minute(test_data)}")
        
        # 这个应该会跳过通知
        handler.process(test_data)
    
    logger.info("✅ 上下文管理器测试完成")

def test_retry_delays():
    """测试重试延迟配置"""
    
    logger.info("🧪 测试重试延迟配置")
    
    handler = KlinkCustomNotifyHandler()
    
    logger.info(f"⏳ 重试延迟配置: {handler.RETRY_DELAYS}")
    logger.info(f"🔢 最大重试次数: {handler.max_retries}")
    
    # 测试时间格式化
    for i, delay in enumerate(handler.RETRY_DELAYS):
        formatted_time = handler._format_retry_time(delay)
        logger.info(f"第{i+1}次重试延迟: {delay}秒 -> {formatted_time}")
    
    handler.close()
    logger.info("✅ 重试延迟配置测试完成")

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 KlinkCustomNotifyHandler 测试开始")
    logger.info("=" * 50)
    
    test_klink_notify_handler()
    logger.info("-" * 30)
    
    test_with_context_manager()
    logger.info("-" * 30)
    
    test_retry_delays()
    
    logger.info("=" * 50)
    logger.info("🎉 所有测试完成")
    logger.info("=" * 50)