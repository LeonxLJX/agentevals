"""Process-private directory for download-eligible export files.

Files served by ``/api/streaming/download`` are confined to this directory
rather than the shared system temp root, so only files this process explicitly
writes here are download-eligible.

Export names are derived from a per-process HMAC of the session id rather than
the raw id, keeping download URLs independent of client-supplied identifiers.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import tempfile
from pathlib import Path

EXPORT_DIR = Path(tempfile.mkdtemp(prefix="agentevals-exports-"))
# mkdtemp already restricts the dir to the owner; set it explicitly so the
# permission is guaranteed even if the creation call is ever changed.
EXPORT_DIR.chmod(0o700)

_NAME_KEY = secrets.token_bytes(32)


def export_name(seed: str, *, prefix: str, suffix: str) -> str:
    """Build a stable, opaque export filename for ``seed``.

    The same seed maps to the same name within a process run, so repeated
    writes for one session reuse a single file, while the name stays
    independent of the seed's value (it derives from a per-process key).
    """
    token = hmac.new(_NAME_KEY, seed.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{prefix}{token}{suffix}"
