from __future__ import annotations

import asyncio
import logging
import signal

import uvicorn
from zeroconf.asyncio import AsyncZeroconf

from companion_daemon.config import DiscoveryConfig, LoggingConfig
from companion_daemon.discovery import (
    AsyncZeroconfAdapter,
    DiscoveryService,
    ServiceRegistrationError,
)
from companion_daemon.tray import TrayIcon
from companion_daemon.web_ui import app as web_app

logger = logging.getLogger(__name__)

WEB_UI_HOST = "127.0.0.1"
WEB_UI_PORT = 8765


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
    tray: TrayIcon | None = None
    web_server: uvicorn.Server | None = None
    web_server_task: asyncio.Task[None] | None = None

    try:
        async with DiscoveryService(discovery_config, zeroconf_client) as discovery:
            try:
                await discovery.start_advertising()
            except ServiceRegistrationError:
                logger.exception("Could not start advertising — is the port already in use?")
                return

            tray = TrayIcon()
            tray.start()

            web_server_config = uvicorn.Config(
                web_app, host=WEB_UI_HOST, port=WEB_UI_PORT, log_level="warning"
            )
            web_server = uvicorn.Server(web_server_config)
            web_server_task = asyncio.create_task(web_server.serve())

            logger.info(
                "Companion Daemon running. Web UI at http://%s:%d. Press Ctrl+C to stop.",
                WEB_UI_HOST, WEB_UI_PORT,
            )
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                pass
            finally:
                logger.info("Shutting down...")
    finally:
        if web_server is not None:
            web_server.should_exit = True
        if web_server_task is not None:
            await web_server_task
        if tray is not None:
            tray.stop()
        await zeroconf.async_close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()