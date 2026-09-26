from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name}={raw!r} is not a valid integer") from None


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class DiscoveryConfig:
    service_type: str
    service_port: int

    @classmethod
    def from_env(cls) -> "DiscoveryConfig":
        return cls(
            service_type=_env_str("COMPANION_SERVICE_TYPE", "_companionlink._tcp.local."),
            service_port=_env_int("COMPANION_SERVICE_PORT", 51820),
        )


@dataclass(frozen=True)
class LoggingConfig:
    level: str

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        return cls(level=_env_str("COMPANION_LOG_LEVEL", "INFO").upper())