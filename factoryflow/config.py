"""Configuration loading and business-rule resolution.

All business-specific behaviour (category taxonomy, channel rules, payment
terms, GL account mapping, allocation options) is described in
``config/rules.yaml`` and surfaced here through a typed :class:`Rules` object.

Keeping every rule in one config file and one resolver keeps the pipeline code
generic: adopters change ``rules.yaml``, not Python.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

# Repo layout anchors -------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "rules.yaml"


def _sku_unit_size(sku: str) -> int | None:
    """Best-effort numeric rating/size parsed from the trailing SKU token.

    ``"VL-BRK-100"`` -> ``100`` (amps); ``"VL-WIR-RL"`` -> ``None``. Adopters
    whose SKUs do not encode a number this way can instead drive rules off
    ``sku_suffix_in`` or add an explicit lookup.
    """
    token = sku.rsplit("-", 1)[-1]
    return int(token) if token.isdigit() else None


@dataclass(frozen=True)
class Rules:
    """Typed, in-memory view of ``rules.yaml`` with resolution helpers."""

    currency: str
    categories: dict[str, Any]
    channels: dict[str, Any]
    payment_terms: dict[str, float]
    gl_accounts: dict[str, Any]
    allocation: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    # --- category -----------------------------------------------------------
    def resolve_category(self, sku: str) -> str:
        """Map a SKU to its product category (exact match beats prefix)."""
        by_sku = self.categories.get("by_sku") or {}
        if sku in by_sku:
            return by_sku[sku]
        by_prefix = self.categories.get("by_prefix") or {}
        # Longest prefix wins, so more specific rules take precedence.
        for prefix in sorted(by_prefix, key=len, reverse=True):
            if sku.startswith(prefix):
                return by_prefix[prefix]
        return self.categories.get("default", "Uncategorized")

    # --- channel ------------------------------------------------------------
    def resolve_channel(self, sku: str, customer: str | None = None) -> str:
        """Assign a sales channel to a line.

        Order: SKU-level ``overrides`` -> customer default -> global default.
        This is where the "bulk / industrial" style rule lives.
        """
        for rule in self.channels.get("overrides") or []:
            if self._override_matches(rule.get("match", {}), sku):
                return rule["channel"]
        by_customer = self.channels.get("by_customer") or {}
        if customer and customer in by_customer:
            return by_customer[customer]
        return self.channels.get("default", "Retail")

    @staticmethod
    def _override_matches(match: dict[str, Any], sku: str) -> bool:
        if "sku_prefix" in match and not sku.startswith(match["sku_prefix"]):
            return False
        if "sku_suffix_in" in match:
            suffix = sku.rsplit("-", 1)[-1]
            if suffix not in match["sku_suffix_in"]:
                return False
        if "min_unit_size" in match:
            size = _sku_unit_size(sku)
            if size is None or size < match["min_unit_size"]:
                return False
        # A match block with no recognised keys never matches (avoids
        # accidentally routing every SKU through an empty rule).
        return bool(match)

    # --- payment terms ------------------------------------------------------
    def payment_term_rate(self, terms: str | None) -> Decimal:
        """Effective discount rate for a terms string (0 if unknown)."""
        if not terms:
            return Decimal("0")
        return Decimal(str(self.payment_terms.get(terms, 0)))

    # --- GL account ---------------------------------------------------------
    def gl_account_for(
        self, *, deduction_type: str, category: str, channel: str
    ) -> str:
        """Resolve the GL account for a coded split.

        Precedence: deduction-type map -> category|channel map -> computed
        promo account -> default.
        """
        by_type = self.gl_accounts.get("by_deduction_type") or {}
        if deduction_type in by_type and by_type[deduction_type]:
            return by_type[deduction_type]
        by_cc = self.gl_accounts.get("by_category_channel") or {}
        key = f"{category}|{channel}"
        if key in by_cc:
            return by_cc[key]
        prefix = self.gl_accounts.get("promo_prefix")
        if prefix:
            cat = category.replace(" ", "")
            return f"{prefix}-{cat}-{channel}"
        return self.gl_accounts.get("default", "5900-Deductions-Uncategorized")

    # --- allocation options -------------------------------------------------
    @property
    def restrict_to_backup_items(self) -> bool:
        return bool(self.allocation.get("restrict_to_backup_items", True))

    @property
    def weight_basis(self) -> str:
        return str(self.allocation.get("weight_basis", "extended_amount"))


def load_rules(path: str | Path | None = None) -> Rules:
    """Load and validate ``rules.yaml`` into a :class:`Rules` object."""
    rules_path = Path(path) if path else DEFAULT_RULES_PATH
    if not rules_path.exists():
        raise FileNotFoundError(f"rules file not found: {rules_path}")
    data = yaml.safe_load(rules_path.read_text()) or {}
    return Rules(
        currency=data.get("currency", "USD"),
        categories=data.get("categories", {}),
        channels=data.get("channels", {}),
        payment_terms=data.get("payment_terms", {}),
        gl_accounts=data.get("gl_accounts", {}),
        allocation=data.get("allocation", {}),
        raw=data,
    )
