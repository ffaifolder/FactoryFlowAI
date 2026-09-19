"""Dashboard builder smoke tests (both the zero-dep and Tabler renderers)."""

import json

from build_dashboard import build_dashboard
from build_dashboard_tabler import build_tabler_dashboard

LEDGER = [
    {
        "entry_id": "JE-1",
        "gl_account": "5010-TradePromo-Connectors-Retail",
        "amount": "100.00",
        "currency": "USD",
        "dimensions": {
            "deduction_id": "DED-1",
            "customer": "Beacon Components Co-op",
            "invoice_ref": "INV-1",
            "deduction_type": "PROMOTION",
            "category": "Connectors",
            "channel": "Retail",
            "sku": "VL-CON-10",
            "description": "Terminal Connector 10A",
        },
    }
]


def _write_ledger(tmp_path):
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps(LEDGER), encoding="utf-8")
    return p


def test_zero_dep_dashboard(tmp_path):
    ledger = _write_ledger(tmp_path)
    out = build_dashboard(ledger, tmp_path / "dash" / "index.html")
    html = out.read_text(encoding="utf-8")
    assert "Beacon Components Co-op" in html
    assert "__DATA__" not in html  # placeholder was substituted


def test_tabler_dashboard(tmp_path):
    ledger = _write_ledger(tmp_path)
    out = build_tabler_dashboard(ledger, tmp_path / "app" / "index.html")
    html = out.read_text(encoding="utf-8")
    assert "./assets/tabler.min.css" in html
    assert "./assets/apexcharts.min.js" in html
    assert "VL-CON-10" in html
    assert "__DATA__" not in html
