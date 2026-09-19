"""Stage 4 — Allocate ("deduction coding").

Split one deduction across the coding key **Product Category x Sales Channel**,
down to **SKU**, weighted by the sales-dollar value of what shipped.

Method
------
1. Pick the SKU basis:
     * if the backup itemises specific SKUs (and ``restrict_to_backup_items``
       is on), allocate across the matching invoice lines only;
     * otherwise allocate across every line on the invoice;
     * if no invoice is available, fall back to the backup's own line items.
2. Weight each SKU by its shipped extended amount (``weight_basis``).
3. Distribute the deduction total across the weights with **largest-remainder**
   rounding, so the cents always re-sum to the exact total.
4. Resolve each SKU's category, channel, and GL account from ``rules.yaml``.

The result is a list of :class:`CodedSplit` — one row per SKU — that the Post
stage writes to the accounting system.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal

from .config import Rules
from .erp import Invoice, InvoiceLine
from .money import quantize
from .parsers.base import DeductionBackup


@dataclass
class CodedSplit:
    """One coded piece of a deduction, ready to post to the GL."""

    deduction_id: str
    source_file: str
    customer: str
    invoice_ref: str
    deduction_type: str
    reason_code: str
    category: str
    channel: str
    sku: str
    description: str
    weight: Decimal
    amount: Decimal
    gl_account: str
    currency: str = "USD"

    def as_json(self) -> dict:
        d = asdict(self)
        d["weight"] = str(self.weight)
        d["amount"] = str(self.amount)
        return d


def allocate_by_weights(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Split ``total`` proportionally to ``weights``, exact to the cent.

    Uses the largest-remainder method: floor every share, then hand the
    leftover cents to the shares with the biggest fractional parts. The returned
    amounts always sum to ``total`` exactly.
    """
    if not weights:
        return []
    sign = Decimal(-1) if total < 0 else Decimal(1)
    total_cents = int((abs(total) * 100).to_integral_value())
    weight_sum = sum(weights, Decimal("0"))

    if weight_sum <= 0:
        # Degenerate weights -> distribute evenly.
        weights = [Decimal(1)] * len(weights)
        weight_sum = Decimal(len(weights))

    raw = [Decimal(total_cents) * w / weight_sum for w in weights]
    base = [int(r) for r in raw]  # floor for non-negative r
    remainder = total_cents - sum(base)
    # Indices ordered by fractional part, largest first.
    order = sorted(range(len(raw)), key=lambda i: raw[i] - base[i], reverse=True)
    for i in range(remainder):
        base[order[i % len(order)]] += 1

    return [sign * Decimal(c) / 100 for c in base]


def _basis_lines(backup: DeductionBackup, invoice: Invoice | None, rules: Rules):
    """Return the (sku, description, weight) rows to allocate across."""
    if invoice and invoice.lines:
        backup_skus = {li.item_code for li in backup.line_items if li.item_code}
        if rules.restrict_to_backup_items and backup_skus:
            lines = [ln for ln in invoice.lines if ln.sku in backup_skus]
            if lines:
                return [(ln.sku, ln.description, ln.extended_amount) for ln in lines]
        return [(ln.sku, ln.description, ln.extended_amount) for ln in invoice.lines]

    # No usable invoice: fall back to the backup's own itemised lines.
    return [
        (li.item_code, li.description, li.extended_amount)
        for li in backup.line_items
        if li.item_code
    ]


def allocate_deduction(
    backup: DeductionBackup,
    invoice: Invoice | None,
    rules: Rules,
    *,
    deduction_id: str,
) -> list[CodedSplit]:
    """Code a single deduction into per-SKU :class:`CodedSplit` rows."""
    customer = backup.customer_ref or (invoice.customer if invoice else "")
    basis = _basis_lines(backup, invoice, rules)
    if not basis:
        # Nothing to allocate against — emit a single uncategorised split so the
        # amount is never silently dropped.
        return [
            CodedSplit(
                deduction_id=deduction_id,
                source_file=backup.source_file,
                customer=customer,
                invoice_ref=backup.invoice_ref,
                deduction_type=backup.deduction_type,
                reason_code=backup.reason_code,
                category=rules.categories.get("default", "Uncategorized"),
                channel=rules.channels.get("default", "Retail"),
                sku="",
                description="(unresolved — no invoice or backup line items)",
                weight=Decimal("0"),
                amount=quantize(backup.deduction_total),
                gl_account=rules.gl_accounts.get("default", "5900-Deductions-Uncategorized"),
                currency=backup.currency,
            )
        ]

    weights = [w for (_, _, w) in basis]
    amounts = allocate_by_weights(backup.deduction_total, weights)

    splits: list[CodedSplit] = []
    for (sku, description, weight), amount in zip(basis, amounts):
        category = rules.resolve_category(sku)
        channel = rules.resolve_channel(sku, customer)
        gl_account = rules.gl_account_for(
            deduction_type=backup.deduction_type,
            category=category,
            channel=channel,
        )
        splits.append(
            CodedSplit(
                deduction_id=deduction_id,
                source_file=backup.source_file,
                customer=customer,
                invoice_ref=backup.invoice_ref,
                deduction_type=backup.deduction_type,
                reason_code=backup.reason_code,
                category=category,
                channel=channel,
                sku=sku,
                description=description,
                weight=quantize(weight),
                amount=amount,
                gl_account=gl_account,
                currency=backup.currency,
            )
        )
    return splits
