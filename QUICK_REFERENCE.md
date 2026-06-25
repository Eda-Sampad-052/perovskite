# SCAPS Workflow - Quick Reference & Examples

## Quick Start (30 seconds)

```bash
# Run the demonstration
python3 test.py
```

## Copy & Paste Examples

### Example 1: Get Results for Single Device
```python
from scaps_workflow import ScapsSimulation

# Create simulation instance
sim = ScapsSimulation("Cs2PtI6 Ag2MgGeS4.def")

# Parse existing results
results = sim.parse_existing_results()

# Or run new simulation (requires Wine)
# results = sim.run(use_xvfb=True)

# Display results
sim.print_results()

# Access individual values
if results['voc']:
    print(f"VOC: {results['voc']:.4f} V")
    print(f"JSC: {results['jsc']:.4f} mA/cm²")
    print(f"FF: {results['ff']:.2f} %")
    print(f"PCE: {results['pce']:.2f} %")
```

### Example 2: Batch Process Multiple Devices
```python
from scaps_workflow import ScapsSimulation

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
        results[device] = sim.results
        
        # Print for each device
        print(f"\n{device}")
        print(f"  VOC: {sim.results['voc']:.4f} V")
        print(f"  JSC: {sim.results['jsc']:.4f} mA/cm²")
        print(f"  FF: {sim.results['ff']:.2f} %")
        print(f"  PCE: {sim.results['pce']:.2f} %")
    except FileNotFoundError:
        print(f"Skipping {device} - not found")
```

### Example 3: Compare Against Expected Results
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

print(f"Results for {device}:")
print(f"{'Parameter':<10} {'Got':<15} {'Expected':<15} {'Error %':<10}")
print("-" * 50)

for param in ['voc', 'jsc', 'pce', 'ff']:
    if results[param] and expected[param]:
        got = results[param]
        exp = expected[param]
        error = abs(got - exp) / exp * 100
        print(f"{param.upper():<10} {got:<15.4f} {exp:<15.4f} {error:<10.2f}")
```

### Example 4: Extract & Analyze IV Curve Data
```python
from scaps_workflow import ScapsResultParser

parser = ScapsResultParser()

# Extract IV curve data
iv_data = parser.extract_iv_curve_data("results/test save iv.iv")

# Access data
voltages = iv_data['voltages']
currents = iv_data['currents']
powers = iv_data['powers']

# Find maximum power point
if powers:
    max_power = max(powers)
    max_idx = powers.index(max_power)
    
    vmp = abs(voltages[max_idx])
    jmp = abs(currents[max_idx])
    pmp = max_power
    
    print(f"Maximum Power Point:")
    print(f"  Voltage: {vmp:.4f} V")
    print(f"  Current: {jmp:.4f} mA/cm²")
    print(f"  Power: {pmp:.4f} mW/cm²")
```

### Example 5: Generate SCAPS Script Manually
```python
from scaps_workflow import ScapsScriptGenerator, ScapsConfig
import tempfile

# Generate script content
def_file = "/path/to/device.def"
script_content = ScapsScriptGenerator.generate_iv_curve_script(def_file)

# Create script file
script_path = ScapsScriptGenerator.create_script_file(script_content)

print(f"Script created: {script_path}")
print("\nScript content:")
print(script_content)

# To execute (requires Wine):
# from scaps_workflow import ScapsExecutor
# executor = ScapsExecutor()
# stdout, stderr, rc = executor.run_with_wine(script_path)
```

### Example 6: Save Results to JSON
```python
from scaps_workflow import ScapsSimulation
import json

devices = [
    "CsBi3I10.def",
    "Cs2PtI6 Ag2MgGeS4.def"
]

all_results = {}

for device in devices:
    try:
        sim = ScapsSimulation(device)
        sim.parse_existing_results()
        all_results[device] = sim.results
    except FileNotFoundError:
        pass

# Save to JSON
with open("scaps_results.json", "w") as f:
    json.dump(all_results, f, indent=2)

print("Results saved to scaps_results.json")

# Load from JSON
with open("scaps_results.json", "r") as f:
    loaded = json.load(f)
    print(f"Loaded {len(loaded)} devices")
```

### Example 7: Create Batch Script for SCAPS
```python
from scaps_workflow import ScapsScriptGenerator

devices = [
    "/workspaces/perovskite/Scaps3312/def/CsBi3I10.def",
    "/workspaces/perovskite/Scaps3312/def/Cs2PtI6 Ag2MgGeS4.def",
    "/workspaces/perovskite/Scaps3312/def/K2LiGaBr6 Cs2AgSbBr6.def"
]

# Generate batch script
batch_script = ScapsScriptGenerator.generate_batch_script(devices)

# Save to file
with open("batch_simulation.script", "w") as f:
    f.write(batch_script)

print("Batch script saved to batch_simulation.script")
print("\nTo run:")
print("  xvfb-run -a wine /path/to/scaps3312.exe batch_simulation.script")
```

### Example 8: Parse All Available IV Files
```python
from scaps_workflow import ScapsResultParser, ScapsConfig
import os

parser = ScapsResultParser()
results_dir = ScapsConfig.RESULTS_DIR

# Find all IV files
iv_files = [f for f in os.listdir(results_dir) if f.endswith('.iv')]

print(f"Found {len(iv_files)} IV files in {results_dir}\n")

for iv_file in iv_files:
    iv_path = os.path.join(results_dir, iv_file)
    results = parser.parse_iv_file(iv_path)
    
    device_name = iv_file.replace('.iv', '')
    
    print(f"{device_name}:")
    if results['voc']:
        print(f"  VOC: {results['voc']:.4f} V")
        print(f"  JSC: {results['jsc']:.4f} mA/cm²")
        print(f"  FF: {results['ff']:.2f} %")
        print(f"  PCE: {results['pce']:.2f} %")
    else:
        print(f"  No results found")
    print()
```

### Example 9: Temperature Variation
```python
from scaps_workflow import ScapsScriptGenerator
import tempfile

# Generate scripts for different temperatures
temperatures = [250, 300, 350, 400]
def_file = "/path/to/device.def"

scripts = {}

for temp in temperatures:
    generator = ScapsScriptGenerator()
    
    # Note: generate_iv_curve_script takes temp as parameter
    script = generator.generate_iv_curve_script(def_file, temp=temp)
    script_path = generator.create_script_file(script)
    
    scripts[temp] = script_path
    print(f"Created script for T={temp}K: {script_path}")

# Execute each and compare results...
```

### Example 10: Export to CSV
```python
from scaps_workflow import ScapsSimulation
import csv

devices = [
    "CsBi3I10.def",
    "Cs2PtI6 Ag2MgGeS4.def",
    "K2LiGaBr6 Cs2AgSbBr6.def"
]

# Collect results
results_list = []

for device in devices:
    try:
        sim = ScapsSimulation(device)
        sim.parse_existing_results()
        
        results_list.append({
            'Device': device,
            'VOC (V)': f"{sim.results['voc']:.6f}" if sim.results['voc'] else "N/A",
            'JSC (mA/cm²)': f"{sim.results['jsc']:.6f}" if sim.results['jsc'] else "N/A",
            'FF (%)': f"{sim.results['ff']:.4f}" if sim.results['ff'] else "N/A",
            'PCE (%)': f"{sim.results['pce']:.4f}" if sim.results['pce'] else "N/A"
        })
    except FileNotFoundError:
        pass

# Write to CSV
with open("scaps_results.csv", "w", newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Device', 'VOC (V)', 'JSC (mA/cm²)', 'FF (%)', 'PCE (%)'])
    writer.writeheader()
    writer.writerows(results_list)

print(f"Results exported to scaps_results.csv ({len(results_list)} devices)")
```

## Common Parameters

### SCAPS Characteristics

| Parameter | Symbol | Unit | Description |
|-----------|--------|------|-------------|
| Open Circuit Voltage | VOC | V | Maximum voltage when J=0 |
| Short Circuit Current | JSC | mA/cm² | Current density when V=0 |
| Fill Factor | FF | % | Pmax/(VOC×JSC) |
| Power Conversion Efficiency | PCE/eta | % | Pmax/Pin |

### Simulation Conditions

| Parameter | Default | Range |
|-----------|---------|-------|
| Temperature | 300 K | 250-400 K |
| Illumination | AM1.5G | Various spectra |
| Intensity | 1 Sun | 0-2 Sun |
| Voltage Range | 0 to 1.5 V | Configurable |
| Increment | 0.01 V | Variable |

## Troubleshooting

### "IV file not found"
- Check file path is correct
- Verify SCAPS has been run to generate output
- Check RESULTS_DIR configuration

### "Definition file not found"
- Check device name is correct
- Verify DEF_DIR path is correct
- Ensure .def file exists in directory

### "No results found" when parsing
- IV file format may have changed
- Verify SCAPS generated the output
- Check file is not corrupted

### Wine execution fails
- Install Wine: `sudo apt install wine wine32`
- Use xvfb-run for headless execution
- Check SCAPS_EXE path is correct

## Tips & Tricks

1. **Use pathlib for paths**:
   ```python
   from pathlib import Path
   device = Path(sim.def_file).name
   ```

2. **Check if results exist**:
   ```python
   if results and any(results.values()):
       print("Results found")
   ```

3. **Handle missing files gracefully**:
   ```python
   try:
       sim = ScapsSimulation(device)
   except FileNotFoundError:
       print(f"Device {device} not available")
   ```

4. **Round results for display**:
   ```python
   print(f"VOC: {results['voc']:.4f} V")  # 4 decimal places
   ```

5. **Store configurations**:
   ```python
   config = {
       'temp': 300,
       'v_start': 0,
       'v_stop': 1.5,
       'increment': 0.01
   }
   ```

## Performance Notes

- Single device analysis: < 1 second (parsing only)
- SCAPS simulation: 10-60 seconds per device (depends on settings)
- Batch processing: Linear with number of devices
- IV data extraction: < 100ms per file

## Further Reading

- SCAPS official website: https://scaps.elis.ugent.be
- SCAPS manual: `New folder/New folder/SCAPS manual most recent.pdf`
- Script reference: `New folder/New folder/scriptdescription3312.txt`
- Full documentation: `SCAPS_WORKFLOW_README.md`

---

**Version**: 1.0  
**Last Updated**: 2026-06-25  
**Tested With**: SCAPS 3.3.12, Python 3.8+
