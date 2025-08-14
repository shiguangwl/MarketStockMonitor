"""统一的日志配置模块."""

import logging
import sys
import os
from datetime import datetime
from typing import Optional
from logging.handlers import TimedRotatingFileHandler


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


def setup_file_handler(
    log_dir: str,
    log_filename: str,
    level: int = logging.INFO,
    when: str = "midnight",
    backup_count: int = 7,
    fmt: Optional[logging.Formatter] = None
) -> logging.Handler:
    """创建一个基于时间滚动的文件日志处理器."""
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, log_filename)
    file_handler = TimedRotatingFileHandler(
        filename=log_path,
        when=when,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    if fmt is None:
        fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(fmt)
    return file_handler


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_dir: Optional[str] = "./logs",
) -> logging.Logger:
    """设置统一的日志器配置，始终开启文件日志.
    
    Args:
        name: 日志器名称
        level: 日志级别，默认为INFO
        log_dir: 日志文件存储目录，默认"./logs"
    
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    log_level = getattr(logging, (level or 'INFO').upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = ColoredFormatter(
        fmt='%(time_formatted)s %(levelname_colored)s %(name_short)-20s | %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件handler 始终开启
    if log_dir:
        file_fmt = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = setup_file_handler(
            log_dir=log_dir,
            log_filename=f"{name}.log",
            level=log_level,
            fmt=file_fmt
        )
        logger.addHandler(file_handler)
    
    logger.propagate = False
    
    return logger


def setup_market_data_logger(log_dir: Optional[str] = "./logs") -> logging.Logger:
    """设置市场数据专用日志器."""
    return setup_logger('market_data', 'INFO', log_dir=log_dir)


def setup_api_logger(log_dir: Optional[str] = "./logs") -> logging.Logger:
    """设置API专用日志器.""" 
    return setup_logger('api', 'INFO', log_dir=log_dir)


def setup_pipeline_logger(log_dir: Optional[str] = "./logs") -> logging.Logger:
    """设置管道处理器专用日志器."""
    return setup_logger('pipeline', 'INFO', log_dir=log_dir)


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


# if __name__ == "__main__":
#     LOG_DIR = "./logs"

#     market_logger = setup_market_data_logger(log_dir=LOG_DIR)
#     api_logger = setup_api_logger(log_dir=LOG_DIR)
#     pipeline_logger = setup_pipeline_logger(log_dir=LOG_DIR)

#     market_logger.info("市场数据日志记录测试")
#     api_logger.warning("API 请求警告")
#     pipeline_logger.error("管道处理错误")
