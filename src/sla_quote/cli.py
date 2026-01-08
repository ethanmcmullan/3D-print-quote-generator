from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

from .utils import load_config
from .model import QuoteInput
from .engine import compute_quote
from .render_pdf import write_pdf
from .render_xlsx import write_xlsx

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sla-quote",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="SLA quote automation (JSON -> PDF + XLSX + JSON)",
        epilog=textwrap.dedent("""\
        Examples:
          sla-quote examples/input_form4_basic.json --config config/default.example.yaml --out dist
          sla-quote examples/input_viper_basic.json --out dist
        """),
    )
    p.add_argument("input", nargs="?", help="Path to quote input JSON")
    p.add_argument("--config", default="config/default.example.yaml", help="Path to YAML config")
    p.add_argument("--out", default="dist", help="Output directory")
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
    r = compute_quote(q, cfg)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    pdf_path = outdir / f"QUOTE-{r.quote_id}.pdf"
    xlsx_path = outdir / f"QUOTE-{r.quote_id}.xlsx"
    json_path = outdir / f"QUOTE-{r.quote_id}.json"

    write_pdf(pdf_path, q, r)
    write_xlsx(xlsx_path, q, r)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
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
        }, f, indent=2)

    print(f"Wrote: {pdf_path}")
    print(f"Wrote: {xlsx_path}")
    print(f"Wrote: {json_path}")
