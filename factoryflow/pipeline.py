"""The pipeline — wires the five stages together.

    ingest -> parse -> resolve -> allocate -> post

Every collaborator is injected as an interface, so swapping the mock inbox /
ERP / accounting for real adapters is a constructor change, nothing more.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .accounting import AccountingClient
from .allocate import CodedSplit, allocate_deduction
from .config import Rules
from .erp import ERPClient
from .ingest import EmailSource
from .parsers import BackupParser, get_parser


@dataclass
class RunResult:
    """Summary of a pipeline run."""

    messages_processed: int = 0
    backups_parsed: int = 0
    deductions_coded: int = 0
    splits: list[CodedSplit] = field(default_factory=list)
    unresolved_invoices: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    ledger_path: str = ""

    @property
    def total_allocated(self) -> Decimal:
        return sum((s.amount for s in self.splits), Decimal("0"))


class Pipeline:
    """Runs deduction coding end to end over an injected set of adapters."""

    def __init__(
        self,
        *,
        source: EmailSource,
        erp: ERPClient,
        accounting: AccountingClient,
        rules: Rules,
        parsers: list[BackupParser] | None = None,
    ) -> None:
        self.source = source
        self.erp = erp
        self.accounting = accounting
        self.rules = rules
        self.parsers = parsers

    def run(self) -> RunResult:
        result = RunResult()
        counter = 0

        for message in self.source.fetch_unread():
            result.messages_processed += 1
            for attachment in message.backups:
                parser = get_parser(attachment.path, self.parsers)
                if parser is None:
                    result.skipped_files.append(attachment.filename)
                    continue

                # Stage 2 — parse
                backup = parser.parse(attachment.path)
                result.backups_parsed += 1

                # Stage 3 — resolve
                invoice = self.erp.get_invoice(backup.invoice_ref)
                if invoice is None and backup.invoice_ref:
                    result.unresolved_invoices.append(backup.invoice_ref)

                # Stage 4 — allocate
                counter += 1
                deduction_id = f"DED-{counter:04d}"
                splits = allocate_deduction(
                    backup, invoice, self.rules, deduction_id=deduction_id
                )

                # Stage 5 — post
                self.accounting.post_splits(splits)

                result.deductions_coded += 1
                result.splits.extend(splits)

            self.source.mark_processed(message.message_id)

        # Persist the mock ledger if the client supports it.
        flush = getattr(self.accounting, "flush", None)
        if callable(flush):
            result.ledger_path = str(flush())

        return result
