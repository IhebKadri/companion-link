"""Persistent local device identity for this PC daemon instance.

This ID is NOT a trust credential by itself — it's just a stable label so
the same daemon install is recognizable across restarts. Actual trust is
established later via the public-key pairing handshake (Sprint 1, Step 3).
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_IDENTITY_FILE = Path.home() / ".companion-link" / "identity.json"


def get_or_create_device_id() -> str:
    """Return a stable UUID identifying this PC installation."""
    _IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)

    if _IDENTITY_FILE.exists():
        try:
            data = json.loads(_IDENTITY_FILE.read_text(encoding="utf-8"))
            device_id = data["device_id"]
            if isinstance(device_id, str) and device_id:
                return device_id
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.warning("Corrupt identity file, regenerating: %s", exc)

    device_id = str(uuid.uuid4())
    _IDENTITY_FILE.write_text(json.dumps({"device_id": device_id}), encoding="utf-8")
    logger.info("Generated new device identity: %s", device_id)
    return device_id