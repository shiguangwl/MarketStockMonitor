"""
股票数据抓取调度器
提供统一的定时任务管理功能，支持收盘后延续抓取
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job
import threading
import time
from utils.logger_config import setup_logger

logger = setup_logger("TickerScheduler")


class TickerScheduler:
    """股票数据抓取调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs: Dict[str, Job] = {}
        self.job_execution_times: Dict[str, float] = {}  # 记录任务执行时间
        self.job_error_counts: Dict[str, int] = {}  # 记录任务错误次数
        self.is_running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """启动调度器"""
        with self._lock:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                logger.info("🚀 定时任务调度器已启动")

    def stop(self) -> None:
        """停止调度器"""
        with self._lock:
            if self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                self.jobs.clear()
                self.job_execution_times.clear()
                self.job_error_counts.clear()
                logger.info("🛑 定时任务调度器已停止")

    def _wrapped_job_function(self, job_id: str, func: Callable, description: str = "") -> Callable:
        """包装任务函数，添加执行时间监控和错误处理"""
        def wrapped_func(*args, **kwargs):
            start_time = time.time()
            try:
                logger.debug(f"🔄 开始执行任务: {job_id}")
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                self.job_execution_times[job_id] = execution_time
                
                # 重置错误计数
                if job_id in self.job_error_counts:
                    self.job_error_counts[job_id] = 0
                
                # 如果执行时间过长，记录警告
                if execution_time > 5.0:
                    logger.warning(f"⚠️ 任务 {job_id} 执行时间较长: {execution_time:.2f}秒")
                else:
                    logger.debug(f"✅ 任务 {job_id} 执行完成，耗时: {execution_time:.2f}秒")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                self.job_execution_times[job_id] = execution_time
                
                # 增加错误计数
                self.job_error_counts[job_id] = self.job_error_counts.get(job_id, 0) + 1
                error_count = self.job_error_counts[job_id]
                
                logger.error(f"❌ 任务 {job_id} 执行失败 (第{error_count}次)，耗时: {execution_time:.2f}秒: {e}")
                
                # 如果连续错误次数过多，考虑暂停任务
                if error_count >= 5:
                    logger.critical(f"🚨 任务 {job_id} 连续失败{error_count}次，建议检查任务逻辑")
                
                raise
        
        return wrapped_func

    def add_interval_job(
        self, job_id: str, func: Callable, seconds: int, description: str = ""
    ) -> bool:
        """
        添加间隔执行的定时任务

        Args:
            job_id: 任务唯一标识
            func: 要执行的函数
            seconds: 执行间隔（秒）
            description: 任务描述

        Returns:
            bool: 添加成功返回True，失败返回False
        """
        try:
            with self._lock:
                if job_id in self.jobs:
                    logger.warning(f"⚠️ 任务 {job_id} 已存在，跳过添加")
                    return False

                # 包装任务函数，添加监控
                wrapped_func = self._wrapped_job_function(job_id, func, description)

                job = self.scheduler.add_job(
                    func=wrapped_func,
                    trigger="interval",
                    seconds=seconds,
                    id=job_id,
                    max_instances=1,  # 防止任务重叠执行
                    coalesce=True,  # 合并错过的任务
                    misfire_grace_time=30,  # 错过执行时间的宽限期（秒）
                )

                self.jobs[job_id] = job
                self.job_execution_times[job_id] = 0.0
                self.job_error_counts[job_id] = 0
                
                desc_text = f" - {description}" if description else ""
                logger.info(f"✅ 添加定时任务: {job_id} (每{seconds}秒){desc_text}")
                return True

        except Exception as e:
            logger.error(f"❌ 添加定时任务 {job_id} 失败: {e}")
            return False

    def remove_job(self, job_id: str) -> bool:
        """
        移除定时任务

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 移除成功返回True，失败返回False
        """
        try:
            with self._lock:
                if job_id not in self.jobs:
                    logger.warning(f"⚠️ 任务 {job_id} 不存在")
                    return False

                self.scheduler.remove_job(job_id)
                del self.jobs[job_id]
                del self.job_execution_times[job_id]
                del self.job_error_counts[job_id]
                logger.info(f"🗑️ 移除定时任务: {job_id}")
                return True

        except Exception as e:
            logger.error(f"❌ 移除定时任务 {job_id} 失败: {e}")
            return False

    def pause_job(self, job_id: str) -> bool:
        """
        暂停定时任务

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 暂停成功返回True，失败返回False
        """
        try:
            with self._lock:
                if job_id not in self.jobs:
                    logger.warning(f"⚠️ 任务 {job_id} 不存在")
                    return False

                self.scheduler.pause_job(job_id)
                logger.info(f"⏸️ 暂停定时任务: {job_id}")
                return True

        except Exception as e:
            logger.error(f"❌ 暂停定时任务 {job_id} 失败: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        恢复定时任务

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 恢复成功返回True，失败返回False
        """
        try:
            with self._lock:
                if job_id not in self.jobs:
                    logger.warning(f"⚠️ 任务 {job_id} 不存在")
                    return False

                self.scheduler.resume_job(job_id)
                logger.info(f"▶️ 恢复定时任务: {job_id}")
                return True

        except Exception as e:
            logger.error(f"❌ 恢复定时任务 {job_id} 失败: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态信息

        Args:
            job_id: 任务唯一标识

        Returns:
            Dict: 任务状态信息，如果任务不存在返回None
        """
        try:
            with self._lock:
                if job_id not in self.jobs:
                    return None

                job = self.jobs[job_id]
                execution_time = self.job_execution_times.get(job_id, 0.0)
                error_count = self.job_error_counts.get(job_id, 0)
                
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                    "pending": job.pending,
                    "last_execution_time": execution_time,
                    "error_count": error_count,
                    "status": "healthy" if error_count == 0 else "warning" if error_count < 3 else "critical"
                }

        except Exception as e:
            logger.error(f"❌ 获取任务状态 {job_id} 失败: {e}")
            return None

    def list_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有任务状态

        Returns:
            Dict: 所有任务的状态信息
        """
        result = {}
        with self._lock:
            for job_id in self.jobs:
                status = self.get_job_status(job_id)
                if status:
                    result[job_id] = status
        return result

    def is_job_running(self, job_id: str) -> bool:
        """
        检查任务是否正在运行

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 任务正在运行返回True，否则返回False
        """
        with self._lock:
            if job_id not in self.jobs:
                return False

            job = self.jobs[job_id]
            return job.pending if hasattr(job, "pending") else False

    def get_job_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取任务性能统计信息

        Returns:
            Dict: 任务性能统计
        """
        stats = {}
        with self._lock:
            for job_id in self.jobs:
                execution_time = self.job_execution_times.get(job_id, 0.0)
                error_count = self.job_error_counts.get(job_id, 0)
                
                stats[job_id] = {
                    "avg_execution_time": execution_time,
                    "error_count": error_count,
                    "health_status": "healthy" if error_count == 0 else "warning" if error_count < 3 else "critical"
                }
        return stats

    def reset_job_error_count(self, job_id: str) -> bool:
        """
        重置任务错误计数

        Args:
            job_id: 任务唯一标识

        Returns:
            bool: 重置成功返回True，失败返回False
        """
        try:
            with self._lock:
                if job_id in self.job_error_counts:
                    self.job_error_counts[job_id] = 0
                    logger.info(f"🔄 重置任务 {job_id} 错误计数")
                    return True
                return False
        except Exception as e:
            logger.error(f"❌ 重置任务错误计数 {job_id} 失败: {e}")
            return False


# 全局调度器实例
_global_scheduler: Optional[TickerScheduler] = None


def get_global_scheduler() -> TickerScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = TickerScheduler()
    return _global_scheduler


def start_global_scheduler() -> None:
    """启动全局调度器"""
    scheduler = get_global_scheduler()
    scheduler.start()


def stop_global_scheduler() -> None:
    """停止全局调度器"""
    global _global_scheduler
    if _global_scheduler is not None:
        _global_scheduler.stop()
        _global_scheduler = None
