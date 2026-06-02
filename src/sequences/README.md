# `src/sequences/` — 序列目录

本包提供按名称组织的脉冲序列封装。每个序列签名统一为：

```python
seq(sys: SpinSystem, regime: Regime, acq: Acquisition, **kw) -> SimulationResult
```

下表列出当前已实现的所有序列。

| 实现的序列 | 函数 | 文件 | Bruker 名 | 简介 |
|---|---|---|---|---|
| 标准单脉冲采集 (1D pulse-acquire) | `pulse_acquire` | [`oneD.py`](oneD.py) | `zg` | 标准单脉冲采集。 |
| 异核去耦单脉冲采集 (1D with heteronuclear decoupling) | `pulse_acquire_decoupled` | [`oneD.py`](oneD.py) | `zgpg` / `zgig` | 理想 CW 异核去耦下的单脉冲采集。 |
| Hahn 自旋回波 (spin echo) | `spin_echo` | [`oneD.py`](oneD.py) | `hahnecho` | Hahn 自旋回波：90°x — τ — 180° — τ — acq。 |
| 反转恢复 T1 测量 (inversion recovery) | `inversion_recovery` | [`oneD.py`](oneD.py) | `t1ir` | 反转恢复 T1 测量：180°x — τ — 90°x — acq。 |
| CPMG 回波链 (Carr–Purcell–Meiboom–Gill) | `cpmg` | [`oneD.py`](oneD.py) | `cpmg` | CPMG 回波链：90°x — [τ — 180°y — τ]·n — acq。 |
| 异核单量子相关谱 (HSQC, 2D) | `hsqc` | [`hetcor.py`](hetcor.py) | `hsqcetgp` | 异核单量子相关 2D：INEPT — t1(180° obs refocus) — reverse INEPT — acq。 |
| 异核多键相关谱 (HMBC, 2D) | `hmbc` | [`hetcor.py`](hetcor.py) | `hmbcgplpndqf` | 异核多键 (long-range) 相关 2D：τ = 1/(4·nJ_CH)，其它与 HSQC 同构。 |
| 同核相关谱 (COSY-90, 2D) | `cosy` | [`homcor.py`](homcor.py) | `cosygpqf` / `cosy90` | 同核 2D 相关：90°φ₁ — t1 — 90°x — acq，对角峰与J 耦合交叉峰。 |
| 总相关谱 (TOCSY, 2D) | `tocsy` | [`homcor.py`](homcor.py) | `dipsi2etgpsi` / `mlevphpr` | 同一 J 网络内的全部相关（可跨单一键继接）；理想 isotropic mixing。 |

---

## 标准单脉冲采集 — `pulse_acquire` (`zg`)

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

## 异核去耦单脉冲采集 — `pulse_acquire_decoupled` (`zgpg` / `zgig`)

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

## Hahn 自旋回波 — `spin_echo` (`hahnecho`)

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

## 反转恢复 T1 测量 — `inversion_recovery` (`t1ir`)

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

## CPMG 回波链 — `cpmg` (`cpmg`)

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

---

## 异核单量子相关谱 — `hsqc` (`hsqcetgp`)

二维异核相关：F1 = 间接核（如 ¹³C）化学位移，F2 = 观测核（如 ¹H）。
骨架为 `INEPT — t1(中央 180° 观测核重聚) — reverse INEPT — acq`，t1
方向采用 States 超复数正交（两次 90°(indirect)：+x 给 cos 集，-y 给
sin 集），两套 FID 合成后做 2D FFT，得到纯吸收型 2D 谱。返回
`SimulationResult2D`（包含 `spectrum`、`freq_F1_Hz`、`freq_F2_Hz`、
`ppm_F1`、`ppm_F2`）。

**签名**
```python
hsqc(sys, regime, acq2d, *, indirect='13C', J_CH,
     decouple_during_acq=True) -> SimulationResult2D
```

**参数**
- `acq2d`：`Acquisition2D(t1=..., t2=...)`，分别控制间接维与直接维的
  采样（`dt`、`n_points`、零填充、apodization 等）。
- `indirect`：间接核同位素标签（默认 `'13C'`）。
- `J_CH`：观测核–间接核之间的单键 J（Hz）；决定 INEPT 时延
  `τ = 1/(4·J_CH)`。
- `decouple_during_acq`：若为 True（默认），t2 采集期间将观测核与间接核
  之间的 J 置零（理想 CW 去耦），每个交叉峰在 F2 上是单峰。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import hsqc

sys = SpinSystem(['1H','13C'], [4.0, 50.0], [[0, 140.0],[140.0, 0]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
acq2d = Acquisition2D(
    t1=Acquisition(n_points=64,  dt=1/16000, zero_fill=2, half_first=True),
    t2=Acquisition(n_points=1024, dt=1/6000,  zero_fill=2, half_first=True),
)

res = hsqc(sys, regime, acq2d, indirect='13C', J_CH=140.0)
# res.spectrum: (n_F1, n_F2) 复数 2D 谱；res.ppm_F1 / res.ppm_F2 用于绘图
```

---

## 异核多键相关谱 — `hmbc` (`hmbcgplpndqf`)

与 `hsqc` 同一骨架，仅把 INEPT 时延改为 `τ = 1/(4·J_long)` 以匹配长程
²J/³J_CH（典型 4–10 Hz）；用于检测非直接键合的远程相关峰。简化版本
未实现 low-pass J 滤波器，故 ¹J_CH 峰可能残留（当 ¹J 不接近 sin 零点
时）。`decouple_during_acq` 默认为 False，以保留 F2 上的 ¹J_CH 裂分
（与真实 HMBC 习惯一致）。

**签名**
```python
hmbc(sys, regime, acq2d, *, indirect='13C', J_long=8.0,
     decouple_during_acq=False) -> SimulationResult2D
```

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import hmbc

# 1H 4 ppm 既与 C-1 (1J=140) 又与 C-2 (2J=8) 耦合
J = np.zeros((3, 3))
J[0,1] = J[1,0] = 140.0; J[0,2] = J[2,0] = 8.0
sys = SpinSystem(['1H','13C','13C'], [4.0, 50.0, 100.0], J)
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
acq2d  = Acquisition2D(
    t1=Acquisition(n_points=128, dt=1/24000, zero_fill=2, half_first=True),
    t2=Acquisition(n_points=1024, dt=1/4000, zero_fill=2, half_first=True),
)

res = hmbc(sys, regime, acq2d, indirect='13C', J_long=8.0)
# 主峰位于 (4 ppm in F2, 100 ppm in F1) —— 长程相关
```

---

## 同核相关谱 — `cosy` (`cosygpqf` / `cosy90`)

二维同核相关：F1 = F2 = 观测核化学位移。骨架为
`90°φ₁(obs) — t1 — 90°x(obs) — acq`，以 States 超复数采集：
φ₁ = +π/2 (“y”) 给 cos 集，φ₁ = 0 (“x”) 给 sin 集。对角峰位于
(δᵢ, δᵢ)，交叉峰位于所有直接 J 耦合对。不包含轴峰过滤、双量子过滤
或梯度选的的太许多动作。

**签名**
```python
cosy(sys, regime, acq2d) -> SimulationResult2D
```

**调用示例**
```python
from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import cosy

sys = SpinSystem(['1H','1H'], [2.0, 4.0], [[0, 7.0], [7.0, 0]])
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
acq2d  = Acquisition2D(
    t1=Acquisition(n_points=64,  dt=1/6000, zero_fill=2, half_first=True,
                   apodization='exponential', lb_Hz=2.0, t2_star=0.4),
    t2=Acquisition(n_points=1024, dt=1/6000, zero_fill=2, half_first=True,
                   apodization='exponential', lb_Hz=2.0, t2_star=0.4),
)

res = cosy(sys, regime, acq2d)
# 对角峰 (2,2)、(4,4)；交叉峰 (2,4)、(4,2)
```

---

## 总相关谱 — `tocsy` (`dipsi2etgpsi` / `mlevphpr`)

与 `cosy` 同一超复数骨架，但将 t1 后的 90° 读出脉冲替换为 *理想 isotropic
mixing*：`U_mix = exp(-i · τ_m · H_iso)`，其中 `H_iso` 仅包含观测核内部
同核对的完整 `Ix·Ix + Iy·Iy + Iz·Iz` 项（实际上是 DIPSI / MLEV 的理想
极限）。高奏时 J 网络中跨多键中转连接的两个自旋之间也会出现交叉峰，
这是与 COSY 的关键区别。

**签名**
```python
tocsy(sys, regime, acq2d, *, mixing_time) -> SimulationResult2D
```

**参数**
- `mixing_time`：混合时间 τ_m（秒）；¹H TOCSY 常用 30–120 ms。

**调用示例**
```python
import numpy as np
from src.core import HF, Acquisition, Acquisition2D, SpinSystem
from src.sequences import tocsy

# A-M-X 链：J_AM = J_MX = 7 Hz, J_AX = 0
J = np.array([[0,7,0],[7,0,7],[0,7,0]])
sys = SpinSystem(['1H']*3, [1.0, 3.0, 5.0], J)
regime = HF(B0_T=9.4, observed='1H', carrier_ppm=0.0)
acq2d  = Acquisition2D(
    t1=Acquisition(n_points=96,  dt=1/6000, zero_fill=2, half_first=True,
                   apodization='exponential', lb_Hz=2.0, t2_star=0.4),
    t2=Acquisition(n_points=1024, dt=1/6000, zero_fill=2, half_first=True,
                   apodization='exponential', lb_Hz=2.0, t2_star=0.4),
)

res = tocsy(sys, regime, acq2d, mixing_time=0.080)
# 除 (1,3)、(3,5) 等直接交叉峰外，经 M 转接的 (1,5) / (5,1) 也会出现
```
