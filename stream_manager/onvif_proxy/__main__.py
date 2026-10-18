"""Local and add-on entrypoint: python -m onvif_proxy"""

from __future__ import annotations

import asyncio
import logging
import sys

from .config import load_settings
from .server import serve


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logging.getLogger("onvif_proxy").info(
        "starting data %s ui %s onvif %s rtsp %s supervisor %s log_level %s",
        settings.data_dir,
        settings.ui_port,
        settings.onvif_port,
        settings.rtsp_port,
        settings.supervisor,
        settings.log_level,
    )
    try:
        asyncio.run(serve(settings))
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
