"""Allocation engine tests — the core deduction-coding math."""

from decimal import Decimal

from factoryflow.allocate import allocate_by_weights, allocate_deduction
from factoryflow.config import load_rules
from factoryflow.erp import Invoice, InvoiceLine
from factoryflow.parsers.base import DeductionBackup, LineItem


def test_weights_sum_to_total_exactly():
    weights = [Decimal("432.00"), Decimal("336.00"), Decimal("297.00")]
    out = allocate_by_weights(Decimal("100.00"), weights)
    assert sum(out) == Decimal("100.00")


def test_largest_remainder_penny_split():
    # $1.00 across three equal shares -> one share gets the extra cent.
    out = allocate_by_weights(Decimal("1.00"), [Decimal(1)] * 3)
    assert sorted(out) == [Decimal("0.33"), Decimal("0.33"), Decimal("0.34")]
    assert sum(out) == Decimal("1.00")


def test_zero_weights_split_evenly():
    out = allocate_by_weights(Decimal("0.99"), [Decimal(0), Decimal(0), Decimal(0)])
    assert sum(out) == Decimal("0.99")
    assert all(a > 0 for a in out)


def test_allocate_deduction_sums_to_total():
    rules = load_rules()
    invoice = Invoice(
        invoice_number="INV-1",
        customer="Beacon Components Co-op",
        lines=[
            InvoiceLine(sku="VL-CON-10", extended_amount=Decimal("432.00")),
            InvoiceLine(sku="VL-RLY-12", extended_amount=Decimal("336.00")),
            InvoiceLine(sku="VL-CAP-100", extended_amount=Decimal("297.00")),
        ],
    )
    backup = DeductionBackup(
        source_file="b.csv",
        customer_ref="Beacon Components Co-op",
        invoice_ref="INV-1",
        deduction_type="PROMOTION",
        deduction_total=Decimal("100.00"),
    )
    splits = allocate_deduction(backup, invoice, rules, deduction_id="DED-1")
    assert sum(s.amount for s in splits) == Decimal("100.00")
    assert len(splits) == 3


def test_allocate_restricts_to_backup_items():
    rules = load_rules()
    invoice = Invoice(
        invoice_number="INV-2",
        customer="Beacon Components Co-op",
        lines=[
            InvoiceLine(sku="VL-CON-10", extended_amount=Decimal("432.00")),
            InvoiceLine(sku="VL-RLY-12", extended_amount=Decimal("336.00")),
        ],
    )
    backup = DeductionBackup(
        source_file="b.csv",
        customer_ref="Beacon Components Co-op",
        invoice_ref="INV-2",
        deduction_type="SHORTAGE",
        deduction_total=Decimal("50.00"),
        line_items=[LineItem(item_code="VL-CON-10", extended_amount=Decimal("28.80"))],
    )
    splits = allocate_deduction(backup, invoice, rules, deduction_id="DED-2")
    assert {s.sku for s in splits} == {"VL-CON-10"}
    assert sum(s.amount for s in splits) == Decimal("50.00")


def test_allocate_without_invoice_uses_backup_items():
    rules = load_rules()
    backup = DeductionBackup(
        source_file="b.csv",
        customer_ref="Harbor Point Electronics",
        invoice_ref="INV-missing",
        deduction_type="DAMAGE",
        deduction_total=Decimal("30.00"),
        line_items=[
            LineItem(item_code="VL-CAP-100", extended_amount=Decimal("10.00")),
            LineItem(item_code="VL-RLY-12", extended_amount=Decimal("20.00")),
        ],
    )
    splits = allocate_deduction(backup, None, rules, deduction_id="DED-3")
    assert sum(s.amount for s in splits) == Decimal("30.00")
    assert {s.sku for s in splits} == {"VL-CAP-100", "VL-RLY-12"}
