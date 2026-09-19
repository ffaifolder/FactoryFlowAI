"""Stage 1 — Ingest.

Read an email inbox and surface each message together with its deduction
*backup* attachments (the PDF/CSV/XLSX files a customer sends to justify a
short-payment).

This is a **shell only**. The bundled :class:`MockInboxSource` reads from a
local ``sample_inbox/`` directory and needs no credentials. Real transports
(IMAP / Microsoft Graph / Gmail) are defined as stubs implementing the same
:class:`EmailSource` interface — fill them in per ``AGENTS.md``.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

# Attachment content types we treat as deduction backups.
BACKUP_SUFFIXES = {".csv", ".xlsx", ".pdf"}


@dataclass(frozen=True)
class Attachment:
    """A single email attachment stored on the local filesystem."""

    filename: str
    path: Path
    content_type: str = "application/octet-stream"

    @property
    def suffix(self) -> str:
        return Path(self.filename).suffix.lower()

    @property
    def is_backup(self) -> bool:
        return self.suffix in BACKUP_SUFFIXES


@dataclass(frozen=True)
class EmailMessage:
    """A normalised inbound message with its attachments."""

    message_id: str
    subject: str
    sender: str
    received_at: datetime
    body: str = ""
    attachments: list[Attachment] = field(default_factory=list)

    @property
    def backups(self) -> list[Attachment]:
        return [a for a in self.attachments if a.is_backup]


class EmailSource(ABC):
    """Interface for anything that yields inbound deduction emails.

    Implement this to connect a real mailbox. The rest of the pipeline only
    depends on :meth:`fetch_unread` returning :class:`EmailMessage` objects.
    """

    @abstractmethod
    def fetch_unread(self) -> Iterator[EmailMessage]:
        """Yield messages that have not yet been processed."""
        raise NotImplementedError

    def mark_processed(self, message_id: str) -> None:
        """Optionally flag a message as handled (no-op by default)."""


class MockInboxSource(EmailSource):
    """Reads a local ``sample_inbox/`` directory. No network, no credentials.

    Layout — one folder per message::

        sample_inbox/
          msg_0001/
            message.json      # {subject, sender, received_at, body}
            backup.csv        # one or more attachment files
          msg_0002/
            ...

    Any file in the folder other than ``message.json`` is treated as an
    attachment.
    """

    def __init__(self, inbox_dir: str | Path) -> None:
        self.inbox_dir = Path(inbox_dir)

    def fetch_unread(self) -> Iterator[EmailMessage]:
        if not self.inbox_dir.exists():
            return
        for msg_dir in sorted(p for p in self.inbox_dir.iterdir() if p.is_dir()):
            meta_path = msg_dir / "message.json"
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
            attachments = [
                Attachment(
                    filename=f.name,
                    path=f,
                    content_type=_guess_content_type(f.suffix),
                )
                for f in sorted(msg_dir.iterdir())
                if f.is_file() and f.name != "message.json"
            ]
            yield EmailMessage(
                message_id=meta.get("message_id", msg_dir.name),
                subject=meta.get("subject", ""),
                sender=meta.get("sender", ""),
                received_at=_parse_dt(meta.get("received_at")),
                body=meta.get("body", ""),
                attachments=attachments,
            )


def _guess_content_type(suffix: str) -> str:
    return {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pdf": "application/pdf",
    }.get(suffix.lower(), "application/octet-stream")


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime(1970, 1, 1)


# --------------------------------------------------------------------------
# Real-transport stubs. These intentionally raise NotImplementedError; see
# AGENTS.md for the contract an implementation must satisfy.
# --------------------------------------------------------------------------
class ImapEmailSource(EmailSource):
    """IMAP transport stub (e.g. Fastmail, Dovecot, generic IMAP).

    Implementation notes:
      * Connect with ``imaplib.IMAP4_SSL(host)`` and log in.
      * ``SELECT`` the deductions folder; ``SEARCH`` for UNSEEN.
      * For each message, ``FETCH (RFC822)``, parse with ``email.message_from_bytes``,
        write attachment payloads to a temp dir, and build :class:`Attachment`s.
      * In :meth:`mark_processed`, set the ``\\Seen`` flag.
    """

    def __init__(self, host: str, username: str, password: str, folder: str = "INBOX") -> None:
        self.host, self.username, self.password, self.folder = host, username, password, folder

    def fetch_unread(self) -> Iterator[EmailMessage]:  # pragma: no cover - stub
        raise NotImplementedError("Implement IMAP fetch — see AGENTS.md")


class GraphEmailSource(EmailSource):
    """Microsoft Graph (Office 365 / Outlook) transport stub.

    Implementation notes:
      * Authenticate via MSAL (client credentials or delegated flow).
      * GET ``/users/{id}/mailFolders/{folder}/messages?$filter=isRead eq false``.
      * For each message, GET ``/messages/{id}/attachments`` and decode
        ``contentBytes``.
      * :meth:`mark_processed` -> PATCH ``isRead: true``.
    """

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, user_id: str) -> None:
        self.tenant_id, self.client_id = tenant_id, client_id
        self.client_secret, self.user_id = client_secret, user_id

    def fetch_unread(self) -> Iterator[EmailMessage]:  # pragma: no cover - stub
        raise NotImplementedError("Implement Graph fetch — see AGENTS.md")


class GmailEmailSource(EmailSource):
    """Gmail API transport stub.

    Implementation notes:
      * Authenticate with OAuth (``google-auth`` / ``google-api-python-client``).
      * ``users().messages().list(userId='me', q='is:unread has:attachment')``.
      * ``users().messages().get`` then walk ``payload.parts`` for attachments,
        fetching each via ``attachments().get`` and base64url-decoding.
      * :meth:`mark_processed` -> ``modify`` removing the ``UNREAD`` label.
    """

    def __init__(self, credentials_path: str, token_path: str) -> None:
        self.credentials_path, self.token_path = credentials_path, token_path

    def fetch_unread(self) -> Iterator[EmailMessage]:  # pragma: no cover - stub
        raise NotImplementedError("Implement Gmail fetch — see AGENTS.md")
