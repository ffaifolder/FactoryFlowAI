"""A tiny, dependency-free PDF text writer/reader.

This exists so the demo can generate and parse *real* ``.pdf`` files with no
third-party libraries and no native build steps — handy in locked-down
environments. It writes one text line per ``Tj`` operator in an **uncompressed**
content stream, which makes extraction trivial and exact.

For real-world PDFs (scanned, compressed, multi-column) you should plug in a
proper library. Set the environment variable ``FACTORYFLOW_PDF_BACKEND=pdfplumber``
to route extraction through ``pdfplumber``; otherwise the built-in scanner is
used (it handles the uncompressed PDFs this project generates exactly).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_ESCAPE = str.maketrans({"\\": r"\\", "(": r"\(", ")": r"\)"})
_UNESCAPE = re.compile(r"\\([\\()])")
_TJ = re.compile(rb"\((?P<s>(?:[^()\\]|\\.)*)\)\s*Tj")


def write_text_pdf(path: str | Path, lines: list[str], *, font_size: int = 10) -> None:
    """Write ``lines`` to a minimal single-page PDF at ``path``."""
    path = Path(path)
    leading = font_size + 4
    body = ["BT", f"/F1 {font_size} Tf", f"1 0 0 1 50 780 Tm", f"{leading} TL"]
    for line in lines:
        body.append(f"({line.translate(_ESCAPE)}) Tj")
        body.append("T*")
    body.append("ET")
    content = "\n".join(body).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos
    path.write_bytes(bytes(out))


def extract_text_lines(path: str | Path) -> list[str]:
    """Return the text lines of a PDF, one per source line where possible."""
    path = Path(path)
    lines = _extract_with_pdfplumber(path)
    if lines is not None:
        return lines
    data = path.read_bytes()
    return [
        _UNESCAPE.sub(r"\1", m.group("s").decode("latin-1"))
        for m in _TJ.finditer(data)
    ]


def _extract_with_pdfplumber(path: Path) -> list[str] | None:
    """Use pdfplumber only when explicitly opted in via env var.

    Kept opt-in so the built-in scanner stays the default and a broken native
    install of the optional dependency can never disrupt the common path.
    """
    if os.environ.get("FACTORYFLOW_PDF_BACKEND", "").lower() != "pdfplumber":
        return None
    # Broad BaseException: a broken/native optional dep can raise a low-level
    # panic (not an ``Exception``) at import time; fall back cleanly if so.
    try:  # pragma: no cover - depends on optional dependency
        import pdfplumber  # type: ignore
    except BaseException:
        return None
    try:  # pragma: no cover - depends on optional dependency
        out: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                out.extend((page.extract_text() or "").splitlines())
        return out
    except BaseException:
        return None
