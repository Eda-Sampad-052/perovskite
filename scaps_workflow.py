#!/usr/bin/env python3
"""
SCAPS Workflow Module - Complete implementation for running SCAPS simulations
and extracting solar cell performance characteristics (VOC, JSC, PCE, FF).

This module provides:
1. Script generation for SCAPS
2. Simulation execution (requires Wine + SCAPS executable)
3. Result parsing and extraction
4. Batch processing capabilities
5. Data analysis utilities
"""

import subprocess
import os
import sys
import re
import tempfile
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import json
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

class ScapsConfig:
    """SCAPS configuration and paths."""
    SCAPS_EXE = "/workspaces/perovskite/New folder/New folder/scaps3312.exe"
    DEF_DIR = "/workspaces/perovskite/Scaps3312/def"
    RESULTS_DIR = "/workspaces/perovskite/New folder/New folder/results"
    SCRIPT_DIR = "/workspaces/perovskite/New folder/New folder/script"
    
    # SCAPS simulation parameters
    DEFAULT_TEMP = 300  # Temperature in K
    IV_START_V = 0.0
    IV_STOP_V = 1.5
    IV_INCREMENT = 0.01


# ============================================================================
# SCAPS SCRIPT GENERATION
# ============================================================================

class ScapsScriptGenerator:
    """Generate SCAPS script files for various simulation types."""
    
    @staticmethod
    def generate_iv_curve_script(def_file: str, temp: float = 300) -> str:
        """
        Generate a SCAPS script for IV curve calculation.
        
        Args:
            def_file: Full path to definition file
            temp: Temperature in Kelvin
        
        Returns:
            Script content as string
        """
        script = f"""// Auto-generated SCAPS IV curve script
// Generated: {datetime.now().isoformat()}
// Definition file: {def_file}

clear all
clear actions

// Set illuminated conditions
action light
action workingpoint.temperature {temp}
action iv.startv {ScapsConfig.IV_START_V}
action iv.stopv {ScapsConfig.IV_STOP_V}
action iv.increment {ScapsConfig.IV_INCREMENT}
action iv.checkaction
action iv.stopaftervoc

// Load device definition
load definitionfile "{def_file}"

// Calculate IV curve
calculate singleshot
get iv ivcurve

// Extract characteristics
math characteristics.voc voc_value
math characteristics.jsc jsc_value
math characteristics.ff ff_value
math characteristics.eta pce_value

// Display results
show scriptvariables
"""
        return script
    
    @staticmethod
    def generate_batch_script(def_files: List[str]) -> str:
        """
        Generate a SCAPS script for batch processing multiple devices.
        
        Args:
            def_files: List of definition file paths
        
        Returns:
            Script content as string
        """
        script = f"""// Auto-generated SCAPS batch script
// Generated: {datetime.now().isoformat()}
// Processing {len(def_files)} device(s)

clear all
clear actions

// Set illuminated conditions
action light
action workingpoint.temperature {ScapsConfig.DEFAULT_TEMP}
action iv.startv {ScapsConfig.IV_START_V}
action iv.stopv {ScapsConfig.IV_STOP_V}
action iv.increment {ScapsConfig.IV_INCREMENT}
action iv.checkaction
action iv.stopaftervoc

"""
        
        for i, def_file in enumerate(def_files):
            var_prefix = f"cell{i}"
            script += f"""
// Cell {i+1}: {Path(def_file).name}
load definitionfile "{def_file}"
calculate singleshot
get iv {var_prefix}_iv

math characteristics.voc {var_prefix}_voc
math characteristics.jsc {var_prefix}_jsc
math characteristics.ff {var_prefix}_ff
math characteristics.eta {var_prefix}_pce

"""
        
        script += "show scriptvariables\n"
        return script
    
    @staticmethod
    def create_script_file(script_content: str) -> str:
        """
        Create a temporary script file.
        
        Args:
            script_content: Content of the script
        
        Returns:
            Path to created script file
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.script', delete=False) as f:
            f.write(script_content)
            return f.name


# ============================================================================
# SCAPS EXECUTION
# ============================================================================

class ScapsExecutor:
    """Execute SCAPS simulations."""
    
    @staticmethod
    def run_with_wine(script_path: str, timeout: int = 300) -> Tuple[Optional[str], Optional[str], int]:
        """
        Execute SCAPS using Wine with virtual display.
        
        Args:
            script_path: Path to SCAPS script file
            timeout: Execution timeout in seconds
        
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        try:
            cmd = [
                'xvfb-run',
                '-a',
                'wine',
                ScapsConfig.SCAPS_EXE,
                script_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            print(f"Error: SCAPS execution timed out after {timeout} seconds")
            return None, None, -1
        except Exception as e:
            print(f"Error executing SCAPS: {e}")
            return None, None, -1
    
    @staticmethod
    def run_direct(script_path: str, timeout: int = 300) -> Tuple[Optional[str], Optional[str], int]:
        """
        Execute SCAPS directly (without xvfb, for environments with display).
        
        Args:
            script_path: Path to SCAPS script file
            timeout: Execution timeout in seconds
        
        Returns:
            Tuple of (stdout, stderr, returncode)
        """
        try:
            cmd = ['wine', ScapsConfig.SCAPS_EXE, script_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            print(f"Error: SCAPS execution timed out after {timeout} seconds")
            return None, None, -1
        except Exception as e:
            print(f"Error executing SCAPS: {e}")
            return None, None, -1


# ============================================================================
# RESULT PARSING
# ============================================================================

class ScapsResultParser:
    """Parse SCAPS output and extract characteristics."""
    
    @staticmethod
    def parse_iv_file(iv_file_path: str) -> Dict[str, Optional[float]]:
        """
        Parse SCAPS IV curve file and extract characteristics.
        
        SCAPS outputs VOC, JSC, FF, and eta (PCE) at the end of the file
        in the format:
            Voc = X.XXXX Volt
            Jsc = XX.XXXX mA/cm2
            FF = XX.XX %
            eta = XX.XX %
        
        Args:
            iv_file_path: Path to the .iv file
        
        Returns:
            Dictionary with keys: voc, jsc, ff, pce
        """
        results = {
            'voc': None,
            'jsc': None,
            'pce': None,
            'ff': None
        }
        
        if not os.path.exists(iv_file_path):
            print(f"IV file not found: {iv_file_path}")
            return results
        
        try:
            with open(iv_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract all matches and use the last ones (final result)
            voc_matches = re.findall(r'Voc\s*=\s*([\d.]+)\s*Volt', content)
            jsc_matches = re.findall(r'Jsc\s*=\s*([\d.]+)\s*mA/cm2', content)
            ff_matches = re.findall(r'FF\s*=\s*([\d.]+)\s*%', content)
            eta_matches = re.findall(r'eta\s*=\s*([\d.]+)\s*%', content)
            
            if voc_matches:
                results['voc'] = float(voc_matches[-1])
            if jsc_matches:
                results['jsc'] = float(jsc_matches[-1])
            if ff_matches:
                results['ff'] = float(ff_matches[-1])
            if eta_matches:
                results['pce'] = float(eta_matches[-1])
        
        except Exception as e:
            print(f"Error parsing IV file: {e}")
        
        return results
    
    @staticmethod
    def parse_script_output(output: str) -> Dict[str, Optional[float]]:
        """
        Parse SCAPS script output for characteristics.
        
        Args:
            output: SCAPS console output
        
        Returns:
            Dictionary with keys: voc, jsc, ff, pce
        """
        results = {
            'voc': None,
            'jsc': None,
            'pce': None,
            'ff': None
        }
        
        if not output:
            return results
        
        patterns = {
            'voc': r'voc_value\s*=\s*([\d.]+)',
            'jsc': r'jsc_value\s*=\s*([\d.]+)',
            'pce': r'pce_value\s*=\s*([\d.]+)',
            'ff': r'ff_value\s*=\s*([\d.]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                results[key] = float(match.group(1))
        
        return results
    
    @staticmethod
    def extract_iv_curve_data(iv_file_path: str) -> Dict:
        """
        Extract voltage, current, and power data from IV file.
        
        Args:
            iv_file_path: Path to the .iv file
        
        Returns:
            Dictionary with 'voltages', 'currents', 'powers' lists
        """
        data = {
            'voltages': [],
            'currents': [],
            'powers': []
        }
        
        if not os.path.exists(iv_file_path):
            return data
        
        try:
            with open(iv_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            data_started = False
            for line in lines:
                # Find start of data section
                if 'v(V)' in line and 'jtot' in line:
                    data_started = True
                    continue
                
                if data_started:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            v = float(parts[0])
                            j = float(parts[1])
                            p = abs(v * j)
                            
                            data['voltages'].append(v)
                            data['currents'].append(j)
                            data['powers'].append(p)
                        except (ValueError, IndexError):
                            # Stop if we hit non-numeric data (characteristics section)
                            break
        
        except Exception as e:
            print(f"Error extracting IV data: {e}")
        
        return data


# ============================================================================
# HIGH-LEVEL SIMULATION INTERFACE
# ============================================================================

class ScapsSimulation:
    """High-level interface for SCAPS simulations."""
    
    def __init__(self, def_file: str):
        """
        Initialize simulation for a definition file.
        
        Args:
            def_file: Name or path of .def file
        """
        # Handle both full paths and just filenames
        if os.path.dirname(def_file):
            self.def_file = def_file
        else:
            self.def_file = os.path.join(ScapsConfig.DEF_DIR, def_file)
        
        if not os.path.exists(self.def_file):
            raise FileNotFoundError(f"Definition file not found: {self.def_file}")
        
        self.results = None
        self.iv_data = None
        self.output_name = Path(self.def_file).stem
    
    def run(self, use_xvfb: bool = True) -> Dict[str, Optional[float]]:
        """
        Execute the SCAPS simulation.
        
        Args:
            use_xvfb: Whether to use xvfb-run for virtual display
        
        Returns:
            Dictionary with results (voc, jsc, ff, pce)
        """
        print(f"Running SCAPS simulation for: {Path(self.def_file).name}")
        
        # Generate script
        script_content = ScapsScriptGenerator.generate_iv_curve_script(self.def_file)
        script_path = ScapsScriptGenerator.create_script_file(script_content)
        
        try:
            # Execute SCAPS
            executor = ScapsExecutor()
            if use_xvfb:
                stdout, stderr, returncode = executor.run_with_wine(script_path)
            else:
                stdout, stderr, returncode = executor.run_direct(script_path)
            
            if returncode != 0:
                print(f"Warning: SCAPS returned error code {returncode}")
            
            # Parse output
            self.results = ScapsResultParser.parse_script_output(stdout or "")
            
            # Try IV file as fallback
            if not any(self.results.values()):
                iv_file = f"{ScapsConfig.RESULTS_DIR}/{self.output_name}.iv"
                if os.path.exists(iv_file):
                    self.results = ScapsResultParser.parse_iv_file(iv_file)
                    self.iv_data = ScapsResultParser.extract_iv_curve_data(iv_file)
        
        finally:
            try:
                os.remove(script_path)
            except:
                pass
        
        return self.results
    
    def parse_existing_results(self) -> Dict[str, Optional[float]]:
        """
        Parse results from existing IV file without running SCAPS.
        
        Returns:
            Dictionary with results (voc, jsc, ff, pce)
        """
        iv_file = f"{ScapsConfig.RESULTS_DIR}/{self.output_name}.iv"
        
        if not os.path.exists(iv_file):
            print(f"IV file not found: {iv_file}")
            return {}
        
        print(f"Parsing results from: {iv_file}")
        self.results = ScapsResultParser.parse_iv_file(iv_file)
        self.iv_data = ScapsResultParser.extract_iv_curve_data(iv_file)
        
        return self.results
    
    def print_results(self):
        """Print results in formatted table."""
        if not self.results:
            print("No results available. Run simulation first.")
            return
        
        print("\n" + "="*50)
        print(f"Results: {Path(self.def_file).name}")
        print("="*50)
        print(f"VOC (V):     {self.results['voc']:.6f}" if self.results['voc'] else "VOC: N/A")
        print(f"JSC (mA/cm²): {self.results['jsc']:.6f}" if self.results['jsc'] else "JSC: N/A")
        print(f"FF (%):      {self.results['ff']:.6f}" if self.results['ff'] else "FF: N/A")
        print(f"PCE (%):     {self.results['pce']:.6f}" if self.results['pce'] else "PCE: N/A")
        print("="*50 + "\n")
    
    def to_json(self) -> str:
        """Export results as JSON."""
        return json.dumps({
            'device': Path(self.def_file).name,
            'timestamp': datetime.now().isoformat(),
            'results': self.results
        }, indent=2)


# ============================================================================
# MAIN EXAMPLES
# ============================================================================

def example_single_simulation():
    """Example: Run single device simulation."""
    print("Example 1: Single Device Simulation")
    print("-" * 50)
    
    try:
        sim = ScapsSimulation("Cs2PtI6 Ag2MgGeS4.def")
        
        # Try to run SCAPS (will fail gracefully if Wine not available)
        sim.run()
        
        # If that fails, try parsing existing results
        if not any(sim.results.values()):
            print("SCAPS execution failed. Attempting to parse existing results...")
            sim.parse_existing_results()
        
        sim.print_results()
        
    except FileNotFoundError as e:
        print(f"Error: {e}")


def example_batch_simulation():
    """Example: Run batch of simulations."""
    print("Example 2: Batch Simulation")
    print("-" * 50)
    
    devices = [
        "Cs2PtI6 Ag2MgGeS4.def",
        "CsBi3I10.def",
        "K2LiGaBr6 Cs2AgSbBr6.def"
    ]
    
    results_list = []
    
    for device in devices:
        try:
            sim = ScapsSimulation(device)
            sim.parse_existing_results()
            if sim.results:
                results_list.append({
                    'device': device,
                    'results': sim.results
                })
                sim.print_results()
        except FileNotFoundError:
            print(f"Device not found: {device}\n")
        except Exception as e:
            print(f"Error processing {device}: {e}\n")
    
    return results_list


def example_result_comparison():
    """Example: Compare results against expected values."""
    print("Example 3: Result Comparison")
    print("-" * 50)
    
    device = "Cs2PtI6 Ag2MgGeS4.def"
    expected = {
        'voc': 1.1709,
        'jsc': 32.071,
        'pce': 89.50,
        'ff': 33.61
    }
    
    try:
        sim = ScapsSimulation(device)
        # Try to get existing results first
        results = sim.parse_existing_results()
        
        if not results or not any(results.values()):
            # Try running simulation
            results = sim.run()
        
        if results and any(results.values()):
            print(f"\n{'='*60}")
            print(f"Comparison for: {device}")
            print(f"{'='*60}")
            print(f"{'Parameter':<12} {'Got':<15} {'Expected':<15} {'Diff %':<10}")
            print(f"{'-'*60}")
            
            for param in ['voc', 'jsc', 'pce', 'ff']:
                if results[param] and expected[param]:
                    diff_pct = abs(results[param] - expected[param]) / expected[param] * 100
                    print(f"{param.upper():<12} {results[param]:<15.4f} {expected[param]:<15.4f} {diff_pct:<10.2f}")
            print(f"{'='*60}\n")
        else:
            print("No results available to compare.")
    
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main function with examples."""
    print("\n" + "="*60)
    print("SCAPS Workflow - Complete Implementation")
    print("="*60 + "\n")
    
    # Run examples
    example_single_simulation()
    print("\n")
    example_result_comparison()
    print("\n")
    # example_batch_simulation()


if __name__ == "__main__":
    main()
