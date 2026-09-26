"""Entry point for the Companion Daemon."""
from __future__ import annotations

import asyncio
import logging
import signal

from companion_daemon.discovery import DiscoveryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass  # SIGTERM handler unsupported on Windows; Ctrl+C still works

    async with DiscoveryService() as discovery:
        await discovery.start_advertising()
        logger.info("Companion Daemon running. Press Ctrl+C to stop.")
        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            logger.info("Shutting down...")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()