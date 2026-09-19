"""Business-rule resolution tests (categories, channels, GL, terms)."""

from decimal import Decimal

from factoryflow.config import load_rules


def test_category_resolution():
    rules = load_rules()
    assert rules.resolve_category("VL-CON-10") == "Connectors"
    assert rules.resolve_category("VL-CAP-100") == "Capacitors"
    assert rules.resolve_category("XX-YYY-1") == "Uncategorized"


def test_bulk_industrial_channel_rule():
    rules = load_rules()
    # Bulk reels / 3-pole gear route to Industrial regardless of customer.
    assert rules.resolve_channel("VL-WIR-RL", "Harbor Point Electronics") == "Industrial"
    assert rules.resolve_channel("VL-BRK-3P", "Beacon Components Co-op") == "Industrial"
    # High-amperage breaker via numeric rating suffix.
    assert rules.resolve_channel("VL-BRK-100", "Beacon Components Co-op") == "Industrial"
    # A 15A breaker stays on the customer's default channel.
    assert rules.resolve_channel("VL-BRK-15", "Beacon Components Co-op") == "Retail"


def test_customer_default_channel():
    rules = load_rules()
    assert rules.resolve_channel("VL-CON-10", "Ridgeline Electric Supply") == "Distributor"
    assert rules.resolve_channel("VL-CON-10", "Harbor Point Electronics") == "Ecommerce"
    assert rules.resolve_channel("VL-CON-10", "Unknown Customer") == "Retail"


def test_gl_account_precedence():
    rules = load_rules()
    # deduction-type map wins first
    assert rules.gl_account_for(
        deduction_type="FREIGHT", category="Capacitors", channel="Retail"
    ) == "5410-Freight-Out"
    # explicit category|channel map next
    assert rules.gl_account_for(
        deduction_type="PROMOTION", category="Connectors", channel="Retail"
    ) == "5010-TradePromo-Connectors-Retail"
    # computed promo fallback
    assert rules.gl_account_for(
        deduction_type="PROMOTION", category="Capacitors", channel="Ecommerce"
    ) == "5000-TradePromo-Capacitors-Ecommerce"


def test_payment_term_rate():
    rules = load_rules()
    assert rules.payment_term_rate("2/10 NET30") == Decimal("0.02")
    assert rules.payment_term_rate("NET30") == Decimal("0")
    assert rules.payment_term_rate(None) == Decimal("0")
