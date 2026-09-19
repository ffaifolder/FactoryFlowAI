"""Example backup format C — the "Retailer chargeback PDF".

Text layout (one logical line per row)::

    VOLTLINE COMPONENTS - DEDUCTION CHARGEBACK
    Customer: Harbor Point Electronics
    Invoice: INV-100892
    Deduction Type: DAMAGE
    Reason Code: DMG-07
    Currency: USD
    Deduction Total: 233.10
    Item | UPC | Description | Qty | Extended
    VL-CAP-100 | 300000000101 | Film Capacitor 100uF | 12 | 39.60
    ...

Text is extracted by :mod:`factoryflow.parsers._pdf_text`, which uses
``pdfplumber`` when available and a built-in scanner otherwise.
"""

from __future__ import annotations

from pathlib import Path

from ._pdf_text import extract_text_lines
from .base import BackupParser, DeductionBackup, LineItem

_META_KEYS = {
    "customer": "customer",
    "invoice": "invoice",
    "deduction type": "deduction_type",
    "reason code": "reason_code",
    "currency": "currency",
    "deduction total": "deduction_total",
}


class RetailerPdfParser(BackupParser):
    format_name = "retailer-pdf"

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def parse(self, path: Path) -> DeductionBackup:
        lines = [ln.strip() for ln in extract_text_lines(path) if ln.strip()]
        meta: dict[str, str] = {}
        items: list[LineItem] = []
        in_table = False

        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if not in_table:
                    # header row (contains "Description") switches us on
                    if any(p.lower() == "description" for p in parts):
                        in_table = True
                    continue
                if len(parts) >= 5:
                    items.append(
                        LineItem(
                            item_code=parts[0],
                            upc=parts[1],
                            description=parts[2],
                            qty=parts[3],
                            extended_amount=parts[4],
                        )
                    )
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                mapped = _META_KEYS.get(key.strip().lower())
                if mapped:
                    meta[mapped] = value.strip()

        return DeductionBackup(
            source_file=path.name,
            customer_ref=meta.get("customer", ""),
            invoice_ref=meta.get("invoice", ""),
            deduction_type=meta.get("deduction_type", "PROMOTION"),
            deduction_total=meta.get("deduction_total", "0"),
            currency=meta.get("currency", "USD"),
            reason_code=meta.get("reason_code", ""),
            line_items=items,
        )
