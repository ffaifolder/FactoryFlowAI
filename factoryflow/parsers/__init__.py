"""Backup parser registry.

Register a parser per customer/format and let :func:`get_parser` pick the right
one for a file. To add a format, implement :class:`~factoryflow.parsers.base.BackupParser`
and append an instance to :data:`DEFAULT_PARSERS`.
"""

from __future__ import annotations

from pathlib import Path

from .base import BackupParser, DeductionBackup, LineItem
from .csv_parser import VoltlineCsvParser
from .pdf_parser import RetailerPdfParser
from .xlsx_parser import DistributorXlsxParser

#: Order matters — the first parser whose ``can_parse`` returns True wins.
DEFAULT_PARSERS: list[BackupParser] = [
    VoltlineCsvParser(),
    DistributorXlsxParser(),
    RetailerPdfParser(),
]


def get_parser(path: str | Path, parsers: list[BackupParser] | None = None) -> BackupParser | None:
    """Return the first registered parser that can handle ``path``."""
    path = Path(path)
    for parser in parsers or DEFAULT_PARSERS:
        if parser.can_parse(path):
            return parser
    return None


def parse_backup(path: str | Path, parsers: list[BackupParser] | None = None) -> DeductionBackup:
    """Parse ``path`` with the first matching registered parser."""
    path = Path(path)
    parser = get_parser(path, parsers)
    if parser is None:
        raise ValueError(f"no registered parser for {path.name}")
    return parser.parse(path)


__all__ = [
    "BackupParser",
    "DeductionBackup",
    "LineItem",
    "DEFAULT_PARSERS",
    "get_parser",
    "parse_backup",
    "VoltlineCsvParser",
    "DistributorXlsxParser",
    "RetailerPdfParser",
]
