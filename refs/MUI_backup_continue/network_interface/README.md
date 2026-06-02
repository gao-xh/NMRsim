# Network Interface Module

本模块提供了本地和云端仿真后端之间的无缝切换能力。

## 模块结构

```
network_interface/
├── __init__.py              # 模块导出
├── simulation_backend.py    # 后端抽象接口
├── cloud_connector.py       # 云端连接管理
├── task_manager.py          # 任务生命周期管理
└── README.md               # 本文档
```

## 核心组件

### 1. SimulationBackend (抽象基类)

定义了统一的仿真后端接口:

```python
from network_interface import SimulationBackend, LocalBackend, CloudBackend, BackendType

# 使用本地后端
backend = LocalBackend()
config = {}  # 本地后端不需要配置
backend.connect(config)

# 提交仿真任务
task_id = backend.submit_simulation(parameters)

# 获取结果
result = backend.get_result(task_id)
```

### 2. LocalBackend (本地MATLAB后端)

包装现有的 `spinach_bridge` 模块:

**特点:**
- 同步执行,立即返回结果
- 无需网络连接
- 使用本地 MATLAB 引擎
- 默认后端,向后兼容

**使用方法:**
```python
backend = LocalBackend()
backend.connect({})  # 启动 MATLAB 引擎

# 提交任务(同步执行)
task_id = backend.submit_simulation({
    'molecule_data': molecule_data,
    'inter': inter,
    'sys_info': sys_info,
    'spin_system': spin_system
})

# 立即获取结果
result = backend.get_result(task_id)
print(result['spectrum'])
```

### 3. CloudBackend (云端工作站后端)

使用 REST API 与云端工作站通信:

**特点:**
- 异步执行,需要轮询状态
- 需要网络连接和认证
- 支持任务队列和并行计算
- 适合大规模计算

**使用方法:**
```python
from network_interface import CloudBackend, CloudConfig

# 配置云端连接
config = CloudConfig(
    endpoint="https://workstation.example.com/api/v1",
    api_key="your-api-key-here",
    timeout=30
)

backend = CloudBackend()
backend.connect(config)

# 提交任务(异步)
task_id = backend.submit_simulation(parameters)

# 轮询状态
import time
while True:
    status = backend.get_task_status(task_id)
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(2)

# 获取结果
if status['status'] == 'completed':
    result = backend.get_result(task_id)
```

### 4. CloudConnector (云端连接器)

管理与云端的 HTTP 连接:

**特点:**
- 自动重试机制
- 连接池管理
- Bearer Token 认证
- 文件上传/下载支持

**使用方法:**
```python
from network_interface import CloudConnector, CloudConfig

config = CloudConfig(
    endpoint="https://workstation.example.com/api/v1",
    api_key="your-api-key",
    max_retries=3
)

connector = CloudConnector(config)
connector.connect()

# 发送 GET 请求
info = connector.get('/info')

# 发送 POST 请求
response = connector.post('/simulations', data={'param': 'value'})

# 上传文件
connector.upload_file('/upload', 'data.json')

# 下载文件
connector.download_file('/results/abc123', 'result.json')
```

### 5. TaskManager (任务管理器)

跟踪任务状态和结果:

**特点:**
- 任务生命周期管理
- 结果缓存
- 状态统计
- 导入/导出功能

**使用方法:**
```python
from network_interface import TaskManager, SimulationTask, TaskStatus

manager = TaskManager(max_cache_size=100)

# 创建任务
task = manager.create_task('task-001', parameters={'field': 1.5})

# 更新状态
manager.update_task_status('task-001', TaskStatus.RUNNING, progress=50.0)

# 设置结果
manager.set_task_result('task-001', {'spectrum': [...]})

# 获取任务
task = manager.get_task('task-001')
print(f"Status: {task.status.value}, Progress: {task.progress}%")

# 获取统计
stats = manager.get_statistics()
print(f"Total: {stats['total']}, Completed: {stats['completed']}")
```

### 6. TaskMonitor (任务监控器)

自动轮询云端任务状态:

**使用方法:**
```python
from network_interface import TaskMonitor

monitor = TaskMonitor(
    task_manager=manager,
    poll_interval=2.0,  # 每2秒检查一次
    max_poll_time=3600  # 最多轮询1小时
)

# 定义状态变化回调
def on_status_change(task):
    print(f"Task {task.task_id} status: {task.status.value}")

# 开始监控
monitor.start_monitoring('task-001', on_status_change)

# 轮询一次
should_continue = monitor.poll_once('task-001', backend.get_task_status)
```

## 配置管理

### 方式1: 配置文件

创建 `~/.spinach_ui/cloud_config.json`:

```json
{
  "endpoint": "https://workstation.example.com/api/v1",
  "api_key": "your-api-key-here",
  "timeout": 30,
  "max_retries": 3,
  "verify_ssl": true,
  "proxy": null
}
```

加载配置:
```python
from network_interface import load_default_config

config = load_default_config()
if config:
    backend = CloudBackend()
    backend.connect(config)
```

### 方式2: 环境变量

设置环境变量:
```bash
# Windows PowerShell
$env:SPINACH_CLOUD_ENDPOINT = "https://workstation.example.com/api/v1"
$env:SPINACH_CLOUD_API_KEY = "your-api-key-here"
$env:SPINACH_CLOUD_TIMEOUT = "30"

# Linux/Mac
export SPINACH_CLOUD_ENDPOINT="https://workstation.example.com/api/v1"
export SPINACH_CLOUD_API_KEY="your-api-key-here"
export SPINACH_CLOUD_TIMEOUT="30"
```

加载配置:
```python
from network_interface import CloudConfig

config = CloudConfig.from_env()
```

### 方式3: 代码创建

```python
from network_interface import CloudConfig, save_default_config

config = CloudConfig(
    endpoint="https://workstation.example.com/api/v1",
    api_key="your-api-key-here",
    timeout=30
)

# 保存为默认配置
save_default_config(config)
```

## 集成到主UI

### 基本集成示例

```python
from network_interface import (
    BackendType, LocalBackend, CloudBackend,
    CloudConfig, TaskManager, load_default_config
)

class MultiSystemSpinachUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化后端
        self.backend_type = BackendType.LOCAL
        self.backend = None
        self.task_manager = TaskManager()
        
        # 创建后端选择器
        self.setup_backend_selector()
        
        # 连接到默认后端
        self.connect_backend()
    
    def setup_backend_selector(self):
        """创建后端选择UI"""
        backend_group = QGroupBox("Simulation Backend")
        layout = QVBoxLayout()
        
        self.local_radio = QRadioButton("Local (MATLAB)")
        self.cloud_radio = QRadioButton("Cloud Workstation")
        
        self.local_radio.setChecked(True)
        self.local_radio.toggled.connect(self.on_backend_changed)
        
        layout.addWidget(self.local_radio)
        layout.addWidget(self.cloud_radio)
        backend_group.setLayout(layout)
        
        # 添加到主界面
        # self.main_layout.addWidget(backend_group)
    
    def on_backend_changed(self, checked):
        """后端选择变化"""
        if checked:
            self.backend_type = BackendType.LOCAL
        else:
            self.backend_type = BackendType.CLOUD
        
        # 重新连接
        self.connect_backend()
    
    def connect_backend(self):
        """连接到选定的后端"""
        # 断开旧连接
        if self.backend:
            self.backend.disconnect()
        
        # 创建新后端
        if self.backend_type == BackendType.LOCAL:
            self.backend = LocalBackend()
            config = {}
        else:
            self.backend = CloudBackend()
            config = load_default_config()
            
            if not config:
                QMessageBox.warning(
                    self,
                    "Cloud Config Missing",
                    "Please configure cloud connection first"
                )
                self.local_radio.setChecked(True)
                return
        
        # 连接
        if self.backend.connect(config):
            print(f"Connected to {self.backend_type.value} backend")
        else:
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Failed to connect to {self.backend_type.value} backend"
            )
    
    def run_simulation(self, parameters):
        """运行仿真"""
        # 提交任务
        task_id = self.backend.submit_simulation(parameters)
        
        # 创建任务记录
        self.task_manager.create_task(task_id, parameters)
        
        # 本地后端立即返回结果
        if self.backend_type == BackendType.LOCAL:
            result = self.backend.get_result(task_id)
            self.task_manager.set_task_result(task_id, result)
            self.on_simulation_complete(task_id, result)
        
        # 云端后端需要轮询
        else:
            self.poll_cloud_task(task_id)
    
    def poll_cloud_task(self, task_id):
        """轮询云端任务状态"""
        # 这里可以使用 QTimer 定期检查
        # 或者使用 TaskMonitor 自动轮询
        status = self.backend.get_task_status(task_id)
        
        # 更新任务管理器
        self.task_manager.update_task_status(
            task_id,
            TaskStatus(status['status']),
            progress=status.get('progress')
        )
        
        # 如果完成,获取结果
        if status['status'] == 'completed':
            result = self.backend.get_result(task_id)
            self.task_manager.set_task_result(task_id, result)
            self.on_simulation_complete(task_id, result)
    
    def on_simulation_complete(self, task_id, result):
        """仿真完成回调"""
        print(f"Simulation {task_id} completed")
        # 更新UI,显示结果
```

## API端点规范 (云端工作站)

云端工作站需要实现以下REST API端点:

### 健康检查
- `GET /health` - 返回服务状态
- Response: `{"status": "ok"}`

### 服务信息
- `GET /info` - 返回服务能力
- Response:
  ```json
  {
    "name": "Spinach Cloud Backend",
    "version": "1.0.0",
    "capabilities": ["parallel", "gpu"],
    "max_concurrent_tasks": 10
  }
  ```

### 提交任务
- `POST /simulations` - 提交新任务
- Request Body: `{"parameters": {...}}`
- Response: `{"task_id": "abc123", "status": "queued"}`

### 查询状态
- `GET /simulations/{task_id}` - 获取任务状态
- Response:
  ```json
  {
    "task_id": "abc123",
    "status": "running",
    "progress": 45.5,
    "created_at": "2024-01-01T12:00:00Z",
    "started_at": "2024-01-01T12:00:05Z"
  }
  ```

### 获取结果
- `GET /simulations/{task_id}/result` - 获取结果
- Response: `{"spectrum": [...], "processed_data": {...}}`

### 取消任务
- `DELETE /simulations/{task_id}` - 取消任务
- Response: `{"status": "cancelled"}`

## 依赖项

```
requests>=2.28.0
urllib3>=1.26.0
```

安装:
```bash
pip install requests urllib3
```

## 未来扩展

1. **批量提交**: 支持一次提交多个任务
2. **任务优先级**: 云端任务队列优先级控制
3. **结果订阅**: WebSocket 实时推送结果
4. **缓存策略**: 智能结果缓存和复用
5. **负载均衡**: 多个云端节点负载均衡
6. **断点续传**: 大文件上传下载断点续传

## 注意事项

1. 云端连接需要有效的API密钥
2. 建议在 `~/.spinach_ui/cloud_config.json` 中存储配置
3. API密钥应妥善保管,不要提交到版本控制
4. 云端任务可能需要较长时间,建议使用异步处理
5. 本地后端仍然是默认选项,保证向后兼容
