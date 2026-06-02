# Network Interface Quick Start Guide

快速集成网络接口到主UI的指南

## 第一步: 安装依赖

```bash
pip install requests urllib3
```

## 第二步: 导入模块

在 `Multi_system_spinach_UI.py` 顶部添加:

```python
from network_interface import (
    BackendType,
    LocalBackend, 
    CloudBackend,
    CloudConfig,
    TaskManager,
    TaskStatus,
    load_default_config
)
```

## 第三步: 初始化后端 (在 __init__ 中)

```python
class MultiSystemSpinachUI(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化后端系统
        self.backend_type = BackendType.LOCAL  # 默认使用本地
        self.backend = None
        self.task_manager = TaskManager(max_cache_size=100)
        
        # ... 其他初始化代码 ...
        
        # 连接到后端
        self.connect_backend()
```

## 第四步: 添加连接方法

```python
def connect_backend(self):
    """连接到选定的后端"""
    # 断开旧连接
    if self.backend:
        try:
            self.backend.disconnect()
        except:
            pass
    
    # 创建新后端
    if self.backend_type == BackendType.LOCAL:
        self.backend = LocalBackend()
        config = {}
        backend_name = "Local MATLAB"
    else:
        self.backend = CloudBackend()
        config = load_default_config()
        backend_name = "Cloud Workstation"
        
        if not config:
            QMessageBox.warning(
                self,
                "Configuration Missing",
                "Cloud configuration not found. Using local backend."
            )
            self.backend_type = BackendType.LOCAL
            return self.connect_backend()
    
    # 连接
    try:
        if self.backend.connect(config):
            print(f"Connected to {backend_name}")
            self.log_message(f"Backend: {backend_name} connected")
        else:
            raise Exception("Connection failed")
    except Exception as e:
        QMessageBox.critical(
            self,
            "Connection Error",
            f"Failed to connect to {backend_name}: {str(e)}"
        )
```

## 第五步: 修改运行仿真方法

找到现有的 `run_simulation()` 或类似方法,修改为:

```python
def run_simulation(self):
    """运行仿真 (修改后的版本)"""
    # 获取当前系统的参数
    current_sys = self.current_system
    
    # 准备仿真参数
    parameters = {
        'molecule_data': self.get_molecule_data(current_sys),
        'inter': self.get_inter_data(current_sys),
        'sys_info': self.get_sys_info(current_sys),
        'spin_system': self.get_spin_system(current_sys)
    }
    
    # 提交到后端
    try:
        task_id = self.backend.submit_simulation(parameters)
        self.log_message(f"Simulation submitted: {task_id}")
        
        # 创建任务记录
        self.task_manager.create_task(task_id, parameters)
        
        # 根据后端类型处理结果
        if self.backend_type == BackendType.LOCAL:
            # 本地后端: 同步执行,立即获取结果
            result = self.backend.get_result(task_id)
            self.task_manager.set_task_result(task_id, result)
            self.on_simulation_complete(task_id, result)
        else:
            # 云端后端: 异步执行,需要轮询
            self.start_polling_task(task_id)
            
    except Exception as e:
        QMessageBox.critical(
            self,
            "Simulation Error",
            f"Failed to submit simulation: {str(e)}"
        )
```

## 第六步: 添加云端任务轮询 (如果使用云端)

```python
def start_polling_task(self, task_id):
    """开始轮询云端任务"""
    # 创建定时器
    if not hasattr(self, 'poll_timers'):
        self.poll_timers = {}
    
    timer = QTimer()
    timer.setInterval(2000)  # 2秒轮询一次
    timer.timeout.connect(lambda: self.poll_task_status(task_id))
    timer.start()
    
    self.poll_timers[task_id] = timer
    self.log_message(f"Started polling task {task_id}")

def poll_task_status(self, task_id):
    """轮询任务状态"""
    try:
        # 获取状态
        status_info = self.backend.get_task_status(task_id)
        
        # 更新任务管理器
        self.task_manager.update_task_status(
            task_id,
            TaskStatus(status_info['status']),
            progress=status_info.get('progress', 0),
            error=status_info.get('error')
        )
        
        # 更新UI显示
        task = self.task_manager.get_task(task_id)
        self.log_message(
            f"Task {task_id}: {task.status.value} ({task.progress:.1f}%)"
        )
        
        # 如果完成,停止轮询并获取结果
        if task.is_terminal():
            self.poll_timers[task_id].stop()
            del self.poll_timers[task_id]
            
            if task.status == TaskStatus.COMPLETED:
                result = self.backend.get_result(task_id)
                self.task_manager.set_task_result(task_id, result)
                self.on_simulation_complete(task_id, result)
            else:
                QMessageBox.warning(
                    self,
                    "Simulation Failed",
                    f"Task {task_id} failed: {task.error}"
                )
                
    except Exception as e:
        self.log_message(f"Error polling task {task_id}: {e}")
```

## 第七步: 结果处理回调

```python
def on_simulation_complete(self, task_id, result):
    """仿真完成回调"""
    self.log_message(f"Simulation {task_id} completed")
    
    # 提取结果
    if result and 'spectrum' in result:
        spectrum = result['spectrum']
        
        # 更新UI (与原来的代码相同)
        # 例如: self.update_spectrum_plot(spectrum)
        
        self.log_message("Spectrum data received and displayed")
    else:
        QMessageBox.warning(
            self,
            "No Result",
            "Simulation completed but no spectrum data received"
        )
```

## 第八步: (可选) 添加后端选择UI

在设置菜单或工具栏添加:

```python
def setup_backend_menu(self):
    """创建后端选择菜单"""
    backend_menu = self.menuBar().addMenu("Backend")
    
    # 本地后端选项
    local_action = QAction("Use Local MATLAB", self)
    local_action.setCheckable(True)
    local_action.setChecked(True)
    local_action.triggered.connect(lambda: self.switch_backend(BackendType.LOCAL))
    
    # 云端后端选项
    cloud_action = QAction("Use Cloud Workstation", self)
    cloud_action.setCheckable(True)
    cloud_action.triggered.connect(lambda: self.switch_backend(BackendType.CLOUD))
    
    # 添加到菜单
    backend_menu.addAction(local_action)
    backend_menu.addAction(cloud_action)
    
    # 互斥组
    backend_group = QActionGroup(self)
    backend_group.addAction(local_action)
    backend_group.addAction(cloud_action)
    
    # 配置云端
    backend_menu.addSeparator()
    config_action = QAction("Configure Cloud...", self)
    config_action.triggered.connect(self.configure_cloud)
    backend_menu.addAction(config_action)

def switch_backend(self, backend_type):
    """切换后端"""
    if backend_type != self.backend_type:
        self.backend_type = backend_type
        self.connect_backend()

def configure_cloud(self):
    """配置云端连接"""
    # 打开配置对话框
    # 这里可以创建一个简单的对话框让用户输入:
    # - API Endpoint
    # - API Key
    # - Timeout
    # 然后保存到 ~/.spinach_ui/cloud_config.json
    pass
```

## 第九步: 测试

1. 首先测试本地后端(默认):
   ```python
   python Multi_system_spinach_UI.py
   ```

2. 运行网络接口测试:
   ```bash
   python network_interface/test_network_interface.py
   ```

3. 如果要测试云端,需要先配置 `~/.spinach_ui/cloud_config.json`

## 完整示例: 最小修改

如果想最小化修改现有代码,只需:

1. 在 `__init__` 中添加:
   ```python
   self.backend = LocalBackend()
   self.backend.connect({})
   ```

2. 在运行仿真时,替换:
   ```python
   # 原来的代码:
   # result = spinach_eng.run_simulation(params)
   
   # 改为:
   task_id = self.backend.submit_simulation(params)
   result = self.backend.get_result(task_id)
   ```

这样就完成了基本集成,保持向后兼容!

## 注意事项

1. **本地后端是默认**: 如果不配置云端,系统会自动使用本地MATLAB
2. **云端需要配置**: 必须先配置 API endpoint 和密钥
3. **错误处理**: 添加适当的 try-except 块
4. **日志记录**: 使用现有的日志系统记录后端切换
5. **清理资源**: 在程序退出时调用 `self.backend.disconnect()`

## 下一步

- [ ] 实现云端配置对话框
- [ ] 添加任务历史查看器
- [ ] 实现任务进度条显示
- [ ] 添加任务取消功能
- [ ] 实现结果缓存和复用
