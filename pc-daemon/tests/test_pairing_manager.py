from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from companion_daemon.pairing import PairingError
from companion_daemon.pairing_manager import PairingManager
from companion_daemon.trusted_devices import TrustedDeviceStore


@pytest.fixture
def manager(tmp_path) -> PairingManager:
    identity_key = X25519PrivateKey.generate()
    store = TrustedDeviceStore(path=tmp_path / "trusted_devices.json")
    return PairingManager(identity_key, store)


@pytest.mark.asyncio
async def test_successful_pairing_stores_device(manager):
    start = await manager.start_session()
    peer_key = X25519PrivateKey.generate()

    await manager.handle_pair_request(
        submitted_code=start.code,
        peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
        device_name="My Phone",
    )

    device = manager.get_last_paired_device()
    assert device is not None
    assert device.device_name == "My Phone"


@pytest.mark.asyncio
async def test_pairing_fails_without_active_session(manager):
    peer_key = X25519PrivateKey.generate()
    with pytest.raises(PairingError, match="No pairing session"):
        await manager.handle_pair_request(
            submitted_code="123456",
            peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
            device_name="My Phone",
        )


@pytest.mark.asyncio
async def test_lockout_after_max_failed_attempts(manager):
    start = await manager.start_session()
    peer_key = X25519PrivateKey.generate()
    wrong_code = "000000" if start.code != "000000" else "111111"

    for _ in range(manager.MAX_FAILED_ATTEMPTS):
        with pytest.raises(PairingError, match="Incorrect"):
            await manager.handle_pair_request(
                submitted_code=wrong_code,
                peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
                device_name="Attacker",
            )

    with pytest.raises(PairingError, match="Too many failed attempts"):
        await manager.handle_pair_request(
            submitted_code=wrong_code,
            peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
            device_name="Attacker",
        )

    with pytest.raises(PairingError, match="No pairing session"):
        await manager.handle_pair_request(
            submitted_code=start.code,
            peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
            device_name="My Phone",
        )


@pytest.mark.asyncio
async def test_device_name_rejects_non_printable_content(manager):
    start = await manager.start_session()
    peer_key = X25519PrivateKey.generate()

    await manager.handle_pair_request(
        submitted_code=start.code,
        peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
        device_name="My\x00Phone\x07",  # non-printable control characters
    )

    device = manager.get_last_paired_device()
    assert device is not None
    assert device.device_name == "Unknown device"


@pytest.mark.asyncio
async def test_html_in_device_name_is_stored_as_is_but_escaped_at_render_time(manager):
    start = await manager.start_session()
    peer_key = X25519PrivateKey.generate()
    malicious_name = "<img src=x onerror=alert(1)>"

    await manager.handle_pair_request(
        submitted_code=start.code,
        peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
        device_name=malicious_name,
    )

    device = manager.get_last_paired_device()
    assert device is not None
    assert device.device_name == malicious_name  


@pytest.mark.asyncio
async def test_overlong_device_name_is_truncated(manager):
    start = await manager.start_session()
    peer_key = X25519PrivateKey.generate()

    await manager.handle_pair_request(
        submitted_code=start.code,
        peer_public_key_bytes=peer_key.public_key().public_bytes_raw(),
        device_name="A" * 200,
    )

    device = manager.get_last_paired_device()
    assert device is not None
    assert len(device.device_name) <= 64