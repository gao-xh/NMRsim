"""
Network Interface Module for Multi-System Spinach UI

This module provides interfaces for both local and cloud-based simulation execution.
Supports seamless switching between local MATLAB engine and remote workstation.

Author: Multi-System Spinach UI Team
Date: 2025-10-08
Version: 1.0.0
"""

from .simulation_backend import SimulationBackend, LocalBackend, CloudBackend
from .cloud_connector import CloudConnector, CloudConfig
from .task_manager import TaskManager, SimulationTask, TaskStatus

__all__ = [
    'SimulationBackend',
    'LocalBackend',
    'CloudBackend',
    'CloudConnector',
    'CloudConfig',
    'TaskManager',
    'SimulationTask',
    'TaskStatus'
]

__version__ = '1.0.0'
