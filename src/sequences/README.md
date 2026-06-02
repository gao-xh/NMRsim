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
| `spin_echo` | [`oneD.py`](oneD.py) | `hahnecho` | Hahn 自旋回波：90°x — τ — 180° — τ — acq。 |
| `inversion_recovery` | [`oneD.py`](oneD.py) | `t1ir` | 反转恢复 T1 测量：180°x — τ — 90°x — acq。 |
| `cpmg` | [`oneD.py`](oneD.py) | `cpmg` | CPMG 回波链：90°x — [τ — 180°y — τ]·n — acq。 |

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

---

## `spin_echo` — Hahn 自旋回波 (`hahnecho`)

`90°x — τ — 180°φ — τ — acq`。化学位移在采集起点被重聚；标量耦合在 2τ
内继续演化（J 调制）。常用判据：AX 体系在 `2τ = 1/(2J)`（即 `τ = 1/(4J)`）
处变为反相多重峰（`|FID[0]| → 0`）。

**签名**
```python
spin_echo(sys, regime, acq, *, tau, pulse_phase_180=0.0) -> SimulationResult
```

**参数**
- `tau`：半回波时延，秒。总回波时间为 `2·tau`。
- `pulse_phase_180`：180° 脉冲的相位（弧度），默认 `0`（x 相）。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, SpinSystem
from src.sequences import spin_echo

sys = SpinSystem(['1H','1H'], [1.0, 3.0], [[0, 7.0], [7.0, 0]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
acq = Acquisition.from_sw_aq(SW_Hz=4800, AQ_s=2.0, t2_star=0.5, zero_fill=2)

r = spin_echo(sys, regime, acq, tau=1.0 / (4.0 * 7.0))  # 反相点
```

---

## `inversion_recovery` — 反转恢复 (`t1ir`)

`180°x — τ — 90°x — acq`。延迟 τ 期间施加按自旋的标量 T1 弛豫（依
`sys.T1`），用于扫描 τ 反演恢复曲线、拟合 T1。若 `sys.T1 is None`，τ
段不发生弛豫，所有 τ 都给出"完全反转"的信号。

**签名**
```python
inversion_recovery(sys, regime, acq, *, tau) -> SimulationResult
```

**参数**
- `tau`：恢复时延，秒。
- `sys.T1`：必须设置为长度 `N` 的数组（秒）；某项为 `None`/非正/`NaN`
  表示该自旋不弛豫。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, SpinSystem
from src.sequences import inversion_recovery

sys = SpinSystem(['1H'], [0.0], [[0.0]], T1=[0.7])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
acq = Acquisition.from_sw_aq(SW_Hz=4800, AQ_s=0.5, t2_star=0.3, zero_fill=2)

taus = np.array([0.05, 0.2, 0.5, 1.0, 2.0])
S = [inversion_recovery(sys, regime, acq, tau=t).fid[0].imag for t in taus]
# S(τ) = S_inf · (1 - 2·exp(-τ/T1))
```

---

## `cpmg` — CPMG 回波链 (`cpmg`)

`90°x — [τ — 180°y — τ]·n — acq`。默认 180° 脉冲取 y 相（标准 CPMG），
对小角度误差自校正。`n_echoes=0` 时退化为 `pulse_acquire`；`n_echoes=1`
等价于以 y 相 180° 的 `spin_echo`。

**签名**
```python
cpmg(sys, regime, acq, *, tau, n_echoes, pulse_phase_180=π/2) -> SimulationResult
```

**参数**
- `tau`：半回波间距，秒。采集前总耗时 `2·n_echoes·tau`。
- `n_echoes`：重聚脉冲个数（`>= 0`）。
- `pulse_phase_180`：180° 脉冲相位，默认 `π/2`（y 相）。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, SpinSystem
from src.sequences import cpmg

sys = SpinSystem(['1H','1H'], [1.0, 3.0], [[0, 7.0], [7.0, 0]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=2.0)
acq = Acquisition.from_sw_aq(SW_Hz=4800, AQ_s=2.0, t2_star=0.5, zero_fill=2)

r = cpmg(sys, regime, acq, tau=0.005, n_echoes=16)
```
