"""Tests for persistent device identity."""
from __future__ import annotations

import json

from companion_daemon import device_identity


def test_get_or_create_device_id_is_stable(tmp_path, monkeypatch):
    identity_file = tmp_path / "identity.json"
    monkeypatch.setattr(device_identity, "_IDENTITY_FILE", identity_file)

    first = device_identity.get_or_create_device_id()
    second = device_identity.get_or_create_device_id()

    assert first == second
    assert json.loads(identity_file.read_text())["device_id"] == first


def test_get_or_create_device_id_recovers_from_corrupt_file(tmp_path, monkeypatch):
    identity_file = tmp_path / "identity.json"
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    identity_file.write_text("not valid json")
    monkeypatch.setattr(device_identity, "_IDENTITY_FILE", identity_file)

    assert device_identity.get_or_create_device_id()