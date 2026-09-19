"""Example backup format B — the "Distributor claim workbook" (.xlsx).

Layout on the first worksheet: labelled metadata in column A/B at the top, a
blank row, then a table whose header row starts with ``Item Code``::

    Customer         | Ridgeline Electric Supply
    Invoice          | INV-100477
    Deduction Type   | PROMOTION
    Reason Code      | PRO-14
    Currency         | USD
    Deduction Total  | 1875.00
                     |
    Item Code | UPC | Description | Qty | Extended
    VL-WIR-250 | ... | THHN Wire 250ft | 60 | 1920.00

Requires ``openpyxl`` (an optional dependency). If it is not installed the
parser reports ``can_parse -> False`` so the pipeline simply skips this format.
"""

from __future__ import annotations

from pathlib import Path

from .base import BackupParser, DeductionBackup, LineItem

try:
    import openpyxl  # type: ignore

    _HAVE_OPENPYXL = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_OPENPYXL = False

_META_KEYS = {
    "customer": "customer",
    "invoice": "invoice",
    "deduction type": "deduction_type",
    "reason code": "reason_code",
    "currency": "currency",
    "deduction total": "deduction_total",
}


class DistributorXlsxParser(BackupParser):
    format_name = "distributor-xlsx"

    def can_parse(self, path: Path) -> bool:
        return _HAVE_OPENPYXL and path.suffix.lower() == ".xlsx"

    def parse(self, path: Path) -> DeductionBackup:
        if not _HAVE_OPENPYXL:  # pragma: no cover - guarded by can_parse
            raise RuntimeError("openpyxl is required to parse .xlsx backups")
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        ws = wb.active

        meta: dict[str, str] = {}
        items: list[LineItem] = []
        header: list[str] | None = None

        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if not any(cells):
                continue
            first = cells[0].lower()
            if header is None and first in ("item code", "item_code"):
                header = [c.lower().replace(" ", "_") for c in cells]
                continue
            if header is None:
                key = _META_KEYS.get(first)
                if key and len(cells) >= 2:
                    meta[key] = cells[1]
                continue
            record = dict(zip(header, cells))
            items.append(
                LineItem(
                    item_code=record.get("item_code", ""),
                    upc=record.get("upc", ""),
                    description=record.get("description", ""),
                    qty=record.get("qty", "0"),
                    extended_amount=record.get("extended", record.get("extended_amount", "0")),
                )
            )
        wb.close()

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
