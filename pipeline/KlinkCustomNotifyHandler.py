"""K线合并处理器."""

import time
import threading
from datetime import datetime
from typing import Any, Dict
from queue import Queue, Empty
from models.market_data import MarketDataType
from markt.IProcessingHandler import AbstractProcessingHandler
from models.market_data import MarketData
from utils.logger_config import setup_logger, setup_pipeline_logger
from utils.remote_notify import RemoteNotifier

logger = setup_logger("NotifyHandler")

class KlinkCustomNotifyHandler(AbstractProcessingHandler):
    """分钟K线数据在特定时间点触发远程通知，采用后台队列和循环重试机制."""

    def __init__(
        self,
        notify_url: str = "http://lottery-api:8087/api/draw/openDraw",
        secret_key: str = "InrKOvmSZjsCxkwLxT0rTg==",
        request_timeout: int = 15,
        queue_max_size: int = 1000,
        notify_interval_seconds: int = 10,
    ):
        """
        初始化通知处理器

        Args:
            notify_url: 通知接口地址
            secret_key: 签名密钥
            request_timeout: 请求超时时间(秒)
            queue_max_size: 队列最大大小
            notify_interval_seconds: 通知失败后的重试间隔时间(秒)
        """
        self.queue_max_size = queue_max_size
        self.notify_interval_seconds = notify_interval_seconds

        # 初始化数据队列
        self.data_queue = Queue(maxsize=queue_max_size)
        self._running = False
        self._worker_thread = None

        # 初始化远程通知器
        self.remote_notifier = RemoteNotifier(
            notify_url=notify_url,
            secret_key=secret_key,
            request_timeout=request_timeout
        )

        # 启动后台处理线程
        self._start_worker_thread()

        logger.info(
            f"🔧 初始化K线通知处理器 - 队列大小: {queue_max_size}, 重试间隔: {notify_interval_seconds}秒"
        )

    def _start_worker_thread(self) -> None:
        """启动后台工作线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop, daemon=True
            )
            self._worker_thread.start()
            logger.info("🚀 启动K线通知后台处理线程")

    def _worker_loop(self) -> None:
        """后台工作线程循环，从队列获取数据并持续重试直到成功"""
        logger.info("🔄 K线通知后台处理线程开始运行")

        while self._running:
            try:
                # 阻塞式获取数据，设置超时以响应关闭信号
                data_to_process = self.data_queue.get(timeout=1.0)

                if data_to_process is None:  # 停止信号
                    break

                logger.info(f"📥 从队列中获取待处理数据: {data_to_process}")

                # 循环重试，直到通知成功或处理器关闭
                attempt_count = 0
                while self._running:
                    attempt_count += 1
                    logger.info(f"📡 第 {attempt_count} 次尝试通知: {data_to_process.symbol.value}")

                    success = self.remote_notifier.send_notification(data_to_process)

                    if success:
                        logger.info(f"✅ 通知成功")
                        self.data_queue.task_done()
                        break  # 成功，跳出重试循环，处理下一个队列项目
                    else:
                        logger.warning(
                            f"⏳ 通知失败，将在 {self.notify_interval_seconds} 秒后重试..."
                        )
                        # 等待指定间隔后重试，除非处理器被关闭
                        for _ in range(self.notify_interval_seconds):
                            if not self._running:
                                break
                            time.sleep(1)

            except Empty:
                # 队列为空，是正常情况，继续等待
                continue
            except Exception as e:
                # 捕获意外错误，防止线程崩溃
                if self._running:
                    logger.error(f"❌ 后台处理线程发生意外错误: {e}", exc_info=True)
                continue

        logger.info("🛑 K线通知后台处理线程已停止")

    def process(self, data: MarketData) -> None:
        """
        处理数据 - 过滤后快速入队，立即返回。
        如果队列已满，则丢弃最旧的数据，为新数据腾出空间。
        """
        try:
            # 检查是否为分钟级别数据
            if not self._is_minute_data(data):
                return

            # 检查是否为15分钟整数倍或特殊时间
            if not self._is_quarter_minute(data):
                return

            # 如果队列已满，丢弃最旧的元素
            if self.data_queue.full():
                try:
                    dropped_item = self.data_queue.get_nowait()
                    logger.warning(
                        f"⚠️ 通知队列已满({self.queue_max_size})，丢弃最旧数据: {dropped_item}"
                    )
                    self.data_queue.task_done()
                except Empty:
                    pass

            # 将数据放入队列
            self.data_queue.put_nowait(data)
            logger.info(
                f"📤 数据已入队: {data.symbol.value} - {data.price}, 当前队列大小: {self.data_queue.qsize()}"
            )

        except Exception as e:
            logger.error(f"❌ 数据入队失败: {e}", exc_info=True)

    def _is_minute_data(self, data: MarketData) -> bool:
        """检查是否为分钟级别数据"""
        return data.type == MarketDataType.KLINE1M

    def _is_quarter_minute(self, data: MarketData) -> bool:
        """检查是否为5分钟的整数倍"""
        if hasattr(data, "timestamp") and isinstance(data.timestamp, datetime):
            minute = data.timestamp.minute
            hour = data.timestamp.hour
            is_quarter = minute % 5 == 0
            is_special_time = (hour == 16 and minute == 10)

            if is_special_time:
                logger.info(f"🎯 命中特殊时间 16:10，准备通知: {data}")
            return is_quarter or is_special_time
        return False

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态信息"""
        return {
            "queue_size": self.data_queue.qsize(),
            "queue_max_size": self.queue_max_size,
            "queue_full": self.data_queue.full(),
            "worker_running": self._running
            and (self._worker_thread is not None and self._worker_thread.is_alive()),
        }

    def close(self) -> None:
        """关闭处理器，释放资源"""
        if not self._running:
            return

        logger.info("🛑 开始关闭K线通知处理器...")
        self._running = False

        # 发送停止信号以唤醒阻塞的get
        try:
            self.data_queue.put_nowait(None)
        except:
            pass

        if self._worker_thread and self._worker_thread.is_alive():
            logger.info("⏳ 等待后台处理线程结束...")
            self._worker_thread.join(timeout=self.notify_interval_seconds + 2)
            if self._worker_thread.is_alive():
                logger.warning(f"⚠️ 后台处理线程未能在 {self.notify_interval_seconds + 2} 秒内结束")

        # 关闭远程通知器
        self.remote_notifier.close()

        logger.info("✅ K线通知处理器已关闭")

    def __del__(self):
        """析构函数，确保资源被正确释放"""
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
