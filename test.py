"""Simplified solar-cell IV simulation for extracting Jsc, Voc, FF, and PCE.

This script uses the standard one-diode model with series and shunt resistance.
It is intentionally dependency-light so it runs with plain Python.
It can also read a SCAPS-style .def file from the workspace and estimate the metrics
from the parsed material parameters.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def solve_current_density(voltage: float, params: Dict[str, float]) -> float:
    """Solve the one-diode current density at a given voltage."""
    jph = params["Jph"]
    j0 = params["J0"]
    rs = params["Rs"]
    rsh = params["Rsh"]
    ideality = params["n"]
    temperature = params["T"]

    q = 1.602176634e-19
    k = 1.380649e-23
    vt = ideality * k * temperature / q

    current_density = jph
    for _ in range(100):
        exp_arg = (voltage + current_density * rs) / vt
        if exp_arg > 700:
            exp_arg = 700
        if exp_arg < -700:
            exp_arg = -700

        f = (
            current_density
            - jph
            + j0 * (math.exp(exp_arg) - 1)
            + (voltage + current_density * rs) / rsh
        )
        df = 1 + (j0 * rs / vt) * math.exp(exp_arg) + rs / rsh

        new_current = current_density - f / df
        if abs(new_current - current_density) < 1e-12:
            return new_current
        current_density = new_current

    return current_density


def find_voc(params: Dict[str, float], upper_limit: float = 1.5) -> float:
    """Find the open-circuit voltage by bisection."""
    lo = 0.0
    hi = upper_limit
    while solve_current_density(hi, params) > 0:
        hi *= 1.2
        if hi > 5.0:
            raise RuntimeError("Could not bracket Voc.")

    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if solve_current_density(mid, params) > 0:
            lo = mid
        else:
            hi = mid

    return 0.5 * (lo + hi)


def simulate_iv_curve(params: Dict[str, float], num_points: int = 401) -> List[Tuple[float, float]]:
    """Create a voltage-current density curve."""
    voc = find_voc(params)
    vmax = max(voc * 1.05, 1.2)
    voltages = [vmax * i / (num_points - 1) for i in range(num_points)]
    curve: List[Tuple[float, float]] = []
    for voltage in voltages:
        current_density = solve_current_density(voltage, params)
        curve.append((voltage, current_density))
    return curve


def extract_metrics(params: Dict[str, float], num_points: int = 401) -> Dict[str, float]:
    """Extract Jsc, Voc, FF, and PCE from the simulated IV curve."""
    curve = simulate_iv_curve(params, num_points=num_points)

    jsc = solve_current_density(0.0, params)
    voc = find_voc(params)

    max_power = -1.0
    vmp = 0.0
    jmp = 0.0
    for voltage, current_density in curve:
        power = voltage * current_density
        if power > max_power:
            max_power = power
            vmp = voltage
            jmp = current_density

    ff = (vmp * jmp) / (voc * jsc) if (voc * jsc) > 0 else 0.0
    pin = params.get("Pin", 0.1)
    pce = (voc * jsc * ff) / pin

    return {
        "Jsc_A_cm2": jsc,
        "Jsc_mA_cm2": jsc * 1000.0,
        "Voc_V": voc,
        "FF": ff,
        "PCE": pce,
        "PCE_percent": pce * 100.0,
        "Vmp_V": vmp,
        "Jmp_A_cm2": jmp,
        "Jmp_mA_cm2": jmp * 1000.0,
    }


def run_example() -> Dict[str, float]:
    """Example parameters for a typical perovskite-like solar cell."""
    params = {
        "Jph": 0.035,      # A/cm^2, roughly 35 mA/cm^2
        "J0": 1e-12,       # diode reverse saturation current
        "Rs": 1.5,         # series resistance (ohm cm^2)
        "Rsh": 800.0,      # shunt resistance (ohm cm^2)
        "n": 1.35,         # ideality factor
        "T": 300.0,        # temperature (K)
        "Pin": 0.1,        # irradiance in W/cm^2 (100 mW/cm^2)
    }
    return extract_metrics(params)


def parse_scaps_layers(def_file: Path) -> List[Dict[str, Optional[float]]]:
    """Parse a SCAPS-style .def file and extract layer thickness and bandgap values."""
    text = def_file.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    layers: List[Dict[str, Optional[float]]] = []
    current: Optional[Dict[str, Optional[float]]] = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("layer"):
            if current is not None:
                layers.append(current)
            current = {"name": None, "d_m": None, "eg_eV": None, "na_m3": None, "nd_m3": None}
            continue

        if current is None:
            continue

        if current["name"] is None:
            m = re.match(r"name\s*:\s*(.+)$", line)
            if m:
                current["name"] = m.group(1).strip()
                continue

        if current["d_m"] is None:
            m = re.match(r"d\s*:\s*([0-9.eE+-]+)\s*\[m\]", line)
            if m:
                current["d_m"] = float(m.group(1))
                continue

        if current["eg_eV"] is None and stripped.startswith("Eg"):
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", stripped)
            if nums:
                current["eg_eV"] = float(nums[0])
                continue

        if current["na_m3"] is None:
            m = re.match(r"Na\(uniform\)\s*:\s*([0-9.eE+-]+)", line)
            if m:
                current["na_m3"] = float(m.group(1))
                continue

        if current["nd_m3"] is None:
            m = re.match(r"Nd\(uniform\)\s*:\s*([0-9.eE+-]+)", line)
            if m:
                current["nd_m3"] = float(m.group(1))
                continue

    if current is not None:
        layers.append(current)

    return [layer for layer in layers if layer.get("d_m") is not None and layer.get("eg_eV") is not None]


def estimate_metrics_from_scaps(def_file: Path) -> Dict[str, float]:
    """Create a rough solar-cell estimate from SCAPS layer properties."""
    layers = parse_scaps_layers(def_file)
    if not layers:
        raise ValueError(f"No SCAPS layers could be parsed from {def_file}")

    absorber = None
    for layer in layers:
        if layer.get("eg_eV") is None or layer.get("d_m") is None:
            continue
        if absorber is None:
            absorber = layer
            continue
        if float(layer["eg_eV"]) < float(absorber["eg_eV"]):
            absorber = layer

    if absorber is None:
        raise ValueError(f"No absorber layer found in {def_file}")

    eg = float(absorber["eg_eV"])
    thickness_um = float(absorber["d_m"]) * 1e6

    absorption_factor = min(1.0, thickness_um / 500.0)
    bandgap_factor = max(0.1, 1.0 - 0.18 * max(0.0, eg - 1.4))
    jph = 38.0 * absorption_factor * bandgap_factor / 1000.0  # A/cm^2 from mA/cm^2 estimate

    # A rough empirical link between the absorber bandgap and diode saturation current.
    j0 = 1e-12 * math.exp(-(eg - 1.1) / 0.10)

    params = {
        "Jph": jph,
        "J0": j0,
        "Rs": 1.2,
        "Rsh": 600.0,
        "n": 1.35,
        "T": 300.0,
        "Pin": 0.1,
    }
    metrics = extract_metrics(params)
    metrics["source_file"] = str(def_file)
    metrics["absorber_name"] = absorber.get("name", "unknown")
    metrics["absorber_bandgap_eV"] = eg
    metrics["absorber_thickness_um"] = thickness_um
    return metrics


def find_default_def_file(base_dir: Path) -> Optional[Path]:
    """Pick a reasonable SCAPS definition file if none is specified."""
    preferred_names = ["MAPbI3-FaPbBr3.def", "MaSnI3.def", "default.scaps"]
    for name in preferred_names:
        candidate = base_dir / name
        if candidate.exists():
            return candidate

    def_files = sorted(base_dir.rglob("*.def"))
    if def_files:
        return def_files[0]
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estimate Jsc, Voc, FF, and PCE for a solar cell")
    parser.add_argument("def_file", nargs="?", help="Optional path to a SCAPS .def file")
    args = parser.parse_args()

    if args.def_file:
        target = Path(args.def_file).expanduser().resolve()
        if not target.exists():
            raise FileNotFoundError(f"SCAPS file not found: {target}")
        metrics = estimate_metrics_from_scaps(target)
        print(f"Using SCAPS file: {target}")
    else:
        workspace = Path(__file__).resolve().parent
        scaps_file = find_default_def_file(workspace / "Scaps3312" / "def")
        if scaps_file is not None:
            metrics = estimate_metrics_from_scaps(scaps_file)
            print(f"Using SCAPS file: {scaps_file}")
        else:
            metrics = run_example()
            print("Using built-in example parameters")

    print("Solar cell metrics")
    print("==================")
    print(f"Jsc: {metrics['Jsc_mA_cm2']:.2f} mA/cm^2")
    print(f"Voc: {metrics['Voc_V']:.3f} V")
    print(f"FF: {metrics['FF']:.3f}")
    print(f"PCE: {metrics['PCE_percent']:.2f} %")
    if "absorber_name" in metrics:
        print(f"Absorber: {metrics['absorber_name']}")
        print(f"Bandgap: {metrics['absorber_bandgap_eV']:.3f} eV")
        print(f"Thickness: {metrics['absorber_thickness_um']:.2f} um")
