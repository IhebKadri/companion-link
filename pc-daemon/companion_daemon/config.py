"""Central configuration for the Companion Daemon."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryConfig:
    """Configuration for mDNS/zeroconf service advertisement."""

    service_type: str = "_companionlink._tcp.local."
    service_port: int = 51820


DEFAULT_DISCOVERY_CONFIG = DiscoveryConfig()