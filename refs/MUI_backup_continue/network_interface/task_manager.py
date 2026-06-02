"""
Task Manager Module

Manages simulation task lifecycle, status tracking, and result caching.
"""

import json
import time
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"      # Task created, not yet submitted
    QUEUED = "queued"        # Task submitted, waiting to run
    RUNNING = "running"      # Task is executing
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"        # Task failed with error
    CANCELLED = "cancelled"  # Task was cancelled
    UNKNOWN = "unknown"      # Status cannot be determined


@dataclass
class SimulationTask:
    """
    Represents a simulation task.
    
    Attributes:
        task_id: Unique task identifier
        status: Current task status
        parameters: Simulation parameters
        result: Simulation result (if completed)
        error: Error message (if failed)
        created_at: Creation timestamp
        started_at: Start timestamp
        completed_at: Completion timestamp
        progress: Progress percentage (0-100)
        metadata: Additional task metadata
    """
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationTask':
        """Create task from dictionary."""
        data = data.copy()
        if 'status' in data:
            data['status'] = TaskStatus(data['status'])
        return cls(**data)
    
    def is_terminal(self) -> bool:
        """Check if task is in terminal state."""
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED
        ]
    
    def is_active(self) -> bool:
        """Check if task is actively running."""
        return self.status in [
            TaskStatus.QUEUED,
            TaskStatus.RUNNING
        ]


class TaskManager:
    """
    Manages simulation tasks.
    
    Provides task tracking, status monitoring, and result caching.
    """
    
    def __init__(self, max_cache_size: int = 100):
        """
        Initialize task manager.
        
        Args:
            max_cache_size: Maximum number of tasks to cache
        """
        self.tasks: Dict[str, SimulationTask] = {}
        self.max_cache_size = max_cache_size
        
    def create_task(self, task_id: str, parameters: Dict[str, Any]) -> SimulationTask:
        """
        Create a new task.
        
        Args:
            task_id: Unique task identifier
            parameters: Simulation parameters
            
        Returns:
            Created task
        """
        task = SimulationTask(
            task_id=task_id,
            parameters=parameters,
            status=TaskStatus.PENDING
        )
        
        self.tasks[task_id] = task
        self._cleanup_cache()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[SimulationTask]:
        """
        Get task by ID.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task or None if not found
        """
        return self.tasks.get(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
        error: Optional[str] = None
    ):
        """
        Update task status.
        
        Args:
            task_id: Task identifier
            status: New status
            progress: Progress percentage (optional)
            error: Error message (optional)
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.status = status
        
        if progress is not None:
            task.progress = progress
        
        if error is not None:
            task.error = error
        
        # Update timestamps
        if status == TaskStatus.RUNNING and not task.started_at:
            task.started_at = datetime.now().isoformat()
        
        if task.is_terminal() and not task.completed_at:
            task.completed_at = datetime.now().isoformat()
            task.progress = 100.0 if status == TaskStatus.COMPLETED else task.progress
    
    def set_task_result(self, task_id: str, result: Any):
        """
        Set task result.
        
        Args:
            task_id: Task identifier
            result: Simulation result
        """
        task = self.tasks.get(task_id)
        if task:
            task.result = result
            if task.status != TaskStatus.FAILED:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                task.progress = 100.0
    
    def get_active_tasks(self) -> List[SimulationTask]:
        """
        Get all active tasks.
        
        Returns:
            List of active tasks
        """
        return [
            task for task in self.tasks.values()
            if task.is_active()
        ]
    
    def get_completed_tasks(self) -> List[SimulationTask]:
        """
        Get all completed tasks.
        
        Returns:
            List of completed tasks
        """
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        ]
    
    def get_failed_tasks(self) -> List[SimulationTask]:
        """
        Get all failed tasks.
        
        Returns:
            List of failed tasks
        """
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.FAILED
        ]
    
    def cancel_task(self, task_id: str):
        """
        Mark task as cancelled.
        
        Args:
            task_id: Task identifier
        """
        self.update_task_status(task_id, TaskStatus.CANCELLED)
    
    def remove_task(self, task_id: str):
        """
        Remove task from manager.
        
        Args:
            task_id: Task identifier
        """
        self.tasks.pop(task_id, None)
    
    def clear_completed(self):
        """Remove all completed tasks from cache."""
        to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        ]
        for task_id in to_remove:
            del self.tasks[task_id]
    
    def clear_all(self):
        """Clear all tasks."""
        self.tasks.clear()
    
    def _cleanup_cache(self):
        """Remove oldest tasks if cache is full."""
        if len(self.tasks) <= self.max_cache_size:
            return
        
        # Sort by creation time
        sorted_tasks = sorted(
            self.tasks.items(),
            key=lambda x: x[1].created_at
        )
        
        # Remove oldest tasks
        num_to_remove = len(self.tasks) - self.max_cache_size
        for task_id, _ in sorted_tasks[:num_to_remove]:
            del self.tasks[task_id]
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get task statistics.
        
        Returns:
            Dictionary with task counts by status
        """
        stats = {status.value: 0 for status in TaskStatus}
        stats['total'] = len(self.tasks)
        
        for task in self.tasks.values():
            stats[task.status.value] += 1
        
        return stats
    
    def export_tasks(self, filepath: str):
        """
        Export tasks to JSON file.
        
        Args:
            filepath: Path to save file
        """
        data = {
            task_id: task.to_dict()
            for task_id, task in self.tasks.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_tasks(self, filepath: str):
        """
        Import tasks from JSON file.
        
        Args:
            filepath: Path to load file
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for task_id, task_data in data.items():
            task = SimulationTask.from_dict(task_data)
            self.tasks[task_id] = task
        
        self._cleanup_cache()


class TaskMonitor:
    """
    Monitors task progress with polling.
    
    Useful for tracking cloud tasks that require periodic status checks.
    """
    
    def __init__(
        self,
        task_manager: TaskManager,
        poll_interval: float = 2.0,
        max_poll_time: float = 3600.0
    ):
        """
        Initialize task monitor.
        
        Args:
            task_manager: TaskManager instance
            poll_interval: Seconds between status checks
            max_poll_time: Maximum time to poll before giving up
        """
        self.task_manager = task_manager
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time
        self._monitoring = {}
    
    def start_monitoring(self, task_id: str, status_callback):
        """
        Start monitoring a task.
        
        Args:
            task_id: Task to monitor
            status_callback: Callback function(task) called on status change
        """
        self._monitoring[task_id] = {
            'callback': status_callback,
            'start_time': time.time(),
            'last_status': None
        }
    
    def stop_monitoring(self, task_id: str):
        """
        Stop monitoring a task.
        
        Args:
            task_id: Task to stop monitoring
        """
        self._monitoring.pop(task_id, None)
    
    def poll_once(self, task_id: str, get_status_func) -> bool:
        """
        Poll task status once.
        
        Args:
            task_id: Task to poll
            get_status_func: Function to get current status
            
        Returns:
            bool: True if should continue polling
        """
        if task_id not in self._monitoring:
            return False
        
        monitor_info = self._monitoring[task_id]
        
        # Check timeout
        elapsed = time.time() - monitor_info['start_time']
        if elapsed > self.max_poll_time:
            self.stop_monitoring(task_id)
            return False
        
        # Get current task
        task = self.task_manager.get_task(task_id)
        if not task:
            self.stop_monitoring(task_id)
            return False
        
        # Update status
        try:
            status_info = get_status_func(task_id)
            if status_info:
                self.task_manager.update_task_status(
                    task_id,
                    TaskStatus(status_info.get('status', 'unknown')),
                    progress=status_info.get('progress'),
                    error=status_info.get('error')
                )
        except Exception as e:
            print(f"Error polling task {task_id}: {e}")
        
        # Check if status changed
        current_status = task.status
        if current_status != monitor_info['last_status']:
            monitor_info['last_status'] = current_status
            monitor_info['callback'](task)
        
        # Stop if terminal
        if task.is_terminal():
            self.stop_monitoring(task_id)
            return False
        
        return True
    
    def get_monitored_tasks(self) -> List[str]:
        """
        Get list of currently monitored task IDs.
        
        Returns:
            List of task IDs
        """
        return list(self._monitoring.keys())
