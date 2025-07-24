"""系统启动入口."""

import logging
from ast import List
import asyncio
from markt.impl.WenCaiSource import WenCaiSource
from models.market_data import MarketData
from pipeline.KlinkCustomNotifyHandler import KlinkCustomNotifyHandler
from pipeline.RealTimeDataSeeHandler import RealTimeDataSeeHandler

log = logging.getLogger(__name__)

source_list = [
    WenCaiSource(),
]

pipeline = [
    RealTimeDataSeeHandler(),
    KlinkCustomNotifyHandler(),
]

def data_handler(data: MarketData) -> None:
    """数据处理"""
    log.info(f"收到数据: {data}")
    for pipeline in pipeline:
        pipeline.process(data)

def main() -> None:
    """主函数，启动应用."""
    # 注册回调
    for source in source_list:
        source.attach(data_handler)
    # 启动数据源
    for source in source_list:
        source.start()
    # 初始化 WEB 服务
    # init_web_server()

if __name__ == "__main__":
    """程序入口点."""
    asyncio.run(main())