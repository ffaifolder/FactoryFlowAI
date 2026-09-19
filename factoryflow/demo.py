"""One-command demo: ``python -m factoryflow.demo``.

Runs the whole pipeline on synthetic data with the mock adapters:

    ingest (sample_inbox/) -> parse -> resolve (mock ERP) -> allocate -> post
    (ledger.json), then renders dashboard/index.html.

Generates the synthetic data first if it is not already present. Everything is
offline and safe to run repeatedly.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from .accounting import MockAccountingClient
from .config import PROJECT_ROOT, load_rules
from .erp import MockERPClient
from .ingest import MockInboxSource
from .pipeline import Pipeline, RunResult


def _ensure_project_on_path() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def _money(value: Decimal) -> str:
    return f"${value:,.2f}"


def run_demo() -> RunResult:
    _ensure_project_on_path()
    from build_dashboard import build_dashboard  # noqa: WPS433 (local import by design)
    from build_dashboard_tabler import build_tabler_dashboard
    from scripts.generate_synthetic_data import ensure_synthetic_data

    inbox_dir = PROJECT_ROOT / "sample_inbox"
    invoices_dir = PROJECT_ROOT / "data" / "invoices"
    ledger_path = PROJECT_ROOT / "ledger.json"
    dashboard_path = PROJECT_ROOT / "dashboard" / "index.html"
    tabler_path = PROJECT_ROOT / "dashboard-app" / "index.html"

    # Generate synthetic invoices + inbox backups if they are missing.
    ensure_synthetic_data(PROJECT_ROOT)

    rules = load_rules()
    pipeline = Pipeline(
        source=MockInboxSource(inbox_dir),
        erp=MockERPClient(invoices_dir),
        accounting=MockAccountingClient(ledger_path),
        rules=rules,
    )
    result = pipeline.run()

    _print_summary(result)

    out = build_dashboard(ledger_path, dashboard_path)
    print(f"\nDashboard (zero-dep)   : {out}")
    tabler_out = build_tabler_dashboard(ledger_path, tabler_path)
    print(f"Dashboard (Tabler UI)  : {tabler_out}")
    return result


def _print_summary(result: RunResult) -> None:
    print("=" * 64)
    print("FactoryFlow AI — Deduction Coder :: demo run")
    print("=" * 64)
    print(f"Messages processed : {result.messages_processed}")
    print(f"Backups parsed     : {result.backups_parsed}")
    print(f"Deductions coded   : {result.deductions_coded}")
    print(f"Coded splits       : {len(result.splits)}")
    print(f"Total allocated    : {_money(result.total_allocated)}")
    if result.unresolved_invoices:
        print(f"Unresolved invoices: {', '.join(result.unresolved_invoices)}")
    if result.skipped_files:
        print(f"Skipped files      : {', '.join(result.skipped_files)}")

    by_customer: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_key: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for s in result.splits:
        by_customer[s.customer] += s.amount
        by_key[f"{s.category} / {s.channel}"] += s.amount

    print("\nBy customer:")
    for name, amount in sorted(by_customer.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {name:<32} {_money(amount):>14}")

    print("\nBy category / channel:")
    for key, amount in sorted(by_key.items(), key=lambda kv: kv[1], reverse=True):
        print(f"  {key:<40} {_money(amount):>14}")

    print(f"\nLedger written to  : {result.ledger_path}")


def main() -> int:
    run_demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
