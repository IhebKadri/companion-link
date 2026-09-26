from __future__ import annotations

import asyncio
import logging
import signal

from zeroconf.asyncio import AsyncZeroconf

from companion_daemon.config import DiscoveryConfig, LoggingConfig
from companion_daemon.discovery import (
    AsyncZeroconfAdapter,
    DiscoveryService,
    ServiceRegistrationError,
)

logger = logging.getLogger(__name__)


def _configure_logging(config: LoggingConfig) -> None:
    logging.basicConfig(
        level=getattr(logging, config.level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


async def run() -> None:
    _configure_logging(LoggingConfig.from_env())
    discovery_config = DiscoveryConfig.from_env()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    zeroconf = AsyncZeroconf()
    zeroconf_client = AsyncZeroconfAdapter(zeroconf)
    try:
        async with DiscoveryService(discovery_config, zeroconf_client) as discovery:
            try:
                await discovery.start_advertising()
            except ServiceRegistrationError:
                logger.exception("Could not start advertising — is the port already in use?")
                return

            logger.info("Companion Daemon running. Press Ctrl+C to stop.")
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                pass
            finally:
                logger.info("Shutting down...")
    finally:
        await zeroconf.async_close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()