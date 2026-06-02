# 变量名前缀快速参考

## 快速开始

### 在 Python 脚本中使用

```python
from spinach_bridge import sys as SYS, bas as BAS, spinach_eng

with spinach_eng() as eng:
    # 创建系统 1（带前缀）
    sys1 = SYS(eng, var_prefix='sys1_')
    sys1.isotopes(['1H', '13C'])
    sys1.magnet(14.1)
    
    # 创建系统 2（带前缀）
    sys2 = SYS(eng, var_prefix='sys2_')
    sys2.isotopes(['1H', '1H', '1H'])
    sys2.magnet(9.4)
    
    # 两个系统的数据完全独立！
```

### 在 UI 中使用

**无需任何操作！** UI 会自动处理：
- System 1 自动使用 `System_1_` 前缀
- System 2 自动使用 `System_2_` 前缀

## API 参考

### 所有类的构造函数

```python
# 基类
obj = call_spinach(eng=None, var_prefix='')

# 系统配置类
sys_obj = sys(eng=None, var_prefix='')
bas_obj = bas(eng=None, var_prefix='')
par_obj = parameters(eng=None, var_prefix='')
inter_obj = inter(eng=None, var_prefix='')

# 模拟和数据类
sim_obj = sim(eng=None, var_prefix='')
data_obj = data(eng=None, var_prefix='')
```

### 参数说明

- `eng`: MATLAB 引擎对象（默认使用 `call_spinach.default_eng`）
- `var_prefix`: 变量名前缀（默认为空字符串 `''`）

## MATLAB 变量映射

### 不使用前缀（默认）

```python
sys_obj = SYS(eng)
```

MATLAB 变量：
```
sys
bas
parameters
inter
spin_system
fid
fid_apod
spec
```

### 使用前缀 'my_'

```python
sys_obj = SYS(eng, var_prefix='my_')
```

MATLAB 变量：
```
my_sys
my_bas
my_parameters
my_inter
my_spin_system
my_fid
my_fid_apod
my_spec
```

## 常见用例

### 用例 1: 比较两个分子

```python
# 分子 A
sys_a = SYS(eng, var_prefix='molA_')
bas_a = BAS(eng, var_prefix='molA_')
# ... 设置并运行模拟 ...

# 分子 B
sys_b = SYS(eng, var_prefix='molB_')
bas_b = BAS(eng, var_prefix='molB_')
# ... 设置并运行模拟 ...
```

### 用例 2: 参数扫描

```python
results = []
for i, magnet_field in enumerate([9.4, 11.7, 14.1]):
    prefix = f'scan{i}_'
    sys_obj = SYS(eng, var_prefix=prefix)
    sys_obj.magnet(magnet_field)
    # ... 运行模拟并保存结果 ...
    results.append(spectrum)
```

### 用例 3: 向后兼容（单系统）

```python
# 不需要前缀时，可以省略该参数
sys_obj = SYS(eng)
bas_obj = BAS(eng)
# ... 与之前的代码完全相同 ...
```

## 注意事项

### ✅ 推荐做法

1. 所有相关对象使用**相同的前缀**
   ```python
   prefix = 'sys1_'
   sys_obj = SYS(eng, var_prefix=prefix)
   bas_obj = BAS(eng, var_prefix=prefix)
   inter_obj = INTER(eng, var_prefix=prefix)
   # 保持一致！
   ```

2. 使用**有意义**的前缀名称
   ```python
   var_prefix='ethanol_'  # ✅ 好
   var_prefix='sys1_'     # ✅ 好
   var_prefix='x_'        # ❌ 不够清晰
   ```

3. 前缀以**下划线结尾**（推荐）
   ```python
   var_prefix='system_'   # ✅ 推荐
   var_prefix='system'    # ⚠️ 可以但不推荐
   ```

### ❌ 避免的做法

1. 不要混用前缀
   ```python
   # ❌ 错误：同一系统使用不同前缀
   sys_obj = SYS(eng, var_prefix='sys1_')
   bas_obj = BAS(eng, var_prefix='sys2_')  # 错！
   ```

2. 不要使用 MATLAB 保留字
   ```python
   # ❌ 避免使用 MATLAB 保留字作为前缀
   var_prefix='for_'      # 不推荐
   var_prefix='function_' # 不推荐
   ```

## 调试技巧

### 检查 MATLAB 工作空间

```python
# 在 Python 中
eng.eval("whos", nargout=0)  # 显示所有变量

# 检查特定前缀的变量
eng.eval("whos sys1_*", nargout=0)
```

### 验证变量存在

```python
exists = bool(eng.eval("exist('sys1_sys', 'var');", nargout=1))
print(f"sys1_sys exists: {exists}")
```

### 清理特定系统的变量

```python
# 清理 sys1_ 开头的所有变量
eng.eval("clear sys1_*", nargout=0)
```

## 更多信息

- 📖 详细文档: `BRIDGE_VAR_PREFIX_README.md`
- 🧪 测试脚本: `test_bridge_variables.py`
- 📝 示例代码: `example_multi_system.py`
- 📋 修改总结: `MODIFICATION_SUMMARY.md`
