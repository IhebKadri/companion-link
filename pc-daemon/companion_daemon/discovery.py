"""Local network discovery (mDNS/zeroconf) for Companion Link.

Advertises this PC as a discoverable endpoint on the local network so the
mobile app can find it. Discovery alone establishes NO trust — anyone on
the same network can see this advertisement. Pairing (Step 3) is required
before any sensitive channel opens, and the advertisement below carries no
secrets, only a public device_id and display name.
"""
from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from companion_daemon.config import DEFAULT_DISCOVERY_CONFIG, DiscoveryConfig
from companion_daemon.device_identity import get_or_create_device_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceAdvertisement:
    """Public metadata broadcast about this device. Contains no secrets."""

    device_id: str
    device_name: str
    port: int


def _get_local_ip() -> str:
    """Best-effort LAN IP discovery via a connectionless UDP 'connect'."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        logger.warning("Could not determine LAN IP, falling back to loopback")
        return "127.0.0.1"
    finally:
        sock.close()


class DiscoveryService:
    """Advertises this PC daemon on the local network via mDNS/zeroconf.

    Usage:
        async with DiscoveryService() as service:
            await service.start_advertising()
    """

    def __init__(self, config: DiscoveryConfig = DEFAULT_DISCOVERY_CONFIG) -> None:
        self._config = config
        self._aiozc: AsyncZeroconf | None = None
        self._service_info: AsyncServiceInfo | None = None
        self._device_id = get_or_create_device_id()

    async def __aenter__(self) -> "DiscoveryService":
        self._aiozc = AsyncZeroconf()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.stop_advertising()
        if self._aiozc is not None:
            await self._aiozc.async_close()

    async def start_advertising(self, device_name: str | None = None) -> DeviceAdvertisement:
        """Register this PC as a discoverable service on the local network."""
        if self._aiozc is None:
            raise RuntimeError("DiscoveryService must be used as an async context manager")

        hostname = socket.gethostname()
        resolved_name = device_name or hostname
        local_ip = _get_local_ip()

        info = AsyncServiceInfo(
            type_=self._config.service_type,
            name=f"{self._device_id}.{self._config.service_type}",
            addresses=[socket.inet_aton(local_ip)],
            port=self._config.service_port,
            properties={
                "device_id": self._device_id,
                "device_name": resolved_name,
                "protocol_version": "1",  # lets future clients handle upgrades gracefully
            },
            server=f"{hostname}.local.",
        )

        await self._aiozc.async_register_service(info)
        self._service_info = info
        logger.info(
            "Advertising as %r (%s) on %s:%d",
            resolved_name, self._device_id, local_ip, self._config.service_port,
        )
        return DeviceAdvertisement(
            device_id=self._device_id, device_name=resolved_name, port=self._config.service_port,
        )

    async def stop_advertising(self) -> None:
        """Unregister this device's mDNS service, if currently advertising."""
        if self._aiozc is not None and self._service_info is not None:
            await self._aiozc.async_unregister_service(self._service_info)
            logger.info("Stopped advertising")
            self._service_info = None