from __future__ import annotations

import logging
import threading
import webbrowser

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

WEB_UI_URL = "http://127.0.0.1:8765"


def _create_icon_image() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=(63, 81, 181, 255))
    return image


def _open_web_ui(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    webbrowser.open(WEB_UI_URL)


def _quit(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    icon.stop()


class TrayIcon:
    def __init__(self) -> None:
        self._icon = pystray.Icon(
            "companion_link",
            icon=_create_icon_image(),
            title="Companion Link",
            menu=pystray.Menu(
                pystray.MenuItem("Open Companion Link", _open_web_ui, default=True),
                pystray.MenuItem("Quit", _quit),
            ),
        )
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        logger.info("System tray icon started")

    def stop(self) -> None:
        self._icon.stop()