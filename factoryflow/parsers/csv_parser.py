"""Example backup format A — the "Voltline remittance CSV".

Layout: a small ``key,value`` metadata block, a blank line, then an itemised
table::

    customer,Beacon Components Co-op
    invoice,INV-100234
    deduction_type,SHORTAGE
    reason_code,SHT-01
    currency,USD
    deduction_total,412.50

    item_code,upc,description,qty,extended_amount
    VL-CON-10,300000000010,Terminal Connector 10A,24,44.40
    ...
"""

from __future__ import annotations

import csv
from pathlib import Path

from .base import BackupParser, DeductionBackup, LineItem


class VoltlineCsvParser(BackupParser):
    format_name = "voltline-csv"

    def can_parse(self, path: Path) -> bool:
        if path.suffix.lower() != ".csv":
            return False
        head = path.read_text(errors="ignore").lower()
        return "deduction_total" in head

    def parse(self, path: Path) -> DeductionBackup:
        rows = list(csv.reader(path.read_text().splitlines()))
        meta: dict[str, str] = {}
        items: list[LineItem] = []
        header: list[str] | None = None

        for row in rows:
            if not row or not any(cell.strip() for cell in row):
                continue
            if header is None and row[0].strip() == "item_code":
                header = [c.strip() for c in row]
                continue
            if header is None:
                # metadata "key,value" line
                if len(row) >= 2:
                    meta[row[0].strip().lower()] = row[1].strip()
                continue
            record = dict(zip(header, [c.strip() for c in row]))
            items.append(
                LineItem(
                    item_code=record.get("item_code", ""),
                    upc=record.get("upc", ""),
                    description=record.get("description", ""),
                    qty=record.get("qty", "0"),
                    extended_amount=record.get("extended_amount", "0"),
                )
            )

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
