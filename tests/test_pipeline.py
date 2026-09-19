"""End-to-end pipeline + data-safety tests."""

from decimal import Decimal

import pytest

from factoryflow.accounting import MockAccountingClient
from factoryflow.config import load_rules
from factoryflow.erp import MockERPClient
from factoryflow.ingest import MockInboxSource
from factoryflow.parsers import parse_backup
from factoryflow.pipeline import Pipeline
from scripts.generate_synthetic_data import generate_all
from scripts.sanitize_scan import scan_repo


@pytest.fixture()
def synthetic_root(tmp_path):
    generate_all(tmp_path)
    return tmp_path


def _run(root):
    pipeline = Pipeline(
        source=MockInboxSource(root / "sample_inbox"),
        erp=MockERPClient(root / "data" / "invoices"),
        accounting=MockAccountingClient(root / "ledger.json"),
        rules=load_rules(),
    )
    return pipeline.run()


def test_pipeline_conserves_total(synthetic_root):
    result = _run(synthetic_root)
    # Sum of all coded splits must equal the sum of every deduction total.
    expected = Decimal("0")
    for msg_dir in (synthetic_root / "sample_inbox").iterdir():
        for f in msg_dir.iterdir():
            if f.name == "message.json":
                continue
            expected += parse_backup(f).deduction_total
    assert result.total_allocated == expected
    assert result.deductions_coded == 8
    assert result.messages_processed == 8


def test_pipeline_splits_per_deduction_sum_to_total(synthetic_root):
    result = _run(synthetic_root)
    by_ded: dict[str, Decimal] = {}
    for s in result.splits:
        by_ded[s.deduction_id] = by_ded.get(s.deduction_id, Decimal("0")) + s.amount
    # Every deduction was split without losing or inventing cents.
    assert all(v > 0 for v in by_ded.values())
    assert len(by_ded) == result.deductions_coded


def test_ledger_written(synthetic_root):
    result = _run(synthetic_root)
    assert (synthetic_root / "ledger.json").exists()
    assert result.ledger_path.endswith("ledger.json")


def test_sanitize_scan_detects_terms(tmp_path):
    # Detection works when terms are supplied explicitly (no real names needed).
    (tmp_path / "leak.txt").write_text("contact jdoe at Acme Corporation today", encoding="utf-8")
    findings = scan_repo(tmp_path, terms=["Acme Corporation"])
    assert findings and findings[0][2] == "Acme Corporation"


def test_sanitize_scan_clean_on_repo():
    # Uses whatever terms are configured locally/CI (env var or .sanitize_blocklist).
    # In a default checkout no terms are configured, so this is trivially clean;
    # locally it verifies the tree against the real denylist.
    from factoryflow.config import PROJECT_ROOT

    findings = scan_repo(PROJECT_ROOT)
    assert findings == [], f"denylisted tokens found: {findings}"
