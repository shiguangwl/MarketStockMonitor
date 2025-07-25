"""系统启动入口."""

import logging
import asyncio
import uvicorn
from markt.impl.WenCaiSource import WenCaiSource
from models.market_data import MarketData
from pipeline.ConsoleLogHandler import ConsoleLogHandler
from pipeline.KlinkCustomNotifyHandler import KlinkCustomNotifyHandler
from pipeline.RealTimeDataSeeHandler import RealTimeDataSeeHandler
from typing import Union
from fastapi import FastAPI


log = logging.getLogger(__name__)

source_list = [
    WenCaiSource(),
]

pipelines = [
    ConsoleLogHandler(),
    # RealTimeDataSeeHandler(),
    # KlinkCustomNotifyHandler(),
]

def data_handler(data: MarketData) -> None:
    """数据处理"""
    log.info(f"收到数据: {data}")
    for pipeline in pipelines:
        pipeline.process(data)

def init_data_core() -> None:
    """主函数，启动应用."""
    # 注册回调
    for source in source_list:
        source.attach(data_handler)
    # 启动数据源
    for source in source_list:
        source.start()

app = FastAPI()

init_data_core()

@app.get("/")
def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
