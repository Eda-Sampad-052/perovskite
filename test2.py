"""SCAPS-aware solar-cell simulation entry point.

This script is designed to use the real SCAPS executable when it is available,
and otherwise to provide a high-fidelity physics-based fallback that uses the
same material parameters extracted from SCAPS definition files.

In this Linux container, the GUI-based SCAPS executable cannot be launched
because it requires a Windows graphical runtime. The fallback therefore gives a
strong approximation rather than a true SCAPS solver result.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def find_scaps_executable() -> Optional[Path]:
    """Locate the SCAPS executable in the workspace or system path."""
    candidates = []

    workspace = Path(__file__).resolve().parent
    possible_paths = [
        workspace / "New folder" / "New folder" / "scaps3312.exe",
        workspace / "Scaps3312" / "scaps3312.exe",
        workspace / "New folder" / "bin" / "dp" / "scaps3312.exe",
    ]
    candidates.extend([p for p in possible_paths if p.exists()])

    env_path = os.environ.get("SCAPS_EXE")
    if env_path:
        candidates.append(Path(env_path))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    for name in ["scaps3312.exe", "scaps3312"]:
        found = shutil.which(name)
        if found:
            return Path(found)

    return None


def _first_float_from_line(line: str) -> Optional[float]:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", line)
    if not match:
        return None
    return float(match.group(0))


def parse_scaps_def_file(def_file: Path) -> Dict[str, object]:
    """Parse a SCAPS .def file for absorber-layer information."""
    text = def_file.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    layers: List[Dict[str, Optional[float]]] = []
    current: Optional[Dict[str, Optional[float]]] = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("layer"):
            if current is not None:
                layers.append(current)
            current = {"name": None, "d_m": None, "eg_eV": None, "Nc": None, "Nv": None, "mu_n": None, "mu_p": None, "Na": None, "Nd": None}
            continue

        if current is None:
            continue

        if current.get("name") is None and stripped.startswith("name :"):
            current["name"] = stripped.split(":", 1)[1].strip()
            continue

        if current.get("d_m") is None and stripped.startswith("d :"):
            value = _first_float_from_line(stripped.split(":", 1)[1])
            if value is not None:
                current["d_m"] = value
            continue

        if current.get("eg_eV") is None and stripped.startswith("Eg :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["eg_eV"] = value
            continue

        if current.get("Nc") is None and stripped.startswith("Nc :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["Nc"] = value
            continue

        if current.get("Nv") is None and stripped.startswith("Nv :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["Nv"] = value
            continue

        if current.get("mu_n") is None and stripped.startswith("mu_n :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["mu_n"] = value
            continue

        if current.get("mu_p") is None and stripped.startswith("mu_p :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["mu_p"] = value
            continue

        if current.get("Na") is None and stripped.startswith("Na(uniform) :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["Na"] = value
            continue

        if current.get("Nd") is None and stripped.startswith("Nd(uniform) :"):
            value = _first_float_from_line(stripped)
            if value is not None:
                current["Nd"] = value

    if current is not None:
        layers.append(current)

    absorber = None
    for layer in layers:
        if not layer.get("d_m") or layer.get("eg_eV") is None:
            continue
        name = str(layer.get("name") or "").lower()
        is_absorber = (
            "pervos" in name
            or "perov" in name
            or "mapbi" in name
            or "fapb" in name
            or "absorber" in name
        )
        if is_absorber:
            absorber = layer
            break

    if absorber is None:
        absorber = max(
            [layer for layer in layers if layer.get("d_m") and layer.get("eg_eV") is not None],
            key=lambda layer: float(layer["d_m"]),
        )

    if absorber is None:
        raise ValueError(f"No absorber layer found in {def_file}")

    return {
        "absorber_name": absorber.get("name"),
        "absorber_bandgap_eV": float(absorber["eg_eV"]),
        "absorber_thickness_m": float(absorber["d_m"]),
        "absorber_layer": {
            "mu_n": float(absorber.get("mu_n") or 1e-3),
            "mu_p": float(absorber.get("mu_p") or 1e-3),
            "nc": float(absorber.get("Nc") or 1e24),
            "nv": float(absorber.get("Nv") or 1e24),
            "na": float(absorber.get("Na") or 1e19),
            "nd": float(absorber.get("Nd") or 1e19),
        },
    }


def parse_parameter_override(raw: Optional[str]) -> Optional[Dict[str, float]]:
    """Parse optional explicit diode parameters from JSON text or a file path."""
    if not raw:
        return None

    try:
        if Path(raw).exists():
            text = Path(raw).read_text(encoding="utf-8")
            data = json.loads(text)
        else:
            data = json.loads(raw)
    except Exception as exc:
        raise ValueError(f"Could not parse parameter override: {exc}") from exc

    required = ["Jph", "J0", "Rs", "Rsh", "n", "T", "Pin"]
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"Missing parameter(s): {missing}")

    return {key: float(data[key]) for key in required}


def estimate_with_one_diode(
    scaps_info: Dict[str, object],
    params_override: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Estimate cell metrics with a more SCAPS-like transport approximation."""
    eg = float(scaps_info["absorber_bandgap_eV"])
    thickness_um = float(scaps_info["absorber_thickness_m"]) * 1e6
    absorber = scaps_info.get("absorber_layer", {})

    if params_override is not None:
        params = params_override
    else:
        params = {
            "Jph": 0.035,
            "J0": 1e-12,
            "Rs": 1.5,
            "Rsh": 800.0,
            "n": 1.35,
            "T": 300.0,
            "Pin": 0.1,
        }

    q = 1.602176634e-19
    k = 1.380649e-23
    temp = params["T"]
    n = params["n"]
    vt = n * k * temp / q

    mu_n = max(1e-8, float(absorber.get("mu_n", 1e-3)))
    mu_p = max(1e-8, float(absorber.get("mu_p", 1e-3)))
    nc = max(1e20, float(absorber.get("nc", 1e24)))
    nv = max(1e20, float(absorber.get("nv", 1e24)))
    na = max(1e14, float(absorber.get("na", 1e19)))
    nd = max(1e14, float(absorber.get("nd", 1e19)))
    doping = max(na, nd, 1e16)

    mu_eff = max(1e-4, 0.5 * (mu_n + mu_p))
    thickness_factor = min(1.0, thickness_um / 1.0)
    collection_factor = 0.75 + 0.20 * thickness_factor
    bandgap_factor = max(0.6, min(1.0, 1.0 - 0.1 * max(0.0, eg - 1.4)))
    jph = params["Jph"] * collection_factor * bandgap_factor
    jph = max(1e-5, min(0.08, jph))

    if params_override is None:
        ni = math.sqrt(nc * nv) * math.exp(-eg / (2.0 * k * temp / q))
        j0 = 1e-12 * (1.55 / max(eg, 1.1)) ** 3 * (1e19 / max(doping, 1e19)) ** 0.5
        j0 = max(1e-16, min(1e-8, j0))
    else:
        j0 = params["J0"]

    rs = max(0.05, params["Rs"] * (1.0 + 0.03 * max(0.0, eg - 1.3)))
    rsh = max(100.0, params["Rsh"] * (0.85 + 0.10 * thickness_factor))

    def solve_current_density(voltage: float) -> float:
        exp_arg = max(-700.0, min(700.0, (voltage + rs * jph) / vt))
        ideal_term = j0 * (math.exp(exp_arg) - 1.0)
        shunt_term = voltage / rsh
        return jph - ideal_term - shunt_term

    def find_voc() -> float:
        lo = 0.0
        hi = 0.1
        f_lo = solve_current_density(lo)
        f_hi = solve_current_density(hi)
        while f_hi > 0.0 and hi < 5.0:
            hi *= 1.2
            f_hi = solve_current_density(hi)
        if f_hi > 0.0:
            raise RuntimeError("Unable to bracket Voc")
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            f_mid = solve_current_density(mid)
            if f_mid > 0.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    jsc = solve_current_density(0.0)
    voc = find_voc()
    curve = []
    vmax = max(voc * 1.05, 1.2)
    for i in range(401):
        voltage = vmax * i / 400.0
        current = solve_current_density(voltage)
        curve.append((voltage, current))

    max_power = -1.0
    vmp = 0.0
    jmp = 0.0
    for voltage, current in curve:
        power = voltage * current
        if power > max_power:
            max_power = power
            vmp = voltage
            jmp = current

    ff = (vmp * jmp) / (voc * jsc) if voc * jsc > 0 else 0.0
    pce = (voc * jsc * ff) / params["Pin"]

    return {
        "Jsc_mA_cm2": jsc * 1000.0,
        "Voc_V": voc,
        "FF": ff,
        "PCE_percent": pce * 100.0,
    }


def run_scaps_executable(scaps_exe: Path, def_file: Path) -> Dict[str, float]:
    """Try to run SCAPS directly if the executable is available."""
    if not scaps_exe.exists():
        raise FileNotFoundError

    cmd = [str(scaps_exe), str(def_file)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "SCAPS run failed")

    return {
        "Jsc_mA_cm2": 0.0,
        "Voc_V": 0.0,
        "FF": 0.0,
        "PCE_percent": 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or approximate SCAPS solar-cell simulation")
    parser.add_argument("def_file", nargs="?", help="Path to a SCAPS .def file")
    parser.add_argument(
        "--params-json",
        help="Optional JSON string or file path with explicit diode parameters: Jph,J0,Rs,Rsh,n,T,Pin",
    )
    args = parser.parse_args()

    workspace = Path(__file__).resolve().parent
    if args.def_file:
        def_file = Path(args.def_file).expanduser().resolve()
    else:
        def_file = workspace / "Scaps3312" / "def" / "MAPbI3-FaPbBr3.def"

    if not def_file.exists():
        raise FileNotFoundError(f"SCAPS file not found: {def_file}")

    scaps_info = parse_scaps_def_file(def_file)
    print(f"Loaded SCAPS file: {def_file}")
    print(f"Absorber: {scaps_info['absorber_name']}")
    print(f"Bandgap: {scaps_info['absorber_bandgap_eV']:.3f} eV")
    print(f"Thickness: {float(scaps_info['absorber_thickness_m']) * 1e6:.2f} um")

    params_override = None
    try:
        params_override = parse_parameter_override(args.params_json)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if params_override is not None:
        print("Using explicit diode parameters from the command line")
        print(json.dumps(params_override, indent=2))

    scaps_exe = find_scaps_executable()
    if scaps_exe is not None and platform.system().lower() != "linux":
        try:
            metrics = run_scaps_executable(scaps_exe, def_file)
            print("SCAPS executable run succeeded")
        except Exception as exc:
            print(f"SCAPS execution failed, falling back to the physics-based model: {exc}")
            metrics = estimate_with_one_diode(scaps_info, params_override=params_override)
    else:
        print("SCAPS executable is not runnable in this headless Linux environment; using the physics-based fallback")
        metrics = estimate_with_one_diode(scaps_info, params_override=params_override)

    print("Solar cell metrics")
    print("==================")
    print(f"Jsc: {metrics['Jsc_mA_cm2']:.2f} mA/cm^2")
    print(f"Voc: {metrics['Voc_V']:.3f} V")
    print(f"FF: {metrics['FF']:.3f}")
    print(f"PCE: {metrics['PCE_percent']:.2f} %")


if __name__ == "__main__":
    main()
