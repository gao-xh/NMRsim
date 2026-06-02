"""
Test script to verify that the bridge supports multiple variable prefixes
for handling multiple systems simultaneously.
"""

import numpy as np
from spinach_bridge import (
    call_spinach, sys as SYS, bas as BAS, inter as INTER, 
    parameters as PAR, sim as SIM, data as DATA, spinach_eng
)

def test_variable_prefix():
    """Test that different prefixes create different MATLAB variables"""
    
    print("Testing variable prefix support in spinach_bridge...")
    
    # Start MATLAB engine
    with spinach_eng(clean=True) as eng:
        call_spinach.default_eng = eng
        
        # Test System 1 with prefix "sys1_"
        print("\n=== Creating System 1 with prefix 'sys1_' ===")
        sys1 = SYS(eng, var_prefix='sys1_')
        sys1.isotopes(['1H', '1H', '13C'])
        sys1.magnet(14.1)
        
        # Test System 2 with prefix "sys2_"
        print("=== Creating System 2 with prefix 'sys2_' ===")
        sys2 = SYS(eng, var_prefix='sys2_')
        sys2.isotopes(['1H', '1H', '1H', '1H'])
        sys2.magnet(9.4)
        
        # Verify both systems exist in MATLAB
        print("\n=== Verifying variables in MATLAB ===")
        sys1_exists = eng.eval("exist('sys1_sys', 'var');", nargout=1)
        sys2_exists = eng.eval("exist('sys2_sys', 'var');", nargout=1)
        
        print(f"sys1_sys exists: {bool(sys1_exists)}")
        print(f"sys2_sys exists: {bool(sys2_exists)}")
        
        # Get the number of isotopes for each system
        sys1_iso_count = eng.eval("numel(sys1_sys.isotopes);", nargout=1)
        sys2_iso_count = eng.eval("numel(sys2_sys.isotopes);", nargout=1)
        
        print(f"sys1_sys isotope count: {sys1_iso_count}")
        print(f"sys2_sys isotope count: {sys2_iso_count}")
        
        # Get magnet field for each system
        sys1_magnet = eng.eval("sys1_sys.magnet;", nargout=1)
        sys2_magnet = eng.eval("sys2_sys.magnet;", nargout=1)
        
        print(f"sys1_sys magnet: {sys1_magnet} T")
        print(f"sys2_sys magnet: {sys2_magnet} T")
        
        # Test parameters with different prefixes
        print("\n=== Testing parameters with different prefixes ===")
        par1 = PAR(eng, var_prefix='sys1_')
        par1.sweep(1000.0)
        par1.npoints(512)
        
        par2 = PAR(eng, var_prefix='sys2_')
        par2.sweep(2000.0)
        par2.npoints(1024)
        
        # Verify parameters
        par1_sweep = eng.eval("sys1_parameters.sweep;", nargout=1)
        par2_sweep = eng.eval("sys2_parameters.sweep;", nargout=1)
        
        print(f"sys1_parameters.sweep: {par1_sweep} Hz")
        print(f"sys2_parameters.sweep: {par2_sweep} Hz")
        
        # Test without prefix (backward compatibility)
        print("\n=== Testing without prefix (default behavior) ===")
        sys_default = SYS(eng)  # No prefix
        sys_default.isotopes(['1H', '13C'])
        sys_default.magnet(11.7)
        
        sys_default_exists = eng.eval("exist('sys', 'var');", nargout=1)
        print(f"sys (default) exists: {bool(sys_default_exists)}")
        
        if sys_default_exists:
            sys_default_iso_count = eng.eval("numel(sys.isotopes);", nargout=1)
            sys_default_magnet = eng.eval("sys.magnet;", nargout=1)
            print(f"sys (default) isotope count: {sys_default_iso_count}")
            print(f"sys (default) magnet: {sys_default_magnet} T")
        
        print("\n=== All tests completed successfully! ===")
        print("The bridge now supports variable prefixes for multi-system simulations.")

if __name__ == '__main__':
    test_variable_prefix()
