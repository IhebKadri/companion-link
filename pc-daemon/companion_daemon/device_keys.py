from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

logger = logging.getLogger(__name__)

_IDENTITY_KEY_FILE = Path.home() / ".companion-link" / "identity_key.pem"


def _restrict_file_permissions(path: Path) -> None:
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{Path.home().name}:F"],
                check=True,
                capture_output=True,
            )
        else:
            path.chmod(0o600)
    except (OSError, subprocess.CalledProcessError) as exc:
        logger.warning("Could not restrict identity key file permissions: %s", exc)


def get_or_create_identity_key() -> X25519PrivateKey:
    if _IDENTITY_KEY_FILE.exists():
        try:
            data = _IDENTITY_KEY_FILE.read_bytes()
            key = serialization.load_pem_private_key(data, password=None)
            if isinstance(key, X25519PrivateKey):
                return key
            logger.warning("Identity key file has unexpected key type, regenerating")
        except (ValueError, TypeError) as exc:
            logger.warning("Corrupt identity key file, regenerating: %s", exc)

    key = X25519PrivateKey.generate()
    _IDENTITY_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    _IDENTITY_KEY_FILE.write_bytes(pem)
    _restrict_file_permissions(_IDENTITY_KEY_FILE)
    logger.info("Generated new device identity key")
    return key