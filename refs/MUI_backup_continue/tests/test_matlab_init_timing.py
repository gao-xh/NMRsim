"""
Test script to measure MATLAB initialization timing
Captures terminal output and timestamps for each step
"""

import sys
import os
import time
import io
from contextlib import redirect_stdout, redirect_stderr

# Add project to path
parent_dir = os.path.dirname(os.path.abspath(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

class TimingCapture:
    """Capture output and timing information"""
    def __init__(self):
        self.events = []
        self.start_time = None
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
    
    def start(self):
        """Start timing"""
        self.start_time = time.time()
        self.log_event("START", "Initialization started")
    
    def log_event(self, event_type, message):
        """Log an event with timestamp"""
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed = time.time() - self.start_time
        self.events.append({
            'elapsed': elapsed,
            'type': event_type,
            'message': message
        })
        print(f"[{elapsed:6.2f}s] {event_type}: {message}")
    
    def get_percentage(self, elapsed):
        """Estimate percentage based on elapsed time"""
        # This will be adjusted after we know total time
        return min(100, (elapsed / 20.0) * 100)  # Assume ~20s total
    
    def print_summary(self):
        """Print timing summary"""
        print("\n" + "="*80)
        print("TIMING SUMMARY")
        print("="*80)
        
        total_time = self.events[-1]['elapsed'] if self.events else 0
        
        for event in self.events:
            elapsed = event['elapsed']
            percent = (elapsed / total_time * 100) if total_time > 0 else 0
            print(f"{elapsed:6.2f}s ({percent:5.1f}%) - {event['type']}: {event['message']}")
        
        print(f"\nTotal time: {total_time:.2f}s")
        print("="*80)
        
        # Suggest progress bar breakpoints
        print("\nSUGGESTED PROGRESS BAR BREAKPOINTS (30-90%):")
        print("-"*80)
        
        # Map to 30-90% range (60% total)
        for event in self.events[1:]:  # Skip START event
            elapsed = event['elapsed']
            # Map to 30-90% range
            progress_percent = 30 + (elapsed / total_time * 60)
            print(f"{progress_percent:5.1f}% - {event['message']}")
        
        print("-"*80)


def run_matlab_initialization():
    """Run MATLAB initialization and capture timing"""
    
    timer = TimingCapture()
    timer.start()
    
    try:
        # Step 1: Import modules
        timer.log_event("IMPORT", "Importing spinach_bridge modules")
        from src.core.spinach_bridge import (
            spinach_eng, call_spinach, 
            sys as SYS, bas as BAS, inter as INTER, sim as SIM
        )
        
        # Step 2: Start MATLAB engine
        timer.log_event("ENGINE_START", "Starting MATLAB engine")
        engine_cm = spinach_eng(clean=True)
        eng = engine_cm.__enter__()
        call_spinach.default_eng = eng
        timer.log_event("ENGINE_READY", "MATLAB engine ready")
        
        # Step 3: Create system objects
        timer.log_event("SYS_CREATE", "Creating system object")
        sys_obj = SYS()
        
        timer.log_event("SYS_ISOTOPES", "Setting isotopes ['1H', '1H']")
        sys_obj.isotopes(['1H', '1H'])
        
        timer.log_event("SYS_MAGNET", "Setting magnet field 14.1T")
        sys_obj.magnet(14.1)
        
        # Step 4: Create basis objects
        timer.log_event("BAS_CREATE", "Creating basis object")
        bas_obj = BAS()
        
        timer.log_event("BAS_FORMALISM", "Setting formalism 'sphten-liouv'")
        bas_obj.formalism('sphten-liouv')
        
        timer.log_event("BAS_APPROX", "Setting approximation 'none'")
        bas_obj.approximation('none')
        
        # Step 5: Create interactions
        timer.log_event("INTER_CREATE", "Creating interactions object")
        inter_obj = INTER()
        
        timer.log_event("INTER_ZEEMAN", "Setting Zeeman interactions")
        inter_obj.zeeman([0.0, 0.0])
        
        timer.log_event("INTER_COUPLING", "Setting J-coupling matrix")
        import numpy as np
        J_matrix = np.array([[0.0, 7.0],
                             [7.0, 0.0]])
        inter_obj.coupling_array(J_matrix)
        
        # Step 6: Create spin system (most time-consuming)
        timer.log_event("SIM_CREATE_START", "Creating SIM object")
        sim_obj = SIM()
        
        timer.log_event("SIM_CREATE_CALL", "Calling sim.create() [this will take time]")
        sim_obj.create()  # This calls create(sys, inter) and basis(spin_system, bas)
        timer.log_event("SIM_CREATE_DONE", "sim.create() completed")
        
        # Cleanup
        timer.log_event("CLEANUP", "Cleaning up")
        engine_cm.__exit__(None, None, None)
        timer.log_event("END", "Initialization completed successfully")
        
        # Print summary
        timer.print_summary()
        
        return timer.events
        
    except Exception as e:
        timer.log_event("ERROR", f"Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        timer.print_summary()
        return timer.events


if __name__ == "__main__":
    print("="*80)
    print("MATLAB INITIALIZATION TIMING TEST")
    print("="*80)
    print("\nThis will run a complete MATLAB initialization and measure timing.")
    print("Please wait...\n")
    
    events = run_matlab_initialization()
    
    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
    
    # Export timing data
    print("\nExporting timing data to 'matlab_init_timing.txt'...")
    with open('matlab_init_timing.txt', 'w', encoding='utf-8') as f:
        f.write("MATLAB Initialization Timing Data\n")
        f.write("="*80 + "\n\n")
        
        for event in events:
            f.write(f"{event['elapsed']:6.2f}s - {event['type']}: {event['message']}\n")
        
        total_time = events[-1]['elapsed'] if events else 0
        f.write(f"\nTotal time: {total_time:.2f}s\n")
        
        # Progress mapping for 30-90% range
        f.write("\n" + "="*80 + "\n")
        f.write("PROGRESS MAPPING (30-90% range, 60% total)\n")
        f.write("="*80 + "\n")
        
        for event in events[1:]:
            elapsed = event['elapsed']
            progress = 30 + (elapsed / total_time * 60)
            f.write(f"{progress:5.1f}% at {elapsed:6.2f}s - {event['message']}\n")
    
    print("[OK] Timing data saved to 'matlab_init_timing.txt'")
    print("\nYou can now use this data to design accurate progress bar updates.")
