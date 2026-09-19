# AGENTS.md — implementing adapters with an LLM

This file tells a coding agent (or a human) exactly how to extend FactoryFlow
from the bundled mocks to real systems. The architecture is interface-driven:
you implement small, well-defined interfaces and inject them into the
`Pipeline`. **You never modify the pipeline or the allocation engine.**

## Ground rules

1. **Keep synthetic data synthetic.** Never commit real customers, SKUs,
   invoices, dollars, or credentials. Run `python -m scripts.sanitize_scan`
   before every commit; it must exit 0.
2. **One interface per stage.** Add a new class implementing the interface;
   register it where the mock is wired (`factoryflow/demo.py` or your own
   entry point). Don't branch inside the pipeline.
3. **Money is `Decimal`.** Never introduce `float` for amounts. Use
   `factoryflow.money.to_decimal` / `quantize`.
4. **Business rules live in `config/rules.yaml`**, not in code.
5. **Validate:** add/extend tests in `tests/` and keep `pytest` green.

## The five interfaces

| Stage    | Interface (module)                          | Mock to mirror              |
|----------|---------------------------------------------|-----------------------------|
| Ingest   | `EmailSource` (`factoryflow/ingest.py`)     | `MockInboxSource`           |
| Parse    | `BackupParser` (`factoryflow/parsers/base.py`) | `VoltlineCsvParser` etc.|
| Resolve  | `ERPClient` (`factoryflow/erp.py`)          | `MockERPClient`             |
| Allocate | *(no adapter — pure logic in `allocate.py`)* | —                          |
| Post     | `AccountingClient` (`factoryflow/accounting.py`) | `MockAccountingClient` |

### 1. EmailSource — read a real inbox
Implement `fetch_unread() -> Iterator[EmailMessage]` and (optionally)
`mark_processed(message_id)`. Write each attachment to a temp path and wrap it
in an `Attachment`. Stubs with concrete API notes are already in `ingest.py`:
`ImapEmailSource`, `GraphEmailSource`, `GmailEmailSource`.

### 2. BackupParser — support a new backup format
Implement `can_parse(path) -> bool` and `parse(path) -> DeductionBackup`.
Return a normalised `DeductionBackup` (customer_ref, invoice_ref,
deduction_type, deduction_total, and `line_items` when the document itemises
SKUs). Register your parser in `factoryflow/parsers/__init__.py::DEFAULT_PARSERS`
(order matters — first `can_parse` wins). Model your parser on
`csv_parser.py` / `pdf_parser.py`.

### 3. ERPClient — fetch invoice lines
Implement `get_invoice(ref) -> Invoice | None`, where `ref` is an invoice **or**
PO number. Populate `Invoice.lines` with `InvoiceLine(sku, extended_amount, ...)`
— `extended_amount` is the shipped sales-dollar value allocation weights by.
Stubs with API notes: `QuickBooksERPClient`, `NetSuiteERPClient`, `SAPERPClient`.

### 4. Allocation — usually no code, just config
Allocation is generic and stays as-is. To change behaviour, edit `rules.yaml`:
category taxonomy, channel rules (including the bulk/industrial override),
GL mapping, and allocation options. Only touch `allocate.py` if you need a new
*weighting scheme* (e.g. weight by quantity instead of dollars) — add it behind
`allocation.weight_basis`.

### 5. AccountingClient — post to a real GL
Implement `post_split(split) -> str` (return the entry id). Debit the account
in `split.gl_account`, carry `category`/`channel` as classes/dimensions, and
reference `invoice_ref` in the memo. Stubs: `QuickBooksAccountingClient`,
`NetSuiteAccountingClient`.

## Wiring it together

```python
from factoryflow.config import load_rules
from factoryflow.pipeline import Pipeline

pipeline = Pipeline(
    source=MyImapSource(...),        # your EmailSource
    erp=MyNetSuiteClient(...),       # your ERPClient
    accounting=MyQuickBooksClient(...),  # your AccountingClient
    rules=load_rules("config/rules.yaml"),
    parsers=[MyCustomerAParser(), MyCustomerBParser()],  # optional
)
result = pipeline.run()
```

## Definition of done
- New adapter implements its interface; no pipeline edits.
- `pytest` is green; you added tests for the new adapter.
- `python -m scripts.sanitize_scan` exits 0.
- No `float` money, no committed secrets, no real identifiers.
