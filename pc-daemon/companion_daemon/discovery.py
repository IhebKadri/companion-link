from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import Protocol

from zeroconf import Error as ZeroconfError
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from companion_daemon.config import DiscoveryConfig
from companion_daemon.device_identity import get_or_create_device_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeviceAdvertisement:
    device_id: str
    device_name: str
    port: int


class ZeroconfClient(Protocol):
    async def async_register_service(self, info: AsyncServiceInfo) -> None: ...
    async def async_unregister_service(self, info: AsyncServiceInfo) -> None: ...
    async def async_close(self) -> None: ...


class AsyncZeroconfAdapter:
    def __init__(self, zeroconf: AsyncZeroconf) -> None:
        self._zeroconf = zeroconf

    async def async_register_service(self, info: AsyncServiceInfo) -> None:
        await self._zeroconf.async_register_service(info)

    async def async_unregister_service(self, info: AsyncServiceInfo) -> None:
        await self._zeroconf.async_unregister_service(info)

    async def async_close(self) -> None:
        await self._zeroconf.async_close()


class ServiceRegistrationError(RuntimeError):
    """Raised when this device could not be advertised on the network."""


def _get_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        address: str = sock.getsockname()[0]
        return address
    except OSError:
        logger.warning("Could not determine LAN IP, falling back to loopback")
        return "127.0.0.1"
    finally:
        sock.close()


class DiscoveryService:
    def __init__(self, config: DiscoveryConfig, zeroconf_client: ZeroconfClient) -> None:
        self._config = config
        self._client = zeroconf_client
        self._service_info: AsyncServiceInfo | None = None
        self._device_id = get_or_create_device_id()

    async def __aenter__(self) -> "DiscoveryService":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.stop_advertising()

    async def start_advertising(self, device_name: str | None = None) -> DeviceAdvertisement:
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
                "protocol_version": "1",
            },
            server=f"{hostname}.local.",
        )

        try:
            await self._client.async_register_service(info)
        except ZeroconfError as exc:
            raise ServiceRegistrationError(
                f"Failed to advertise on the local network: {exc}"
            ) from exc

        self._service_info = info
        logger.info(
            "Advertising as %r (%s) on %s:%d",
            resolved_name, self._device_id, local_ip, self._config.service_port,
        )
        return DeviceAdvertisement(
            device_id=self._device_id, device_name=resolved_name, port=self._config.service_port,
        )

    async def stop_advertising(self) -> None:
        if self._service_info is None:
            return
        try:
            await self._client.async_unregister_service(self._service_info)
            logger.info("Stopped advertising")
        except ZeroconfError as exc:
            logger.warning("Error while unregistering service (continuing shutdown): %s", exc)
        finally:
            self._service_info = None