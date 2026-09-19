"""Stage 5 — Post.

Write each coded split to the correct GL account in the accounting system.

:class:`AccountingClient` is the interface. :class:`MockAccountingClient` writes
a local ``ledger.json`` so the demo is fully offline and inspectable; real
adapters (QuickBooks / NetSuite) are stubs — see ``AGENTS.md``.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from .allocate import CodedSplit


class AccountingClient(ABC):
    """Interface for posting coded splits to a GL / accounting system."""

    @abstractmethod
    def post_split(self, split: CodedSplit) -> str:
        """Post one split; return the accounting system's entry id."""
        raise NotImplementedError

    def post_splits(self, splits: list[CodedSplit]) -> list[str]:
        """Post many splits; default posts them one at a time."""
        return [self.post_split(s) for s in splits]


class MockAccountingClient(AccountingClient):
    """Appends journal entries to a local ``ledger.json`` file.

    Each entry records the GL account, amount, and the full set of coding
    dimensions so the ledger is self-describing and drives the dashboard.
    """

    def __init__(self, ledger_path: str | Path) -> None:
        self.ledger_path = Path(ledger_path)
        self.entries: list[dict] = []

    def post_split(self, split: CodedSplit) -> str:
        entry_id = f"JE-{uuid.uuid4().hex[:12]}"
        self.entries.append(
            {
                "entry_id": entry_id,
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "gl_account": split.gl_account,
                "amount": str(split.amount),
                "currency": split.currency,
                "memo": f"Deduction {split.deduction_id} / {split.deduction_type}"
                f" / inv {split.invoice_ref}",
                "dimensions": {
                    "deduction_id": split.deduction_id,
                    "source_file": split.source_file,
                    "customer": split.customer,
                    "invoice_ref": split.invoice_ref,
                    "deduction_type": split.deduction_type,
                    "reason_code": split.reason_code,
                    "category": split.category,
                    "channel": split.channel,
                    "sku": split.sku,
                    "description": split.description,
                },
            }
        )
        return entry_id

    def flush(self) -> Path:
        """Persist all posted entries to ``ledger.json`` and return the path."""
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(self.entries, indent=2))
        return self.ledger_path


# --------------------------------------------------------------------------
# Real accounting adapter stubs.
# --------------------------------------------------------------------------
class QuickBooksAccountingClient(AccountingClient):
    """QuickBooks Online adapter stub.

    Implementation notes:
      * OAuth2 (Intuit). Create a ``JournalEntry`` via the Accounting API with
        two ``Line`` entries (debit the deduction/expense account named by
        ``split.gl_account``, credit A/R).
      * Attach coding dimensions as ``ClassRef`` / ``DepartmentRef`` or custom
        fields (category/channel), and the invoice ref in ``PrivateNote``.
    """

    def post_split(self, split: CodedSplit) -> str:  # pragma: no cover - stub
        raise NotImplementedError("Implement QuickBooks posting — see AGENTS.md")


class NetSuiteAccountingClient(AccountingClient):
    """NetSuite adapter stub.

    Implementation notes:
      * Token-based auth. POST a ``journalEntry`` record via SuiteTalk REST.
      * Each line: ``account`` = mapped GL, ``debit``/``credit`` = amount, and
        classification fields (``class``, ``department``, ``location``) carrying
        category/channel. Reference the invoice in ``memo``.
    """

    def post_split(self, split: CodedSplit) -> str:  # pragma: no cover - stub
        raise NotImplementedError("Implement NetSuite posting — see AGENTS.md")
