"""数据源控制器."""

import json
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.models.responses import SourceInfoResponse
from app.services import SourceService, MarketService
from app.services.sse_manager import get_sse_manager, SSEFilter
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()

sources_router = APIRouter(prefix="/sources", tags=["数据源"])


def get_source_service() -> SourceService:
    """依赖注入：获取数据源服务."""
    return None  # 将通过dependency_overrides设置


def get_market_service() -> MarketService:
    """依赖注入：获取市场数据服务."""
    return None  # 将通过dependency_overrides设置


@sources_router.get(
    "/",
    response_model=List[SourceInfoResponse],
    summary="获取数据源列表",
    description="获取系统中所有可用的数据源列表及其支持的市场"
)
def get_data_sources(source_service: SourceService = Depends(get_source_service)):
    """获取数据源列表."""
    api_logger.info("🔍 请求获取数据源列表")
    
    sources = source_service.get_all_sources()
    api_logger.info(f"✅ 返回 {len(sources)} 个数据源")
    
    return sources


@sources_router.get(
    "/stream",
    summary="SSE实时数据流",
    description="""
    通过Server-Sent Events (SSE) 接收实时市场数据推送
    
    参数说明:
    - sources: 数据源列表，逗号分隔，为空则监听所有数据源
    - markets: 市场列表，逗号分隔，为空则监听所有市场  
    - data_types: 数据类型列表，逗号分隔，为空则监听所有数据类型
    
    示例:
    - /api/sources/stream - 接收所有数据
    - /api/sources/stream?sources=wen_cai&markets=HSI,NASDAQ - 监听问财的HSI和NASDAQ数据
    - /api/sources/stream?data_types=realtime - 只接收实时数据
    
    数据推送模式: 实时推送，收到数据立即发送，无延迟
    """
)
async def sse_data_stream(
    sources: Optional[str] = Query(None, description="数据源列表，逗号分隔，为空则监听所有"),
    markets: Optional[str] = Query(None, description="市场列表，逗号分隔，为空则监听所有"),
    data_types: Optional[str] = Query(None, description="数据类型列表，逗号分隔，为空则监听所有")
):
    """统一的SSE数据流端点."""
    
    # 解析参数
    source_list = [s.strip() for s in sources.split(',')] if sources else None
    market_list = [m.strip() for m in markets.split(',')] if markets else None
    data_type_list = [dt.strip() for dt in data_types.split(',')] if data_types else None
    
    # 创建过滤器
    filter_config = SSEFilter(
        source_ids=set(source_list) if source_list else None,
        markets=set(market_list) if market_list else None,
        data_types=set(data_type_list) if data_type_list else None
    )
    
    # 记录连接信息
    filter_desc = []
    if source_list:
        filter_desc.append(f"数据源: {','.join(source_list)}")
    if market_list:
        filter_desc.append(f"市场: {','.join(market_list)}")
    if data_type_list:
        filter_desc.append(f"数据类型: {','.join(data_type_list)}")
    
    if not filter_desc:
        filter_desc.append("全部数据")
    
    api_logger.info(f"🔄 开始SSE数据流: {' | '.join(filter_desc)}")
    
    try:
        # 获取SSE管理器并创建连接
        sse_manager = get_sse_manager()
        
        async def event_generator():
            """SSE事件生成器."""
            connection_id = None
            try:
                # 创建连接
                connection_id = sse_manager.create_connection(filter_config)
                
                # 发送连接确认数据
                connection_data = {
                    "message": "已连接到数据流",
                    "connection_id": connection_id,
                    "filter": {
                        "mode": "realtime"
                    }
                }
                
                # 添加过滤条件
                if source_list:
                    connection_data["filter"]["sources"] = source_list
                if market_list:
                    connection_data["filter"]["markets"] = market_list
                if data_type_list:
                    connection_data["filter"]["data_types"] = data_type_list
                
                # 发送连接确认
                yield f"event: connected\n"
                yield f"data: {json.dumps(connection_data, ensure_ascii=False)}\n\n"
                
                # 获取连接对象
                connection = sse_manager.get_connection(connection_id)
                if not connection:
                    raise Exception("无法获取SSE连接")
                
                # 持续发送数据
                while connection.connected:
                    try:
                        # 从连接队列获取数据 (阻塞等待)
                        data = await connection.get_data()
                        
                        if data:
                            # 立即发送数据事件
                            yield f"event: {data['event']}\n"
                            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                        else:
                            # 如果没有数据，发送保活心跳 (每30秒)
                            heartbeat = {
                                "event": "heartbeat",
                                "connection_id": connection_id,
                                "timestamp": datetime.now().isoformat()
                            }
                            yield f"event: heartbeat\n"
                            yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(30)
                        
                    except Exception as e:
                        # 发送错误消息
                        error_data = {
                            "message": str(e),
                            "connection_id": connection_id,
                            "timestamp": datetime.now().isoformat()
                        }
                        yield f"event: error\n"
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                        api_logger.error(f"❌ SSE数据流异常: {str(e)}")
                        break
                    
            except Exception as e:
                api_logger.error(f"❌ SSE流异常: {str(e)}")
                yield f"event: error\n"
                yield f'data: {{"message": "数据流异常: {str(e)}"}}\n\n'
            finally:
                # 清理连接
                if connection_id:
                    sse_manager.disconnect_connection(connection_id)
                    api_logger.info(f"🔌 SSE连接已断开: {connection_id}")
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        api_logger.error(f"❌ 创建SSE流失败: {str(e)}")
        raise


@sources_router.get(
    "/stream/stats",
    summary="SSE连接统计",
    description="获取当前SSE连接的统计信息"
)
async def get_sse_stats():
    """获取SSE连接统计."""
    try:
        sse_manager = get_sse_manager()
        stats = await sse_manager.get_stats()
        api_logger.info("📊 获取SSE统计信息")
        return {
            "status": "success",
            "stats": stats,
            "timestamp": "2025-01-25T09:59:50.945Z"
        }
    except Exception as e:
        api_logger.error(f"❌ 获取SSE统计失败: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": "2025-01-25T09:59:50.945Z"
        }