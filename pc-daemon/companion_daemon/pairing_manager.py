from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from companion_daemon.pairing import (
    PairingError,
    PairingSession,
    complete_pairing,
    generate_pairing_code,
)
from companion_daemon.trusted_devices import TrustedDevice, TrustedDeviceStore


@dataclass(frozen=True)
class PairingStartResult:
    code: str
    expires_at: float


def _sanitize_device_name(device_name: str) -> str:
    cleaned = device_name.strip()[:64]
    if not cleaned or not all(c.isprintable() for c in cleaned):
        return "Unknown device"
    return cleaned


class PairingManager:
    MAX_FAILED_ATTEMPTS = 5

    def __init__(self, identity_key: X25519PrivateKey, store: TrustedDeviceStore) -> None:
        self._identity_key = identity_key
        self._store = store
        self._active_session: PairingSession | None = None
        self._failed_attempts = 0
        self._last_paired_device: TrustedDevice | None = None
        self._lock = asyncio.Lock()

    async def start_session(self) -> PairingStartResult:
        async with self._lock:
            code = generate_pairing_code()
            self._active_session = PairingSession(code=code, private_key=self._identity_key)
            self._failed_attempts = 0
            self._last_paired_device = None
            return PairingStartResult(
                code=code,
                expires_at=time.time() + 300,
            )

    async def handle_pair_request(
        self, submitted_code: str, peer_public_key_bytes: bytes, device_name: str
    ) -> bytes:
        async with self._lock:
            if self._active_session is None:
                raise PairingError("No pairing session is currently active")

            if self._failed_attempts >= self.MAX_FAILED_ATTEMPTS:
                self._active_session = None
                raise PairingError("Too many failed attempts — start a new pairing session")

            try:
                result = complete_pairing(
                    self._active_session, submitted_code, peer_public_key_bytes
                )
            except PairingError:
                self._failed_attempts += 1
                raise

            device = TrustedDevice(
                device_id=str(uuid.uuid4()),
                device_name=_sanitize_device_name(device_name),
                public_key_hex=result.peer_public_key_bytes.hex(),
                paired_at=time.time(),
            )
            self._store.add(device)
            self._last_paired_device = device
            self._active_session = None

            return self._identity_key.public_key().public_bytes_raw()

    def get_last_paired_device(self) -> TrustedDevice | None:
        return self._last_paired_device