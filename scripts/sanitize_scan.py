"""Data-safety scan.

Greps the repository for a denylist of real-world tokens (real customer/brand
names, internal identifiers) and **fails with a non-zero exit code** if any are
found. Run this before publishing::

    python -m scripts.sanitize_scan        # or: python scripts/sanitize_scan.py

Where the denylist comes from
-----------------------------
The terms are intentionally **not** stored in this repository — putting the very
strings you are trying to keep out of a public repo into its source (even
encoded) would leak them. Instead they are loaded from, in order:

* the ``FACTORYFLOW_SANITIZE_TERMS`` environment variable (comma-separated), and
* a local ``.sanitize_blocklist`` file at the repo root (one term per line,
  ``#`` comments allowed).

``.sanitize_blocklist`` is git-ignored — keep your real terms there, locally or
in CI (e.g. a CI secret written to that file, or the env var). See
``.sanitize_blocklist.example`` for the format.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BLOCKLIST_FILE = ".sanitize_blocklist"

# Directories and file types the scan ignores.
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
SKIP_SUFFIXES = {".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pyc"}
# Vendored third-party minified bundles are not our content and legitimately
# contain coincidental substrings — skip them.
SKIP_NAME_SUFFIXES = (".min.js", ".min.css")
# Files that legitimately reference the denylist mechanism itself.
SKIP_NAMES = {BLOCKLIST_FILE}

THIS_FILE = Path(__file__).resolve()


def load_blocklist(root: str | Path) -> list[str]:
    """Load denylist terms from the env var and the local blocklist file."""
    terms: list[str] = []
    env = os.environ.get("FACTORYFLOW_SANITIZE_TERMS", "")
    terms += [t.strip() for t in env.split(",") if t.strip()]

    path = Path(root) / BLOCKLIST_FILE
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                terms.append(line)
    # De-duplicate, preserve order.
    seen: set[str] = set()
    return [t for t in terms if not (t.lower() in seen or seen.add(t.lower()))]


def scan_repo(root: str | Path, terms: list[str] | None = None) -> list[tuple[str, int, str]]:
    """Return a list of (relative_path, line_number, term) denylist hits."""
    root = Path(root).resolve()
    terms = terms if terms is not None else load_blocklist(root)
    needles = [(t, t.lower()) for t in terms]
    findings: list[tuple[str, int, str]] = []
    if not needles:
        return findings

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.resolve() == THIS_FILE:
            continue
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if path.name.endswith(SKIP_NAME_SUFFIXES):
            continue

        try:
            text = path.read_bytes().decode("latin-1", "ignore")
        except Exception:
            continue

        lower = text.lower()
        if not any(low in lower for (_, low) in needles):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            ll = line.lower()
            for original, low in needles:
                if low in ll:
                    findings.append((str(path.relative_to(root)), lineno, original))
    return findings


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    root = Path(argv[0]) if argv else THIS_FILE.parent.parent
    terms = load_blocklist(root)
    if not terms:
        print(
            "SANITIZE: no denylist terms configured. Set FACTORYFLOW_SANITIZE_TERMS "
            f"or create a local '{BLOCKLIST_FILE}' (see {BLOCKLIST_FILE}.example)."
        )
        return 0

    findings = scan_repo(root, terms)
    if findings:
        print(f"SANITIZE FAIL — {len(findings)} denylisted token(s) found:\n")
        for rel, lineno, token in findings:
            print(f"  {rel}:{lineno}  ->  {token!r}")
        print("\nRemove or replace these before publishing.")
        return 1
    print(f"SANITIZE OK — {len(terms)} term(s) checked, none found under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
