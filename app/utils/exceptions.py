"""自定义异常类."""


class MarketDataError(Exception):
    """市场数据相关异常基类."""
    pass


class SourceNotFoundError(MarketDataError):
    """数据源未找到异常."""
    pass


class InvalidParameterError(MarketDataError):
    """无效参数异常."""
    pass


class DataFetchError(MarketDataError):
    """数据获取异常."""
    pass