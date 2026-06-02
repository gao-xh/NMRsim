import numpy as np
import scipy as sp
from scipy.linalg import expm
import matplotlib.pyplot as plt
from typing import List, Dict, Any  
from dataclasses import dataclass, field

import subprocess
import sys
from pathlib import Path

import src.utils.read_mol as rm


pi = np.pi

# env selection
def get_conda_env():
    env_name = "Simulaton312"
    conda_prefix = Path(subprocess.check_output("conda info --base", shell=True).decode().strip())
    python_exe = conda_prefix / "envs" / env_name / "python"

# Pauli operators
@dataclass(frozen=True)
class Pauli_Operator:
    P_x: np.ndarray = field(default_factory=lambda: np.array([[0, 1/2], [1/2, 0]]))
    P_y: np.ndarray = field(default_factory=lambda: np.array([[0, -1j/2], [1j/2, 0]]))
    P_z: np.ndarray = field(default_factory=lambda: np.array([[1/2, 0], [0, -1/2]]))
    unit: np.ndarray = field(default_factory=lambda: np.eye(2))

# Gamma dictionary
@dataclass(frozen=True)
class Gamma_Dict:
    G_13C: float = 10.71
    G_1H: float = 42.58
    G_15N: float = 60.86

# Spin quantum numbers
@dataclass(frozen=True)
class Spin_Quantum_Numbers:
    S_13C: float = 1/2
    S_1H: float = 1/2
    S_15N: float = -1/2

@dataclass
class system:
    isos: List[str]


    n: int = field(init=False)
    def __post_init__(self):
        self.n = len(self.isos)

@dataclass
class basis:
    # def __init__(self, system: system):
    #     self.system = system
    formalism: str
    symmetry_group: list[str]
    symmetry_spins: list[list[int]]

@dataclass
class interaction:
    # def __init__(self, system: system):
    #     self.system = system

    coupling: np.ndarray

@dataclass
class parameters:
    # sweep: float
    npoints: int
    zerofill: int
    zerofill1: int
    offset: float
    spins: list[str]
    sampling_rate: float = 1000.0
    time_step: float = field(init=False)
    t1_step: float = 1.7        # in ms
    Np1: int = 790

    def __post_init__(self):
        self.time_step = 1 / self.sampling_rate

@dataclass
class environment:
    magnetic_field: float = 0.0  # in mT

@dataclass
class pulse:
    shape: str
    duration: float # in microseconds
    Bx: float   # in microtesla
    By: float   # in microtesla
    Bz: float   # in microtesla
    # phase: float

# Tools for quantum operations
class qutools:
    def __init__(self):
        self.Pauli_Operator = Pauli_Operator()
        self.Gamma_Dict = Gamma_Dict()
    # Gamma array
    def gamma_array(self, nucleus: List[str]) -> np.ndarray:
        gamma_array = np.array([])
        for n in nucleus:
            if n == "13C":
                gamma_array = np.append(gamma_array, self.Gamma_Dict.G_13C)
            elif n == "1H":
                gamma_array = np.append(gamma_array, self.Gamma_Dict.G_1H)
            elif n == "15N":
                gamma_array = np.append(gamma_array, self.Gamma_Dict.G_15N)
            else:
                raise ValueError(f"Unknown nucleus: {n}")
        return gamma_array
    # Kronecker product by numpy
    def kron_all_np(self, *matrices: np.ndarray) -> np.ndarray:
        result = np.eye(1)
        for mat in matrices:
            result = np.kron(result, mat)
        return result
    
    # Kronecker product by scipy
    def kron_all_sp(self, *matrices: np.ndarray) -> np.ndarray:
        result = sp.eye(1)
        for mat in matrices:
            result = sp.kron(result, mat)
        return result

    # Choose method
    def kron_all(self, *matrices: np.ndarray, method: str = "numpy") -> np.ndarray:
        if method == "numpy":
            return self.kron_all_np(*matrices)
        elif method == "scipy":
            return self.kron_all_sp(*matrices)
        else:
            raise ValueError(f"Unknown method: {method}")

    # Build I matrices
    def I_x(self, n: int, method: str = "numpy") -> np.ndarray:
        Ix = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(n)]
        for i in range(n):
            Ix[i] = self.kron_all(*(Pauli_Operator().P_x if j == i else Pauli_Operator().unit for j in range(n)), method=method)
        return Ix

    def I_y(self, n: int, method: str = "numpy") -> np.ndarray:
        Iy = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(n)]
        for i in range(n):
            Iy[i] = self.kron_all(*(Pauli_Operator().P_y if j == i else Pauli_Operator().unit for j in range(n)), method=method)
        return Iy

    def I_z(self, n: int, method: str = "numpy") -> np.ndarray:
        Iz = [np.zeros((2**n, 2**n), dtype=complex) for _ in range(n)]
        for i in range(n):
            Iz[i] = self.kron_all(*(Pauli_Operator().P_z if j == i else Pauli_Operator().unit for j in range(n)), method=method)
        return Iz

    def focusiso(self, isos: List[str], focusiso: str) -> np.ndarray:
        if focusiso in isos:
            indices = [i for i, iso in enumerate(isos) if iso == focusiso]
            return indices
        else:
            raise ValueError(f"Unknown nucleus: {focusiso}")
        

# ---------- Calculation parts ----------

# Hamiltonian and propagation
class calculation:
    def __init__(self, system: system, interaction: interaction, parameters: parameters, environment: environment = environment()):
        self.qutools = qutools()
        self.Pauli_Operator = Pauli_Operator()

        self.isos = system.isos
        self.magnetic_field = environment.magnetic_field
        self.n = len(self.isos)
        self.gamma = self.qutools.gamma_array(self.isos)
        self.J = interaction.coupling

        self.Ix = self.qutools.I_x(len(self.isos))
        self.Iy = self.qutools.I_y(len(self.isos))
        self.Iz = self.qutools.I_z(len(self.isos))

        self.time_step = parameters.time_step

    def H_zemmen(self) -> np.ndarray:
        """Calculate the Zeeman Hamiltonian."""
        H = np.zeros((2**self.n, 2**self.n), dtype=complex)
        for i in range(self.n):
            H += 2*pi*self.gamma[i] * self.magnetic_field * self.Iz[i]
        return H

    def H_coupling(self) -> np.ndarray:
        H = np.zeros((2**self.n, 2**self.n), dtype=complex)
        for i in range(self.n):
            for j in range(i+1, self.n):
                H += 2*pi*self.J[i][j] * (self.Ix[i] @ self.Ix[j] + self.Iy[i] @ self.Iy[j] + self.Iz[i] @ self.Iz[j])
        return H

    def H_total(self) -> np.ndarray:
        H = self.H_zemmen() + self.H_coupling()
        return H

    def propagate(self) -> np.ndarray:
        H = self.H_total()
        P = expm(-1j * H * self.time_step)
        return P

    def pro_dagger(self, P: np.ndarray) -> np.ndarray:
        P_d = P.conj().T
        return P_d

# uncompleted
class operation:
    def __init__(self, system, interaction, parameters, pulse, environment: environment = environment()):
        self.qutools = qutools()
        self.Pauli_Operator = Pauli_Operator()
        self.calculation = calculation(system, interaction, parameters, environment)

        self.isos = system.isos
        self.n = len(self.isos)
        self.gamma = self.qutools.gamma_array(self.isos)
        self.J = interaction.coupling

        self.Ix = self.qutools.I_x(len(self.isos))
        self.Iy = self.qutools.I_y(len(self.isos))
        self.Iz = self.qutools.I_z(len(self.isos))        

        self.H = self.calculation.H_total()
        self.pulse = pulse

    def operator(self) -> np.ndarray:
        O = np.zeros_like(self.Iz[0], dtype=complex)
        for i in range(self.n):
            O += 2*pi*self.gamma[i] * self.Ix[i]
        return O

    def rho0(self) -> np.ndarray:
        rho = np.zeros_like(self.Iz[0], dtype=complex)
        for i in range(self.n):
            rho += 2*pi*self.gamma[i]*self.Ix[i]
        return rho

    def p_pulse(self):
        H_terms_pulse = []
        #Pulse Hamiltonian
        for o in range(len(self.isos)):
            H_terms_pulse.append(2*pi*self.gamma[o] * (self.pulse.Bx * self.Ix[o] + self.pulse.By * self.Iy[o] + self.pulse.Bz * self.Iz[o]))
        #Summing terms with original detection Hamiltonian
        H_glob_pulse = self.H + np.sum(H_terms_pulse, axis=0)
        # Time evolution operators
        t_evo_pulse = expm(-1j * H_glob_pulse * self.pulse.duration * 1e-6)
        # t_evo_dagg_pulse = t_evo_pulse.conj().T
        # rho = t_evo_pulse @ self.rho0() @ t_evo_dagg_pulse
        return (t_evo_pulse)
    
    def rho_pulse(self):
        t_evo_dagg_pulse = self.p_pulse().conj().T
        rho = self.p_pulse() @ self.rho0() @ t_evo_dagg_pulse
        return (rho)

# uncompleted
class simulation:
    def __init__(self, system, interaction, parameters, pulse):
        self.calculation = calculation
        self.qutools = qutools()
        self.Pauli_Operator = Pauli_Operator()

        self.system = system
        self.interaction = interaction
        self.parameters = parameters
        self.pulse = pulse

        self.isos = system.isos
        self.n = len(self.isos)
        self.gamma = self.qutools.gamma_array(self.isos)
        self.J = interaction.coupling

        self.Ix = self.qutools.I_x(len(self.isos))
        self.Iy = self.qutools.I_y(len(self.isos))
        self.Iz = self.qutools.I_z(len(self.isos)) 
        

        self.operation = operation
        # self.rho0 = self.operation.rho0()
        # self.rho = self.operation.rho_pulse()
        # self.pulse = self.operation.p_pulse()
        # self.coil = self.operation.operator()

        self.npoints = parameters.npoints
        self.time_step = parameters.time_step
        self.np1 = parameters.Np1
        self.t1_step = parameters.t1_step*1e-3



    def freq_domain(self, environment: environment = environment()) -> np.ndarray:
        H = self.calculation(self.system, self.interaction, self.parameters, environment).H_total()
        eigvals, eigvecs = np.linalg.eigh(H)
        f = np.zeros((len(eigvals), len(eigvals)), dtype=complex)

        rho = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment).rho_pulse()
        observer = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment).operator()
        rho_eig = eigvecs.conj().T @ rho @ eigvecs
        O_eig   = eigvecs.conj().T @ observer @ eigvecs
        weights = np.zeros((len(eigvals), len(eigvals)), dtype=complex)
        for i in range(len(eigvals)):
            for j in range(i+1, len(eigvals)):
                f[i, j] = np.abs(eigvals[j] - eigvals[i])/(2*pi)
                weights[i, j] = rho_eig[i, j] * O_eig[j, i]
                #weights = rho_eig @ O_eig

        #print(weights)
        idx = np.triu_indices_from(f, k=1)  # upper triangle without diagonal
        f_flat = f[idx]
        w_flat = weights[idx]
        # tol = 1e-6  # Hz
        # mask = np.abs(f_flat) > tol
        # f_flat, w_flat = f_flat[mask], w_flat[mask]
        return f_flat, w_flat

    def freq_domain2d(self, environment1: environment = environment(), environment2: environment = environment()) -> np.ndarray:
        H = self.calculation(self.system, self.interaction, self.parameters, environment1).H_total()
        eigvals, eigvecs = np.linalg.eigh(H)
        f = np.zeros((self.np1, len(eigvals)**2), dtype=complex)
        pulse = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).p_pulse()
        t_evo_dagg_pulse = pulse.conj().T
        rho = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).rho_pulse()
        observer = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment2).operator()
        t1_evo_1 = -1j * H * self.t1_step
        weights = np.zeros((self.np1, len(eigvals)**2), dtype=complex)

        for k in range(self.np1):
            t1_evo = expm(t1_evo_1 * k)
            t1_evo_dagg = t1_evo.conj().T
            rho1 = t1_evo @ rho @ t1_evo_dagg
            rho2 = pulse @ rho1 @ t_evo_dagg_pulse

            rho_eig = eigvecs.conj().T @ rho2 @ eigvecs
            O_eig   = eigvecs.conj().T @ observer @ eigvecs

            m = 0
            for i in range(len(eigvals)):
                for j in range(i+1, len(eigvals)):
                    f[k, m] = np.abs(eigvals[j] - eigvals[i])/(2*pi)
                    weights[k, m] = rho_eig[i, j] * O_eig[j, i]
                    m += 1
        return f, weights
    
    def freq_domain_2d(self, tol_hz: float = 0.0, min_weight: float = 1e-8, max_count: int = 100000):
        """
        Generator for 2D frequency domain stick spectrum, memory efficient.
        Yields (f1, f2, w) for each valid transition.
        """
        H = self.calculation(self.system, self.interaction, self.parameters).H_total()
        evals, V = np.linalg.eigh(H)
        two_pi = 2.0 * np.pi

        pulse = self.operation(self.system, self.interaction, self.parameters, self.pulse).p_pulse()
        coil = self.operation(self.system, self.interaction, self.parameters, self.pulse).operator()
        rho0 = self.operation(self.system, self.interaction, self.parameters, self.pulse).rho_pulse()

        Up   = V.conj().T @ pulse @ V
        Oe   = V.conj().T @ coil  @ V
        rho0 = V.conj().T @ rho0  @ V
        rho1 = Up @ rho0 @ Up.conj().T

        N = H.shape[0]
        count = 0
        for m in range(N):
            for n in range(N):
                if m == n:
                    continue
                f2 = abs(evals[m] - evals[n]) / two_pi
                if tol_hz > 0.0 and f2 <= tol_hz:
                    continue
                for a in range(N):
                    for b in range(N):
                        if a == b:
                            continue
                        f1 = abs(evals[a] - evals[b]) / two_pi
                        if tol_hz > 0.0 and f1 <= tol_hz:
                            continue
                        w = rho1[a, b] * Up[m, a] * Up[n, b].conj() * Oe[n, m]
                        if np.abs(w) > min_weight:
                            yield f1, f2, w
                            count += 1
                            if count >= max_count:
                                return
                            
    def freq_domain_2d_MQ(self, tol_hz: float = 0.0, min_weight: float = 1e-8, max_count: int = 100000):
        """
        2D stick-spectrum generator for MQ-ZULF:
        yields (f1, f2, weight) with MQ excitation U_exc = Px * exp(-i H tm) * Px and reconversion U_re = Px.
        """
        # --- system & diagonalization ---
        H = self.calculation(self.system, self.interaction, self.parameters).H_total()
        E, V = np.linalg.eigh(H)            # H = V E V^†
        two_pi = 2.0 * np.pi

        # --- operators in LAB basis ---
        Px_lab = self.operation(self.system, self.interaction, self.parameters, self.pulse).p_pulse()   # π on 13C
        Mdet_lab = self.operation(self.system, self.interaction, self.parameters, self.pulse).operator()# detection (Σγ I_z)
        rho0_lab = self.operation(self.system, self.interaction, self.parameters, self.pulse).rho_pulse()# initial (≈ Σγ I_z)

        # --- MQ excitation (π – tm – π) in LAB basis ---
        tm = self.t1_step  # in seconds
        Utm_lab  = expm(-1j * H * tm)
        Uexc_lab = Px_lab @ Utm_lab @ Px_lab
        Ure_lab  = Px_lab

        # state after excitation
        rho_exc_lab = Uexc_lab @ rho0_lab @ Uexc_lab.conj().T

        # --- transform everything to eigenbasis of H ---
        Vd = V.conj().T
        rho_e = Vd @ rho_exc_lab @ V
        Ure_e = Vd @ Ure_lab       @ V
        Mdet_e= Vd @ Mdet_lab      @ V

        N = H.shape[0]
        count = 0

        # loop over coherences created by excitation: (a,b), a != b  -> F1
        for a in range(N):
            for b in range(N):
                if a == b: continue
                f1 = abs(E[a] - E[b]) / two_pi
                if tol_hz > 0.0 and f1 <= tol_hz: continue
                rho_ab = rho_e[a, b]
                if abs(rho_ab) <= min_weight: continue

                # after reconversion U_re, this coherence contributes to observable (m,n), m!=n  -> F2
                # weight pathway:  rho_ab * Ure[m,a] * Ure[n,b]^* * Mdet[n,m]
                for m in range(N):
                    for n in range(N):
                        if m == n: continue
                        f2 = abs(E[m] - E[n]) / two_pi
                        if tol_hz > 0.0 and f2 <= tol_hz: continue
                        w = rho_ab * Ure_e[m, a] * np.conj(Ure_e[n, b]) * Mdet_e[n, m]
                        if np.abs(w) > min_weight:
                            yield f1, f2, w
                            count += 1
                            if count >= max_count:
                                return


    def fid(self, t2star: float = 1, environment: environment = environment()) -> np.ndarray:
        rho = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment).rho_pulse()
        observer = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment).operator()
        fid = np.zeros(self.npoints, dtype=complex)
        P = self.calculation(self.system, self.interaction, self.parameters, environment).propagate()
        P_d = self.calculation(self.system, self.interaction, self.parameters, environment).pro_dagger(P)
        for k in range(self.npoints):
            t = k * self.time_step
            decay = np.exp(-t / t2star)
            fid[k] = np.trace(rho @ observer) * decay
            rho = P @ rho @ P_d
        # fid = fid - np.mean(fid)  # Remove DC offset
        return fid

    def fid2d(self, t2star: float = 1, environment1: environment = environment(), environment2: environment = environment()) -> np.ndarray:
        H = self.calculation(self.system, self.interaction, self.parameters, environment1).H_total()

        rho = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).rho_pulse()
        observer = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment2).operator()
        pulse = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).p_pulse()
        t_evo_dagg_pulse = pulse.conj().T

        fid = np.zeros((self.np1, self.npoints), dtype=complex)
        P = self.calculation(self.system, self.interaction, self.parameters, environment2).propagate()
        P_d = self.calculation(self.system, self.interaction, self.parameters, environment2).pro_dagger(P)
        t1_evo_1 = -1j * H * self.t1_step

        # Initialize cumulative evolution operator
        t1_evo = np.eye(rho.shape[0], dtype=complex)  # identity matrix at t=0
        t1_step_evo = expm(t1_evo_1)  # single step evolution operator

        for i in range(self.np1):
            # Use cumulative evolution operator
            t1_evo_dagg = t1_evo.conj().T
            rho1 = t1_evo @ rho @ t1_evo_dagg
            rho2 = pulse @ rho1 @ t_evo_dagg_pulse
            for k in range(self.npoints):
                t = k * self.time_step
                decay = np.exp(-t / t2star)
                fid[i, k] = np.trace(rho2 @ observer) * decay
                rho2 = P @ rho2 @ P_d
            
            # Update cumulative evolution operator for next iteration
            t1_evo = t1_step_evo @ t1_evo
        # fid = fid - np.mean(fid)  # Remove DC offset
        return fid

    def fid2d_MQ(self, t2star: float = 1, tm: float = None, environment1: environment = environment(), environment2: environment = environment()) -> np.ndarray:
        H = self.calculation(self.system, self.interaction, self.parameters, environment1).H_total()
        
        rho0 = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).rho0()
        observer = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment2).operator()
        pulse = self.operation(self.system, self.interaction, self.parameters, self.pulse, environment1).p_pulse()
        t_evo_dagg_pulse = pulse.conj().T

        fid = np.zeros((self.np1, self.npoints), dtype=complex)
        P = self.calculation(self.system, self.interaction, self.parameters, environment2).propagate()
        P_d = self.calculation(self.system, self.interaction, self.parameters, environment2).pro_dagger(P)
        t1_evo_1 = -1j * H * self.t1_step

        # MQ excitation sequence: π - tm - π
        # If tm is not specified, use t1_step; otherwise use the provided tm
        if tm is None:
            tm_time = self.t1_step
        else:
            tm_time = tm * 1e-3  # convert ms to seconds
            
        tm_evo = expm(-1j * H * tm_time)  # evolution for tm period
        U_exc = pulse @ tm_evo @ pulse  # complete MQ excitation
        rho = U_exc @ rho0 @ U_exc.conj().T  # initial state after MQ excitation
        
        # Initialize cumulative evolution operator
        t1_evo = np.eye(rho.shape[0], dtype=complex)  # identity matrix at t=0
        t1_step_evo = expm(t1_evo_1)  # single step evolution operator
        
        for i in range(self.np1):
            # Use cumulative evolution operator
            t1_evo_dagg = t1_evo.conj().T
            rho1 = t1_evo @ rho @ t1_evo_dagg
            rho2 = pulse @ rho1 @ t_evo_dagg_pulse
            for k in range(self.npoints):
                t = k * self.time_step
                decay = np.exp(-t / t2star)
                fid[i, k] = np.trace(rho2 @ observer) * decay
                rho2 = P @ rho2 @ P_d
            
            # Update cumulative evolution operator for next iteration
            t1_evo = t1_step_evo @ t1_evo
        # fid = fid - np.mean(fid)  # Remove DC offset
        return fid

# uncompleted
class SignalProcessor:
    def __init__(self, system, interaction, parameters):
        self.qutools = qutools()

        # self.sweep = parameters.sweep
        self.time_step = parameters.time_step
        self.zerofill = parameters.zerofill
        self.npoints = parameters.npoints



    def apodisation(self, fid: np.ndarray, decay: float = 0.1) -> np.ndarray:
        n = len(fid)
        window = np.exp(-decay * np.linspace(0, 1, n))
        fid_win = fid*window
        fid_win[0] *= 0.5  # Half the first point
        
        # fid_win = fid_win - np.mean(fid_win)  # Remove DC offset
        return fid_win
    
    def apodisation2d(self, fid2d: np.ndarray, decay1: float = 0.1, decay2: float = 0.1) -> np.ndarray:
        n_t1, n_t2 = fid2d.shape
        window_t1 = np.exp(-decay1 * np.linspace(0, 1, n_t1))
        window_t2 = np.exp(-decay2 * np.linspace(0, 1, n_t2))
        window2d = np.outer(window_t1, window_t2)
        fid2d_win = fid2d * window2d
        fid2d_win[0, 0] *= 0.5  # 可选：首点减半
        return fid2d_win
    
    def fft(self, fid: np.ndarray, zerofill: int = None) -> np.ndarray:
        if zerofill is None:
            zerofill = len(fid)
        spectrum = np.fft.fftshift(np.fft.fft(fid, n=zerofill))/zerofill
        return spectrum

    def fft2d(self, fid, zerofill, zerofill1 = 256):
        spectrum = np.fft.fftshift(
            np.fft.fftshift(
                np.fft.fft(
                    np.fft.fft(fid, axis=0, n=zerofill1)/zerofill1, axis=1, n=zerofill
                )/zerofill, axes=1
            ), axes=0
        )
        return spectrum
    
    def freq(self, spectrum, dt):
        N = spectrum.size
        freq_axis = np.fft.fftshift(np.fft.fftfreq(N, d=dt))
        #freq_axis = freq_axis * sweep
        return freq_axis

    def freq2d(self, spectrum2d, dt1, dt2):
        n_t1, n_t2 = spectrum2d.shape
        freq1 = np.fft.fftshift(np.fft.fftfreq(n_t1, d=dt1))
        freq2 = np.fft.fftshift(np.fft.fftfreq(n_t2, d=dt2))
        return freq1, freq2