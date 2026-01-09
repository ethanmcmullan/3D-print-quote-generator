from __future__ import annotations

import sys
import argparse
import json
import textwrap
from pathlib import Path

from .utils import load_config
from .model import QuoteInput
from .engine import compute_quote
from .render_pdf import write_pdf
from .render_xlsx import write_xlsx
from .geometry import load_stl_metrics, check_fits_printer

ALLOWED_EXTS = {".sldprt", ".igs", ".iges", ".x_t", ".step", ".stp", ".stl"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sla-quote",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="SLA quote automation (JSON -> PDF + XLSX + JSON)",
        epilog=textwrap.dedent(
            """\
            Examples:
              sla-quote examples/input_form4_basic.json --config config/default.example.yaml --out dist
              sla-quote examples/input_form4_basic.json --file examples/cube_mm.stl --out dist

            Notes:
              - Accepted CAD types: .sldprt, .igs/.iges, .x_t, .step/.stp, .stl (<=10MB)
              - Instant geometry extraction is implemented for STL only (for now).
            """
        ),
    )
    p.add_argument("input", nargs="?", help="Path to quote input JSON")
    p.add_argument("--config", default="config/default.example.yaml", help="Path to YAML config")
    p.add_argument("--out", default="dist", help="Output directory")
    p.add_argument(
        "--file",
        help="CAD file (.stl/.step/.stp/.igs/.iges/.x_t/.sldprt) <=10MB. STL: auto volume+fit.",
    )
    return p


def main() -> None:
    p = build_parser()
    args = p.parse_args()

    if not args.input:
        p.print_help()
        return

    cfg = load_config(args.config)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    q = QuoteInput.model_validate(data)

    # Optional CAD upload handling
    if args.file:
        fpath = Path(args.file)
        if not fpath.exists():
            raise FileNotFoundError(f"CAD file not found: {fpath}")

        ext = fpath.suffix.lower()
        if ext not in ALLOWED_EXTS:
            raise ValueError(f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTS))}")

        size = fpath.stat().st_size
        if size > MAX_BYTES:
            raise ValueError(f"File too large: {size/1024/1024:.2f} MB. Max is 10 MB.")

        if ext == ".stl":
            m = load_stl_metrics(fpath)
            check_fits_printer(cfg, q.process.printer, m.bounds_in)

            # Auto-fill volume from STL (assumes STL units are mm)
            q.process.part_volume_ml = float(m.volume_ml)

            if not m.is_watertight:
                print("WARNING: STL is not watertight. Computed volume may be inaccurate.")

            print(
                f"STL volume_ml={m.volume_ml:.2f} | "
                f"bounds_in={m.bounds_in[0]:.2f}x{m.bounds_in[1]:.2f}x{m.bounds_in[2]:.2f}"
            )
        else:
            print(
                f"{ext} accepted for upload, but instant quoting is implemented for STL only right now. "
                "Export to STL for automated quoting (CAD->mesh conversion TBD)."
            )
            sys.exit(2)

    r = compute_quote(q, cfg)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    pdf_path = outdir / f"QUOTE-{r.quote_id}.pdf"
    xlsx_path = outdir / f"QUOTE-{r.quote_id}.xlsx"
    json_path = outdir / f"QUOTE-{r.quote_id}.json"

    write_pdf(pdf_path, q, r)
    write_xlsx(xlsx_path, q, r)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
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
                "input_file": str(args.file) if args.file else None,
            },
            f,
            indent=2,
        )

    print(f"Wrote: {pdf_path}")
    print(f"Wrote: {xlsx_path}")
    print(f"Wrote: {json_path}")
