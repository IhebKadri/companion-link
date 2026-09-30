from __future__ import annotations

import time

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from companion_daemon.pairing import (
    PairingError,
    PairingSession,
    complete_pairing,
    generate_pairing_code,
)


def test_generate_pairing_code_is_six_digits():
    code = generate_pairing_code()
    assert len(code) == 6
    assert code.isdigit()


def test_generate_pairing_code_is_random():
    codes = {generate_pairing_code() for _ in range(20)}
    assert len(codes) > 1 


def test_complete_pairing_succeeds_with_correct_code():
    session = PairingSession(code="123456")
    peer_key = X25519PrivateKey.generate()
    peer_public_bytes = peer_key.public_key().public_bytes_raw()

    result = complete_pairing(session, "123456", peer_public_bytes)

    assert len(result.shared_key) == 32
    assert result.peer_public_key_bytes == peer_public_bytes


def test_complete_pairing_derives_matching_key_on_both_sides():
    session = PairingSession(code="123456")
    peer_private_key = X25519PrivateKey.generate()
    peer_public_bytes = peer_private_key.public_key().public_bytes_raw()

    server_result = complete_pairing(session, "123456", peer_public_bytes)

    peer_shared_secret = peer_private_key.exchange(session.private_key.public_key())
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    peer_shared_key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"companion-link-pairing-v1"
    ).derive(peer_shared_secret)

    assert server_result.shared_key == peer_shared_key


def test_complete_pairing_rejects_wrong_code():
    session = PairingSession(code="123456")
    peer_public_bytes = X25519PrivateKey.generate().public_key().public_bytes_raw()

    with pytest.raises(PairingError, match="Incorrect"):
        complete_pairing(session, "000000", peer_public_bytes)


def test_complete_pairing_rejects_expired_session():
    session = PairingSession(code="123456", created_at=time.monotonic() - 999999)
    peer_public_bytes = X25519PrivateKey.generate().public_key().public_bytes_raw()

    with pytest.raises(PairingError, match="expired"):
        complete_pairing(session, "123456", peer_public_bytes)


def test_complete_pairing_rejects_malformed_public_key():
    session = PairingSession(code="123456")

    with pytest.raises(PairingError, match="Invalid peer public key"):
        complete_pairing(session, "123456", b"not-a-valid-key")