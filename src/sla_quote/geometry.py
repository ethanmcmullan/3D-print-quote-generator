from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import trimesh

MM_PER_IN = 25.4
MM3_PER_ML = 1000.0

@dataclass(frozen=True)
class StlMetrics:
    volume_ml: float
    bounds_in: Tuple[float, float, float]  # (x, y, z) in inches
    is_watertight: bool

def _mm_to_in(x_mm: float) -> float:
    return x_mm / MM_PER_IN

def load_stl_metrics(stl_path: str | Path) -> StlMetrics:
    stl_path = Path(stl_path)
    if not stl_path.exists():
        raise FileNotFoundError(f"STL not found: {stl_path}")

    mesh = trimesh.load_mesh(str(stl_path), force="mesh")
    if mesh.is_empty:
        raise ValueError("STL mesh is empty.")

    # Trimesh works in whatever units the STL was authored in.
    # For MVP: assume STL units are millimeters (common in printing workflows).
    volume_mm3 = abs(float(mesh.volume))
    volume_ml = volume_mm3 / MM3_PER_ML

    # bounding box extents
    extents = mesh.extents  # (x,y,z) in same units as mesh
    x_in = _mm_to_in(float(extents[0]))
    y_in = _mm_to_in(float(extents[1]))
    z_in = _mm_to_in(float(extents[2]))

    return StlMetrics(
        volume_ml=volume_ml,
        bounds_in=(x_in, y_in, z_in),
        is_watertight=bool(mesh.is_watertight),
    )

def check_fits_printer(cfg: Dict[str, Any], printer_name: str, bounds_in: Tuple[float, float, float]) -> None:
    printers = cfg.get("printers", {})
    if printer_name not in printers:
        raise KeyError(f"Printer not found in config: {printer_name}")

    bv = printers[printer_name]["build_volume_in"]
    max_x = float(bv["x"])
    max_y = float(bv["y"])
    max_z = float(bv["z"])

    x, y, z = bounds_in
    # MVP: no rotation/orientation optimization; just compare extents
    if x > max_x or y > max_y or z > max_z:
        raise ValueError(
            f"Part does not fit {printer_name} build volume. "
            f"Part extents (in): {x:.2f} x {y:.2f} x {z:.2f} "
            f"Build volume (in): {max_x:.2f} x {max_y:.2f} x {max_z:.2f}"
        )
