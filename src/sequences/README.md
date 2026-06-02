# `src/sequences/` — 序列目录

本包提供按名称组织的脉冲序列封装。每个序列签名统一为：

```python
seq(sys: SpinSystem, regime: Regime, acq: Acquisition, **kw) -> SimulationResult
```

下表列出当前已实现的所有序列。

| 序列 | 文件 | Bruker 名 | 简介 |
|---|---|---|---|
| `pulse_acquire` | [`oneD.py`](oneD.py) | `zg` | 标准单脉冲采集。 |
| `pulse_acquire_decoupled` | [`oneD.py`](oneD.py) | `zgpg` / `zgig` | 理想 CW 异核去耦下的单脉冲采集。 |

---

## `pulse_acquire` — 标准 1D 采集 (`zg`)

执行 `regime` 默认的脉冲-采集流程（HF 下等价于 90°x — acq）。

**签名**
```python
pulse_acquire(sys, regime, acq) -> SimulationResult
```

**调用示例**
```python
from src.core import HF, Acquisition, SpinSystem
from src.sequences import pulse_acquire

sys = SpinSystem(['1H','1H'], [1.0, 3.7], [[0,7],[7,0]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
acq = Acquisition.from_sw_aq(SW_Hz=4800, AQ_s=2.0, t2_star=0.5, zero_fill=2)

result = pulse_acquire(sys, regime, acq)
# result.fid, result.freq_Hz, result.spectrum, result.ppm
```

---

## `pulse_acquire_decoupled` — 异核去耦采集 (`zgpg` / `zgig`)

模拟理想（无限带宽、无残余裂分）的连续波异核去耦：把 `regime.observed`
与所有被去耦核之间的标量耦合在整个实验里置零。观测核内部的同核耦合保留。

**签名**
```python
pulse_acquire_decoupled(sys, regime, acq, *, decouple=None) -> SimulationResult
```

**参数**
- `decouple`
  - `None`（默认）：对所有非观测核去耦（最常见，例如 `¹³C{¹H}`）。
  - 字符串，例如 `'1H'`：只对该核去耦。
  - 字符串可迭代对象，例如 `('1H', '19F')`：对列出的多核去耦。
- `regime` 必须有 `observed`（HF 之类）；否则抛 `ValueError`。
- 不能去耦观测核自身。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, SpinSystem
from src.sequences import pulse_acquire_decoupled

# 丙酮甲基: 1×¹³C 与 3×¹H, 1J_CH = 125 Hz
J = np.zeros((4, 4)); J[0, 1:] = 125.0; J[1:, 0] = 125.0
sys = SpinSystem(['13C','1H','1H','1H'], [30, 2.1, 2.1, 2.1], J)

regime = HF(B0_T=9.4, observed='13C', carrier_ppm=100.0)
acq = Acquisition.from_sw_aq(SW_Hz=24000, AQ_s=1.0, t2_star=0.2, zero_fill=2)

result = pulse_acquire_decoupled(sys, regime, acq)                # 默认去耦所有 ¹H
result = pulse_acquire_decoupled(sys, regime, acq, decouple='1H') # 等价显式写法
```
