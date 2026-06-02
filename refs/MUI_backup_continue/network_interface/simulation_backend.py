"""
Simulation Backend Interface

Defines the abstract interface and concrete implementations for
local and cloud-based simulation backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from enum import Enum
import json


class BackendType(Enum):
    """Simulation backend types"""
    LOCAL = "local"
    CLOUD = "cloud"


class SimulationBackend(ABC):
    """
    Abstract base class for simulation backends.
    
    This interface allows seamless switching between local MATLAB engine
    and cloud workstation execution.
    """
    
    def __init__(self):
        self.is_connected = False
        self.backend_type = None
        
    @abstractmethod
    def connect(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Establish connection to the simulation backend.
        
        Args:
            config: Configuration dictionary (cloud credentials, endpoints, etc.)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to the simulation backend.
        
        Returns:
            bool: True if disconnection successful
        """
        pass
    
    @abstractmethod
    def submit_simulation(self, 
                         task_params: Dict[str, Any],
                         callback: Optional[Callable] = None) -> str:
        """
        Submit a simulation task to the backend.
        
        Args:
            task_params: Dictionary containing simulation parameters
                - isotopes: List[str]
                - J_matrix: List[List[float]]
                - magnet: float
                - sweep: float
                - npoints: int
                - zerofill: int
                - etc.
            callback: Optional callback function for progress updates
            
        Returns:
            str: Task ID for tracking
        """
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a submitted task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict containing:
                - status: str (pending, running, completed, failed)
                - progress: float (0-100)
                - message: str
                - result: Optional[Dict] (if completed)
        """
        pass
    
    @abstractmethod
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve simulation results.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dict containing:
                - freq: List[float]
                - spec: List[complex]
                - metadata: Dict
            Or None if not ready
        """
        pass
    
    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            bool: True if cancellation successful
        """
        pass
    
    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """
        Get information about the backend.
        
        Returns:
            Dict containing:
                - type: BackendType
                - version: str
                - capabilities: List[str]
                - status: str
        """
        pass


class LocalBackend(SimulationBackend):
    """
    Local MATLAB engine backend.
    
    Executes simulations on the local machine using MATLAB engine.
    """
    
    def __init__(self):
        super().__init__()
        self.backend_type = BackendType.LOCAL
        self.engine = None
        
    def connect(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start local MATLAB engine.
        
        Args:
            config: Optional configuration
                - clean: bool (whether to start with 'clear all')
                
        Returns:
            bool: Connection status
        """
        try:
            # Import here to avoid circular dependency
            from src.core.spinach_bridge import spinach_eng, call_spinach
            
            clean = config.get('clean', True) if config else True
            
            # Start MATLAB engine
            self.engine_cm = spinach_eng(clean=clean)
            self.engine = self.engine_cm.__enter__()
            call_spinach.default_eng = self.engine
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Failed to start local MATLAB engine: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """Stop local MATLAB engine."""
        try:
            if self.engine_cm:
                self.engine_cm.__exit__(None, None, None)
            self.engine = None
            self.is_connected = False
            return True
        except Exception as e:
            print(f"Error disconnecting local backend: {e}")
            return False
    
    def submit_simulation(self, 
                         task_params: Dict[str, Any],
                         callback: Optional[Callable] = None) -> str:
        """
        Run simulation locally using MATLAB engine.
        
        This is a synchronous operation - returns after simulation completes.
        For UI integration, should be called from a worker thread.
        
        Args:
            task_params: Simulation parameters
            callback: Progress callback
            
        Returns:
            str: Task ID (for local, just returns a generated ID)
        """
        import uuid
        task_id = f"local_{uuid.uuid4().hex[:8]}"
        
        # In actual implementation, this would call spinach_bridge
        # For now, return the task_id
        # The actual simulation logic remains in SimWorker
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        For local backend, tasks are synchronous.
        Status is either completed or failed immediately.
        """
        return {
            'status': 'completed',
            'progress': 100.0,
            'message': 'Local simulation completed',
            'result': None
        }
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        For local backend, results are returned directly from submit_simulation.
        This method is mainly for cloud backend compatibility.
        """
        return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Local tasks are synchronous and cannot be cancelled mid-execution.
        Would need to be implemented at the worker thread level.
        """
        return False
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get local backend information."""
        return {
            'type': BackendType.LOCAL.value,
            'version': '1.0.0',
            'capabilities': [
                'synchronous_execution',
                'full_spinach_support',
                'gpu_support'
            ],
            'status': 'connected' if self.is_connected else 'disconnected'
        }


class CloudBackend(SimulationBackend):
    """
    Cloud workstation backend.
    
    Submits simulations to a remote workstation via REST API.
    Supports asynchronous task execution and result retrieval.
    """
    
    def __init__(self):
        super().__init__()
        self.backend_type = BackendType.CLOUD
        self.api_endpoint = None
        self.api_key = None
        self.session = None
        
    def connect(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Connect to cloud workstation API.
        
        Args:
            config: Required configuration
                - endpoint: str (API endpoint URL)
                - api_key: str (authentication key)
                - timeout: int (connection timeout in seconds)
                
        Returns:
            bool: Connection status
        """
        if not config:
            raise ValueError("Cloud backend requires configuration")
        
        try:
            import requests
            
            self.api_endpoint = config.get('endpoint')
            self.api_key = config.get('api_key')
            timeout = config.get('timeout', 10)
            
            if not self.api_endpoint or not self.api_key:
                raise ValueError("endpoint and api_key are required")
            
            # Create session with authentication
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
            
            # Test connection
            response = self.session.get(
                f"{self.api_endpoint}/health",
                timeout=timeout
            )
            response.raise_for_status()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to cloud backend: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> bool:
        """Close cloud connection."""
        try:
            if self.session:
                self.session.close()
            self.session = None
            self.is_connected = False
            return True
        except Exception as e:
            print(f"Error disconnecting cloud backend: {e}")
            return False
    
    def submit_simulation(self, 
                         task_params: Dict[str, Any],
                         callback: Optional[Callable] = None) -> str:
        """
        Submit simulation to cloud workstation.
        
        Args:
            task_params: Simulation parameters (will be JSON serialized)
            callback: Progress callback (for polling updates)
            
        Returns:
            str: Task ID from cloud server
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to cloud backend")
        
        try:
            # Submit task
            response = self.session.post(
                f"{self.api_endpoint}/simulations",
                json=task_params,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            task_id = result.get('task_id')
            
            return task_id
            
        except Exception as e:
            raise RuntimeError(f"Failed to submit simulation: {e}")
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check cloud task status.
        
        Args:
            task_id: Cloud task identifier
            
        Returns:
            Status dictionary
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to cloud backend")
        
        try:
            response = self.session.get(
                f"{self.api_endpoint}/simulations/{task_id}/status",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            return {
                'status': 'error',
                'progress': 0,
                'message': f'Failed to get status: {e}',
                'result': None
            }
    
    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve simulation results from cloud.
        
        Args:
            task_id: Cloud task identifier
            
        Returns:
            Result dictionary or None if not ready
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to cloud backend")
        
        try:
            response = self.session.get(
                f"{self.api_endpoint}/simulations/{task_id}/result",
                timeout=30
            )
            
            if response.status_code == 404:
                return None  # Not ready yet
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error retrieving result: {e}")
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a cloud task.
        
        Args:
            task_id: Cloud task identifier
            
        Returns:
            bool: Cancellation status
        """
        if not self.is_connected:
            return False
        
        try:
            response = self.session.delete(
                f"{self.api_endpoint}/simulations/{task_id}",
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Error cancelling task: {e}")
            return False
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get cloud backend information."""
        info = {
            'type': BackendType.CLOUD.value,
            'version': '1.0.0',
            'capabilities': [
                'asynchronous_execution',
                'task_queuing',
                'distributed_computing',
                'result_persistence'
            ],
            'status': 'connected' if self.is_connected else 'disconnected'
        }
        
        if self.is_connected:
            try:
                response = self.session.get(
                    f"{self.api_endpoint}/info",
                    timeout=5
                )
                if response.ok:
                    server_info = response.json()
                    info.update(server_info)
            except:
                pass
        
        return info
