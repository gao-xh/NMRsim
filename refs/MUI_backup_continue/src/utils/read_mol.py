import os
import json
import csv
from dataclasses import dataclass, field    
from typing import List, Dict, Any  
import tkinter as tk
from tkinter import filedialog



@dataclass
class MoleculeData:
    name: str
    isotopes: List[str]  # e.g. ['1H', '13C', ...]
    J_coupling: List[List[float]]  # 2D matrix, e.g. [[0, 7.1], [7.1, 0]]
    symmetry_group: List[str] = None  
    symmetry_spins: List[List[int]] = None  
    information: str = None

def get_user_save_path() -> str:
    root = tk.Tk()
    root.withdraw() 
    user_save_path = filedialog.askdirectory(title="please select a folder")
    return user_save_path

def read_user_molecule(structure_path: str = None, symmetry_path: str = None) -> MoleculeData:
    """Read molecule structure and symmetry from user_save/molecules/NAME/ or any path, with input validation."""
    import warnings
    #USER_SAVE_PATH = filedialog.askdirectory(title="please select a folder")
    # Validate structure file
    if structure_path is None:
        user_save_path = get_user_save_path()
        folder = os.path.join(user_save_path)
        structure_path = os.path.join(folder, 'structure.csv')
        symmetry_path = os.path.join(folder, 'symmetry.csv')
        name = os.path.basename(folder)
    if not os.path.exists(structure_path):
        raise FileNotFoundError(f"Structure file not found: {structure_path}")
    with open(structure_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = [row for row in reader]
    if not rows or len(rows) < 2:
        raise ValueError("Structure file is empty or format error (at least one isotope row and one J matrix row required)")
    isotopes = rows[0]
    try:
        J_coupling = [list(map(float, row)) for row in rows[1:]]
    except Exception:
        raise ValueError("J coupling matrix format error, must be numeric")
    symmetry_group = []
    symmetry_spins = []
    if symmetry_path and os.path.exists(symmetry_path):
        with open(symmetry_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    group = row[0].strip()
                    spins = [int(x) for x in row[1].replace(',', ' ').split() if x.strip().isdigit()]
                    symmetry_group.append(group)
                    symmetry_spins.append(spins)
    else:
        warnings.warn(f"Symmetry file not found: {symmetry_path}")
    # Read information.txt
    information = None
    folder = os.path.join(user_save_path)
    info_path = os.path.join(folder, 'information.txt')
    if os.path.exists(info_path):
        with open(info_path, 'r', encoding='utf-8') as f:
            information = f.read()
    return MoleculeData(name=name, isotopes=isotopes, J_coupling=J_coupling, symmetry_group=symmetry_group, symmetry_spins=symmetry_spins, information=information)

