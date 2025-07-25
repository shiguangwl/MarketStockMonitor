from datetime import datetime
from time import sleep

from markt.impl.WenCaiSource import WenCaiSource
from models.market_data import MarketDataType, MarketSymbol, MarketData


def data_handler(data: MarketData):
    print("获取到数据：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + str(data))

def main() -> None:
    wenCaiSource = WenCaiSource()

    wenCaiSource.attach(data_handler)

    while True:
        wenCaiSource._tick_update_kline()
        wenCaiSource._tick_update_realtime()
        sleep(1.5)



if __name__ == "__main__":
    main()