import os
import json
import csv

# Get project root directory (src/utils/ -> src/ -> root)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRESETS_PATH = os.path.join(ROOT_DIR, 'presets')
USER_SAVE_PATH = os.path.join(ROOT_DIR, 'user_save')
SPECTRUM_PATH = os.path.join(ROOT_DIR, 'spectrum')


from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any


@dataclass
class MoleculeData:
    name: str
    isotopes: List[str]  # e.g. ['1H', '13C', ...]
    J_coupling: List[List[float]]  # 2D matrix, e.g. [[0, 7.1], [7.1, 0]]
    symmetry_group: List[str] = None  
    symmetry_spins: List[List[int]] = None  
    information: str = None

@dataclass
class ParameterData:
    name: str
    params: Dict[str, Any]
    information: str = None

@dataclass
class SpectrumData:
    spectrum_name: str
    settings: Dict[str, Any]
    spectrum: List[List[Any]]  # 2D list, e.g. [[freq, intensity], ...]
    information: str = None

class SaveLoad:

    def read_preset_molecule(name: str, path: str = None) -> list:
        """Read a molecule CSV file from presets/molecules or any path, return as a 2D list."""
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                return [row for row in reader]
        else:
            path = os.path.join(PRESETS_PATH, 'molecules', f'{name}.csv')
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                return [row for row in reader]

    def read_preset_parameters(name: str, path: str = None) -> dict:
        """Read a parameter JSON file from presets/parameters or any path, return as a dict."""
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            path = os.path.join(PRESETS_PATH, 'parameters', f'{name}.json')
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

    def read_user_molecule(name: str, structure_path: str = None, symmetry_path: str = None) -> MoleculeData:
        """Read molecule structure and symmetry from user_save/molecules/NAME/ or any path, with input validation."""
        import warnings
        # Validate structure file
        if structure_path is None:
            folder = os.path.join(USER_SAVE_PATH, 'molecules', name)
            structure_path = os.path.join(folder, 'structure.csv')
            symmetry_path = os.path.join(folder, 'symmetry.csv')
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
        folder = os.path.join(USER_SAVE_PATH, 'molecules', name)
        info_path = os.path.join(folder, 'information.txt')
        if os.path.exists(info_path):
            with open(info_path, 'r', encoding='utf-8') as f:
                information = f.read()
        return MoleculeData(name=name, isotopes=isotopes, J_coupling=J_coupling, symmetry_group=symmetry_group, symmetry_spins=symmetry_spins, information=information)

    def save_user_molecule(mol: MoleculeData):
        """Save molecule structure and symmetry to user_save/molecules/NAME/"""
        folder = os.path.join(USER_SAVE_PATH, 'molecules', mol.name)
        os.makedirs(folder, exist_ok=True)
        # Structure
        structure_path = os.path.join(folder, 'structure.csv')
        with open(structure_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(mol.isotopes)
            writer.writerows(mol.J_coupling)
        # Symmetry
        symmetry_path = os.path.join(folder, 'symmetry.csv')
        with open(symmetry_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            if mol.symmetry_group and mol.symmetry_spins:
                for group, spins in zip(mol.symmetry_group, mol.symmetry_spins):
                    spins_str = ' '.join(str(s) for s in spins)
                    writer.writerow([group, spins_str])
        # Information
        if hasattr(mol, 'information') and mol.information:
            info_path = os.path.join(folder, 'information.txt')
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(mol.information)

    def read_user_parameters(name: str, path: str = None) -> dict:
        """Read a parameter JSON file from user_save/parameters or any path."""
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            path = os.path.join(USER_SAVE_PATH, 'parameters', f'{name}.json')
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

    def save_user_parameters(name: str, data: dict):
        """Save parameter dict to user_save/parameters."""
        path = os.path.join(USER_SAVE_PATH, 'parameters', f'{name}.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_spectrum(spectrum_name: str, setting: dict, spectrum_data: list, information: str = None):
        """Export settings (.json), spectrum data (.csv), and information.txt to a dedicated folder in spectrum/"""
        folder = os.path.join(SPECTRUM_PATH, spectrum_name)
        os.makedirs(folder, exist_ok=True)
        setting_path = os.path.join(folder, 'setting.json')
        spectrum_path = os.path.join(folder, 'spectrum.csv')
        with open(setting_path, 'w', encoding='utf-8') as f:
            json.dump(setting, f, ensure_ascii=False, indent=2)
        with open(spectrum_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(spectrum_data)
        if information:
            info_path = os.path.join(folder, 'information.txt')
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(information)

    def read_spectrum(spectrum_name: str, setting_path: str = None, spectrum_path: str = None) -> tuple:
        """Read settings, spectrum data, and information.txt from spectrum/SPECTRUM_NAME/ or any path. Returns (setting_dict, spectrum_list, information_str), with input validation."""
        import warnings
    # Validate paths
        if setting_path is None or spectrum_path is None:
            folder = os.path.join(SPECTRUM_PATH, spectrum_name)
            setting_path = os.path.join(folder, 'setting.json')
            spectrum_path = os.path.join(folder, 'spectrum.csv')
        if not os.path.exists(setting_path):
            raise FileNotFoundError(f"Spectrum settings file not found: {setting_path}")
        if not os.path.exists(spectrum_path):
            raise FileNotFoundError(f"Spectrum data file not found: {spectrum_path}")
        with open(setting_path, 'r', encoding='utf-8') as f:
            setting = json.load(f)
        with open(spectrum_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            spectrum = [row for row in reader]
        if not spectrum or len(spectrum) < 1:
            raise ValueError("Spectrum data file is empty or format error")
        # Optional: validate settings content
        if not isinstance(setting, dict) or len(setting) == 0:
            warnings.warn("Spectrum settings content is empty or format error")
        # Read information.txt if exists
        folder = os.path.dirname(setting_path)
        info_path = os.path.join(folder, 'information.txt')
        information = None
        if os.path.exists(info_path):
            with open(info_path, 'r', encoding='utf-8') as f:
                information = f.read()
        return setting, spectrum, information

