from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_TRUSTED_DEVICES_FILE = Path.home() / ".companion-link" / "trusted_devices.json"


@dataclass(frozen=True)
class TrustedDevice:
    device_id: str
    device_name: str
    public_key_hex: str
    paired_at: float


class TrustedDeviceStore:
    def __init__(self, path: Path = _TRUSTED_DEVICES_FILE) -> None:
        self._path = path

    def load_all(self) -> list[TrustedDevice]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return [TrustedDevice(**entry) for entry in raw]
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Corrupt trusted_devices.json, treating as empty: %s", exc)
            return []

    def add(self, device: TrustedDevice) -> None:
        devices = [d for d in self.load_all() if d.device_id != device.device_id]
        devices.append(device)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([asdict(d) for d in devices], indent=2), encoding="utf-8"
        )
        logger.info("Trusted device saved: %s (%s)", device.device_name, device.device_id)

    def find_by_id(self, device_id: str) -> TrustedDevice | None:
        return next((d for d in self.load_all() if d.device_id == device_id), None)