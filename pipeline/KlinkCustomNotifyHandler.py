"""K线合并处理器."""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import requests

from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData
from utils.logger_config import setup_pipeline_logger

logger = setup_pipeline_logger()


class KlinkCustomNotifyHandler(AbstractProcessingHandler):
    """分钟级别数据且当前分钟数为15的整数倍时(即00、15、30、45分钟),自动调用第三方通知服务"""
    
    # 重试延迟时间配置（秒）
    RETRY_DELAYS = [15, 15, 30, 180, 600, 1200, 3600, 7200]  # 15秒, 15秒, 30秒, 3分钟, 10分钟, 20分钟, 1小时, 2小时
    
    def __init__(self, notify_url: str = "http://xxxxx.com/api/draw/openDraw", 
                 secret_key: str = "your_secret_key",
                 request_timeout: int = 15):
        """
        初始化通知处理器
        
        Args:
            notify_url: 通知接口地址
            secret_key: 签名密钥
            request_timeout: 请求超时时间(秒)
        """
        self.notify_url = notify_url
        self.secret_key = secret_key
        self.request_timeout = request_timeout
        self.max_retries = len(self.RETRY_DELAYS)
        
        # 配置HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'MarketStockMonitor/1.0',
            'Accept': 'application/json'
        })
        
        logger.info(f"🔧 初始化K线通知处理器 - URL: {notify_url}, 超时: {request_timeout}秒, 最大重试: {self.max_retries}次")

    def process(self, data: MarketData) -> None:
        """处理数据"""
        try:
            # 检查是否为分钟级别数据
            if not self._is_minute_data(data):
                logger.debug(f"⏭️ 数据不是分钟级别，跳过处理: {data}")
                return
            
            # 检查是否为15分钟整数倍
            if not self._is_quarter_minute(data):
                logger.debug(f"⏭️ 当前分钟不是15的整数倍，跳过通知: {data.timestamp}")
                return
            
            logger.info(f"🎯 开始处理15分钟整数倍数据通知: {data}")
            self.notifyRemoteApp(data)
            
        except Exception as e:
            logger.error(f"❌ 处理数据时发生错误: {e}", exc_info=True)

    def _is_minute_data(self, data: MarketData) -> bool:
        """检查是否为分钟级别数据"""
        # 这里可以根据实际的数据结构来判断
        # 假设通过时间戳的秒数来判断，分钟级别数据秒数应该为0
        if hasattr(data, 'timestamp') and isinstance(data.timestamp, datetime):
            return data.timestamp.second == 0
        return True  # 默认认为是分钟数据

    def _is_quarter_minute(self, data: MarketData) -> bool:
        """检查是否为15分钟的整数倍(00、15、30、45分钟)"""
        if hasattr(data, 'timestamp') and isinstance(data.timestamp, datetime):
            minute = data.timestamp.minute
            return minute % 15 == 0
        return False

    def _generate_sign(self, params: Dict[str, str]) -> str:
        """
        生成签名
        MD5加密 通过 key 按ASCII码从小到大排序 value1&value2...+&key
        
        Args:
            params: 待签名的参数字典
            
        Returns:
            str: MD5签名结果
            
        Raises:
            ValueError: 参数为空或签名生成失败
        """
        if not params:
            raise ValueError("签名参数不能为空")
            
        if not self.secret_key:
            raise ValueError("签名密钥不能为空")
        
        try:
            # 按ASCII码排序参数键
            sorted_keys = sorted(params.keys())
            
            # 拼接参数值
            param_values = [str(params[key]) for key in sorted_keys if params[key] is not None]
            sign_string = "&".join(param_values) + "&" + self.secret_key
            
            # MD5加密
            sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest().upper()
            logger.debug(f"🔐 签名参数: {sorted_keys}, 签名结果: {sign}")
            
            return sign
        except Exception as e:
            logger.error(f"❌ 生成签名时发生错误: {e}")
            raise ValueError(f"签名生成失败: {e}")

    def _prepare_notify_data(self, data: MarketData) -> Dict[str, str]:
        """
        准备通知数据
        
        Args:
            data: 市场数据对象
            
        Returns:
            Dict[str, str]: 包含签名的通知数据
            
        Raises:
            ValueError: 数据准备失败
        """
        if not data:
            raise ValueError("市场数据不能为空")
            
        try:
            # 准备基础参数
            params = {
                "type": data.source or "unknown",
                "drawTime": data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "drawIndex": str(data.price)
            }
            
            # 验证必要参数
            for key, value in params.items():
                if not value or value == "0":
                    logger.warning(f"⚠️ 参数 {key} 的值可能无效: {value}")
            
            # 生成签名
            params["sign"] = self._generate_sign(params)
            
            return params
        except Exception as e:
            logger.error(f"❌ 准备通知数据时发生错误: {e}")
            raise ValueError(f"数据准备失败: {e}")

    def _send_notification_request(self, notify_data: Dict[str, str]) -> Dict[str, Any]:
        """
        发送通知请求
        
        Args:
            notify_data: 通知数据
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            requests.RequestException: 请求异常
            ValueError: 响应解析异常
        """
        response = self.session.post(
            self.notify_url,
            json=notify_data,
            timeout=self.request_timeout
        )
        
        # 检查HTTP状态码
        response.raise_for_status()
        
        # 解析JSON响应
        try:
            result = response.json()
        except ValueError as e:
            raise ValueError(f"响应JSON解析失败: {e}")
        
        return result

    def _is_success_response(self, result: Dict[str, Any]) -> bool:
        """
        检查响应是否成功
        
        Args:
            result: API响应数据
            
        Returns:
            bool: 是否成功
        """
        return result.get('code') == 200

    def _format_retry_time(self, seconds: int) -> str:
        """
        格式化重试等待时间显示
        
        Args:
            seconds: 等待秒数
            
        Returns:
            str: 格式化的时间字符串
        """
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        else:
            return f"{seconds // 3600}小时"

    def notifyRemoteApp(self, data: MarketData) -> None:
        """
        通知远程应用
        按照指定的重试策略进行重试：15秒, 15秒, 30秒, 3分钟, 10分钟, 20分钟, 1小时, 2小时
        
        Args:
            data: 市场数据
            
        Raises:
            Exception: 所有重试都失败后抛出异常
        """
        if not data:
            raise ValueError("市场数据不能为空")
            
        last_error = None
        
        for attempt in range(self.max_retries + 1):  # 总共9次尝试（1次初始 + 8次重试）
            try:
                # 准备请求数据
                notify_data = self._prepare_notify_data(data)
                
                logger.info(f"📡 第{attempt + 1}次尝试通知远程应用: {self.notify_url}")
                logger.debug(f"📤 通知数据: {notify_data}")
                
                # 发送请求
                result = self._send_notification_request(notify_data)
                logger.debug(f"📥 远程应用响应: {result}")
                
                # 检查业务状态码
                if self._is_success_response(result):
                    success_msg = f"✅ 通知远程应用成功: {result.get('msg', '成功')}"
                    if attempt > 0:
                        success_msg += f" (重试{attempt}次后成功)"
                    logger.info(success_msg)
                    return
                else:
                    error_msg = f"⚠️ 远程应用返回错误: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                    logger.warning(error_msg)
                    last_error = Exception(error_msg)
                    
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(f"⏰ 第{attempt + 1}次通知超时({self.request_timeout}秒): {e}")
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                logger.warning(f"🔌 第{attempt + 1}次通知连接错误: {e}")
                
            except requests.exceptions.HTTPError as e:
                last_error = e
                logger.warning(f"🌐 第{attempt + 1}次通知HTTP错误: {e}")
                
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"📡 第{attempt + 1}次通知请求异常: {e}")
                
            except ValueError as e:
                last_error = e
                logger.error(f"❌ 第{attempt + 1}次通知数据错误: {e}")
                
            except Exception as e:
                last_error = e
                logger.error(f"❌ 第{attempt + 1}次通知发生未知错误: {e}", exc_info=True)
            
            # 如果还有重试机会，等待后重试
            if attempt < self.max_retries:
                wait_time = self.RETRY_DELAYS[attempt]
                wait_time_str = self._format_retry_time(wait_time)
                logger.info(f"⏳ 等待 {wait_time_str} 后进行第{attempt + 2}次重试...")
                time.sleep(wait_time)
        
        # 所有重试都失败了
        total_attempts = self.max_retries + 1
        error_msg = f"❌ 通知远程应用失败，已尝试{total_attempts}次"
        if last_error:
            error_msg += f"，最后一次错误: {last_error}"
        
        logger.error(error_msg)
        raise Exception(error_msg)

    def close(self) -> None:
        """关闭HTTP会话，释放资源"""
        if hasattr(self, 'session') and self.session:
            self.session.close()
            logger.debug("🔒 HTTP会话已关闭")

    def __del__(self):
        """析构函数，确保资源被正确释放"""
        try:
            self.close()
        except Exception:
            pass  # 忽略析构函数中的异常

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()