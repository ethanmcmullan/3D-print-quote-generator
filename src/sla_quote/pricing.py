from __future__ import annotations

from typing import Any, Dict, List

def volume_unit_discount_pct(cfg: Dict[str, Any], qty: int) -> float:
    """
    Returns a unit discount percent based on qty tiers in config.
    Expects cfg['policies']['volume_discounts'] = [{min_qty, unit_discount_pct}, ...]
    """
    tiers: List[dict] = cfg.get("policies", {}).get("volume_discounts", []) or []
    best = 0.0
    for t in tiers:
        try:
            min_qty = int(t["min_qty"])
            pct = float(t["unit_discount_pct"])
        except Exception:
            continue
        if qty >= min_qty and pct > best:
            best = pct
    # clamp to [0, 0.20] by default; config can choose higher but marketing says "up to 20%"
    return max(0.0, min(best, 0.20))
