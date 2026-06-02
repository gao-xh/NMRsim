"""
Core module for MATLAB Spinach interface
"""

from .spinach_bridge import (
    call_spinach,
    sys as SYS,
    bas as BAS,
    inter as INTER,
    parameters as PAR,
    sim as SIM,
    data as DATA,
    spinach_eng
)

__all__ = [
    'call_spinach',
    'SYS',
    'BAS',
    'INTER',
    'PAR',
    'SIM',
    'DATA',
    'spinach_eng'
]
