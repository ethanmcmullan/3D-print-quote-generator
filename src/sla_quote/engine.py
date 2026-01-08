from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .model import QuoteInput
from .pricing import volume_unit_discount_pct

@dataclass(frozen=True)
class LineItem:
    name: str
    cost: float

@dataclass(frozen=True)
class QuoteResult:
    quote_id: str
    currency: str
    qty: int
    unit_discount_pct: float
    line_items: List[LineItem]
    direct_cost: float
    overhead: float
    loaded_cost: float
    sell_price: float
    price_per_part: float

def _machine_rate(cfg: Dict[str, Any], printer: str) -> float:
    rates = cfg["rates"]["machine_rate_per_hr"]
    return float(rates.get(printer, rates.get("GENERIC_SLA", 0.0)))

def _labor_rate(cfg: Dict[str, Any], key: str) -> float:
    return float(cfg["rates"]["labor_rate_per_hr"][key])

def _resin_cfg(cfg: Dict[str, Any], resin: str) -> Dict[str, Any]:
    resins = cfg["materials"]["resins"]
    if resin not in resins:
        raise KeyError(f"Resin not found in config: {resin}")
    return resins[resin]

def compute_quote(q: QuoteInput, cfg: Dict[str, Any]) -> QuoteResult:
    currency = cfg.get("currency", "USD")
    qty = q.process.qty

    # policies
    overhead_pct = float(cfg["policies"]["overhead_pct"])
    margin_pct = float(cfg["policies"]["margin_pct"])
    expedite_default = float(cfg["policies"].get("expedite_multiplier_default", 1.0))
    expedite = float(q.options.expedite_multiplier or expedite_default)

    # resin/material
    resin = _resin_cfg(cfg, q.process.resin)
    cost_per_ml = float(resin["cost_per_ml"])
    waste_pct = float(resin.get("waste_pct", 0.0))

    # base costs
    material_cost = (q.process.part_volume_ml * qty) * (1.0 + waste_pct) * cost_per_ml

    machine_rate = _machine_rate(cfg, q.process.printer)
    machine_cost = q.process.print_hours * machine_rate

    # labor standards
    s = cfg["standards"]
    operator_rate = _labor_rate(cfg, "operator")
    qc_rate = _labor_rate(cfg, "qc")
    docs_rate = _labor_rate(cfg, "docs")

    def min_to_cost(minutes: float, rate_per_hr: float) -> float:
        return (minutes / 60.0) * rate_per_hr

    labor_cost = 0.0
    labor_cost += min_to_cost(float(s["setup_minutes_per_job"]), operator_rate)

    if q.options.wash_cure:
        labor_cost += min_to_cost(float(s["wash_cure_minutes_per_part"]) * qty, operator_rate)
    if q.options.support_removal:
        labor_cost += min_to_cost(float(s["support_removal_minutes_per_part"]) * qty, operator_rate)
    if q.options.finishing:
        labor_cost += min_to_cost(float(s["finishing_minutes_per_part"]) * qty, operator_rate)
    if q.options.packaging:
        labor_cost += min_to_cost(float(s["packaging_minutes_per_part"]) * qty, operator_rate)
    if q.options.docs_packet:
        labor_cost += min_to_cost(float(s["docs_minutes_per_job"]), docs_rate)
    if q.options.inspection:
        labor_cost += min_to_cost(float(s["inspection_minutes_per_job"]), qc_rate)

    # outside services
    outside_total = 0.0
    for svc in q.outside_services:
        outside_total += float(svc.vendor_cost) * (1.0 + float(svc.markup_pct))

    # expedite: apply to time-driven costs (machine + labor + outside). keep material as-is.
    machine_cost *= expedite
    labor_cost *= expedite
    outside_total *= expedite

    # direct cost and loaded cost
    line_items = [
        LineItem("Material", round(material_cost, 2)),
        LineItem("Machine Time", round(machine_cost, 2)),
        LineItem("Labor", round(labor_cost, 2)),
        LineItem("Outside Services", round(outside_total, 2)),
    ]
    direct_cost = material_cost + machine_cost + labor_cost + outside_total
    overhead = direct_cost * overhead_pct
    loaded = direct_cost + overhead

    # margin (sell price)
    sell = loaded / (1.0 - margin_pct) if margin_pct < 1.0 else loaded

    # volume discount applies to unit price (per marketing) — apply after margin
    unit_disc = volume_unit_discount_pct(cfg, qty)
    sell *= (1.0 - unit_disc)

    ppp = sell / qty

    return QuoteResult(
        quote_id=q.quote_id,
        currency=currency,
        qty=qty,
        unit_discount_pct=round(unit_disc, 4),
        line_items=line_items,
        direct_cost=round(direct_cost, 2),
        overhead=round(overhead, 2),
        loaded_cost=round(loaded, 2),
        sell_price=round(sell, 2),
        price_per_part=round(ppp, 2),
    )
