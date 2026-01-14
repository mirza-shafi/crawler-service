"""
Task Manager Service - Track async crawl tasks
"""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
from ..schemas.crawler import TaskStatus, TaskResponse, CrawlResponse

logger = logging.getLogger(__name__)


class TaskManager:
    """In-memory task manager for tracking async crawl operations"""
    
    def __init__(self):
        self.tasks: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, seed_url: str, max_pages: int, follow_external_links: bool) -> str:
        """Create a new task and return task ID"""
        task_id = str(uuid.uuid4())
        
        async with self._lock:
            self.tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "created_at": datetime.utcnow(),
                "started_at": None,
                "completed_at": None,
                "seed_url": seed_url,
                "max_pages": max_pages,
                "follow_external_links": follow_external_links,
                "progress": {
                    "pages_crawled": 0,
                    "pages_remaining": max_pages
                },
                "result": None,
                "error": None
            }
        
        logger.info(f"Created task {task_id} for {seed_url}")
        return task_id
    
    async def update_status(self, task_id: str, status: TaskStatus, **kwargs):
        """Update task status and optional fields"""
        async with self._lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return
            
            self.tasks[task_id]["status"] = status
            
            if status == TaskStatus.RUNNING and "started_at" not in self.tasks[task_id]:
                self.tasks[task_id]["started_at"] = datetime.utcnow()
            
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                self.tasks[task_id]["completed_at"] = datetime.utcnow()
            
            # Update any additional fields
            for key, value in kwargs.items():
                self.tasks[task_id][key] = value
    
    async def update_progress(self, task_id: str, pages_crawled: int, pages_remaining: int):
        """Update task progress"""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["progress"] = {
                    "pages_crawled": pages_crawled,
                    "pages_remaining": pages_remaining
                }
    
    async def set_result(self, task_id: str, result: CrawlResponse):
        """Set task result"""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["result"] = result
                self.tasks[task_id]["status"] = TaskStatus.COMPLETED
                self.tasks[task_id]["completed_at"] = datetime.utcnow()
    
    async def set_error(self, task_id: str, error: str):
        """Set task error"""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id]["error"] = error
                self.tasks[task_id]["status"] = TaskStatus.FAILED
                self.tasks[task_id]["completed_at"] = datetime.utcnow()
    
    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get task by ID"""
        async with self._lock:
            return self.tasks.get(task_id)
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove tasks older than max_age_hours"""
        async with self._lock:
            now = datetime.utcnow()
            to_remove = []
            
            for task_id, task in self.tasks.items():
                age = (now - task["created_at"]).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                logger.info(f"Cleaned up old task {task_id}")


# Singleton instance
task_manager = TaskManager()
