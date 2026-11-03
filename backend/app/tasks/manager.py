"""
任务管理器 - 在内存中记录每个分析任务的状态

任务状态流转：pending（等待）→ running（执行中）→ done（成功）/ failed（失败）
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor


class TaskManager:
    def __init__(self):
        self._tasks = {}
        self._lock = threading.Lock()

    def create(self) -> str:
        """创建一个新任务，返回任务 ID"""
        task_id = uuid.uuid4().hex
        task = {
            "id": task_id,
            "status": "pending",
            "stage": "等待开始",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }
        with self._lock:
            self._tasks[task_id] = task
        return task_id

    def update(self, task_id: str, **fields):
        """更新任务状态"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.update(fields)

    def get(self, task_id: str):
        """查询任务，返回副本"""
        with self._lock:
            task = self._tasks.get(task_id)
            return dict(task) if task else None


# 全局单例：任务表
task_manager = TaskManager()

# 线程池：在后台线程里跑 Agent，不阻塞 Web 接口
executor = ThreadPoolExecutor(max_workers=2)
