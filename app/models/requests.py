"""API请求模型定义."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class MarketStatusRequest(BaseModel):
    """市场状态查询请求模型."""
    check_time: Optional[str] = Field(None, description="检查时间 (ISO格式，可选，默认为当前时间)")
    
    @validator('check_time')
    def validate_check_time(cls, v):
        """验证时间格式."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError("无效的时间格式，请使用ISO格式，如: 2024-01-15T09:00:00")
        return v