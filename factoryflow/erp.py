"""Stage 3 — Resolve (ERP invoice lookup).

Given an invoice or PO number pulled from a deduction backup, fetch the
invoice's *shipped* line items from the ERP. The shipped sales-dollar value per
SKU is what allocation weights the deduction by.

The :class:`ERPClient` interface is the extension point. :class:`MockERPClient`
is backed by synthetic JSON invoices in ``data/invoices/``; real adapters
(QuickBooks / NetSuite / SAP) are stubs — see ``AGENTS.md``.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from .money import to_decimal


@dataclass
class InvoiceLine:
    """One shipped line on an invoice."""

    sku: str
    description: str = ""
    upc: str = ""
    qty: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    extended_amount: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.qty = to_decimal(self.qty)
        self.unit_price = to_decimal(self.unit_price)
        self.extended_amount = to_decimal(self.extended_amount)


@dataclass
class Invoice:
    """An invoice and its shipped lines."""

    invoice_number: str
    customer: str
    po_number: str = ""
    order_date: str = ""
    terms: str = ""
    currency: str = "USD"
    lines: list[InvoiceLine] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((li.extended_amount for li in self.lines), Decimal("0"))

    def line_for_sku(self, sku: str) -> InvoiceLine | None:
        return next((li for li in self.lines if li.sku == sku), None)


class ERPClient(ABC):
    """Interface for fetching invoices from an ERP / order system."""

    @abstractmethod
    def get_invoice(self, ref: str) -> Invoice | None:
        """Return the invoice for an invoice number or PO number, or None."""
        raise NotImplementedError


class MockERPClient(ERPClient):
    """In-memory ERP backed by synthetic ``data/invoices/*.json`` files."""

    def __init__(self, invoices_dir: str | Path) -> None:
        self.invoices_dir = Path(invoices_dir)
        self._by_invoice: dict[str, Invoice] = {}
        self._by_po: dict[str, Invoice] = {}
        self._load()

    def _load(self) -> None:
        if not self.invoices_dir.exists():
            return
        for path in sorted(self.invoices_dir.glob("*.json")):
            data = json.loads(path.read_text())
            invoice = Invoice(
                invoice_number=data["invoice_number"],
                customer=data.get("customer", ""),
                po_number=data.get("po_number", ""),
                order_date=data.get("order_date", ""),
                terms=data.get("terms", ""),
                currency=data.get("currency", "USD"),
                lines=[
                    InvoiceLine(
                        sku=ln["sku"],
                        description=ln.get("description", ""),
                        upc=ln.get("upc", ""),
                        qty=ln.get("qty", 0),
                        unit_price=ln.get("unit_price", 0),
                        extended_amount=ln.get("extended_amount", 0),
                    )
                    for ln in data.get("lines", [])
                ],
            )
            self._by_invoice[invoice.invoice_number] = invoice
            if invoice.po_number:
                self._by_po[invoice.po_number] = invoice

    def get_invoice(self, ref: str) -> Invoice | None:
        return self._by_invoice.get(ref) or self._by_po.get(ref)


# --------------------------------------------------------------------------
# Real ERP adapter stubs.
# --------------------------------------------------------------------------
class QuickBooksERPClient(ERPClient):
    """QuickBooks Online adapter stub.

    Implementation notes:
      * OAuth2 (Intuit). Query the ``Invoice`` entity via the Accounting API:
        ``SELECT * FROM Invoice WHERE DocNumber = '<ref>'``.
      * Map each ``Line`` of type ``SalesItemLineDetail`` to an
        :class:`InvoiceLine` (``ItemRef`` -> sku, ``Amount`` -> extended_amount,
        ``Qty`` -> qty). Terms come from ``SalesTermRef``.
    """

    def get_invoice(self, ref: str) -> Invoice | None:  # pragma: no cover - stub
        raise NotImplementedError("Implement QuickBooks invoice lookup — see AGENTS.md")


class NetSuiteERPClient(ERPClient):
    """NetSuite (SuiteTalk / REST) adapter stub.

    Implementation notes:
      * Token-based auth (TBA). GET ``/record/v1/invoice?q=tranId IS <ref>``.
      * Expand ``item`` sublist; map ``item.refName`` -> sku, ``amount`` ->
        extended_amount, ``quantity`` -> qty. Terms from ``terms.refName``.
    """

    def get_invoice(self, ref: str) -> Invoice | None:  # pragma: no cover - stub
        raise NotImplementedError("Implement NetSuite invoice lookup — see AGENTS.md")


class SAPERPClient(ERPClient):
    """SAP (S/4HANA OData) adapter stub.

    Implementation notes:
      * Call the Billing Document OData service, filter on ``BillingDocument``.
      * Map ``to_Item`` entries: ``Material`` -> sku, ``NetAmount`` ->
        extended_amount, ``BillingQuantity`` -> qty.
    """

    def get_invoice(self, ref: str) -> Invoice | None:  # pragma: no cover - stub
        raise NotImplementedError("Implement SAP invoice lookup — see AGENTS.md")
