"""
Cloud Connector Module

Handles connection management, authentication, and communication
with cloud workstation services.
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class CloudConfig:
    """
    Cloud workstation configuration.
    
    Attributes:
        endpoint: API endpoint URL (e.g., "https://workstation.example.com/api/v1")
        api_key: Authentication API key
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests
        verify_ssl: Whether to verify SSL certificates
        proxy: Optional proxy configuration
    """
    endpoint: str
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    proxy: Optional[str] = None
    
    @classmethod
    def from_file(cls, filepath: str) -> 'CloudConfig':
        """
        Load configuration from JSON file.
        
        Args:
            filepath: Path to config file
            
        Returns:
            CloudConfig instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_file(self, filepath: str):
        """
        Save configuration to JSON file.
        
        Args:
            filepath: Path to save config
        """
        with open(filepath, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def from_env(cls) -> 'CloudConfig':
        """
        Load configuration from environment variables.
        
        Expected variables:
            - SPINACH_CLOUD_ENDPOINT
            - SPINACH_CLOUD_API_KEY
            - SPINACH_CLOUD_TIMEOUT (optional)
            
        Returns:
            CloudConfig instance
        """
        endpoint = os.getenv('SPINACH_CLOUD_ENDPOINT')
        api_key = os.getenv('SPINACH_CLOUD_API_KEY')
        
        if not endpoint or not api_key:
            raise ValueError(
                "SPINACH_CLOUD_ENDPOINT and SPINACH_CLOUD_API_KEY "
                "environment variables must be set"
            )
        
        timeout = int(os.getenv('SPINACH_CLOUD_TIMEOUT', '30'))
        
        return cls(
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout
        )


class CloudConnector:
    """
    High-level interface for cloud workstation communication.
    
    Provides connection pooling, retry logic, and error handling.
    """
    
    def __init__(self, config: CloudConfig):
        """
        Initialize cloud connector.
        
        Args:
            config: Cloud configuration
        """
        self.config = config
        self.session = None
        self._connected = False
        
    def connect(self) -> bool:
        """
        Establish connection to cloud workstation.
        
        Returns:
            bool: Connection status
        """
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            # Create session with retry logic
            self.session = requests.Session()
            
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            
            # Set headers
            self.session.headers.update({
                'Authorization': f'Bearer {self.config.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'MultiSystemSpinachUI/1.0'
            })
            
            # Set proxy if configured
            if self.config.proxy:
                self.session.proxies = {
                    'http': self.config.proxy,
                    'https': self.config.proxy
                }
            
            # Verify SSL setting
            self.session.verify = self.config.verify_ssl
            
            # Test connection
            response = self.session.get(
                f"{self.config.endpoint}/health",
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            self._connected = True
            return True
            
        except Exception as e:
            print(f"Cloud connection failed: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Close connection to cloud workstation."""
        if self.session:
            self.session.close()
            self.session = None
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to cloud."""
        return self._connected
    
    def get(self, endpoint: str, **kwargs) -> Any:
        """
        Send GET request.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        if not self._connected:
            raise RuntimeError("Not connected to cloud")
        
        url = f"{self.config.endpoint}/{endpoint.lstrip('/')}"
        response = self.session.get(url, timeout=self.config.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Any:
        """
        Send POST request.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            data: Request payload
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        if not self._connected:
            raise RuntimeError("Not connected to cloud")
        
        url = f"{self.config.endpoint}/{endpoint.lstrip('/')}"
        response = self.session.post(
            url,
            json=data,
            timeout=self.config.timeout,
            **kwargs
        )
        response.raise_for_status()
        return response.json()
    
    def delete(self, endpoint: str, **kwargs) -> Any:
        """
        Send DELETE request.
        
        Args:
            endpoint: API endpoint (relative to base URL)
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        if not self._connected:
            raise RuntimeError("Not connected to cloud")
        
        url = f"{self.config.endpoint}/{endpoint.lstrip('/')}"
        response = self.session.delete(url, timeout=self.config.timeout, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def upload_file(self, endpoint: str, filepath: str, **kwargs) -> Any:
        """
        Upload a file to cloud.
        
        Args:
            endpoint: API endpoint
            filepath: Path to file
            **kwargs: Additional parameters
            
        Returns:
            Response data
        """
        if not self._connected:
            raise RuntimeError("Not connected to cloud")
        
        url = f"{self.config.endpoint}/{endpoint.lstrip('/')}"
        
        with open(filepath, 'rb') as f:
            files = {'file': f}
            response = self.session.post(
                url,
                files=files,
                timeout=self.config.timeout * 2,  # Longer timeout for uploads
                **kwargs
            )
        
        response.raise_for_status()
        return response.json()
    
    def download_file(self, endpoint: str, save_path: str, **kwargs):
        """
        Download a file from cloud.
        
        Args:
            endpoint: API endpoint
            save_path: Where to save the file
            **kwargs: Additional parameters
        """
        if not self._connected:
            raise RuntimeError("Not connected to cloud")
        
        url = f"{self.config.endpoint}/{endpoint.lstrip('/')}"
        
        response = self.session.get(
            url,
            stream=True,
            timeout=self.config.timeout * 2,  # Longer timeout for downloads
            **kwargs
        )
        response.raise_for_status()
        
        # Create directory if needed
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Save file
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get information about the cloud server.
        
        Returns:
            Server info dictionary
        """
        return self.get('/info')
    
    def test_connection(self) -> bool:
        """
        Test if connection is working.
        
        Returns:
            bool: Connection test result
        """
        try:
            self.get('/health')
            return True
        except:
            return False


# Default configuration paths
DEFAULT_CONFIG_DIR = Path.home() / '.spinach_ui'
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / 'cloud_config.json'


def load_default_config() -> Optional[CloudConfig]:
    """
    Load default cloud configuration.
    
    Tries in order:
    1. Config file at ~/.spinach_ui/cloud_config.json
    2. Environment variables
    
    Returns:
        CloudConfig or None if not found
    """
    # Try config file first
    if DEFAULT_CONFIG_FILE.exists():
        try:
            return CloudConfig.from_file(str(DEFAULT_CONFIG_FILE))
        except Exception as e:
            print(f"Failed to load config file: {e}")
    
    # Try environment variables
    try:
        return CloudConfig.from_env()
    except ValueError:
        pass
    
    return None


def save_default_config(config: CloudConfig):
    """
    Save configuration as default.
    
    Args:
        config: CloudConfig to save
    """
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.to_file(str(DEFAULT_CONFIG_FILE))
