from __future__ import annotations

import asyncio
import json
import logging

from companion_daemon.pairing import PairingError
from companion_daemon.pairing_manager import PairingManager

logger = logging.getLogger(__name__)

PAIRING_SERVER_PORT = 51821


class PairingServer:
    MAX_CONCURRENT_CONNECTIONS = 10
    MAX_LINE_BYTES = 8192

    def __init__(self, manager: PairingManager, port: int = PAIRING_SERVER_PORT) -> None:
        self._manager = manager
        self._port = port
        self._server: asyncio.AbstractServer | None = None
        self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_CONNECTIONS)

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, host="0.0.0.0", port=self._port
        )
        logger.info("Pairing server listening on port %d", self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        async with self._semaphore:
            peer = writer.get_extra_info("peername")
            try:
                line = await asyncio.wait_for(
                    reader.readuntil(b"\n"), timeout=10.0
                )
                if len(line) > self.MAX_LINE_BYTES:
                    await self._send_error(writer, "Request too large")
                    return

                request = json.loads(line.decode("utf-8"))

                if request.get("type") != "pair_request":
                    await self._send_error(writer, "Unexpected message type")
                    return

                try:
                    public_key_bytes = bytes.fromhex(request["public_key"])
                except (ValueError, KeyError):
                    await self._send_error(writer, "Malformed public_key")
                    return

                own_public_key = await self._manager.handle_pair_request(
                    submitted_code=request.get("code", ""),
                    peer_public_key_bytes=public_key_bytes,
                    device_name=request.get("device_name", "Unknown device"),
                )

                response = {
                    "type": "pair_response",
                    "status": "ok",
                    "public_key": own_public_key.hex(),
                }
                writer.write((json.dumps(response) + "\n").encode("utf-8"))
                await writer.drain()
                logger.info("Pairing succeeded with %s", peer)

            except PairingError as exc:
                await self._send_error(writer, str(exc))
            except asyncio.LimitOverrunError:
                await self._send_error(writer, "Request too large")
            except (asyncio.TimeoutError, asyncio.IncompleteReadError,
                    json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("Malformed pairing request from %s: %s", peer, exc)
                await self._send_error(writer, "Malformed request")
            finally:
                writer.close()
                await writer.wait_closed()

    async def _send_error(self, writer: asyncio.StreamWriter, message: str) -> None:
        response = {"type": "pair_response", "status": "error", "message": message}
        writer.write((json.dumps(response) + "\n").encode("utf-8"))
        await writer.drain()