from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = logging.getLogger(__name__)

PAIRING_CODE_LENGTH = 6
PAIRING_CODE_VALIDITY_SECONDS = 300  


def generate_pairing_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(PAIRING_CODE_LENGTH))


@dataclass
class PairingSession:
    code: str
    created_at: float = field(default_factory=time.monotonic)
    private_key: X25519PrivateKey = field(default_factory=X25519PrivateKey.generate)

    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > PAIRING_CODE_VALIDITY_SECONDS

    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )


class PairingError(RuntimeError):
    """Raised when a pairing attempt fails (wrong code, expired, bad key)."""


@dataclass(frozen=True)
class PairingResult:
    shared_key: bytes
    peer_public_key_bytes: bytes


def complete_pairing(
    session: PairingSession, submitted_code: str, peer_public_key_bytes: bytes
) -> PairingResult:

    if session.is_expired():
        raise PairingError("Pairing code has expired")

    if not secrets.compare_digest(session.code, submitted_code):
        raise PairingError("Incorrect pairing code")

    try:
        peer_public_key = X25519PublicKey.from_public_bytes(peer_public_key_bytes)
    except ValueError as exc:
        raise PairingError(f"Invalid peer public key: {exc}") from exc

    raw_shared_secret = session.private_key.exchange(peer_public_key)

    shared_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"companion-link-pairing-v1",
    ).derive(raw_shared_secret)

    return PairingResult(shared_key=shared_key, peer_public_key_bytes=peer_public_key_bytes)