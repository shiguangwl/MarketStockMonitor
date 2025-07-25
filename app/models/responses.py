"""API响应模型定义."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """错误响应模型."""
    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(None, description="错误代码")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")


class HealthResponse(BaseModel):
    """健康检查响应模型."""
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    uptime: Optional[str] = Field(None, description="运行时间")
    sources_count: int = Field(..., description="数据源数量")


class SourceInfoResponse(BaseModel):
    """数据源信息响应模型."""
    source_id: str = Field(..., description="数据源ID")
    source_name: str = Field(..., description="数据源名称")
    supported_markets: List[str] = Field(..., description="支持的市场列表")


class PriceData(BaseModel):
    """价格数据模型."""
    name: str = Field(..., description="标的名称")
    time: str = Field(..., description="数据时间 (ISO格式)")
    price: float = Field(..., description="价格")
    volume: Optional[int] = Field(None, description="成交量")
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅百分比")


class LatestPriceResponse(BaseModel):
    """最新价格响应模型."""
    source_id: str = Field(..., description="数据源ID")
    market: str = Field(..., description="市场代码")
    data_type: str = Field(..., description="数据类型")
    data: PriceData = Field(..., description="价格数据")


class TradingHour(BaseModel):
    """交易时间模型."""
    start: str = Field(..., description="开始时间 (ISO格式)")
    end: str = Field(..., description="结束时间 (ISO格式)")
    text: str = Field(..., description="时间描述")


class TradingHoursResponse(BaseModel):
    """交易时间表响应模型."""
    source_id: str = Field(..., description="数据源ID")
    market: str = Field(..., description="市场代码")
    trading_hours: List[TradingHour] = Field(..., description="交易时间列表")


class MatchedRule(BaseModel):
    """匹配规则模型."""
    date_pattern: str = Field(..., description="日期模式")
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    description: str = Field(..., description="规则描述")


class MarketStatusInfo(BaseModel):
    """市场状态信息模型."""
    is_open: bool = Field(..., description="是否开盘")
    status_text: str = Field(..., description="状态文本")
    market_time: Optional[str] = Field(None, description="市场时间 (ISO格式)")
    matched_rule: Optional[MatchedRule] = Field(None, description="匹配的规则")


class MarketStatusResponse(BaseModel):
    """市场状态响应模型."""
    source_id: str = Field(..., description="数据源ID")
    market: str = Field(..., description="市场代码")
    check_time: str = Field(..., description="检查时间 (ISO格式)")
    status: MarketStatusInfo = Field(..., description="市场状态信息")


class NextOpeningTimeResponse(BaseModel):
    """下一个开盘时间响应模型."""
    source_id: str = Field(..., description="数据源ID")
    market: str = Field(..., description="市场代码")
    next_opening_time: str = Field(..., description="下一个开盘时间的日期模式")
    start_time: str = Field(..., description="开盘时间")
    end_time: str = Field(..., description="收盘时间")
    description: str = Field(..., description="开盘时间描述")