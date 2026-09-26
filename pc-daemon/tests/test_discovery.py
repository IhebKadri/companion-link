from __future__ import annotations

import pytest
from zeroconf import Error as ZeroconfError

from companion_daemon.config import DiscoveryConfig
from companion_daemon.discovery import DiscoveryService, ServiceRegistrationError


class FakeZeroconfClient:
    def __init__(self, fail_on_register: bool = False) -> None:
        self.registered: list[object] = []
        self.unregistered: list[object] = []
        self._fail_on_register = fail_on_register

    async def async_register_service(self, info: object) -> None:
        if self._fail_on_register:
            raise ZeroconfError("simulated registration failure")
        self.registered.append(info)

    async def async_unregister_service(self, info: object) -> None:
        self.unregistered.append(info)

    async def async_close(self) -> None:
        pass


@pytest.fixture
def config() -> DiscoveryConfig:
    return DiscoveryConfig(service_type="_companionlink._tcp.local.", service_port=51820)


@pytest.mark.asyncio
async def test_start_advertising_registers_service(config):
    client = FakeZeroconfClient()
    async with DiscoveryService(config, client) as service:
        ad = await service.start_advertising(device_name="test-pc")

    assert ad.device_name == "test-pc"
    assert ad.port == 51820
    assert len(client.registered) == 1
    assert len(client.unregistered) == 1


@pytest.mark.asyncio
async def test_start_advertising_raises_on_registration_failure(config):
    client = FakeZeroconfClient(fail_on_register=True)
    async with DiscoveryService(config, client) as service:
        with pytest.raises(ServiceRegistrationError):
            await service.start_advertising()