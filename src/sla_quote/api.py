from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .engine import compute_quote
from .model import QuoteInput
from .render_pdf import write_pdf
from .render_xlsx import write_xlsx
from .utils import load_config
from .geometry import load_stl_metrics, check_fits_printer


def _apply_cad_overrides(q: QuoteInput, cfg: Dict[str, Any], cad_file: Optional[Path]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"input_file": str(cad_file) if cad_file else None}

    if not cad_file:
        return meta

    cad_file = Path(cad_file)
    ext = cad_file.suffix.lower()

    if ext != ".stl":
        meta["cad_supported"] = False
        meta["cad_note"] = f"{ext} accepted but not automated; export to STL for geometry extraction."
        return meta

    m = load_stl_metrics(cad_file)
    check_fits_printer(cfg, q.process.printer, m.bounds_in)

    q.process.part_volume_ml = float(m.volume_ml)

    meta.update(
        {
            "cad_supported": True,
            "stl_is_watertight": bool(m.is_watertight),
            "stl_volume_ml": float(m.volume_ml),
            "stl_bounds_in": [float(m.bounds_in[0]), float(m.bounds_in[1]), float(m.bounds_in[2])],
        }
    )
    return meta


def generate_quote_from_dict(
    input_data: Dict[str, Any],
    cfg: Dict[str, Any],
    cad_file: Optional[Path] = None,
    out_dir: str | Path = "dist",
) -> Tuple[Dict[str, Any], Path, Path]:
    q = QuoteInput.model_validate(input_data)
    cad_meta = _apply_cad_overrides(q, cfg, cad_file)

    r = compute_quote(q, cfg)

    outdir = Path(out_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    pdf_path = outdir / f"QUOTE-{r.quote_id}.pdf"
    xlsx_path = outdir / f"QUOTE-{r.quote_id}.xlsx"

    write_pdf(pdf_path, q, r)
    write_xlsx(xlsx_path, q, r)

    result: Dict[str, Any] = {
        "quote_id": r.quote_id,
        "currency": r.currency,
        "qty": r.qty,
        "unit_discount_pct": r.unit_discount_pct,
        "line_items": [{"name": li.name, "cost": li.cost} for li in r.line_items],
        "direct_cost": r.direct_cost,
        "overhead": r.overhead,
        "loaded_cost": r.loaded_cost,
        "sell_price": r.sell_price,
        "price_per_part": r.price_per_part,
        **cad_meta,
    }
    return result, pdf_path, xlsx_path


def generate_quote_from_files(
    input_json_path: str | Path,
    config_path: str | Path,
    cad_file_path: Optional[str | Path] = None,
    out_dir: str | Path = "dist",
) -> Dict[str, Any]:
    cfg = load_config(config_path)

    input_json_path = Path(input_json_path)
    with input_json_path.open("r", encoding="utf-8") as f:
        input_data = json.load(f)

    cad_path = Path(cad_file_path) if cad_file_path else None
    result, pdf_path, xlsx_path = generate_quote_from_dict(
        input_data=input_data,
        cfg=cfg,
        cad_file=cad_path,
        out_dir=out_dir,
    )

    outdir = Path(out_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / f"QUOTE-{result['quote_id']}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    result["artifact_pdf"] = str(pdf_path)
    result["artifact_xlsx"] = str(xlsx_path)
    result["artifact_json"] = str(json_path)
    return result
