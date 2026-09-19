"""Generate 100% synthetic invoices + deduction backups.

Everything here is invented: a fictional electrical-parts brand ("Voltline
Components"), made-up customers, SKUs, UPCs, and dollar figures. There is no
real-world data anywhere in this project — see DISCLAIMER.md and run
``scripts/sanitize_scan.py``.

Run directly::

    python -m scripts.generate_synthetic_data

or let ``python -m factoryflow.demo`` call :func:`ensure_synthetic_data`.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

# Allow running as a bare script (python scripts/generate_synthetic_data.py).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from factoryflow.money import quantize  # noqa: E402
from factoryflow.parsers._pdf_text import write_text_pdf  # noqa: E402

try:
    import openpyxl  # type: ignore

    _HAVE_OPENPYXL = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_OPENPYXL = False


# --- Fictional catalog -----------------------------------------------------
# sku -> (description, category, unit_price, synthetic UPC)
CATALOG: dict[str, tuple[str, str, str, str]] = {
    "VL-CON-10": ("Terminal Connector 10A", "Connectors", "1.85", "300000000010"),
    "VL-CON-50": ("Power Connector 50A", "Connectors", "4.25", "300000000050"),
    "VL-BRK-15": ("Circuit Breaker 15A", "Circuit-Breakers", "8.90", "300000000015"),
    "VL-BRK-100": ("Circuit Breaker 100A", "Circuit-Breakers", "42.00", "300000000100"),
    "VL-BRK-3P": ("Circuit Breaker 100A 3-Pole", "Circuit-Breakers", "96.00", "300000000103"),
    "VL-WIR-250": ("THHN Wire 250ft", "Wire-Cable", "32.00", "300000000250"),
    "VL-WIR-RL": ("THHN Wire Bulk Reel 5000ft", "Wire-Cable", "480.00", "300000005000"),
    "VL-RLY-12": ("Control Relay 12V", "Relays", "6.40", "300000000012"),
    "VL-RLY-24": ("Control Relay 24V", "Relays", "7.10", "300000000024"),
    "VL-CAP-100": ("Film Capacitor 100uF", "Capacitors", "3.30", "300000000101"),
    "VL-CAP-450": ("Motor Run Capacitor 450V", "Capacitors", "9.75", "300000000450"),
}

# --- Fictional customers ---------------------------------------------------
# name -> (terms, email domain)
CUSTOMERS: dict[str, tuple[str, str]] = {
    "Ridgeline Electric Supply": ("2/10 NET30", "ridgelineelectric.example"),
    "Beacon Components Co-op": ("1/15 NET45", "beaconcomponents.example"),
    "Ironclad Industrial Supply": ("NET30", "ironcladindustrial.example"),
    "Meridian Trade Group": ("NET15", "meridiantrade.example"),
    "Harbor Point Electronics": ("2/10 NET30", "harborpointelec.example"),
}

# --- Invoice specs: (invoice_no, po_no, customer, order_date, [(sku, qty)]) --
INVOICE_SPECS = [
    ("INV-100234", "PO-55021", "Beacon Components Co-op", "2026-07-14",
     [("VL-CON-10", 120), ("VL-RLY-12", 80), ("VL-CAP-100", 60)]),
    ("INV-100311", "PO-55090", "Ridgeline Electric Supply", "2026-07-18",
     [("VL-BRK-15", 90), ("VL-WIR-250", 40), ("VL-CON-50", 100)]),
    ("INV-100477", "PO-55145", "Ironclad Industrial Supply", "2026-07-22",
     [("VL-WIR-RL", 40), ("VL-BRK-3P", 24), ("VL-BRK-100", 36)]),
    ("INV-100588", "PO-55203", "Meridian Trade Group", "2026-07-29",
     [("VL-CAP-100", 72), ("VL-CON-10", 96), ("VL-RLY-24", 180)]),
    ("INV-100692", "PO-55271", "Harbor Point Electronics", "2026-08-03",
     [("VL-RLY-12", 64), ("VL-CAP-450", 300), ("VL-BRK-15", 48)]),
    ("INV-100754", "PO-55330", "Beacon Components Co-op", "2026-08-10",
     [("VL-CON-50", 120), ("VL-CON-10", 144), ("VL-RLY-24", 40)]),
    ("INV-100839", "PO-55402", "Ironclad Industrial Supply", "2026-08-17",
     [("VL-WIR-RL", 60), ("VL-CAP-100", 48), ("VL-BRK-3P", 30)]),
    ("INV-100892", "PO-55466", "Harbor Point Electronics", "2026-08-24",
     [("VL-CAP-100", 84), ("VL-RLY-12", 56), ("VL-CAP-450", 210)]),
]

# --- Deduction specs -------------------------------------------------------
# (msg_id, invoice_no, deduction_type, reason_code, format, mode, param)
#   mode "pct":   deduction_total = round(basis * param), whole-invoice.
#   mode "flat":  deduction_total = param, whole-invoice.
#   mode "items": itemise the given [(sku, short_qty)]; total = their extended.
DEDUCTION_SPECS = [
    ("msg_0001", "INV-100234", "SHORTAGE", "SHT-01", "csv", "items",
     [("VL-CON-10", 8), ("VL-CAP-100", 5)]),
    ("msg_0002", "INV-100311", "PROMOTION", "PRO-14", "csv", "pct", "0.05"),
    ("msg_0003", "INV-100477", "PROMOTION", "PRO-22", "xlsx", "pct", "0.08"),
    ("msg_0004", "INV-100588", "DAMAGE", "DMG-07", "pdf", "items",
     [("VL-CAP-100", 6)]),
    ("msg_0005", "INV-100692", "TERM_DISCOUNT", "TRM-01", "csv", "term", None),
    ("msg_0006", "INV-100754", "DEFECTIVE", "DEF-03", "xlsx", "items",
     [("VL-RLY-24", 4), ("VL-CON-10", 12)]),
    ("msg_0007", "INV-100839", "FREIGHT", "FRT-02", "pdf", "flat", "145.00"),
    ("msg_0008", "INV-100892", "PROMOTION", "PRO-31", "pdf", "pct", "0.06"),
]

_TERMS_RATE = {"2/10 NET30": Decimal("0.02"), "1/15 NET45": Decimal("0.01")}


def _build_invoices() -> dict[str, dict]:
    invoices: dict[str, dict] = {}
    for inv_no, po_no, customer, date, lines in INVOICE_SPECS:
        terms = CUSTOMERS[customer][0]
        out_lines = []
        for sku, qty in lines:
            desc, _cat, price, upc = CATALOG[sku]
            ext = quantize(Decimal(price) * qty)
            out_lines.append(
                {
                    "sku": sku,
                    "upc": upc,
                    "description": desc,
                    "qty": qty,
                    "unit_price": price,
                    "extended_amount": str(ext),
                }
            )
        invoices[inv_no] = {
            "invoice_number": inv_no,
            "po_number": po_no,
            "customer": customer,
            "order_date": date,
            "terms": terms,
            "currency": "USD",
            "lines": out_lines,
        }
    return invoices


def _backup_for_spec(spec, invoices) -> dict:
    msg_id, inv_no, dtype, reason, fmt, mode, param = spec
    invoice = invoices[inv_no]
    customer = invoice["customer"]
    inv_total = sum(Decimal(ln["extended_amount"]) for ln in invoice["lines"])

    items: list[dict] = []
    if mode == "items":
        for sku, short_qty in param:
            desc, _cat, price, upc = CATALOG[sku]
            ext = quantize(Decimal(price) * short_qty)
            items.append(
                {
                    "item_code": sku,
                    "upc": upc,
                    "description": desc,
                    "qty": short_qty,
                    "extended_amount": str(ext),
                }
            )
        total = sum(Decimal(i["extended_amount"]) for i in items)
    elif mode == "pct":
        total = quantize(inv_total * Decimal(param))
    elif mode == "flat":
        total = Decimal(param)
    elif mode == "term":
        total = quantize(inv_total * _TERMS_RATE.get(invoice["terms"], Decimal("0")))
    else:  # pragma: no cover - defensive
        raise ValueError(f"unknown mode {mode}")

    return {
        "msg_id": msg_id,
        "customer": customer,
        "invoice": inv_no,
        "deduction_type": dtype,
        "reason_code": reason,
        "currency": "USD",
        "deduction_total": str(quantize(total)),
        "format": fmt,
        "items": items,
    }


# --- Backup file writers ---------------------------------------------------
def _write_csv(path: Path, b: dict) -> None:
    lines = [
        f"customer,{b['customer']}",
        f"invoice,{b['invoice']}",
        f"deduction_type,{b['deduction_type']}",
        f"reason_code,{b['reason_code']}",
        f"currency,{b['currency']}",
        f"deduction_total,{b['deduction_total']}",
        "",
        "item_code,upc,description,qty,extended_amount",
    ]
    for it in b["items"]:
        lines.append(
            f"{it['item_code']},{it['upc']},{it['description']},{it['qty']},{it['extended_amount']}"
        )
    path.write_text("\n".join(lines) + "\n")


def _write_xlsx(path: Path, b: dict) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Deduction"
    for label, key in [
        ("Customer", "customer"),
        ("Invoice", "invoice"),
        ("Deduction Type", "deduction_type"),
        ("Reason Code", "reason_code"),
        ("Currency", "currency"),
        ("Deduction Total", "deduction_total"),
    ]:
        ws.append([label, b[key]])
    ws.append([])
    ws.append(["Item Code", "UPC", "Description", "Qty", "Extended"])
    for it in b["items"]:
        ws.append(
            [it["item_code"], it["upc"], it["description"], it["qty"], it["extended_amount"]]
        )
    wb.save(str(path))


def _write_pdf(path: Path, b: dict) -> None:
    lines = [
        "VOLTLINE COMPONENTS - DEDUCTION CHARGEBACK",
        f"Customer: {b['customer']}",
        f"Invoice: {b['invoice']}",
        f"Deduction Type: {b['deduction_type']}",
        f"Reason Code: {b['reason_code']}",
        f"Currency: {b['currency']}",
        f"Deduction Total: {b['deduction_total']}",
        "Item | UPC | Description | Qty | Extended",
    ]
    for it in b["items"]:
        lines.append(
            f"{it['item_code']} | {it['upc']} | {it['description']} | {it['qty']} | {it['extended_amount']}"
        )
    write_text_pdf(path, lines)


def _write_backup(directory: Path, filename_stem: str, b: dict) -> str:
    """Write a backup file in its format; fall back to CSV if xlsx unavailable."""
    fmt = b["format"]
    if fmt == "xlsx" and not _HAVE_OPENPYXL:
        fmt = "csv"
    filename = f"{filename_stem}.{fmt}"
    path = directory / filename
    if fmt == "csv":
        _write_csv(path, b)
    elif fmt == "xlsx":
        _write_xlsx(path, b)
    elif fmt == "pdf":
        _write_pdf(path, b)
    return filename


def generate_all(project_root: str | Path) -> None:
    """(Re)generate all synthetic invoices, backups, and inbox messages."""
    root = Path(project_root)
    invoices_dir = root / "data" / "invoices"
    backups_dir = root / "data" / "backups"
    inbox_dir = root / "sample_inbox"
    for d in (invoices_dir, backups_dir, inbox_dir):
        d.mkdir(parents=True, exist_ok=True)

    invoices = _build_invoices()
    for inv_no, invoice in invoices.items():
        (invoices_dir / f"{inv_no}.json").write_text(json.dumps(invoice, indent=2))

    for spec in DEDUCTION_SPECS:
        b = _backup_for_spec(spec, invoices)
        msg_dir = inbox_dir / b["msg_id"]
        msg_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{b['msg_id']}_{b['invoice']}_backup"

        filename = _write_backup(msg_dir, stem, b)
        # Keep a reference copy of every backup under data/backups/ too.
        _write_backup(backups_dir, stem, b)

        domain = CUSTOMERS[b["customer"]][1]
        message = {
            "message_id": b["msg_id"],
            "subject": f"Deduction on {b['invoice']} — {b['deduction_type']}",
            "sender": f"ap@{domain}",
            "received_at": "2026-09-01T09:15:00",
            "body": (
                f"Please see attached backup for a {b['deduction_type']} deduction "
                f"of {b['currency']} {b['deduction_total']} against {b['invoice']}."
            ),
        }
        (msg_dir / "message.json").write_text(json.dumps(message, indent=2))

    print(
        f"Generated {len(invoices)} invoices and {len(DEDUCTION_SPECS)} inbox messages "
        f"under {root}"
    )


def ensure_synthetic_data(project_root: str | Path) -> None:
    """Generate synthetic data only if it is not already present."""
    root = Path(project_root)
    has_invoices = any((root / "data" / "invoices").glob("*.json")) if (
        root / "data" / "invoices"
    ).exists() else False
    has_inbox = any(p.is_dir() for p in (root / "sample_inbox").iterdir()) if (
        root / "sample_inbox"
    ).exists() else False
    if not (has_invoices and has_inbox):
        generate_all(root)


def main() -> int:
    generate_all(_PROJECT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
