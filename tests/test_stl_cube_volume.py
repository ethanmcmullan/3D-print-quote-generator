from pathlib import Path

import pytest

from sla_quote.geometry import load_stl_metrics

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cube_stl_metrics() -> None:
    """
    cube_mm.stl is a 10mm cube:
      - volume = 10*10*10 mm^3 = 1000 mm^3 = 1.0 mL
      - extents = 10mm = 0.3937007874 inches
    """
    stl = REPO_ROOT / "examples" / "cube_mm.stl"
    m = load_stl_metrics(stl)

    assert m.is_watertight is True
    assert m.volume_ml == pytest.approx(1.0, rel=1e-6)

    x, y, z = m.bounds_in
    assert x == pytest.approx(0.3937, abs=0.005)
    assert y == pytest.approx(0.3937, abs=0.005)
    assert z == pytest.approx(0.3937, abs=0.005)
