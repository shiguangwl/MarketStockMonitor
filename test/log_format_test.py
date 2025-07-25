"""测试新的日志格式和MarketData格式化."""

from datetime import datetime
from models.market_data import MarketData, MarketDataType, MarketSymbol
from utils.logger_config import setup_logger, setup_market_data_logger, setup_pipeline_logger
from pipeline.ConsoleLogHandler import ConsoleLogHandler

def test_market_data_formatting():
    """测试MarketData的格式化方法."""
    print("=" * 60)
    print("测试 MarketData 格式化方法")
    print("=" * 60)
    
    # 创建测试数据
    test_data = MarketData(
        source="wen_cai",
        symbol=MarketSymbol.HSI,
        type=MarketDataType.REALTIME,
        price=25398.84,
        timestamp=datetime.now(),
        volume=1000000,
        change=+50.24,
        change_percent=+0.2
    )
    
    print("\n1. 简化字符串格式 (to_simple_string):")
    print(test_data.to_simple_string())
    
    print("\n2. 标准字符串格式 (__str__):")
    print(str(test_data))
    
    print("\n3. JSON格式 (to_json):")
    print(test_data.to_json())
    
    print("\n4. 字典格式 (to_dict):")
    import json
    print(json.dumps(test_data.to_dict(), ensure_ascii=False, indent=2))


def test_logger_formatting():
    """测试日志器格式化."""
    print("\n" + "=" * 60)
    print("测试日志器格式化")
    print("=" * 60)
    
    # 测试不同的日志器
    loggers = [
        ("市场数据日志器", setup_market_data_logger()),
        ("管道日志器", setup_pipeline_logger()),
        ("通用日志器", setup_logger('test_logger'))
    ]
    
    for name, logger in loggers:
        print(f"\n{name}:")
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志") 
        logger.error("这是一条错误日志")


def test_console_handler():
    """测试控制台处理器的不同格式."""
    print("\n" + "=" * 60)
    print("测试控制台处理器格式")
    print("=" * 60)
    
    # 创建测试数据
    test_data = MarketData(
        source="wen_cai",
        symbol=MarketSymbol.NASDAQ,
        type=MarketDataType.KLINE1M,
        price=21057.959,
        timestamp=datetime.now(),
        volume=500000
    )
    
    # 测试不同的格式类型
    formats = ['simple', 'detailed', 'json']
    
    for format_type in formats:
        print(f"\n{format_type.upper()} 格式:")
        handler = ConsoleLogHandler(format_type=format_type)
        handler.process(test_data)


def test_error_handling():
    """测试错误处理."""
    print("\n" + "=" * 60)
    print("测试错误处理")
    print("=" * 60)
    
    logger = setup_logger('error_test')
    
    try:
        # 模拟一个错误
        raise ValueError("这是一个测试错误")
    except Exception as e:
        logger.error(f"❌ 捕获到错误: {e}")
        logger.debug(f"错误详情: {type(e).__name__}")


if __name__ == "__main__":
    test_market_data_formatting()
    test_logger_formatting()
    test_console_handler()
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ 所有日志格式测试完成")
    print("=" * 60) 