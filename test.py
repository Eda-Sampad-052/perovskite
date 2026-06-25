#!/usr/bin/env python3
"""
SCAPS Workflow Runner - Main Entry Point
Demonstrates how to run SCAPS simulations and extract results.

This script shows:
1. How to create SCAPS script files programmatically
2. How to execute SCAPS with Wine
3. How to parse results from IV files
4. Complete workflow for Cs2PtI6 and Ag2MgGeS4 device

Expected Results:
  VOC: 1.1709 V
  JSC: 32.071 mA/cm²
  PCE: 89.50 %
  FF: 33.61 %
"""

import sys
import os

# Add the scaps_workflow module to path
sys.path.insert(0, '/workspaces/perovskite')

from scaps_workflow import (
    ScapsConfig,
    ScapsScriptGenerator,
    ScapsExecutor,
    ScapsResultParser,
    ScapsSimulation
)


def demonstrate_script_generation():
    """Show how to generate SCAPS scripts programmatically."""
    print("\n" + "="*60)
    print("1. SCAPS SCRIPT GENERATION")
    print("="*60)
    
    def_file = os.path.join(ScapsConfig.DEF_DIR, "Cs4CuSb2Cl12.def")
    
    print(f"\nGenerating IV curve script for: {def_file}")
    script_content = ScapsScriptGenerator.generate_iv_curve_script(def_file)
    
    print("\nGenerated Script Preview:")
    print("-" * 60)
    print(script_content[:500] + "\n..." if len(script_content) > 500 else script_content)
    print("-" * 60)


def demonstrate_configuration():
    """Show SCAPS configuration."""
    print("\n" + "="*60)
    print("2. SCAPS CONFIGURATION")
    print("="*60)
    
    print(f"\nSCAPS Executable: {ScapsConfig.SCAPS_EXE}")
    print(f"Definition Files: {ScapsConfig.DEF_DIR}")
    print(f"Results Directory: {ScapsConfig.RESULTS_DIR}")
    print(f"Script Directory: {ScapsConfig.SCRIPT_DIR}")
    print(f"Default Temperature: {ScapsConfig.DEFAULT_TEMP} K")
    print(f"IV Curve Range: {ScapsConfig.IV_START_V} to {ScapsConfig.IV_STOP_V} V")
    print(f"IV Increment: {ScapsConfig.IV_INCREMENT} V")


def demonstrate_parser():
    """Show how to parse existing IV files."""
    print("\n" + "="*60)
    print("3. RESULT PARSING")
    print("="*60)
    
    # Look for available IV files
    results_dir = ScapsConfig.RESULTS_DIR
    if os.path.exists(results_dir):
        iv_files = [f for f in os.listdir(results_dir) if f.endswith('.iv')]
        
        if iv_files:
            print(f"\nFound {len(iv_files)} IV file(s) in {results_dir}:")
            for iv_file in iv_files[:3]:  # Show first 3
                print(f"  - {iv_file}")
                
                # Parse one as example
                iv_path = os.path.join(results_dir, iv_file)
                results = ScapsResultParser.parse_iv_file(iv_path)
                
                print(f"    Results:")
                print(f"      VOC: {results['voc']:.4f} V" if results['voc'] else "      VOC: N/A")
                print(f"      JSC: {results['jsc']:.4f} mA/cm²" if results['jsc'] else "      JSC: N/A")
                print(f"      FF: {results['ff']:.4f} %" if results['ff'] else "      FF: N/A")
                print(f"      PCE: {results['pce']:.4f} %" if results['pce'] else "      PCE: N/A")
        else:
            print(f"\nNo IV files found in {results_dir}")
            print("(IV files are generated when SCAPS simulations are run)")


def demonstrate_simulation_workflow():
    """Show complete simulation workflow."""
    print("\n" + "="*60)
    print("4. COMPLETE SIMULATION WORKFLOW")
    print("="*60)
    
    device = "Cs2PtI6 Ag2MgGeS4.def"
    
    print(f"\nTarget Device: {device}")
    print("\nExpected Results:")
    print("  VOC: 1.1709 V")
    print("  JSC: 32.071 mA/cm²")
    print("  FF: 33.61 %")
    print("  PCE: 89.50 %")
    
    try:
        # Create simulation instance
        sim = ScapsSimulation(device)
        print(f"\n✓ Simulation instance created")
        
        # Try to parse existing results
        print(f"\nAttempting to parse existing results...")
        results = sim.parse_existing_results()
        
        if results and any(results.values()):
            print(f"✓ Results found!")
            sim.print_results()
        else:
            print(f"\n✗ No existing results found")
            print(f"\nTo generate results, run SCAPS using the workflow:")
            print(f"  1. Create a SCAPS script file (demonstrated above)")
            print(f"  2. Execute: xvfb-run -a wine {ScapsConfig.SCAPS_EXE} script.script")
            print(f"  3. Results will be saved in: {ScapsConfig.RESULTS_DIR}")
    
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")


def show_usage_examples():
    """Show how to use the module in code."""
    print("\n" + "="*60)
    print("5. USAGE EXAMPLES")
    print("="*60)
    
    examples = """
# Example 1: Simple simulation and result parsing
from scaps_workflow import ScapsSimulation

sim = ScapsSimulation("Cs2PtI6 Ag2MgGeS4.def")
results = sim.parse_existing_results()  # Parse existing results
print(f"VOC: {results['voc']} V")
print(f"JSC: {results['jsc']} mA/cm²")

# Example 2: Run simulation (if Wine is available)
sim = ScapsSimulation("CsBi3I10.def")
results = sim.run(use_xvfb=True)  # Runs SCAPS
sim.print_results()

# Example 3: Parse IV data
from scaps_workflow import ScapsResultParser

parser = ScapsResultParser()
iv_data = parser.extract_iv_curve_data("/path/to/file.iv")
print(f"Voltages: {iv_data['voltages']}")
print(f"Currents: {iv_data['currents']}")

# Example 4: Generate batch script
from scaps_workflow import ScapsScriptGenerator

devices = [
    "CsBi3I10.def",
    "K2LiGaBr6 Cs2AgSbBr6.def",
    "Cs2PtI6 Ag2MgGeS4.def"
]

script = ScapsScriptGenerator.generate_batch_script(devices)
print(script)
"""
    
    print(examples)


def main():
    """Main function."""
    print("\n" + "="*70)
    print("SCAPS WORKFLOW - Complete Python Implementation")
    print("="*70)
    
    # Run demonstrations
    demonstrate_configuration()
    demonstrate_script_generation()
    demonstrate_parser()
    demonstrate_simulation_workflow()
    show_usage_examples()
    
    print("\n" + "="*70)
    print("Documentation")
    print("="*70)
    print(f"""
The SCAPS workflow consists of several key components:

1. ScapsConfig - Configuration and file paths
2. ScapsScriptGenerator - Generate SCAPS script files
3. ScapsExecutor - Execute SCAPS with Wine
4. ScapsResultParser - Parse and extract results
5. ScapsSimulation - High-level simulation interface

For more details, see:
  - scaps_workflow.py - Complete module documentation
  - ScapsSimulation class - High-level interface
  
To use this workflow with your own devices:
  1. Place definition files (.def) in: {ScapsConfig.DEF_DIR}
  2. Use ScapsSimulation class to manage simulations
  3. Parse results using ScapsResultParser
  
Note: SCAPS requires Wine and a virtual display (xvfb) on Linux.
Make sure both are installed: sudo apt install wine xvfb
""")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
