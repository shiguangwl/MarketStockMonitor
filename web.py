"""系统启动入口."""

import asyncio
import uvicorn
from datetime import datetime
from markt.impl.WenCaiSource import WenCaiSource
from models.market_data import MarketData, MarketDataType, MarketSymbol, MarketSourceInfo
from pipeline.ConsoleLogHandler import ConsoleLogHandler
from pipeline.KlinkCustomNotifyHandler import KlinkCustomNotifyHandler
from pipeline.RealTimeDataSeeHandler import RealTimeDataSeeHandler
from wen_cai.trading_hours_client import CurrentStatus, TradingDay
from typing import Union, List
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from utils.logger_config import setup_market_data_logger, setup_api_logger

# 设置日志器
market_logger = setup_market_data_logger()
api_logger = setup_api_logger()

source_list = [
    WenCaiSource(),
]

pipelines = [
    ConsoleLogHandler(format_type='simple'),  # 使用简化格式
    # RealTimeDataSeeHandler(),
    # KlinkCustomNotifyHandler(),
]

def data_handler(data: MarketData) -> None:
    """数据处理"""
    for pipeline in pipelines:
        pipeline.process(data)

def init_data_core() -> None:
    """主函数，启动应用."""
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
    # 启动时执行
    init_data_core()
    yield
    # 关闭时执行（如果需要的话）

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/api/sources", response_model=List[MarketSourceInfo])
def get_data_sources():
    """获取数据源列表"""
    api_logger.info("🔍 请求获取数据源列表")
    sources = []
    for source in source_list:
        sources.append(source.get_source_info())
    api_logger.info(f"✅ 返回 {len(sources)} 个数据源")
    return sources

@app.get("/api/sources/{source_id}/latest/{market}/{data_type}")
def get_latest_price(source_id: str, market: str, data_type: str):
    """获取指定数据源列表的指定类型的最新价格
    
    Args:
        source_id: 数据源ID (如: wen_cai)
        market: 市场代码 (HSI, NASDAQ)
        data_type: 数据类型 (REALTIME, KLINE1M)
    """
    api_logger.info(f"🔍 请求最新价格: {source_id}/{market}/{data_type}")
    
    try:
        # 找到对应的数据源
        source = None
        for s in source_list:
            if s.get_source_info().source_id == source_id:
                source = s
                break
        
        if not source:
            api_logger.warning(f"❌ 数据源 {source_id} 未找到")
            raise HTTPException(status_code=404, detail=f"数据源 {source_id} 未找到")
        
        # 转换市场和数据类型
        try:
            market_symbol = MarketSymbol(market)
            market_data_type = MarketDataType(data_type.lower())
        except ValueError as e:
            api_logger.warning(f"❌ 无效的参数: {market}/{data_type}")
            raise HTTPException(status_code=400, detail=f"无效的参数: {str(e)}")
        
        # 获取最新数据
        latest_data = source.get_latest_data(market_symbol, market_data_type)
        
        api_logger.info(f"✅ 成功获取 {market} 最新价格: {latest_data.price}")
        
        return {
            "source_id": source_id,
            "market": market,
            "data_type": data_type,
            "data": {
                "name": latest_data.name,
                "time": latest_data.time.isoformat(),
                "price": latest_data.price
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"❌ 获取最新价格失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/{source_id}/trading-hours/{market}")
def get_trading_hours(source_id: str, market: str):
    """获取特殊收盘时间表
    
    Args:
        source_id: 数据源ID (如: wen_cai)
        market: 市场代码 (HSI, NASDAQ)
    """
    api_logger.info(f"🔍 请求交易时间表: {source_id}/{market}")
    
    try:
        # 找到对应的数据源
        source = None
        for s in source_list:
            if s.get_source_info().source_id == source_id:
                source = s
                break
        
        if not source:
            api_logger.warning(f"❌ 数据源 {source_id} 未找到")
            raise HTTPException(status_code=404, detail=f"数据源 {source_id} 未找到")
        
        # 转换市场
        try:
            market_symbol = MarketSymbol(market)
        except ValueError:
            api_logger.warning(f"❌ 无效的市场代码: {market}")
            raise HTTPException(status_code=400, detail=f"无效的市场代码: {market}")
        
        # 获取交易时间表
        trading_hours = source.get_trading_hours(market_symbol)
        
        api_logger.info(f"✅ 成功获取 {market} 交易时间表: {len(trading_hours)} 条记录")
        
        return {
            "source_id": source_id,
            "market": market,
            "trading_hours": [
                {
                    "start": th.start.isoformat(),
                    "end": th.end.isoformat(),
                    "text": th.text
                }
                for th in trading_hours
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"❌ 获取交易时间表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sources/{source_id}/market-status/{market}")
def get_market_status(source_id: str, market: str, check_time: str = None):
    """获取指定源的指定市场的状态
    
    Args:
        source_id: 数据源ID (如: wen_cai)
        market: 市场代码 (HSI, NASDAQ)
        check_time: 检查时间 (ISO格式，可选，默认为当前时间)
    """
    time_info = f" 时间: {check_time}" if check_time else " (当前时间)"
    api_logger.info(f"🔍 请求市场状态: {source_id}/{market}{time_info}")
    
    try:
        # 找到对应的数据源
        source = None
        for s in source_list:
            if s.get_source_info().source_id == source_id:
                source = s
                break
        
        if not source:
            api_logger.warning(f"❌ 数据源 {source_id} 未找到")
            raise HTTPException(status_code=404, detail=f"数据源 {source_id} 未找到")
        
        # 转换市场
        try:
            market_symbol = MarketSymbol(market)
        except ValueError:
            api_logger.warning(f"❌ 无效的市场代码: {market}")
            raise HTTPException(status_code=400, detail=f"无效的市场代码: {market}")
        
        # 处理检查时间
        if check_time:
            try:
                check_datetime = datetime.fromisoformat(check_time.replace('Z', '+00:00'))
            except ValueError:
                api_logger.warning(f"❌ 无效的时间格式: {check_time}")
                raise HTTPException(status_code=400, detail=f"无效的时间格式: {check_time}")
        else:
            check_datetime = datetime.now()
        
        # 获取市场状态
        status = source.get_market_status(check_datetime, market_symbol)
        
        status_emoji = "🟢" if status.is_open else "🔴"
        api_logger.info(f"✅ 成功获取 {market} 市场状态: {status_emoji} {status.status_text}")
        
        return {
            "source_id": source_id,
            "market": market,
            "check_time": check_datetime.isoformat(),
            "status": {
                "is_open": status.is_open,
                "status_text": status.status_text,
                "market_time": status.market_time.isoformat() if status.market_time else None,
                "matched_rule": {
                    "date_pattern": status.matched_rule.date_pattern,
                    "start_time": status.matched_rule.start_time,
                    "end_time": status.matched_rule.end_time,
                    "description": status.matched_rule.description
                } if status.matched_rule else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        api_logger.error(f"❌ 获取市场状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("web:app", host="0.0.0.0", port=8000, reload=True)
    api_logger.info("🌟 启动 MarketStockMonitor API 服务成功")
