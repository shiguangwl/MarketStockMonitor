"""SSE数据广播管理器 - 优化版本."""

import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from models.market_data import MarketData, MarketSymbol, MarketDataType
from utils.logger_config import setup_api_logger

api_logger = setup_api_logger()


@dataclass
class SSEFilter:
    """SSE数据过滤器."""
    source_ids: Optional[Set[str]] = None  # 数据源过滤，None表示所有
    markets: Optional[Set[str]] = None  # 市场过滤，None表示所有（使用字符串）
    data_types: Optional[Set[str]] = None  # 数据类型过滤，None表示所有（使用字符串）
    
    def matches(self, data: MarketData) -> bool:
        """检查数据是否匹配过滤条件."""
        # 检查数据源
        if self.source_ids and data.source not in self.source_ids:
            return False
        
        # 检查市场（转换为字符串比较）
        if self.markets and data.symbol.value not in self.markets:
            return False
        
        # 检查数据类型（转换为字符串比较）
        if self.data_types and data.type.value not in self.data_types:
            return False
        
        return True


class SSEConnection:
    """SSE连接管理."""
    
    def __init__(self, connection_id: str, filter_config: SSEFilter, queue_size: int = 100):
        self.connection_id = connection_id
        self.filter_config = filter_config
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.connected = True
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.data_count = 0
        
    async def send_data(self, data: Dict[str, Any]) -> bool:
        """发送数据到连接队列."""
        if not self.connected:
            return False
        
        try:
            # 非阻塞发送，如果队列满了就丢弃旧数据
            if self.queue.full():
                try:
                    self.queue.get_nowait()  # 移除最旧的数据
                except asyncio.QueueEmpty:
                    pass
            
            await self.queue.put(data)
            self.last_activity = datetime.now()
            self.data_count += 1
            return True
        except Exception as e:
            api_logger.error(f"❌ SSE连接 {self.connection_id} 发送数据失败: {str(e)}")
            return False
    
    async def get_data(self) -> Optional[Dict[str, Any]]:
        """从队列获取数据 - 支持长时间等待."""
        try:
            # 等待更长时间，支持实时推送
            return await asyncio.wait_for(self.queue.get(), timeout=30.0)
        except asyncio.TimeoutError:
            return None
        except Exception:
            return None
    
    def disconnect(self):
        """断开连接."""
        self.connected = False


class SSEManager:
    """SSE数据广播管理器."""
    
    def __init__(self):
        self.connections: Dict[str, SSEConnection] = {}
        self.connection_counter = 0
        self._cleanup_task = None
        self._initialized = False
    
    def _ensure_cleanup_task(self):
        """确保清理任务已启动."""
        if not self._initialized:
            try:
                # 检查是否有运行的事件循环
                loop = asyncio.get_running_loop()
                if self._cleanup_task is None or self._cleanup_task.done():
                    self._cleanup_task = asyncio.create_task(self._cleanup_connections())
                self._initialized = True
                api_logger.info("🔧 SSE管理器清理任务已启动")
            except RuntimeError:
                # 没有运行的事件循环，稍后再启动
                pass
    
    async def _cleanup_connections(self):
        """定期清理断开的连接."""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒清理一次
                
                disconnected = []
                for conn_id, conn in self.connections.items():
                    if not conn.connected:
                        disconnected.append(conn_id)
                    elif (datetime.now() - conn.last_activity).seconds > 300:  # 5分钟无活动
                        api_logger.warning(f"⚠️ SSE连接 {conn_id} 超时，自动断开")
                        conn.disconnect()
                        disconnected.append(conn_id)
                
                for conn_id in disconnected:
                    self.connections.pop(conn_id, None)
                    api_logger.info(f"🗑️ 清理SSE连接: {conn_id}")
                
                if disconnected:
                    api_logger.info(f"📊 当前活跃SSE连接数: {len(self.connections)}")
                    
            except Exception as e:
                api_logger.error(f"❌ SSE连接清理异常: {str(e)}")
    
    def create_connection(self, filter_config: SSEFilter) -> str:
        """创建新的SSE连接."""
        self._ensure_cleanup_task()
        
        self.connection_counter += 1
        connection_id = f"sse_{self.connection_counter}_{int(datetime.now().timestamp())}"
        
        connection = SSEConnection(connection_id, filter_config)
        self.connections[connection_id] = connection
        
        api_logger.info(f"🔗 创建SSE连接: {connection_id}")
        api_logger.info(f"📊 当前SSE连接数: {len(self.connections)}")
        
        return connection_id
    
    def get_connection(self, connection_id: str) -> Optional[SSEConnection]:
        """获取SSE连接."""
        return self.connections.get(connection_id)
    
    def disconnect_connection(self, connection_id: str):
        """断开指定连接."""
        if connection_id in self.connections:
            self.connections[connection_id].disconnect()
            api_logger.info(f"❌ 断开SSE连接: {connection_id}")
    
    async def broadcast_data(self, data: MarketData):
        """广播数据到所有匹配的连接."""
        if not self.connections:
            return
        
        # 构造广播数据
        broadcast_data = {
            "event": "market_data",
            "source": data.source,
            "symbol": data.symbol.value,
            "type": data.type.value,
            "price": data.price,
            "timestamp": data.timestamp.isoformat(),
            "volume": data.volume,
            "open_price": data.open_price,
            "high_price": data.high_price,
            "low_price": data.low_price,
            "close_price": data.close_price,
            "change": data.change,
            "change_percent": data.change_percent
        }
        
        # 发送到匹配的连接
        sent_count = 0
        for conn_id, connection in self.connections.items():
            if connection.connected:
                if connection.filter_config.matches(data):
                    success = await connection.send_data(broadcast_data)
                    if success:
                        sent_count += 1
                    else:
                        api_logger.error(f"❌ 数据发送失败到连接 {conn_id}")
        
        if sent_count > 0:
            api_logger.debug(f"📡 广播数据到 {sent_count} 个连接: {data.symbol.value} - {data.price}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取SSE管理器统计信息."""
        active_connections = sum(1 for conn in self.connections.values() if conn.connected)
        total_data_sent = sum(conn.data_count for conn in self.connections.values())
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "total_data_sent": total_data_sent,
            "connections_detail": [
                {
                    "id": conn.connection_id,
                    "connected": conn.connected,
                    "created_at": conn.created_at.isoformat(),
                    "last_activity": conn.last_activity.isoformat(),
                    "data_count": conn.data_count,
                    "filter": {
                        "source_ids": list(conn.filter_config.source_ids) if conn.filter_config.source_ids else None,
                        "markets": list(conn.filter_config.markets) if conn.filter_config.markets else None,
                        "data_types": list(conn.filter_config.data_types) if conn.filter_config.data_types else None
                    }
                }
                for conn in self.connections.values()
            ]
        }


# 全局SSE管理器实例
_sse_manager = None


def get_sse_manager() -> SSEManager:
    """获取SSE管理器实例."""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
    return _sse_manager