# SLA Quote Automation (Open Source)

Config-driven SLA 3D printing quote automation.

This project takes a standardized quote input (JSON) and generates:
- a PDF quote (customer-facing)
- an XLSX job log / job ticket (internal tracking)
- a JSON output record (for repeatability, audits, and future database storage)

It is designed to be:
- **fast** (instant quote generation once inputs are known)
- **configurable** (rates/materials/policies live in YAML, not hardcoded in code)
- **extensible** (CLI today; web integration tomorrow)

This repo is intentionally open-source. Shop-specific pricing can be kept private via a local config file that is not committed.

---

## Quickstart (2 minutes)

1. **Setup**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

2. **Generate a quote**
```bash
sla-quote examples/input_form4_basic.json --config config/default.example.yaml --out dist
ls -la dist
```

Outputs:
- `dist/QUOTE-<timestamp>.pdf`
- `dist/QUOTE-<timestamp>.xlsx`
- `dist/QUOTE-<timestamp>.json`

---

## How it works (non-technical)

You provide:
- which printer + material (resin)
- part volume (ml)
- quantity
- estimated print hours
- post-processing options (wash/cure, support removal, finishing, packaging, docs, inspection)
- optional outside services

The tool calculates:
- resin/material cost (with waste factor)
- machine time cost (print hours × machine rate)
- labor cost (based on standard minutes per step)
- overhead and margin
- volume discounts (up to 20% off unit price for duplicates)

Then it outputs a standardized quote and job log.

---

## Configuration

All pricing knobs are in YAML:
- `config/default.example.yaml` (committed example config)
- `config/local.yaml` (your real rates; keep private)

Create a private config by copying the example:
```bash
cp config/default.example.yaml config/local.yaml
```

Then run:
```bash
sla-quote examples/input_form4_basic.json --config config/local.yaml --out dist
```

---

## Project Structure

- `src/sla_quote/` — core quoting engine + CLI + renderers
- `config/` — printers/materials/rates/policies
- `examples/` — sample quote inputs
- `tests/` — sanity tests
- `dist/` — generated outputs (gitignored)

---

## Roadmap

### Near-term (to support "CAD file → instant quote")
- Accept STL input and compute part volume automatically
- Validate the part fits within the selected printer build volume
- Keep print-hours manual initially (from slicer), then add slicer integration

### Web integration (shop deployment)
- Wrap the engine in an HTTP API (e.g., FastAPI)
- Upload CAD → compute volume/fit → quote → email / checkout
- Persist quotes to a database (Postgres/Airtable/etc.)

---

## Contributing

See `CONTRIBUTING.md`.

---

## Disclaimer

This tool produces estimates. Final pricing may change after CAD review, tolerances, and QA requirements.
