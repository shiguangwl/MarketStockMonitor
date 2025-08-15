"""统一的日志配置模块，保持API兼容性，按级别和标签分离文件。"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional
from logging.handlers import TimedRotatingFileHandler

# 全局标志，确保日志系统只配置一次
_is_logging_configured = False


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器，用于控制台输出。"""

    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\03d[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname_colored = f"{level_color}{record.levelname:<8}{self.COLORS['RESET']}"
        record.time_formatted = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]

        if len(record.name) > 20:
            record.name_short = '...' + record.name[-17:]
        else:
            record.name_short = record.name

        return super().format(record)


class LevelFilter(logging.Filter):
    """日志级别过滤器，只允许指定级别的日志通过。"""
    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


def _setup_global_logging(
    log_dir: str = "./logs",
    tag: Optional[str] = None
):
    """
    (内部函数) 配置全局根日志器，按级别分离文件。
    此函数由任何 setup_* 函数在首次调用时触发，且只执行一次。
    """
    global _is_logging_configured
    if _is_logging_configured:
        return

    root_logger = logging.getLogger()
    # 设置最低级别，以捕获所有日志，由handlers进行具体过滤
    root_logger.setLevel(logging.DEBUG)

    # 1. 配置控制台处理器 (使用原始的 ColoredFormatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # 控制台通常不需要DEBUG信息
    console_formatter = ColoredFormatter(
        fmt='%(time_formatted)s %(levelname_colored)s %(name_short)-20s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. 配置文件处理器 (按级别分离)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        # 文件格式化器 (使用原始的普通 Formatter)
        file_fmt = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件名前缀
        file_prefix = f"{tag}_" if tag else ""

        # INFO 日志
        info_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, f"{file_prefix}info.log"),
            when="midnight", backupCount=7, encoding='utf-8'
        )
        info_handler.setLevel(logging.INFO)
        info_handler.addFilter(LevelFilter(logging.INFO))
        info_handler.setFormatter(file_fmt)
        root_logger.addHandler(info_handler)

        # WARNING 日志
        warning_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, f"{file_prefix}warning.log"),
            when="midnight", backupCount=7, encoding='utf-8'
        )
        warning_handler.setLevel(logging.WARNING)
        warning_handler.addFilter(LevelFilter(logging.WARNING))
        warning_handler.setFormatter(file_fmt)
        root_logger.addHandler(warning_handler)

        # ERROR 日志 (处理 ERROR 和 CRITICAL)
        error_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, f"{file_prefix}error.log"),
            when="midnight", backupCount=7, encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_fmt)
        root_logger.addHandler(error_handler)

    # 3. 配置第三方库日志级别
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.WARNING)

    _is_logging_configured = True


def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_dir: Optional[str] = "./logs",
    tag: Optional[str] = None
) -> logging.Logger:
    """
    设置或获取一个日志器。

    首次调用时，会初始化全局日志系统，按级别（INFO, WARNING, ERROR）
    和标签（tag）创建日志文件。后续调用仅获取日志器实例并设置其级别。

    Args:
        name: 日志器名称。
        level: 该日志器的日志级别 (e.g., 'INFO', 'DEBUG')。
        log_dir: 日志文件存储目录 (仅在首次配置时生效)。
        tag: 日志文件名前缀 (e.g., 'my_app') (仅在首次配置时生效)。

    Returns:
        配置好的日志器实例。
    """
    # 确保全局日志系统已配置
    _setup_global_logging(log_dir, tag)

    logger = logging.getLogger(name)
    
    # 设置特定logger的级别，允许更精细的控制
    log_level = getattr(logging, (level or 'INFO').upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 不再为每个logger单独添加handler，它们会将日志传播到root logger
    logger.propagate = True # 确保日志能传播到root
    
    return logger


# --- API 兼容层 ---

def setup_market_data_logger(log_dir: Optional[str] = "./logs", tag: Optional[str] = None) -> logging.Logger:
    """设置市场数据专用日志器"""
    return setup_logger('MarketData', 'INFO', log_dir=log_dir, tag=tag)


def setup_api_logger(log_dir: Optional[str] = "./logs", tag: Optional[str] = None) -> logging.Logger:
    """设置API专用日志器 """
    return setup_logger('API', 'INFO', log_dir=log_dir, tag=tag)


def setup_pipeline_logger(log_dir: Optional[str] = "./logs", tag: Optional[str] = None) -> logging.Logger:
    """设置管道处理器专用日志器"""
    return setup_logger('Pipeline', 'INFO', log_dir=log_dir, tag=tag)


# # --- 示例用法 ---

# if __name__ == "__main__":
#     LOG_DIR = "./logs_tagged"
#     LOG_TAG = "my_app" # 定义一个日志标签

#     print(f"日志将保存在目录: {os.path.abspath(LOG_DIR)}")
#     print(f"日志文件将使用标签: '{LOG_TAG}'")
#     print("--- 开始日志配置 (将在第一次获取logger时自动触发) ---")

#     # 使用与原来完全相同的API，但增加了tag参数
#     # 全局配置只会在第一次调用（这里是market_logger）时执行一次
#     market_logger = setup_market_data_logger(log_dir=LOG_DIR, tag=LOG_TAG)
#     api_logger = setup_api_logger(log_dir=LOG_DIR, tag=LOG_TAG)
#     pipeline_logger = setup_pipeline_logger(log_dir=LOG_DIR, tag=LOG_TAG)
    
#     # 也可以使用通用的setup_logger，并设置不同的级别
#     debug_logger = setup_logger("debug_tool", "DEBUG", log_dir=LOG_DIR, tag=LOG_TAG)

#     print("--- 日志配置完成 ---")

#     print("\n--- 开始记录日志 ---")
#     market_logger.info("市场数据日志记录测试")
#     api_logger.warning("API 请求警告")
#     pipeline_logger.error("管道处理错误")
#     pipeline_logger.critical("管道发生致命错误，无法恢复")
    
#     # 这条DEBUG信息会显示在控制台，因为根handler级别是INFO，但logger本身是DEBUG
#     # 它不会写入任何文件，因为没有为DEBUG级别配置file handler
#     debug_logger.debug("这是一个详细的调试信息，用于开发。")
#     debug_logger.info("调试工具也可能产生普通信息。")

#     print("\n--- 日志记录完成 ---")
#     print(f"请检查控制台输出以及 '{LOG_DIR}' 目录下的文件:")
#     print(f"- {os.path.join(LOG_DIR, f'{LOG_TAG}_info.log')}")
#     print(f"- {os.path.join(LOG_DIR, f'{LOG_TAG}_warning.log')}")
#     print(f"- {os.path.join(LOG_DIR, f'{LOG_TAG}_error.log')}")

