from pathlib import Path

import pytest

from sla_quote.api import generate_quote_from_files

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_quote_golden_stl_cube(tmp_path: Path) -> None:
    """
    Golden test: fixed input + default config + cube STL -> stable totals.
    This protects pricing math from accidental changes.
    """
    input_json = REPO_ROOT / "examples" / "input_form4_basic.json"
    cfg = REPO_ROOT / "config" / "default.example.yaml"
    stl = REPO_ROOT / "examples" / "cube_mm.stl"

    result = generate_quote_from_files(
        input_json_path=input_json,
        config_path=cfg,
        cad_file_path=stl,
        out_dir=tmp_path,
    )

    # core invariants
    assert result["quote_id"] == "DEMO-001"
    assert result["qty"] == 2
    assert result["unit_discount_pct"] == pytest.approx(0.05, abs=1e-9)

    # STL-derived checks
    assert result.get("cad_supported") is True
    assert result.get("stl_is_watertight") is True
    assert result.get("stl_volume_ml") == pytest.approx(1.0, rel=1e-6)

    # pricing checks (update these only if you intentionally change config/pricing logic)
    assert result["sell_price"] == pytest.approx(360.38, abs=0.05)
    assert result["price_per_part"] == pytest.approx(180.19, abs=0.05)

    # line items should remain stable for this case
    line_items = {li["name"]: li["cost"] for li in result["line_items"]}
    assert line_items["Material"] == pytest.approx(0.67, abs=0.05)
    assert line_items["Machine Time"] == pytest.approx(150.00, abs=0.01)
    assert line_items["Labor"] == pytest.approx(39.00, abs=0.01)
