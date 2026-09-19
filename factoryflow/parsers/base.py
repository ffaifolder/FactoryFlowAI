"""Stage 2 — Parse (shared types + interface).

A *deduction backup* is the document a customer attaches to justify a
short-payment. Formats vary wildly by customer, so each format gets its own
:class:`BackupParser`, all producing the same normalised :class:`DeductionBackup`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from ..money import to_decimal

# Canonical deduction types. Adopters can extend this set; it maps to GL
# accounts via config/rules.yaml -> gl_accounts.by_deduction_type.
DEDUCTION_TYPES = {
    "PROMOTION",
    "SHORTAGE",
    "DAMAGE",
    "DEFECTIVE",
    "FREIGHT",
    "TERM_DISCOUNT",
}


@dataclass
class LineItem:
    """One itemised line from a backup document."""

    item_code: str = ""
    upc: str = ""
    description: str = ""
    qty: Decimal = Decimal("0")
    extended_amount: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.qty = to_decimal(self.qty)
        self.extended_amount = to_decimal(self.extended_amount)


@dataclass
class DeductionBackup:
    """Normalised result of parsing a single backup file."""

    source_file: str
    customer_ref: str
    invoice_ref: str
    deduction_type: str
    deduction_total: Decimal
    currency: str = "USD"
    reason_code: str = ""
    line_items: list[LineItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.deduction_total = to_decimal(self.deduction_total)
        self.deduction_type = (self.deduction_type or "PROMOTION").upper()

    @property
    def itemised_total(self) -> Decimal:
        return sum((li.extended_amount for li in self.line_items), Decimal("0"))


class BackupParser(ABC):
    """Interface every format parser implements."""

    #: Human-readable format name, used in logs/summaries.
    format_name: str = "generic"

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Return True if this parser recognises the file at ``path``."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, path: Path) -> DeductionBackup:
        """Parse ``path`` into a :class:`DeductionBackup`."""
        raise NotImplementedError
