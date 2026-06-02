# 详细日志功能说明

## 更新日期
2025-10-08

## 功能概述
在 Multi-System ZULF-NMR Simulator 中添加了详细日志功能，提供两层日志输出：

### 1. 简洁日志（主窗口）
- 显示系统信息和运行状态
- 位置：主窗口底部的 "Log Output" 区域
- 内容：精简的状态更新和关键信息
- 示例：
  ```
  [15:54:58] [System 1] Starting simulation...
  [15:54:58] [System 1] Using formalism: zeeman-hilb, approximation: none
  [15:54:58] [System 1] Symmetry: 2 group(s), 8 spin(s)
  [15:54:58] [System 1] Simulation completed!
  ```

### 2. 详细日志（独立窗口）
- 显示完整的 MATLAB/Spinach 执行细节
- 点击 "📋 Detailed Logs" 按钮打开
- 内容：包括所有中间步骤、参数、矩阵信息等
- 特点：
  - 深色主题（类似 VS Code 终端）
  - 等宽字体（Consolas/Courier New）
  - 自动滚动选项
  - 清除日志按钮

## 代码改动

### 1. 移除了冗余的 DEBUG 日志
**修改位置**：`SimWorker.run()` 方法中的 symmetry 处理部分

**改动前**（冗余）：
```python
self.log.emit(f"[{self.system_name}] DEBUG - Received sym_group_name: ...")
self.log.emit(f"[{self.system_name}] DEBUG - Received sym_spins: ...")
self.log.emit(f"[{self.system_name}] Setting symmetry groups: ...")
self.log.emit(f"[{self.system_name}] DEBUG - Calling bas_obj.sym_group(...)")
self.log.emit(f"[{self.system_name}] Setting symmetry spins: ...")
self.log.emit(f"[{self.system_name}] DEBUG - Calling bas_obj.sym_spins(...)")
self.log.emit(f"[{self.system_name}] Symmetry optimization enabled")
```

**改动后**（简洁）：
```python
self.log.emit(f"[{self.system_name}] Symmetry: 2 group(s), 8 spin(s)")
```

同时，详细信息会发送到详细日志窗口：
```python
self.detailed_log.emit(f"Symmetry groups: {valid_groups}")
self.detailed_log.emit(f"Symmetry spins: {self.sym_spins}")
```

### 2. 新增类：DetailedLogWindow
**位置**：`Multi_system_spinach_UI.py` 第 430-480 行

**功能**：
- 独立窗口显示详细日志
- 自动滚动选项
- 清除日志按钮
- 深色主题 UI

### 3. 新增信号：detailed_log
**位置**：
- `SimWorker` 类：第 131 行
- `PostProcessWorker` 类：第 290 行

**用途**：
- 发送详细日志消息到 DetailedLogWindow

### 4. UI 改动
**位置**：`DualSystemWindow.setup_ui()` 方法

**改动**：
- 在 Log Output 区域添加了 "Detailed Logs" 按钮
- 按钮点击后打开详细日志窗口

**代码**：
```python
self.detailed_log_btn = QPushButton("Detailed Logs")
self.detailed_log_btn.setToolTip("Show detailed MATLAB/terminal output")
self.detailed_log_btn.clicked.connect(self.show_detailed_logs)
```

### 5. 新增方法
**位置**：`DualSystemWindow` 类

**方法**：
```python
def show_detailed_logs(self):
    """Show the detailed log window"""
    self.detailed_log_window.show()
    self.detailed_log_window.raise_()
    self.detailed_log_window.activateWindow()
```

### 6. Worker 连接
**位置**：`run_system()` 和 `reprocess_system()` 方法

**改动**：
```python
worker.log.connect(self.log)  # 简洁日志
worker.detailed_log.connect(self.detailed_log_window.append_log)  # 详细日志
```

## 详细日志内容示例

```
============================================================
[System 1] DETAILED SIMULATION LOG
============================================================
Isotopes: ['1H', '1H', '13C', '13C']
Magnet field: 0.0 T
Sweep: 200.0 Hz, Points: 512, Zerofill: 10000
J-matrix shape: (4, 4)
Initializing MATLAB engine...
MATLAB engine started successfully
Variable prefix: System_1_
Creating Spinach system object...
  → isotopes: ['1H', '1H', '13C', '13C']
  → magnet: 0.0 T
Creating basis object...
  → formalism: zeeman-hilb
  → approximation: none
Symmetry groups: ['S2', 'S2']
Symmetry spins: [[1, 2], [3, 4]]
Setting up interactions...
  → J-coupling matrix loaded: (4, 4)
Setting acquisition parameters...
  → sweep=200.0 Hz, npoints=512, zerofill=10000
Creating Spinach system and running simulation...
  → Spinach system created
  → Liquid-state simulation completed
Processing FID data...
  → Applying exp window (k=10)
Computing spectrum via FFT...
  → Spectrum computed: 10000 points
  → Frequency range: -100.00 to 100.00 Hz
============================================================
```

## 使用方法

1. **运行模拟**：正常使用软件，运行 System 1 或 System 2 的模拟
2. **查看简洁日志**：在主窗口底部的 Log Output 区域查看状态更新
2. **查看详细日志**：
   - 点击 Log Output 区域右上角的 "Detailed Logs" 按钮
   - 详细日志窗口会弹出，显示完整的执行过程
   - 可以勾选/取消 "Auto-scroll" 控制是否自动滚动
   - 点击 "Clear" 清除所有日志

## 技术细节

### 信号连接流程
```
SimWorker.run()
    ├── self.log.emit(简洁消息)
    │   └── → DualSystemWindow.log()
    │       ├── 显示在主窗口 log_text
    │       └── 同时发送到 detailed_log_window
    │
    └── self.detailed_log.emit(详细消息)
        └── → DetailedLogWindow.append_log()
            └── 仅显示在详细日志窗口
```

### 日志分类原则
- **简洁日志（log）**：系统状态、关键步骤、结果
- **详细日志（detailed_log）**：参数值、矩阵形状、中间步骤、调试信息

## 优势

1. **用户友好**：主界面保持简洁，不被大量日志淹没
2. **可调试性**：需要时可以查看完整的执行细节
3. **灵活性**：详细日志窗口可以独立移动、调整大小
4. **可维护性**：清晰的日志分层，便于未来添加更多详细信息

## 未来改进建议

1. **日志导出**：添加导出详细日志到文件的功能
2. **日志过滤**：按系统名称、日志级别过滤
3. **MATLAB 输出捕获**：直接捕获 MATLAB stdout/stderr（需要修改 spinach_bridge）
4. **日志搜索**：在详细日志窗口中添加搜索功能
5. **颜色高亮**：不同类型的消息使用不同颜色（错误红色、警告黄色等）
