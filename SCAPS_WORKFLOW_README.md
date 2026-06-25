# SCAPS Workflow - Python Implementation

Complete Python implementation for running SCAPS solar cell simulations and extracting performance characteristics (VOC, JSC, PCE, FF).

## Overview

This project provides a complete workflow to:
1. **Generate SCAPS scripts** programmatically for simulations
2. **Execute SCAPS** simulations using Wine on Linux
3. **Parse results** from SCAPS output files
4. **Extract characteristics** like VOC, JSC, PCE, and FF
5. **Batch process** multiple devices

## Architecture

### Core Components

#### 1. **ScapsConfig** - Configuration and Paths
```python
ScapsConfig.SCAPS_EXE      # Path to SCAPS executable
ScapsConfig.DEF_DIR        # Definition files directory
ScapsConfig.RESULTS_DIR    # Results directory
ScapsConfig.DEFAULT_TEMP   # Default simulation temperature
```

#### 2. **ScapsScriptGenerator** - Script Creation
Generates SCAPS script files for simulations:
```python
# Generate IV curve script
script = ScapsScriptGenerator.generate_iv_curve_script(def_file)

# Generate batch script for multiple devices
script = ScapsScriptGenerator.generate_batch_script([def1, def2, def3])

# Create temporary script file
script_path = ScapsScriptGenerator.create_script_file(script_content)
```

#### 3. **ScapsExecutor** - Simulation Execution
Executes SCAPS with Wine:
```python
executor = ScapsExecutor()

# With virtual display (recommended for Linux)
stdout, stderr, returncode = executor.run_with_wine(script_path)

# Direct execution (if display available)
stdout, stderr, returncode = executor.run_direct(script_path)
```

#### 4. **ScapsResultParser** - Result Extraction
Parses SCAPS output and extracts characteristics:
```python
parser = ScapsResultParser()

# Parse IV file
results = parser.parse_iv_file("file.iv")
# Returns: {'voc': 1.17, 'jsc': 32.07, 'ff': 33.61, 'pce': 89.5}

# Extract IV curve data
iv_data = parser.extract_iv_curve_data("file.iv")
# Returns: {'voltages': [...], 'currents': [...], 'powers': [...]}
```

#### 5. **ScapsSimulation** - High-Level Interface
Simple interface for running simulations:
```python
sim = ScapsSimulation("Cs2PtI6 Ag2MgGeS4.def")

# Parse existing results
results = sim.parse_existing_results()

# Or run new simulation
results = sim.run(use_xvfb=True)

# Print formatted results
sim.print_results()
```

## Quick Start

### 1. Run the Demonstration

```bash
python3 test.py
```

This demonstrates:
- SCAPS configuration
- Script generation
- Result parsing
- Complete workflow

### 2. Parse Existing Results

```python
from scaps_workflow import ScapsSimulation

# Create simulation instance
sim = ScapsSimulation("Cs2PtI6 Ag2MgGeS4.def")

# Parse existing results
results = sim.parse_existing_results()

# Access results
print(f"VOC: {results['voc']} V")
print(f"JSC: {results['jsc']} mA/cm²")
print(f"FF: {results['ff']} %")
print(f"PCE: {results['pce']} %")
```

### 3. Run New Simulation

```python
from scaps_workflow import ScapsSimulation

sim = ScapsSimulation("CsBi3I10.def")

# Run SCAPS simulation (requires Wine)
results = sim.run(use_xvfb=True)

# Print results
sim.print_results()
```

### 4. Batch Process Devices

```python
from scaps_workflow import ScapsScriptGenerator, ScapsSimulation

devices = [
    "CsBi3I10.def",
    "K2LiGaBr6 Cs2AgSbBr6.def",
    "Cs2PtI6 Ag2MgGeS4.def"
]

# Generate batch script
script = ScapsScriptGenerator.generate_batch_script(devices)

# Run simulation with batch script
# ... execute script with SCAPS ...

# Parse results
all_results = {}
for device in devices:
    sim = ScapsSimulation(device)
    all_results[device] = sim.parse_existing_results()
```

## SCAPS Script Format

SCAPS uses a custom script language. Example generated script:

```scaps
// Auto-generated SCAPS IV curve script
clear all
clear actions

// Set illuminated conditions
action light
action workingpoint.temperature 300
action iv.startv 0.0
action iv.stopv 1.5
action iv.increment 0.01
action iv.checkaction
action iv.stopaftervoc

// Load device definition
load definitionfile "/path/to/device.def"

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
```

### Common SCAPS Commands

| Command | Purpose |
|---------|---------|
| `clear all` | Clear all definitions |
| `load definitionfile` | Load device definition |
| `action light` | Set illuminated conditions |
| `action dark` | Set dark conditions |
| `calculate singleshot` | Calculate at working point |
| `get iv` | Get IV curve data |
| `math characteristics.voc` | Calculate VOC |
| `math characteristics.jsc` | Calculate JSC |
| `math characteristics.ff` | Calculate fill factor |
| `math characteristics.eta` | Calculate efficiency (PCE) |
| `save results.iv` | Save IV curve |

## Result Extraction

### From IV Files

SCAPS saves results in `.iv` files with this format:

```
SCAPS output generated by a script
...
[IV curve data with V and J columns]
...
Voc =       1.1709    Volt
Jsc =      32.071000  mA/cm2
FF =       33.61      %
eta =       89.50      %
```

The parser automatically extracts:
- **VOC** (Volt-Open Circuit): Maximum voltage when current = 0
- **JSC** (mA/cm²): Short-circuit current density
- **FF** (%): Fill Factor = Pmax / (VOC × JSC)
- **PCE/eta** (%): Power Conversion Efficiency

### Programmatic Access

```python
from scaps_workflow import ScapsResultParser

parser = ScapsResultParser()

# Parse IV file
results = parser.parse_iv_file("results.iv")

# Extract raw IV curve data
iv_data = parser.extract_iv_curve_data("results.iv")

# Access individual components
voltages = iv_data['voltages']
currents = iv_data['currents']
powers = iv_data['powers']
```

## System Requirements

### On Windows
- SCAPS 3.3.12 or later
- Python 3.7+

### On Linux
- Python 3.7+
- Wine (for running Windows executable)
- Xvfb (virtual display for headless execution)

Install dependencies:
```bash
sudo apt update
sudo apt install wine xvfb python3
```

## Configuration

Edit configuration in `scaps_workflow.py`:

```python
class ScapsConfig:
    SCAPS_EXE = "/path/to/scaps3312.exe"
    DEF_DIR = "/path/to/definitions"
    RESULTS_DIR = "/path/to/results"
    DEFAULT_TEMP = 300  # Temperature in K
    IV_START_V = 0.0
    IV_STOP_V = 1.5
    IV_INCREMENT = 0.01
```

## Examples

### Example 1: Simple Analysis

```python
from scaps_workflow import ScapsSimulation

# Create simulation for device
sim = ScapsSimulation("MAPbI3-FaPbBr3.def")

# Get results from existing IV file
results = sim.parse_existing_results()

# Display results
if results and any(results.values()):
    print(f"Device: MAPbI3-FaPbBr3")
    print(f"VOC: {results['voc']:.4f} V")
    print(f"JSC: {results['jsc']:.4f} mA/cm²")
    print(f"FF: {results['ff']:.2f} %")
    print(f"PCE: {results['pce']:.2f} %")
```

### Example 2: Batch Analysis

```python
from scaps_workflow import ScapsSimulation
import json

devices = [
    "CsBi3I10.def",
    "Cs2PtI6 Ag2MgGeS4.def",
    "K2LiGaBr6 Cs2AgSbBr6.def"
]

results = {}

for device in devices:
    try:
        sim = ScapsSimulation(device)
        sim.parse_existing_results()
        if sim.results:
            results[device] = sim.results
    except FileNotFoundError:
        pass

# Save results to JSON
with open("scaps_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Print summary
print("\nBatch Results Summary:")
for device, res in results.items():
    print(f"{device}: PCE = {res['pce']:.2f}%")
```

### Example 3: Comparing Results

```python
from scaps_workflow import ScapsSimulation

device = "Cs2PtI6 Ag2MgGeS4.def"

expected = {
    'voc': 1.1709,
    'jsc': 32.071,
    'pce': 89.50,
    'ff': 33.61
}

sim = ScapsSimulation(device)
results = sim.parse_existing_results()

print(f"Comparison: {device}")
print(f"{'Parameter':<10} {'Got':<12} {'Expected':<12} {'Error %':<10}")
print("-" * 44)

for param in ['voc', 'jsc', 'pce', 'ff']:
    if results[param]:
        error = abs(results[param] - expected[param]) / expected[param] * 100
        print(f"{param.upper():<10} {results[param]:<12.4f} {expected[param]:<12.4f} {error:<10.2f}")
```

## Troubleshooting

### Wine Issues

**Error: "could not load kernel32.dll"**
- Install Wine properly: `sudo apt install wine wine32`
- Try direct execution without xvfb if display available

### IV File Not Found

- Ensure SCAPS has been run and generated output files
- Check RESULTS_DIR path is correct
- Verify .iv file name matches definition file name

### Python Import Errors

```bash
# Make sure scaps_workflow.py is in same directory or Python path
python3 -c "import scaps_workflow"
```

## File Structure

```
/workspaces/perovskite/
├── test.py                    # Main demonstration script
├── scaps_workflow.py          # Complete module implementation
├── Scaps3312/
│   ├── def/                   # Definition files (.def)
│   ├── script/                # SCAPS script files
│   └── ...
├── New folder/
│   └── New folder/
│       ├── scaps3312.exe      # SCAPS executable
│       ├── results/           # Output files (.iv, .xls)
│       └── ...
└── README.md                  # This file
```

## References

- SCAPS Official: https://scaps.elis.ugent.be
- Definition of VOC, JSC, FF, PCE: Standard photovoltaic terminology
- Script Commands: See `scriptdescription3312.txt` in SCAPS directory

## License

This Python implementation is provided as-is for research purposes.
SCAPS itself is developed by Marc Burgelman and team at ELIS-UGent.

## Support

For issues with:
- **Python workflow**: Check scaps_workflow.py and test.py
- **SCAPS execution**: Ensure Wine is properly installed
- **Result parsing**: Verify IV file format and path
