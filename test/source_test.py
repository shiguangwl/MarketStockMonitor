from datetime import datetime
from markt.impl.WenCaiSource import WenCaiSource
from models.market_data import MarketDataType, MarketSymbol


def main() -> None:
    wenCaiSource = WenCaiSource()
    
    # 获取收盘状态和节假日计划
    nasdaq_status = wenCaiSource.get_market_status(datetime.now(), MarketSymbol.NASDAQ)
    hsi_status = wenCaiSource.get_market_status(datetime.now(), MarketSymbol.HSI)
    print("纳斯达克收盘状态: " + str(nasdaq_status))
    print("香港收盘状态: " + str(hsi_status))
    
    # 获取节假日计划
    nasdaq_holidays = wenCaiSource.get_trading_hours(MarketSymbol.NASDAQ)
    hsi_holidays = wenCaiSource.get_trading_hours(MarketSymbol.HSI)
    print("纳斯达克节假日计划: " + str(nasdaq_holidays))
    print("香港节假日计划: " + str(hsi_holidays))
    
    # 获取K线数据
    nasdaq_kline = wenCaiSource.get_latest_data(MarketSymbol.NASDAQ, MarketDataType.KLINE1M)
    hsi_kline = wenCaiSource.get_latest_data(MarketSymbol.HSI, MarketDataType.KLINE1M)
    print("纳斯达克K线数据(最新): " + str(nasdaq_kline))
    print("香港K线数据(最新): " + str(hsi_kline))
    
    # 实时数据
    nasdaq_realtime = wenCaiSource.get_latest_data(MarketSymbol.NASDAQ, MarketDataType.REALTIME)
    hsi_realtime = wenCaiSource.get_latest_data(MarketSymbol.HSI, MarketDataType.REALTIME)
    print("纳斯达克实时数据: " + str(nasdaq_realtime))
    print("香港实时数据: " + str(hsi_realtime))


if __name__ == "__main__":
    main()