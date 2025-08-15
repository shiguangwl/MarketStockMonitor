"""远程通知工具模块."""

import hashlib
import time
from typing import Any, Dict, Optional
import requests
from models.market_data import MarketData
from utils.logger_config import setup_pipeline_logger

logger = setup_pipeline_logger()


class RemoteNotifier:
    """远程通知发送器，负责处理HTTP请求、签名生成和数据格式化."""

    def __init__(
        self,
        notify_url: str,
        secret_key: str,
        request_timeout: int = 15,
    ):
        """
        初始化远程通知器

        Args:
            notify_url: 通知接口地址
            secret_key: 签名密钥
            request_timeout: 请求超时时间(秒)
        """
        self.notify_url = notify_url
        self.secret_key = secret_key
        self.request_timeout = request_timeout

        # 配置HTTP会话
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "MarketStockMonitor/1.0",
            "Accept": "application/json",
        })

        logger.info(f"🔧 初始化远程通知器 - URL: {notify_url}, 超时: {request_timeout}秒")

    def _generate_sign(self, params: Dict[str, str]) -> str:
        """生成MD5签名"""
        if not params:
            raise ValueError("签名参数不能为空")
        if not self.secret_key:
            raise ValueError("签名密钥不能为空")
        
        try:
            sorted_keys = sorted(params.keys())
            param_values = [str(params[key]) for key in sorted_keys if params[key] is not None]
            sign_string = "&".join(param_values) + "&" + self.secret_key
            sign = hashlib.md5(sign_string.encode("utf-8")).hexdigest().upper()
            logger.debug(f"🔐 签名字符串: '{sign_string}', 签名结果: {sign}")
            return sign
        except Exception as e:
            logger.error(f"❌ 生成签名时发生错误: {e}")
            raise ValueError(f"签名生成失败: {e}")

    def _prepare_notify_data(self, data: MarketData) -> Dict[str, str]:
        """准备通知数据"""
        try:
            params = {
                "type": data.source or "unknown",
                "drawTime": data.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "drawIndex": str(data.price),
            }
            params["sign"] = self._generate_sign(params)
            return params
        except Exception as e:
            logger.error(f"❌ 准备通知数据时发生错误: {e}")
            raise ValueError(f"数据准备失败: {e}")

    def _send_notification_request(self, notify_data: Dict[str, str]) -> Dict[str, Any]:
        """发送通知请求"""
        response = self.session.post(
            self.notify_url, json=notify_data, timeout=self.request_timeout
        )
        response.raise_for_status()
        try:
            return response.json()
        except ValueError as e:
            raise ValueError(f"响应JSON解析失败: {e}, 响应文本: {response.text}")

    def _is_success_response(self, result: Dict[str, Any]) -> bool:
        """检查响应是否成功"""
        return result.get("code") == 200

    def send_notification(self, data: MarketData) -> bool:
        """
        发送远程通知

        Args:
            data: 市场数据

        Returns:
            bool: True表示通知成功，False表示失败
        """
        try:
            notify_data = self._prepare_notify_data(data)
            logger.debug(f"📤 准备发送的通知数据: {notify_data}")
            
            result = self._send_notification_request(notify_data)
            logger.debug(f"📥 收到远程应用响应: {result}")

            if self._is_success_response(result):
                return True
            else:
                error_msg = f"⚠️ 远程应用返回业务错误: code={result.get('code')}, msg={result.get('msg', '未知错误')}"
                logger.warning(error_msg)
                return False

        except requests.exceptions.Timeout as e:
            logger.warning(f"⏰ 通知超时({self.request_timeout}秒): {e}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 通知连接错误: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"🌐 通知HTTP或请求错误: {e}")
        except ValueError as e:
            logger.error(f"❌ 通知数据准备或响应解析错误: {e}")
        except Exception as e:
            logger.error(f"❌ 通知时发生未知错误: {e}", exc_info=True)
        
        return False

    def close(self) -> None:
        """关闭HTTP会话"""
        if hasattr(self, "session") and self.session:
            self.session.close()
            logger.debug("🔒 HTTP会话已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
