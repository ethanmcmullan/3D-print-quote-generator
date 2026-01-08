from __future__ import annotations

from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from .engine import QuoteResult
from .model import QuoteInput

def write_pdf(outpath: str | Path, q: QuoteInput, r: QuoteResult) -> Path:
    outpath = Path(outpath)
    c = canvas.Canvas(str(outpath), pagesize=LETTER)
    w, h = LETTER

    y = h - 1.0 * inch
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1.0 * inch, y, "QUOTE")
    y -= 0.35 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.0 * inch, y, f"Quote ID: {r.quote_id}")
    y -= 0.2 * inch
    c.drawString(1.0 * inch, y, f"Customer: {q.customer.name}")
    y -= 0.2 * inch
    c.drawString(1.0 * inch, y, f"Part: {q.part.name} ({q.part.part_number} rev {q.part.revision})")
    y -= 0.2 * inch
    c.drawString(1.0 * inch, y, f"Printer: {q.process.printer} | Resin: {q.process.resin}")
    y -= 0.2 * inch
    c.drawString(1.0 * inch, y, f"Qty: {r.qty} | Print Hours: {q.process.print_hours}")
    y -= 0.35 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Line Items")
    y -= 0.2 * inch

    c.setFont("Helvetica", 11)
    for li in r.line_items:
        c.drawString(1.0 * inch, y, li.name)
        c.drawRightString(w - 1.0 * inch, y, f"{r.currency} {li.cost:,.2f}")
        y -= 0.2 * inch

    y -= 0.10 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1.0 * inch, y, "Sell Price (Pre-Tax)")
    c.drawRightString(w - 1.0 * inch, y, f"{r.currency} {r.sell_price:,.2f}")
    y -= 0.2 * inch

    c.drawString(1.0 * inch, y, "Price / Part")
    c.drawRightString(w - 1.0 * inch, y, f"{r.currency} {r.price_per_part:,.2f}")
    y -= 0.2 * inch

    if r.unit_discount_pct > 0:
        c.setFont("Helvetica", 10)
        c.drawString(1.0 * inch, y, f"Volume discount applied: {r.unit_discount_pct*100:.1f}%")
        y -= 0.2 * inch

    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(1.0 * inch, y, "Estimate only. Final pricing may change after CAD review, tolerances, and QA requirements.")

    c.showPage()
    c.save()
    return outpath
