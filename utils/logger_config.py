"""统一的日志配置模块."""

import logging
import sys
from datetime import datetime
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器."""
    
    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def format(self, record):
        # 添加颜色
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname_colored = f"{level_color}{record.levelname:<8}{self.COLORS['RESET']}"
        
        # 格式化时间
        record.time_formatted = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # 截断模块名
        if len(record.name) > 20:
            record.name_short = '...' + record.name[-17:]
        else:
            record.name_short = record.name
            
        return super().format(record)


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """设置统一的日志器配置.
    
    Args:
        name: 日志器名称
        level: 日志级别，默认为INFO
        
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = getattr(logging, (level or 'INFO').upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 设置格式
    formatter = ColoredFormatter(
        fmt='%(time_formatted)s %(levelname_colored)s %(name_short)-20s | %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    # 防止向上传播
    logger.propagate = False
    
    return logger


def setup_market_data_logger() -> logging.Logger:
    """设置市场数据专用日志器."""
    logger = setup_logger('market_data', 'INFO')
    return logger


def setup_api_logger() -> logging.Logger:
    """设置API专用日志器.""" 
    logger = setup_logger('api', 'INFO')
    return logger


def setup_pipeline_logger() -> logging.Logger:
    """设置管道处理器专用日志器."""
    logger = setup_logger('pipeline', 'INFO')
    return logger


# 全局日志器配置
def configure_global_logging():
    """配置全局日志."""
    # 设置根日志器级别
    logging.getLogger().setLevel(logging.WARNING)
    
    # 设置第三方库日志级别
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.WARNING)


# 立即配置全局日志
configure_global_logging() 