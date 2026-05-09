"""
定时任务调度模块

支持：
1. 定时分析任务
2. 数据更新任务
3. 监控告警
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    func: Callable
    interval_seconds: int
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None
    run_count: int = 0


class TaskScheduler:
    """任务调度器"""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def add_task(self, name: str, func: Callable, interval_seconds: int,
                 start_immediately: bool = False) -> ScheduledTask:
        """
        添加定时任务

        参数:
            name: 任务名称
            func: 任务函数
            interval_seconds: 执行间隔（秒）
            start_immediately: 是否立即执行一次
        """
        with self._lock:
            task = ScheduledTask(
                name=name,
                func=func,
                interval_seconds=interval_seconds,
                next_run=datetime.now() if start_immediately else datetime.now() + timedelta(seconds=interval_seconds)
            )
            self._tasks[name] = task
            logger.info(f"添加定时任务: {name}, 间隔: {interval_seconds}秒")
            return task

    def remove_task(self, name: str) -> bool:
        """移除任务"""
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                logger.info(f"移除定时任务: {name}")
                return True
            return False

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("任务调度器已启动")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("任务调度器已停止")

    def _run_loop(self):
        """主循环"""
        while self._running:
            try:
                self._check_and_run_tasks()
                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                logger.error(f"调度器错误: {e}")

    def _check_and_run_tasks(self):
        """检查并执行到期任务"""
        now = datetime.now()

        with self._lock:
            tasks_to_run = []

            for name, task in self._tasks.items():
                if task.status == TaskStatus.RUNNING:
                    continue

                if task.next_run and task.next_run <= now:
                    tasks_to_run.append(task)

        for task in tasks_to_run:
            self._execute_task(task)

    def _execute_task(self, task: ScheduledTask):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        logger.info(f"开始执行任务: {task.name}")

        try:
            task.func()
            task.status = TaskStatus.COMPLETED
            task.error = None
            task.run_count += 1
            logger.info(f"任务完成: {task.name}, 已执行{task.run_count}次")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"任务失败: {task.name} - {e}")

        finally:
            task.last_run = datetime.now()
            task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)

    def get_task_status(self, name: str) -> Optional[Dict]:
        """获取任务状态"""
        with self._lock:
            if name in self._tasks:
                task = self._tasks[name]
                return {
                    "name": task.name,
                    "status": task.status.value,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "error": task.error
                }
            return None

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        with self._lock:
            return [self.get_task_status(name) for name in self._tasks]


# 全局调度器实例
_scheduler = None


def get_scheduler() -> TaskScheduler:
    """获取全局调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


# 预定义任务函数
def task_update_realtime_quotes():
    """更新实时行情任务"""
    try:
        from src.utils.tencent_api import get_stock_quotes
        from src.utils.cache_enhanced import get_cache

        # 热门股票代码
        codes = ["600519", "600036", "000858", "300750", "000001"]
        quotes = get_stock_quotes(codes)

        if quotes:
            cache = get_cache()
            cache.set("realtime_quotes", quotes, ttl=60)
            logger.info(f"更新实时行情: {len(quotes)}只股票")

    except Exception as e:
        logger.error(f"更新实时行情失败: {e}")


def task_update_northbound_flow():
    """更新北向资金任务"""
    try:
        from src.tools.a_stock_api import AStockAPI
        from src.utils.cache_enhanced import get_cache

        api = AStockAPI()
        flows = api.get_northbound_flow(days=30)

        if flows:
            cache = get_cache()
            cache.set("northbound_flow", flows, ttl=300)
            logger.info(f"更新北向资金: {len(flows)}天数据")

    except Exception as e:
        logger.error(f"更新北向资金失败: {e}")


def task_analyze_hot_stocks():
    """分析热门股票任务"""
    try:
        from comprehensive_analyze import ComprehensiveAnalyzer

        analyzer = ComprehensiveAnalyzer()
        results = analyzer.analyze_all()

        # 保存结果
        import json
        from datetime import datetime

        output = {
            "analysis_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "results": results
        }

        with open("scheduled_analysis_result.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"定时分析完成: {len(results)}只股票")

    except Exception as e:
        logger.error(f"定时分析失败: {e}")


def setup_default_tasks():
    """设置默认定时任务"""
    scheduler = get_scheduler()

    # 每1分钟更新实时行情
    scheduler.add_task(
        "update_realtime_quotes",
        task_update_realtime_quotes,
        interval_seconds=60,
        start_immediately=True
    )

    # 每5分钟更新北向资金
    scheduler.add_task(
        "update_northbound_flow",
        task_update_northbound_flow,
        interval_seconds=300,
        start_immediately=True
    )

    # 每小时分析热门股票
    scheduler.add_task(
        "analyze_hot_stocks",
        task_analyze_hot_stocks,
        interval_seconds=3600,
        start_immediately=False
    )

    return scheduler


if __name__ == "__main__":
    # 测试调度器
    scheduler = setup_default_tasks()
    scheduler.start()

    print("调度器已启动，按Ctrl+C停止...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
        print("调度器已停止")
