"""Parser round-trip tests over generated synthetic backups."""

from decimal import Decimal

import pytest

from factoryflow.parsers import parse_backup
from factoryflow.parsers._pdf_text import extract_text_lines, write_text_pdf
from scripts.generate_synthetic_data import _HAVE_OPENPYXL, generate_all


@pytest.fixture()
def synthetic_root(tmp_path):
    generate_all(tmp_path)
    return tmp_path


def _find(root, ext):
    return sorted(root.glob(f"data/backups/*.{ext}"))


def test_csv_parser_roundtrip(synthetic_root):
    csvs = _find(synthetic_root, "csv")
    assert csvs, "expected at least one CSV backup"
    backup = parse_backup(csvs[0])
    assert backup.invoice_ref.startswith("INV-")
    assert backup.deduction_total > 0
    assert backup.deduction_type in {
        "PROMOTION", "SHORTAGE", "DAMAGE", "DEFECTIVE", "FREIGHT", "TERM_DISCOUNT"
    }


def test_pdf_parser_roundtrip(synthetic_root):
    pdfs = _find(synthetic_root, "pdf")
    assert pdfs, "expected at least one PDF backup"
    backup = parse_backup(pdfs[0])
    assert backup.customer_ref
    assert backup.deduction_total > 0


def test_pdf_text_writer_reader(tmp_path):
    lines = ["Invoice: INV-123", "Deduction Total: 42.50", "VL-CON-10 | x | Connector | 3 | 10.80"]
    path = tmp_path / "sample.pdf"
    write_text_pdf(path, lines)
    assert path.read_bytes().startswith(b"%PDF-")
    out = extract_text_lines(path)
    assert "Invoice: INV-123" in out


@pytest.mark.skipif(not _HAVE_OPENPYXL, reason="openpyxl not installed")
def test_xlsx_parser_roundtrip(synthetic_root):
    xlsxs = _find(synthetic_root, "xlsx")
    assert xlsxs, "expected at least one XLSX backup"
    backup = parse_backup(xlsxs[0])
    assert backup.invoice_ref.startswith("INV-")
    assert backup.deduction_total > 0
