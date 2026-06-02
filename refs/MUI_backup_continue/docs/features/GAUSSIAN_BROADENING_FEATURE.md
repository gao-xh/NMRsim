# 高斯展宽功能 (Gaussian Line Broadening)

## 功能概述

添加了后处理高斯展宽功能，允许用户在不重新运行模拟的情况下调整谱线宽度。每个系统可以独立设置展宽参数。

## 实现方式

### 1. 数据结构扩展

每个系统(`self.systems[sys_name]`)新增字段：

```python
{
    'spec_raw': None,          # 原始未展宽的频谱
    'spec': None,              # 当前显示的频谱（可能已展宽）
    'broadening_fwhm': 0.0,    # 高斯展宽的半高全宽(FWHM)，单位Hz
    'broadening_enabled': False # 是否启用展宽
}
```

### 2. UI 控件位置

**位置**：每个系统的 System Tab → Basis Settings 之后

**组件**：
```
┌─ Line Broadening (Post-Processing) ────────────────┐
│ ☑ Enable Gaussian Broadening                      │
│                                                    │
│ FWHM: [━━━━━━━━━━━━] [1.0 Hz ▼] 【1.0 Hz】        │
│       滑块(0.1-50Hz)  数值框      显示标签         │
│                                                    │
│ 💡 Gaussian Broadening: Smooths spectral lines... │
└────────────────────────────────────────────────────┘
```

### 3. 核心算法

#### 高斯卷积函数

```python
def apply_gaussian_broadening(self, freq, spec, fwhm_hz):
    """
    在频域应用高斯展宽
    
    参数:
        freq: 频率数组 (Hz)
        spec: 复数频谱
        fwhm_hz: 半高全宽 (Hz)
    
    返回:
        展宽后的复数频谱
    """
    # FWHM → 标准差
    sigma = fwhm_hz / (2 * sqrt(2 * ln(2)))
    
    # 创建高斯核
    kernel_width = 3 * sigma  # 覆盖99.7%
    gaussian = exp(-x² / (2σ²))
    gaussian /= sum(gaussian)  # 归一化保持总强度
    
    # 分别对实部和虚部卷积
    spec_real = convolve(spec.real, gaussian)
    spec_imag = convolve(spec.imag, gaussian)
    
    return spec_real + i*spec_imag
```

**数学原理**：
- FWHM (半高全宽) = 2√(2ln2) × σ ≈ 2.355σ
- 高斯函数: G(x) = exp(-x²/(2σ²))
- 卷积保持总积分不变，只改变线形

### 4. 工作流程

#### 模拟完成时：
```
SimWorker.done → on_simulation_done()
  ├─ 保存原始频谱: spec_raw = spec
  ├─ 检查是否启用展宽
  │   ├─ 是: spec = apply_gaussian_broadening(spec_raw, fwhm)
  │   └─ 否: spec = spec_raw
  └─ 绘制图表
```

#### 调整展宽参数时：
```
用户拖动滑块/修改数值
  ├─ 更新 broadening_fwhm
  ├─ spec = apply_gaussian_broadening(spec_raw, fwhm)
  ├─ 更新当前系统图表
  └─ 更新加权和图表
```

## 控件说明

### Enable Checkbox
- **功能**: 启用/禁用展宽
- **启用时**: 对 `spec_raw` 应用高斯卷积，更新图表
- **禁用时**: 恢复原始频谱 `spec = spec_raw`

### FWHM Slider
- **范围**: 0.1 - 50.0 Hz
- **精度**: 0.1 Hz
- **内部存储**: 1-500 (×10)
- **实时更新**: 拖动时立即应用展宽并刷新图表

### FWHM SpinBox
- **范围**: 0.0 - 50.0 Hz
- **精度**: 0.1 Hz
- **后缀**: " Hz"
- **双向同步**: 与滑块保持同步

### Value Label
- **显示**: 当前 FWHM 值
- **样式**: 蓝色加粗，便于识别
- **更新**: 随滑块/数值框同步更新

## 优势特性

### ✅ 实时性
- **无需重新模拟**: 基于已有数据即时计算
- **即时反馈**: 滑块拖动时实时看到效果
- **快速测试**: 可以快速尝试不同展宽参数

### ✅ 独立性
- **每系统独立**: System 1 和 System 2 可以设置不同的展宽
- **不影响原始数据**: `spec_raw` 始终保持不变
- **可逆操作**: 关闭展宽立即恢复原始频谱

### ✅ 集成性
- **自动更新加权和**: 修改展宽后自动更新 Weighted Sum
- **保存/加载支持**: 展宽参数可与其他参数一起保存
- **兼容现有功能**: 与窗函数、显示模式等功能无冲突

## 物理意义

### 什么是展宽？
展宽模拟了真实NMR实验中的线形效果：
- **T2弛豫**: 横向弛豫时间越短，谱线越宽
- **场不均匀性**: 磁场不均匀导致线宽增加
- **分子动力学**: 化学交换、旋转等动态过程

### FWHM 参数选择

| FWHM (Hz) | 效果 | 适用场景 |
|-----------|------|---------|
| 0.1 - 1.0 | 轻微展宽 | 高分辨液体NMR |
| 1.0 - 5.0 | 中等展宽 | 典型液体NMR |
| 5.0 - 20.0 | 明显展宽 | 固体NMR、生物大分子 |
| 20.0 - 50.0 | 强烈展宽 | 去除噪声、快速弛豫体系 |

### 展宽 vs 窗函数

| 特性 | 窗函数 (时域) | 高斯展宽 (频域) |
|------|--------------|----------------|
| **应用时机** | 模拟时，FID信号 | 后处理，频谱数据 |
| **物理意义** | 模拟真实采集条件 | 后期美化/匹配实验 |
| **计算成本** | 需重新模拟 | 即时计算 |
| **可调性** | 低（需重新运行） | 高（实时调整） |
| **推荐用途** | 模拟真实仪器 | 可视化优化 |

## 使用示例

### 场景1：匹配实验线宽

```
1. 运行模拟 → 得到理想频谱
2. 启用 Gaussian Broadening
3. 调整 FWHM 滑块，观察线宽变化
4. 匹配实验谱线宽度 (如 FWHM = 3.5 Hz)
5. 导出或截图用于对比
```

### 场景2：多系统对比

```
System 1: 高分辨条件
  - Broadening: OFF (FWHM = 0)
  
System 2: 模拟低场仪器
  - Broadening: ON (FWHM = 15 Hz)
  
Weighted Sum: 混合效果
  - 自动包含两个系统的展宽
```

### 场景3：噪声抑制

```
原始频谱: 有尖锐噪声峰
  ↓
启用展宽: FWHM = 10 Hz
  ↓
结果: 噪声被平滑，真实信号保留
```

## 技术细节

### 卷积核大小
```python
kernel_half_width = ceil(3 * sigma / df)
kernel_size = 2 * kernel_half_width + 1
```
- **3σ 原则**: 覆盖高斯分布的 99.7%
- **自适应**: 根据频率分辨率 `df` 调整
- **性能优化**: 小核快速卷积

### 归一化
```python
gaussian /= gaussian.sum()
```
- **目的**: 保持总积分强度不变
- **效果**: 只改变线形，不改变峰面积

### 复数处理
```python
spec_real = convolve(spec.real, gaussian, mode='same')
spec_imag = convolve(spec.imag, gaussian, mode='same')
return spec_real + 1j * spec_imag
```
- **分离处理**: 实部和虚部独立卷积
- **mode='same'**: 保持数组长度不变
- **重新组合**: 合成复数频谱

## 注意事项

### ⚠️ 过度展宽
- **问题**: FWHM 过大会丢失精细结构
- **建议**: 从小值开始逐步增加
- **检查**: 确保关键峰仍可分辨

### ⚠️ 负频率
- **处理**: `plot_spectrum` 自动过滤负频率
- **展宽**: 在全频谱上进行，然后过滤
- **原因**: 避免边界效应

### ⚠️ 内存占用
- **存储**: 每个系统额外保存 `spec_raw`
- **影响**: 大型频谱（>10000点）略增内存
- **优化**: 可选择性保存（当前实现始终保存）

## 代码位置

| 功能 | 位置 | 说明 |
|------|------|------|
| 高斯卷积函数 | `apply_gaussian_broadening()` | 第2462行 |
| 启用/禁用回调 | `_on_broadening_enabled_changed()` | 第2210行 |
| 滑块回调 | `_on_broadening_slider_changed()` | 第2233行 |
| 数值框回调 | `_on_broadening_spinbox_changed()` | 第2248行 |
| 应用展宽 | `_apply_broadening_to_system()` | 第2263行 |
| UI创建 | `create_system_controls()` | 第1447-1507行 |
| 信号连接 | `_setup_broadening_connections()` | 第1580-1596行 |

## 未来改进

### 可能的增强功能

1. **多种展宽类型**
   - Lorentzian (洛伦兹型)
   - Voigt (高斯+洛伦兹混合)
   - 自定义核函数

2. **自动拟合**
   - 从实验谱自动估计 FWHM
   - 最小二乘拟合

3. **频率依赖展宽**
   - 不同频率区域不同 FWHM
   - 模拟场梯度效应

4. **预设库**
   - 常见仪器预设（如 "400 MHz Liquid", "600 MHz Solid"）
   - 一键应用

## 总结

高斯展宽功能提供了一个强大而灵活的后处理工具：
- ✅ 快速、实时、可逆
- ✅ 物理意义明确
- ✅ 每系统独立控制
- ✅ 与现有功能完美集成

这使得用户可以轻松地：
- 匹配实验条件
- 优化图表美观度
- 比较不同展宽效果
- 抑制噪声干扰

**推荐使用场景**: 任何需要调整谱线宽度、改善可视化效果或匹配实验数据的情况。
