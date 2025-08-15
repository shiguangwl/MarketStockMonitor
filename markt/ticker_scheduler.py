"""
股票数据抓取调度器
提供统一的定时任务管理功能，支持收盘后延续抓取
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.job import Job
import threading
from utils.logger_config import setup_logger

logger = setup_logger("TickerScheduler")


class TickerScheduler:
    """股票数据抓取调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.jobs: Dict[str, Job] = {}
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
                logger.info("🛑 定时任务调度器已停止")

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

                job = self.scheduler.add_job(
                    func=func,
                    trigger="interval",
                    seconds=seconds,
                    id=job_id,
                    max_instances=1,  # 防止任务重叠执行
                    coalesce=True,  # 合并错过的任务
                )

                self.jobs[job_id] = job
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
                return {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                    "pending": job.pending,
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
